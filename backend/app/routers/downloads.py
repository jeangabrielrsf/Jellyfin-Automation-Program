"""Downloads router."""
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.download import Download, DownloadStatus, ContentType
from app.services.qbittorrent_service import QBittorrentService
from app.services.path_resolver import PathResolver
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


class ClearDownloadItem(BaseModel):
    id: int
    delete_files: bool = False


class ClearDownloadsRequest(BaseModel):
    downloads: list[ClearDownloadItem]


@router.get("/")
def list_downloads(
    status: Optional[DownloadStatus] = None,
    tmdb_id: Optional[int] = Query(None, description="Filter by TMDB media id"),
    db: Session = Depends(get_db)
):
    """List all downloads with optional status filter. Excludes CLEARED by default."""
    query = db.query(Download)
    if status:
        query = query.filter(Download.status == status)
    else:
        query = query.filter(Download.status != DownloadStatus.CLEARED)
    if tmdb_id is not None:
        query = query.filter(Download.tmdb_id == tmdb_id)
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
    
    # qBittorrent runs in Docker (Linux container), so WSL paths (/mnt/d/...)
    # work as-is — no Windows path conversion needed.
    qb_save_path = save_path

    # Try to add torrent to qBittorrent immediately
    logger.info("Creating download", magnet_link=magnet_link, download_url=download_url, torrent_name=download.torrent_name)
    service = QBittorrentService(db=db)
    try:
        ...
        # Tag única para identificar o torrent no qBittorrent
        tag = f"jellyfin-auto-{db_download.id}"
        success, already_exists = await service.add_torrent(
            magnet_link=magnet_link,
            download_url=download_url,
            category=download.media_type.value,
            torrent_name=download.torrent_name,
            save_path=qb_save_path,
            tags=tag
        )
        if success:
            hash_source = magnet_link if magnet_link else download_url
            torrent_hash = Download.extract_hash(hash_source) if hash_source and hash_source.startswith("magnet:") else None
            if not torrent_hash:
                try:
                    torrents = await service.get_torrents_by_tag(tag)
                    if torrents:
                        torrent_hash = torrents[0].get("hash")
                        logger.info("Hash obtido via tag", download_id=db_download.id, hash=torrent_hash)
                    else:
                        logger.warning(
                            "Torrent não encontrado via tag após upload; hash ficará NULL "
                            "até o DownloadWorker fazer o backfill por source_folder",
                            download_id=db_download.id,
                            tag=tag,
                        )
                except Exception as e:
                    logger.warning("Falha ao obter hash via tag", download_id=db_download.id, error=str(e))
            if torrent_hash:
                db_download.torrent_hash = torrent_hash
            db_download.transition_to(DownloadStatus.DOWNLOADING)
            try:
                db.commit()
            except Exception:
                db.rollback()
                db_download.torrent_hash = None
                db_download.transition_to(DownloadStatus.DOWNLOADING)
                db.commit()
            db.refresh(db_download)
            logger.info("Torrent added to qBittorrent", download_id=db_download.id, hash=db_download.torrent_hash, already_exists=already_exists)
            
            response = db_download.to_dict()
            response["already_exists"] = already_exists
            return response
        else:
            db_download.transition_to(DownloadStatus.FAILED)
            db_download.error_message = "Failed to add torrent to qBittorrent"
            db.commit()
            db.refresh(db_download)
            logger.error("Failed to add torrent to qBittorrent", download_id=db_download.id)
            raise HTTPException(status_code=502, detail="Falha ao adicionar torrent ao qBittorrent. Verifique se o qBittorrent está em execução.")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        db_download.transition_to(DownloadStatus.FAILED)
        db_download.error_message = str(e)
        db.commit()
        db.refresh(db_download)
        logger.error("Exception while adding torrent to qBittorrent", error=str(e), download_id=db_download.id)
        raise HTTPException(status_code=502, detail=f"Erro ao comunicar com qBittorrent: {str(e)}")
    finally:
        await service.close()

@router.get("/clearable")
def list_clearable_downloads(db: Session = Depends(get_db)):
    """List all downloads that can be cleared (completed, failed, cancelled, organized)."""
    clearable_statuses = [
        DownloadStatus.COMPLETED,
        DownloadStatus.FAILED,
        DownloadStatus.CANCELLED,
        DownloadStatus.ORGANIZED,
    ]
    return db.query(Download).filter(
        Download.status.in_(clearable_statuses)
    ).order_by(Download.created_at.desc()).all()

