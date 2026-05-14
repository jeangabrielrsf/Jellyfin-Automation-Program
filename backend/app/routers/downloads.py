"""Downloads router."""
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.download import Download, DownloadStatus, ContentType
from app.services.qbittorrent_service import QBittorrentService
from app.services.path_resolver import PathResolver
from app.services.path_converter import is_wsl2, wsl_to_windows
from app.logging_config import get_logger
from pydantic import BaseModel

router = APIRouter(prefix="/api/downloads", tags=["downloads"])
logger = get_logger(__name__)

class DownloadCreate(BaseModel):
    tmdb_id: int
    title: str
    media_type: ContentType
    torrent_name: str
    magnet_link: Optional[str] = None
    download_url: Optional[str] = None
    quality: str = "1080p"
    language_preference: str = "legendado"
    indexer_used: Optional[str] = None
    size: Optional[str] = None
    seeds: Optional[int] = None
    peers: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    year: Optional[int] = None


def _extract_hash_from_magnet(magnet_link: str) -> Optional[str]:
    """Extract btih hash from a magnet link."""
    match = re.search(r"xt=urn:btih:([a-fA-F0-9]{40})", magnet_link)
    if match:
        return match.group(1).lower()
    return None


@router.get("/")
def list_downloads(
    status: Optional[DownloadStatus] = None,
    db: Session = Depends(get_db)
):
    """List all downloads with optional status filter."""
    query = db.query(Download)
    if status:
        query = query.filter(Download.status == status)
    return query.order_by(Download.created_at.desc()).all()

