"""Base scraper interface."""
from abc import ABC, abstractmethod
from typing import List
from app.models.torrent import TorrentResult

class BaseScraper(ABC):
    """Base class for all torrent scrapers."""
    
    name: str = "base"
    enabled: bool = True
    priority: int = 100
    
    @abstractmethod
    async def search(self, query: str, type: str, quality: str = "1080p", language: str = "legendado") -> List[TorrentResult]:
        """Search for torrents."""
        pass
    
    @abstractmethod
    async def get_magnet(self, torrent_id: str) -> str:
        """Get magnet link for a torrent."""
        pass
    
    def calculate_score(self, torrent: TorrentResult, preferred_quality: str, preferred_language: str) -> float:
        """Calculate torrent score based on preferences."""
        score = 0.0
        
        # Seeds factor (0-50 points)
        score += min(torrent.seeds * 0.5, 50)
        
        # Quality match (0-30 points)
        if torrent.quality and preferred_quality.lower() in torrent.quality.lower():
            score += 30
        elif torrent.quality:
            score += 15
        
        # Language match (0-20 points)
        if torrent.language and preferred_language.lower() in torrent.language.lower():
            score += 20
        
        return score
