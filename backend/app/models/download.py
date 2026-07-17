"""Download model."""
import enum
import re
from typing import Optional

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
    CLEARED = "cleared"

class Download(Base):
    __tablename__ = "downloads"
    
    VALID_TRANSITIONS = {
        DownloadStatus.PENDING: {
            DownloadStatus.DOWNLOADING,
            DownloadStatus.FAILED,
            DownloadStatus.CANCELLED,
            DownloadStatus.PENDING,
        },
        DownloadStatus.DOWNLOADING: {
            DownloadStatus.COMPLETED,
            DownloadStatus.FAILED,
            DownloadStatus.CANCELLED,
            DownloadStatus.DOWNLOADING,
        },
        DownloadStatus.COMPLETED: {
            DownloadStatus.ORGANIZED,
            DownloadStatus.FAILED,
            DownloadStatus.CLEARED,
            DownloadStatus.COMPLETED,
        },
        DownloadStatus.FAILED: {
            DownloadStatus.FAILED,
            DownloadStatus.CLEARED,
        },
        DownloadStatus.CANCELLED: {
            DownloadStatus.CANCELLED,
            DownloadStatus.CLEARED,
        },
        DownloadStatus.ORGANIZED: {
            DownloadStatus.ORGANIZED,
            DownloadStatus.CLEARED,
        },
        DownloadStatus.CLEARED: {
            DownloadStatus.CLEARED,
        },
    }
    
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
    size = Column(String(50))
    seeds = Column(Integer)
    peers = Column(Integer)
    error_message = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))

    def transition_to(self, new_status: DownloadStatus) -> None:
        """Transition to a new status if valid."""
        if new_status not in self.VALID_TRANSITIONS.get(self.status, set()):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")
        self.status = new_status

    @staticmethod
    def extract_hash(magnet_link: Optional[str]) -> Optional[str]:
        """Extract btih hash from a magnet link."""
        if not magnet_link:
            return None
        match = re.search(r"xt=urn:btih:([a-fA-F0-9]{40})(?:[^a-fA-F0-9]|$)", magnet_link)
        if match:
            return match.group(1).lower()
        return None

    def is_active(self) -> bool:
        """Check if download is in an active state."""
        return self.status in {
            DownloadStatus.PENDING,
            DownloadStatus.DOWNLOADING,
            DownloadStatus.COMPLETED,
        }

    def to_dict(self) -> dict:
        """Serialize Download to a dict."""
        return {
            "id": self.id,
            "tmdb_id": self.tmdb_id,
            "title": self.title,
            "type": self.type.value if self.type else None,
            "season": self.season,
            "episode": self.episode,
            "torrent_name": self.torrent_name,
            "torrent_hash": self.torrent_hash,
            "magnet_link": self.magnet_link,
            "quality": self.quality,
            "language_preference": self.language_preference,
            "status": self.status.value if self.status else None,
            "progress": self.progress,
            "speed": self.speed,
            "eta": self.eta,
            "source_folder": self.source_folder,
            "destination_folder": self.destination_folder,
            "indexer_used": self.indexer_used,
            "size": self.size,
            "seeds": self.seeds,
            "peers": self.peers,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