@router.post("/")
async def create_download(
    download: DownloadCreate,
    db: Session = Depends(get_db)
):
    """Create a new download record and add torrent to qBittorrent."""
    # Determine which link to use
    magnet_link = download.magnet_link
    download_url = download.download_url
    
    # If no magnet link but has download_url, use download_url as magnet_link for storage
    link_to_store = magnet_link if magnet_link else download_url
    
    # Resolve save path using PathResolver
    path_resolver = PathResolver()
    season = download.season
    episode = download.episode
    if season is None and download.torrent_name:
        extracted = path_resolver.extract_season_episode(download.torrent_name)
        season = extracted.get("season")
        episode = extracted.get("episode")
    
    try:
        save_path = path_resolver.resolve_path(
            title=download.title,
            media_type=download.media_type.value,
            torrent_name=download.torrent_name,
            season=season,
            episode=episode,
            year=download.year,
            quality=download.quality,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to create download directory: {str(e)}")
    
    db_download = Download(
        tmdb_id=download.tmdb_id,
        title=download.title,
        type=download.media_type,
        torrent_name=download.torrent_name,
        magnet_link=link_to_store,
        quality=download.quality,
        language_preference=download.language_preference,
        status=DownloadStatus.PENDING,
        indexer_used=download.indexer_used,
        size=download.size,
        seeds=download.seeds,
        peers=download.peers,
        season=season,
        episode=episode,
        source_folder=save_path
    )
    try:
        db.add(db_download)
        db.commit()
        db.refresh(db_download)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")
    
    # Convert save_path for qBittorrent if running in WSL2
    # WSL2 paths (/mnt/d/...) need to be converted to Windows format (D:\...) for qBittorrent on Windows
    qb_save_path = save_path
    if is_wsl2():
        qb_save_path = wsl_to_windows(save_path)
        if qb_save_path != save_path:
            logger.info("Converted save path for qBittorrent", original=save_path, converted=qb_save_path)

    # Try to add torrent to qBittorrent immediately
    logger.info("Creating download", magnet_link=magnet_link, download_url=download_url, torrent_name=download.torrent_name)
    service = QBittorrentService(db=db)
    try:
        ...
        # Tag única para identificar o torrent no qBittorrent
        tag = f"jellyfin-auto-{db_download.id}"
        success = await service.add_torrent(
            magnet_link=magnet_link,
            download_url=download_url,
            category=download.media_type.value,
            torrent_name=download.torrent_name,
            save_path=qb_save_path,
            tags=tag
        )
        if success:
            # Try to extract hash from magnet link
            hash_source = magnet_link if magnet_link else download_url
            torrent_hash = _extract_hash_from_magnet(hash_source) if hash_source and hash_source.startswith("magnet:") else None
            if not torrent_hash:
                # Se não for magnet, buscar hash via tag no qBittorrent
                try:
                    torrents = await service.get_torrents_by_tag(tag)
                    if torrents:
                        torrent_hash = torrents[0].get("hash")
                        logger.info("Hash obtido via tag", download_id=db_download.id, hash=torrent_hash)
                except Exception as e:
                    logger.warning("Falha ao obter hash via tag", download_id=db_download.id, error=str(e))
            if torrent_hash:
                db_download.torrent_hash = torrent_hash
            db_download.status = DownloadStatus.DOWNLOADING
            try:
                db.commit()
            except Exception:
                db.rollback()
                # Torrent was already added to qBittorrent - update anyway without unique hash
                db_download.torrent_hash = None
                db_download.status = DownloadStatus.DOWNLOADING
                db.commit()
            db.refresh(db_download)
            logger.info("Torrent added to qBittorrent", download_id=db_download.id, hash=db_download.torrent_hash)
            return db_download
        else:
            db_download.status = DownloadStatus.FAILED
            db_download.error_message = "Failed to add torrent to qBittorrent"
            db.commit()
            db.refresh(db_download)
            logger.error("Failed to add torrent to qBittorrent", download_id=db_download.id)
            raise HTTPException(status_code=502, detail="Falha ao adicionar torrent ao qBittorrent. Verifique se o qBittorrent está em execução.")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        db_download.status = DownloadStatus.FAILED
        db_download.error_message = str(e)
        db.commit()
        db.refresh(db_download)
        logger.error("Exception while adding torrent to qBittorrent", error=str(e), download_id=db_download.id)
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com qBittorrent: {str(e)}")
    finally:
        await service.close()

@router.get("/{download_id}")
def get_download(download_id: int, db: Session = Depends(get_db)):
    """Get download by ID."""
    download = db.query(Download).filter(Download.id == download_id).first()
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    return download

@router.delete("/{download_id}")
def cancel_download(download_id: int, db: Session = Depends(get_db)):
    """Cancel a download."""
    download = db.query(Download).filter(Download.id == download_id).first()
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    
    try:
        download.status = DownloadStatus.CANCELLED
        db.commit()
        return {"message": "Download cancelled"}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")

@router.post("/{download_id}/pause")
async def pause_download(download_id: int, db: Session = Depends(get_db)):
    """Pause a download in qBittorrent."""
    download = db.query(Download).filter(Download.id == download_id).first()
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    
    if not download.torrent_hash:
        raise HTTPException(status_code=400, detail="No torrent hash associated with this download")
    
    from app.services.qbittorrent_service import QBittorrentService
    service = QBittorrentService(db=db)
    success = await service.pause_torrent(download.torrent_hash)
    await service.close()
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to pause torrent in qBittorrent")
    
    return {"message": "Download paused"}

@router.post("/{download_id}/resume")
async def resume_download(download_id: int, db: Session = Depends(get_db)):
    """Resume a download in qBittorrent."""
    download = db.query(Download).filter(Download.id == download_id).first()
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    
    if not download.torrent_hash:
        raise HTTPException(status_code=400, detail="No torrent hash associated with this download")
    
    from app.services.qbittorrent_service import QBittorrentService
    service = QBittorrentService(db=db)
    success = await service.resume_torrent(download.torrent_hash)
    await service.close()
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to resume torrent in qBittorrent")
    
    return {"message": "Download resumed"}

@router.delete("/")
async def delete_all_downloads(db: Session = Depends(get_db)):
    """Delete all completed, failed, and cancelled downloads. Skips active downloads.
    Removes torrents from qBittorrent but keeps files on disk."""
    
    # Count active downloads that will be skipped
    active_count = db.query(Download).filter(
        Download.status.in_([DownloadStatus.PENDING, DownloadStatus.DOWNLOADING])
    ).count()
    
    # Get all removable downloads
    removable = db.query(Download).filter(
        Download.status.not_in([DownloadStatus.PENDING, DownloadStatus.DOWNLOADING])
    ).all()
    
    # Remove torrents from qBittorrent (keep files)
    service = QBittorrentService(db=db)
    for download in removable:
        if download.torrent_hash:
            try:
                await service.delete_torrent(download.torrent_hash, delete_files=False)
            except Exception:
                logger.warning(
                    "Failed to remove torrent from qBittorrent",
                    download_id=download.id,
                    torrent_hash=download.torrent_hash,
                )
    await service.close()
    
    # Delete all removable records in a single query
    deleted_count = db.query(Download).filter(
        Download.status.not_in([DownloadStatus.PENDING, DownloadStatus.DOWNLOADING])
    ).delete(synchronize_session=False)
    
    db.commit()
    
    logger.info("Cleared downloads", deleted=deleted_count, skipped=active_count)
    return {"deleted": deleted_count, "skipped": active_count}
