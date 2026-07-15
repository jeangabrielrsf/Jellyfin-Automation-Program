"""Jackett scraper implementation."""
import re
from datetime import datetime
from typing import List

from app.scrapers.base import BaseScraper
from app.clients.jackett_client import JackettClient
from app.models.torrent import TorrentResult
from sqlalchemy.orm import Session
from app.logging_config import get_logger

logger = get_logger(__name__)

class JackettScraper(BaseScraper):
    """Scraper that uses Jackett as a gateway to multiple indexers."""
    
    name = "jackett"
    priority = 10
    
    def __init__(self, db: Session | None = None, jackett_client: JackettClient | None = None):
        self.db = db
        self.jackett_client = jackett_client or JackettClient(db=db)
    
    async def search(self, query: str, media_type: str, quality: str = "1080p", language: str = "legendado") -> List[TorrentResult]:
        """Search for torrents via Jackett."""
        logger.info("Searching Jackett", query=query, media_type=media_type, quality=quality)
        
        try:
            category = self._get_category(media_type)
            raw_results = await self.jackett_client.search(query, category=category)
            
            results = []
            for item in raw_results:
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
                    release_group=self._extract_release_group(item.get("Title", "")),
                    publish_date=self._parse_date(item.get("PublishDate")),
                    grabs=item.get("Grabs"),
                    download_volume_factor=item.get("DownloadVolumeFactor"),
                    files=item.get("Files")
                )
                torrent.score = self.calculate_score(torrent, quality, language)
                results.append(torrent)
            
            results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info("Jackett search completed", results_count=len(results))
            return results
            
        except Exception as e:
            logger.error(
                "Jackett search failed with unexpected error",
                error_type=type(e).__name__,
                error=str(e)
            )
            return []
    
    async def get_magnet(self, torrent_id: str) -> str:
        """Return the magnet URL (Jackett already provides the magnet link in search results)."""
        return torrent_id
    
    async def close(self):
        """Close the HTTP client."""
        await self.jackett_client.close()
    
    def _get_category(self, media_type: str) -> List[int]:
        """Get Jackett category IDs based on content type."""
        categories = {
            "movie": [2000],
            "series": [5000],
            "anime": [5070]
        }
        return categories.get(media_type, [2000, 5000])
    
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
        if re.search(r'\bdual\b', title_lower):
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
    
    def _parse_date(self, date_str: str | None):
        """Parse ISO 8601 date string from Jackett."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
