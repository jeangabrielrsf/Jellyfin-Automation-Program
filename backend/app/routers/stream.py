"""Streaming router — playback contract and direct file streaming."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.models.download import Download
from app.services.stream_service import StreamService

playback_router = APIRouter(prefix="/api/downloads", tags=["downloads"])
stream_router = APIRouter(prefix="/api/stream", tags=["stream"])
logger = get_logger(__name__)


def _get_download(download_id: int, db: Session) -> Download:
    """Fetch a download or raise HTTP 404."""
    download = db.query(Download).filter(Download.id == download_id).first()
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    return download


def _file_url(download_id: int, entry: dict) -> str:
    """Build the stream URL for a resolved file entry."""
    url = f"/api/stream/{download_id}/playlist.m3u8"
    if entry["episode"] is not None:
        url += f"?episode={entry['episode']}"
    return url


@playback_router.get("/{download_id}/playback")
def get_playback(download_id: int, db: Session = Depends(get_db)):
    """Return the playable files for a download (direct mode).

    Movies resolve to a single file; series/anime packs list every episode
    of the download's season.
    """
    download = _get_download(download_id, db)
    service = StreamService()
    try:
        files = service.resolve_files(download)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "mode": "direct",
        "files": [
            {
                "episode": entry["episode"],
                "title": entry["title"],
                "url": _file_url(download_id, entry),
            }
            for entry in files
        ],
    }


@stream_router.get("/{download_id}/playlist.m3u8")
def stream_playlist(
    download_id: int,
    episode: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Serve the resolved video file directly.

    Starlette's FileResponse handles Range requests (HTTP 206), which gives
    browsers seek support. Transcoding to HLS is added in a later stage.
    """
    download = _get_download(download_id, db)

    service = StreamService()
    try:
        path = service.resolve_file(download, episode)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    logger.info("Streaming file", download_id=download_id, episode=episode, path=str(path))
    return FileResponse(path)