@router.get("/{download_id}")
def get_download(download_id: int, db: Session = Depends(get_db)):
    """Get download by ID."""
    download = db.query(Download).filter(Download.id == download_id).first()
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    return download

@router.delete("/{download_id}")
async def cancel_download(
    download_id: int,
    delete_files: bool = Query(False, description="Whether to delete downloaded files from disk"),
    db: Session = Depends(get_db)
):
    """Cancel a download or clear a finished download from the list. Optionally delete files from disk."""
    download = db.query(Download).filter(Download.id == download_id).first()
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    
    is_active = download.status in {DownloadStatus.PENDING, DownloadStatus.DOWNLOADING}
    
    if is_active and download.torrent_hash:
        service = QBittorrentService(db=db)
        try:
            await service.delete_torrent(download.torrent_hash, delete_files=False)
        except Exception as e:
            logger.warning("Failed to remove torrent from qBittorrent", download_id=download_id, error=str(e))
        finally:
            await service.close()
    
    if delete_files:
        folders_to_check = [download.source_folder, download.destination_folder]
        for folder in folders_to_check:
            if folder:
                try:
                    path = Path(folder)
                    if path.exists() and path.is_dir():
                        shutil.rmtree(path)
                        logger.info("Deleted download folder", path=str(path))
                except Exception as e:
                    logger.warning("Failed to delete folder", path=folder, error=str(e))
    
    try:
        if is_active:
            download.transition_to(DownloadStatus.CANCELLED)
            db.commit()
            return {"message": "Download cancelled", "files_deleted": delete_files}
        else:
            download.transition_to(DownloadStatus.CLEARED)
            db.commit()
            return {"message": "Download cleared", "files_deleted": delete_files}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")

@router.delete("/")
async def clear_downloads(
    payload: ClearDownloadsRequest,
    db: Session = Depends(get_db)
):
    """Clear the selected downloads from the list.

    Finished downloads are marked CLEARED; active ones are cancelled (kept
    in the list). Torrents are removed from qBittorrent (files kept) and,
    when requested, the download folder is deleted from disk.
    """
    service = QBittorrentService(db=db)
    cleared = 0
    files_deleted = False
    try:
        for item in payload.downloads:
            download = db.query(Download).filter(Download.id == item.id).first()
            if not download:
                continue

            is_active = download.status in {
                DownloadStatus.PENDING,
                DownloadStatus.DOWNLOADING,
            }
            if download.torrent_hash:
                try:
                    await service.delete_torrent(download.torrent_hash, delete_files=False)
                except Exception as e:
                    logger.warning(
                        "Failed to remove torrent from qBittorrent",
                        download_id=download.id,
                        error=str(e),
                    )

            if item.delete_files:
                for folder in [download.source_folder, download.destination_folder]:
                    if not folder:
                        continue
                    try:
                        path = Path(folder)
                        if path.exists() and path.is_dir():
                            shutil.rmtree(path)
                            logger.info("Deleted download folder", path=str(path))
                    except Exception as e:
                        logger.warning("Failed to delete folder", path=folder, error=str(e))
                files_deleted = True

            if is_active:
                download.transition_to(DownloadStatus.CANCELLED)
            else:
                download.transition_to(DownloadStatus.CLEARED)
                cleared += 1
        db.commit()
    finally:
        await service.close()

    logger.info("Cleared downloads", cleared=cleared)
    return {"cleared": cleared, "files_deleted": files_deleted}


@router.post("/{download_id}/pause")
async def pause_download(download_id: int, db: Session = Depends(get_db)):
    """Pause a download in qBittorrent."""
    download = db.query(Download).filter(Download.id == download_id).first()
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    
    if not download.torrent_hash:
        raise HTTPException(status_code=400, detail="No torrent hash associated with this download")
    
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
    
    service = QBittorrentService(db=db)
    success = await service.resume_torrent(download.torrent_hash)
    await service.close()
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to resume torrent in qBittorrent")
    
    return {"message": "Download resumed"}

