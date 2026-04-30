"""Torrent Pydantic models."""
from typing import Optional

from pydantic import BaseModel

class TorrentResult(BaseModel):
    title: str
    indexer: str
    size: str
    seeds: int
    peers: Optional[int] = None
    download_url: Optional[str] = None
    magnet_url: Optional[str] = None
    quality: Optional[str] = None
    language: Optional[str] = None
    release_group: Optional[str] = None
    score: float = 0.0

    class Config:
        from_attributes = True

class TorrentSearchRequest(BaseModel):
    query: str
    media_type: str
    quality: Optional[str] = "1080p"
    language: Optional[str] = "legendado"
    tmdb_id: Optional[int] = None
