"""Main FastAPI application."""
import asyncio
from contextlib import asynccontextmanager
import json
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.logging_config import setup_logging
from app.routers import search, downloads, settings, logs, filesystem
from app.services.download_worker import DownloadWorker

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Handle application startup and shutdown events."""
    logger.info("Starting up Jellyfin Automation")
    await asyncio.to_thread(init_db)
    
    # Start DownloadWorker background task
    download_worker = DownloadWorker()
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

app.include_router(search.router)
app.include_router(downloads.router)
app.include_router(settings.router)
app.include_router(logs.router)
app.include_router(filesystem.router)


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
