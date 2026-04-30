"""Downloads router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.download import Download, DownloadStatus, ContentType
from pydantic import BaseModel

router = APIRouter(prefix="/api/downloads", tags=["downloads"])

class DownloadCreate(BaseModel):
    tmdb_id: int
    title: str
    media_type: ContentType
    torrent_name: str
    magnet_link: str
    quality: str = "1080p"
    language_preference: str = "legendado"
    indexer_used: Optional[str] = None

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
def create_download(
    download: DownloadCreate,
    db: Session = Depends(get_db)
):
    """Create a new download record."""
    db_download = Download(
        tmdb_id=download.tmdb_id,
        title=download.title,
        type=download.media_type,
        torrent_name=download.torrent_name,
        magnet_link=download.magnet_link,
        quality=download.quality,
        language_preference=download.language_preference,
        status=DownloadStatus.PENDING,
        indexer_used=download.indexer_used
    )
    try:
        db.add(db_download)
        db.commit()
        db.refresh(db_download)
        return db_download
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")

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
