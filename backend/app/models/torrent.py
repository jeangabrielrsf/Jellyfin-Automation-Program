"""Torrent Pydantic models."""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict

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
    publish_date: Optional[datetime] = None
    grabs: Optional[int] = None
    download_volume_factor: Optional[float] = None
    files: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
