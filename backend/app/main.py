"""Main FastAPI application."""
import asyncio
from contextlib import asynccontextmanager
import json
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import init_db, SessionLocal
from app.logging_config import setup_logging
from app.routers import search, downloads, settings, logs, filesystem, discover
from app.services.download_worker import DownloadWorker
from app.exceptions import ConfigurationError
from fastapi.responses import JSONResponse

logger = setup_logging()


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and track a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected", total=len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from tracking."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected", total=len(self.active_connections))

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to all connected WebSocket clients."""
        message_json = json.dumps(message)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as exc:
                logger.warning("Failed to send WebSocket message", error=str(exc))
                disconnected.append(connection)

        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


manager = ConnectionManager()


def _seed_config_from_env(db) -> None:
    """Populate DB with .env values if keys are missing."""
    from app.config import get_settings
    from app.models.settings import Setting

    env = get_settings()
    critical_keys = [
        "tmdb_api_key", "omdb_api_key",
        "jackett_url", "jackett_api_key", "jackett_timeout",
        "qbittorrent_host", "qbittorrent_username", "qbittorrent_password",
        "jellyfin_url", "jellyfin_api_key",
        "movies_path", "series_path", "animes_path",
        "default_quality", "default_language",
    ]
    seeded = 0
    for key in critical_keys:
        existing = db.query(Setting).filter(Setting.key == key).first()
        if not existing:
            env_value = getattr(env, key, None)
            if env_value:
                db.add(Setting(key=key, value=env_value))
                seeded += 1
    if seeded:
        db.commit()
        logger.info("Seeded configuration from .env to DB", count=seeded)


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Handle application startup and shutdown events."""
    logger.info("Starting up Jellyfin Automation")
    await asyncio.to_thread(init_db)

    # Seed config from .env if DB is empty
    db = SessionLocal()
    try:
        _seed_config_from_env(db)
    finally:
        db.close()

    # Start DownloadWorker background task
    download_worker = DownloadWorker(broadcast_callback=manager.broadcast)
    worker_task = asyncio.create_task(download_worker.start())
    app.state.download_worker = download_worker
    app.state.worker_task = worker_task
    
    yield
    
    # Shutdown
    logger.info("Shutting down Jellyfin Automation")
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Jellyfin Automation",
    description="Automate content search, download and organization for Jellyfin",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(request, exc: ConfigurationError):
    return JSONResponse(
        status_code=500,
        content={
            "error": "configuration_error",
            "key": exc.key,
            "message": exc.message,
        },
    )


app.include_router(search.router)
app.include_router(downloads.router)
app.include_router(settings.router)
app.include_router(logs.router)
app.include_router(filesystem.router)
app.include_router(discover.router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle WebSocket client connections and messages."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if isinstance(message, dict) and message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                logger.debug("Received malformed JSON via WebSocket")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        manager.disconnect(websocket)


@app.get("/health")
def health_check() -> dict:
    """Return application health status."""
    return {"status": "healthy", "version": "1.0.0"}


try:
    app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")
except RuntimeError:
    logger.warning("Frontend dist directory not found; running without static file mount.")
