"""Download model."""
import enum

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Text
from sqlalchemy.sql import func
from app.database import Base

class ContentType(str, enum.Enum):
    MOVIE = "movie"
    SERIES = "series"
    ANIME = "anime"

class DownloadStatus(str, enum.Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ORGANIZED = "organized"

class Download(Base):
    __tablename__ = "downloads"
    
    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(Enum(ContentType), nullable=False)
    season = Column(Integer)
    episode = Column(Integer)
    
    torrent_name = Column(String(500))
    torrent_hash = Column(String(64), unique=True)
    magnet_link = Column(Text)
    
    quality = Column(String(20), default="1080p")
    language_preference = Column(String(50), default="legendado")
    
    status = Column(Enum(DownloadStatus), default=DownloadStatus.PENDING)
    progress = Column(Float, default=0.0)
    speed = Column(String(50))
    eta = Column(String(50))
    
    source_folder = Column(Text)
    destination_folder = Column(Text)
    
    indexer_used = Column(String(100))
    error_message = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
