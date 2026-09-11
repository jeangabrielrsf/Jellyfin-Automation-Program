"""Jackett API client adapter."""
from typing import List, Dict, Optional
import httpx
from sqlalchemy.orm import Session
from app.services.config_service import get_config
from app.logging_config import get_logger

logger = get_logger(__name__)


class JackettClient:
    """Client adapter for Jackett API."""
    
    def __init__(self, db: Session | None = None):
        self.db = db
        self.url = get_config("jackett_url", db, required=True)
        self.api_key = get_config("jackett_api_key", db, required=True)
        timeout_val = get_config("jackett_timeout", db, required=False) or "120"
        self.timeout = float(timeout_val)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, read=self.timeout)
        )
    
    async def search(self, query: str, category: List[int]) -> List[Dict]:
        """Search Jackett and return raw Results.
        
        Args:
            query: Search query string
            category: List of category IDs to search
            
        Returns:
            List of raw Jackett result dictionaries
        """
        url = f"{self.url}/api/v2.0/indexers/all/results"
        params = {
            "apikey": self.api_key,
            "Query": query,
            "Category": category
        }
        
        try:
            logger.info("Searching Jackett", query=query, category=category)
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("Results", [])
            logger.info("Jackett search completed", results_count=len(results))
            return results
            
        except httpx.HTTPError as e:
            logger.error("Jackett search failed", error=str(e), query=query)
            return []
        except Exception as e:
            logger.error("Unexpected error in Jackett search", error=str(e), error_type=type(e).__name__)
            return []
    
    async def download_torrent_file(
        self,
        tracker_id: str,
        path: str,
        filename: Optional[str] = None
    ) -> Optional[bytes]:
        """Download .torrent file through Jackett's proxy.
        
        Args:
            tracker_id: Tracker identifier for Jackett proxy
            path: Original torrent link path
            filename: Optional filename for the torrent
            
        Returns:
            Torrent file bytes or None on failure
        """
        if not tracker_id:
            logger.warning("No tracker_id provided for torrent download")
            return None
        
        proxy_url = f"{self.url}/dl/{tracker_id}"
        params = {"path": path}
        if filename:
            params["file"] = filename
        
        try:
            logger.info("Downloading .torrent via Jackett proxy", proxy_url=proxy_url, path=path[:100])
            response = await self.client.get(proxy_url, params=params, follow_redirects=True, timeout=60.0)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type or response.status_code != 200:
                logger.warning("Jackett proxy returned non-torrent content", content_type=content_type)
                return None
            
            logger.info("Downloaded .torrent via Jackett proxy successfully", size=len(response.content))
            return response.content
            
        except httpx.HTTPError as e:
            logger.error("Jackett proxy download failed", error=str(e))
            return None
        except Exception as e:
            logger.error("Unexpected error in Jackett proxy download", error=str(e), error_type=type(e).__name__)
            return None
    
    async def find_fresh_link(self, torrent_name: str) -> Optional[Dict]:
        """Find a fresh download link by searching Jackett again.
        
        Matches by exact, word-subset then substring title, preferring
        MagnetUri (doesn't expire) over Link (expires quickly).
        
        Args:
            torrent_name: Name of the torrent to find
            
        Returns:
            Dictionary with 'link' and 'tracker_id' keys, or None if not found
        """
        if not torrent_name:
            logger.warning("No torrent name provided, cannot search for fresh link")
            return None
        
        try:
            search_url = f"{self.url}/api/v2.0/indexers/all/results"
            params = {
                "apikey": self.api_key,
                "Query": torrent_name,
            }
            
            logger.info("Searching Jackett for fresh link", torrent_name=torrent_name)
            response = await self.client.get(search_url, params=params, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("Results", [])
            normalized_name = self._normalize(torrent_name)
            name_words = set(normalized_name.split())
            
            def rank(title: str) -> Optional[int]:
                """0 exact, 1 word-subset, 2 substring; None when no match."""
                normalized_title = self._normalize(title)
                if normalized_title == normalized_name:
                    return 0
                if name_words.issubset(set(normalized_title.split())):
                    return 1
                if normalized_name in normalized_title or normalized_title in normalized_name:
                    return 2
                return None
            
            best: Optional[tuple] = None
            for item in results:
                title_rank = rank(item.get("Title", ""))
                if title_rank is None:
                    continue
                magnet = item.get("MagnetUri")
                link = item.get("Link")
                if not magnet and not link:
                    continue
                # Magnet always beats an expiring Link; then best match rank.
                candidate = (0 if magnet else 1, title_rank, item)
                if best is None or candidate[:2] < best[:2]:
                    best = candidate
            
            if best is None:
                logger.warning("Could not find fresh link for torrent", torrent_name=torrent_name, results_count=len(results))
                return None
            
            item = best[2]
            matched_title = item.get("Title", "")
            if item.get("MagnetUri"):
                logger.info("Found fresh magnet link for torrent", torrent_name=torrent_name, matched_title=matched_title)
                return {"link": item["MagnetUri"], "tracker_id": None}
            
            tracker_id = item.get("TrackerId") or item.get("Tracker")
            logger.info("Found fresh download link for torrent", torrent_name=torrent_name, matched_title=matched_title)
            return {"link": item["Link"], "tracker_id": tracker_id}
            
        except Exception as e:
            logger.error("Failed to get fresh Jackett link", error=str(e))
            return None
    
    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for comparison: lowercase, dots/dashes/underscores to spaces."""
        return text.lower().replace('.', ' ').replace('-', ' ').replace('_', ' ')
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
