"""Jackett scraper implementation."""
import httpx
import re
from typing import List
from app.scrapers.base import BaseScraper
from app.models.torrent import TorrentResult
from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

class JackettScraper(BaseScraper):
    """Scraper that uses Jackett as a gateway to multiple indexers."""
    
    name = "jackett"
    priority = 10
    
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def search(self, query: str, type: str, quality: str = "1080p", language: str = "legendado") -> List[TorrentResult]:
        """Search for torrents via Jackett."""
        logger.info("Searching Jackett", query=query, type=type, quality=quality)
        
        if not self.settings.jackett_api_key:
            logger.warning("Jackett API key not configured")
            return []
        
        url = f"{self.settings.jackett_url}/api/v2.0/indexers/all/results"
        params = {
            "apikey": self.settings.jackett_api_key,
            "Query": query,
            "Category": self._get_category(type)
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("Results", []):
                torrent = TorrentResult(
                    title=item.get("Title", ""),
                    indexer=f"Jackett ({item.get('Tracker', 'Unknown')})",
                    size=self._format_size(item.get("Size", 0)),
                    seeds=item.get("Seeders", 0),
                    peers=item.get("Peers", 0),
                    download_url=item.get("Link", ""),
                    magnet_url=item.get("MagnetUri", None),
                    quality=self._extract_quality(item.get("Title", "")),
                    language=self._extract_language(item.get("Title", "")),
                    release_group=self._extract_release_group(item.get("Title", ""))
                )
                torrent.score = self.calculate_score(torrent, quality, language)
                results.append(torrent)
            
            results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info("Jackett search completed", results_count=len(results))
            return results
            
        except httpx.HTTPError as e:
            logger.error("Jackett search failed", error=str(e))
            return []
    
    async def get_magnet(self, torrent_id: str) -> str:
        """Get magnet link."""
        return torrent_id
    
    def _get_category(self, type: str) -> List[int]:
        """Get Jackett category IDs based on content type."""
        categories = {
            "movie": [2000],
            "series": [5000],
            "anime": [5070]
        }
        return categories.get(type, [2000, 5000])
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def _extract_quality(self, title: str) -> str:
        """Extract quality from title."""
        qualities = ['2160p', '1080p', '720p', '480p', '360p']
        for quality in qualities:
            if quality in title.lower():
                return quality
        return "Unknown"
    
    def _extract_language(self, title: str) -> str:
        """Extract language from title."""
        title_lower = title.lower()
        if 'dual' in title_lower or 'dublado' in title_lower:
            return "Dual Áudio"
        elif 'dublado' in title_lower or 'dub' in title_lower:
            return "Dublado"
        elif 'legendado' in title_lower or 'leg' in title_lower:
            return "Legendado"
        return "Unknown"
    
    def _extract_release_group(self, title: str) -> str:
        """Extract release group from title."""
        match = re.search(r'-([A-Za-z0-9]+)$', title)
        if match:
            return match.group(1)
        return "Unknown"
