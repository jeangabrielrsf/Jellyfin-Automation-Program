"""Streaming router — playback contract, direct streaming and HLS transcode."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import StreamLimitError, StreamTranscodeError
from app.logging_config import get_logger
from app.models.download import Download
from app.services.stream_service import StreamService, stream_manager

playback_router = APIRouter(prefix="/api/downloads", tags=["downloads"])
stream_router = APIRouter(prefix="/api/stream", tags=["stream"])
logger = get_logger(__name__)

HLS_MEDIA_TYPE = "application/vnd.apple.mpegurl"
SEGMENT_MEDIA_TYPE = "video/mp2t"


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
    """Return the playable files for a download and the playback modes.

    Overall mode is "transcode" when any file needs HLS transcoding; each
    file also carries its own mode so the player can pick the right source
    (direct file vs HLS) even inside a mixed pack.
    """
    download = _get_download(download_id, db)
    service = StreamService()
    try:
        files = service.resolve_files(download)
        modes = [service.decide_mode(entry["path"]) for entry in files]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "mode": "transcode" if "transcode" in modes else "direct",
        "files": [
            {
                "episode": entry["episode"],
                "title": entry["title"],
                "mode": mode,
                "url": _file_url(download_id, entry),
            }
            for entry, mode in zip(files, modes)
        ],
    }


@stream_router.get("/{download_id}/playlist.m3u8")
def stream_playlist(
    download_id: int,
    episode: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Serve the stream for a download.

    Files the browser can play directly are served as-is (Starlette's
    FileResponse handles Range requests for seeking). Everything else is
    transcoded on-demand: the first request lazily creates an HLS session
    (ffmpeg + segments directory), later requests reuse it.
    """
    download = _get_download(download_id, db)
    service = StreamService()
    try:
        path = service.resolve_file(download, episode)
        mode = service.decide_mode(path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if mode == "direct":
        logger.info("Streaming file directly", download_id=download_id, episode=episode, path=str(path))
        return FileResponse(path)

    try:
        session = stream_manager.get_or_create(download_id, episode, path, db=db)
    except StreamLimitError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except StreamTranscodeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    logger.info("Streaming HLS playlist", download_id=download_id, episode=episode)
    return FileResponse(session.playlist_path(), media_type=HLS_MEDIA_TYPE)


@stream_router.get("/{download_id}/{filename}")
def stream_segment(download_id: int, filename: str):
    """Serve an HLS segment from the download's active transcode session.

    ffmpeg writes segment references relative to the playlist, so the
    browser requests /api/stream/{download_id}/segment_00000.ts. This route
    is registered after playlist.m3u8, which wins for that exact path.
    """
    session = stream_manager.find_by_download(download_id)
    if session is None:
        raise HTTPException(
            status_code=404, detail="Sessão de stream expirada ou inexistente"
        )
    segment = session.segment_path(filename)
    if segment is None or not segment.exists():
        raise HTTPException(status_code=404, detail="Segmento não encontrado")
    return FileResponse(segment, media_type=SEGMENT_MEDIA_TYPE)
