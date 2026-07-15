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
        
        Uses three-tier matching strategy: exact → word → substring.
        Prioritizes MagnetUri (doesn't expire) over Link (expires quickly).
        
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
            
            def normalize(text: str) -> str:
                """Normalize text for comparison: lowercase and replace dots with spaces."""
                return text.lower().replace('.', ' ').replace('-', ' ').replace('_', ' ')
            
            normalized_torrent_name = normalize(torrent_name)
            torrent_words = set(normalized_torrent_name.split())
            
            logger.info(
                "Looking for torrent match",
                torrent_name=torrent_name,
                normalized=normalized_torrent_name,
                words=torrent_words,
                total_results=len(results)
            )
            
            # Pass 1: Exact match with MagnetUri
            for item in results:
                title = item.get("Title", "")
                normalized_title = normalize(title)
                if normalized_title == normalized_torrent_name:
                    magnet_uri = item.get("MagnetUri")
                    if magnet_uri:
                        logger.info("Found fresh magnet link for torrent (exact match)", torrent_name=torrent_name, matched_title=title)
                        return {"link": magnet_uri, "tracker_id": None}
            
            # Pass 1: Word match with MagnetUri
            for item in results:
                title = item.get("Title", "")
                normalized_title = normalize(title)
                title_words = set(normalized_title.split())
                if torrent_words.issubset(title_words):
                    magnet_uri = item.get("MagnetUri")
                    if magnet_uri:
                        logger.info("Found fresh magnet link for torrent (word match)", torrent_name=torrent_name, matched_title=title)
                        return {"link": magnet_uri, "tracker_id": None}
            
            # Pass 1: Substring match with MagnetUri
            for item in results:
                title = item.get("Title", "")
                normalized_title = normalize(title)
                if normalized_torrent_name in normalized_title or normalized_title in normalized_torrent_name:
                    magnet_uri = item.get("MagnetUri")
                    if magnet_uri:
                        logger.info("Found fresh magnet link for torrent (substring match)", torrent_name=torrent_name, matched_title=title)
                        return {"link": magnet_uri, "tracker_id": None}
            
            # Pass 2: Exact match with Link (fallback)
            for item in results:
                title = item.get("Title", "")
                normalized_title = normalize(title)
                if normalized_title == normalized_torrent_name:
                    fresh_link = item.get("Link")
                    if fresh_link:
                        tracker_id = item.get("TrackerId") or item.get("Tracker")
                        logger.info("Found fresh download link for torrent (exact match)", torrent_name=torrent_name, matched_title=title)
                        return {"link": fresh_link, "tracker_id": tracker_id}
            
            # Pass 2: Word match with Link (fallback)
            for item in results:
                title = item.get("Title", "")
                normalized_title = normalize(title)
                title_words = set(normalized_title.split())
                if torrent_words.issubset(title_words):
                    fresh_link = item.get("Link")
                    if fresh_link:
                        tracker_id = item.get("TrackerId") or item.get("Tracker")
                        logger.info("Found fresh download link for torrent (word match)", torrent_name=torrent_name, matched_title=title)
                        return {"link": fresh_link, "tracker_id": tracker_id}
            
            # Pass 2: Substring match with Link (fallback)
            for item in results:
                title = item.get("Title", "")
                normalized_title = normalize(title)
                if normalized_torrent_name in normalized_title or normalized_title in normalized_torrent_name:
                    fresh_link = item.get("Link")
                    if fresh_link:
                        tracker_id = item.get("TrackerId") or item.get("Tracker")
                        logger.info("Found fresh download link for torrent (substring match)", torrent_name=torrent_name, matched_title=title)
                        return {"link": fresh_link, "tracker_id": tracker_id}
            
            logger.warning("Could not find fresh link for torrent", torrent_name=torrent_name, results_count=len(results))
            return None
            
        except Exception as e:
            logger.error("Failed to get fresh Jackett link", error=str(e))
            return None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
