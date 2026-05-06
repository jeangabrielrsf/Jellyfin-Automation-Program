"""qBittorrent Web API service."""
from typing import List, Optional, Dict
import httpx
from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

class QBittorrentService:
    """Service to interact with qBittorrent Web API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=30.0)
        self._authenticated = False
    
    async def _authenticate(self) -> bool:
        """Authenticate with qBittorrent."""
        if self._authenticated:
            return True
        
        try:
            login_url = f"{self.settings.qbittorrent_host}/api/v2/auth/login"
            logger.info("Authenticating with qBittorrent", url=login_url, username=self.settings.qbittorrent_username)
            response = await self.client.post(
                login_url,
                data={
                    "username": self.settings.qbittorrent_username,
                    "password": self.settings.qbittorrent_password
                }
            )
            logger.info("qBittorrent auth response", status=response.status_code, text=response.text)
            if response.status_code == 200 and response.text == "Ok.":
                self._authenticated = True
                logger.info("Authenticated with qBittorrent")
                return True
            else:
                logger.error("qBittorrent authentication failed", status=response.status_code, response=response.text)
                return False
        except httpx.HTTPError as e:
            logger.error("qBittorrent authentication error", error=str(e))
            return False
    
    async def add_torrent(self, magnet_link: Optional[str] = None, download_url: Optional[str] = None, save_path: Optional[str] = None, category: Optional[str] = None, torrent_name: Optional[str] = None, tags: Optional[str] = None) -> bool:
        """Add torrent to qBittorrent."""
        logger.info("Adding torrent to qBittorrent", magnet_link=magnet_link[:50] if magnet_link else None, download_url=download_url[:50] if download_url else None, save_path=save_path, category=category)
        if not await self._authenticate():
            logger.error("Cannot add torrent: authentication failed")
            return False
        
        # Determine which link to use
        link = magnet_link if magnet_link else download_url
        if not link:
            logger.error("No link provided for torrent")
            return False
        
        is_magnet = link.strip().startswith("magnet:")
        
        # Build common data dict
        data = {}
        if save_path:
            data["savepath"] = save_path
        if category:
            data["category"] = category
        if tags:
            data["tags"] = tags
        
        try:
            add_url = f"{self.settings.qbittorrent_host}/api/v2/torrents/add"
            
            if is_magnet:
                data["urls"] = link
                logger.info("Sending magnet link to qBittorrent", url=add_url)
                response = await self.client.post(
                    add_url,
                    data=data
                )
            else:
                # Download the .torrent file and upload it to qBittorrent
                logger.info("Downloading .torrent file", url=link[:100])
                try:
                    torrent_response = await self.client.get(link, follow_redirects=True, timeout=60.0)
                    torrent_response.raise_for_status()
                    torrent_response_content = torrent_response.content
                    logger.info("Downloaded .torrent file", size=len(torrent_response_content), content_type=torrent_response.headers.get('content-type'))
                except httpx.HTTPError as e:
                    logger.error("Failed to download .torrent file", error=str(e), url=link[:100])
                    # If download failed, try to get a fresh link from Jackett
                    if download_url:
                        logger.info("Attempting to get fresh download link from Jackett")
                        fresh_result = await self._get_fresh_jackett_link(download_url, torrent_name)
                        if fresh_result:
                            fresh_link = fresh_result.get("link")
                            fresh_tracker = fresh_result.get("tracker_id")
                            logger.info("Got fresh link from Jackett", url=fresh_link[:100] if fresh_link else None, tracker_id=fresh_tracker)
                            # Check if the fresh link is a magnet link
                            if fresh_link and fresh_link.strip().startswith("magnet:"):
                                logger.info("Fresh link is a magnet link, sending directly to qBittorrent")
                                data["urls"] = fresh_link
                                response = await self.client.post(add_url, data=data)
                                logger.info("qBittorrent add response (fresh magnet)", status=response.status_code, text=response.text)
                                response.raise_for_status()
                                logger.info("Torrent added to qBittorrent successfully (fresh magnet)", link=fresh_link[:50])
                                return True
                            else:
                                # Try to download via Jackett proxy first, then direct link as fallback
                                torrent_content = await self._download_torrent_via_jackett(
                                    fresh_link, fresh_tracker, torrent_name
                                )
                                if torrent_content:
                                    torrent_response_content = torrent_content
                                    logger.info("Downloaded .torrent via Jackett proxy", size=len(torrent_content))
                                elif fresh_link:
                                    try:
                                        torrent_response = await self.client.get(fresh_link, follow_redirects=True, timeout=60.0)
                                        torrent_response.raise_for_status()
                                        torrent_response_content = torrent_response.content
                                        logger.info("Downloaded .torrent file with fresh link", size=len(torrent_response_content))
                                    except httpx.HTTPError as fresh_error:
                                        logger.error("Failed to download with fresh link", error=str(fresh_error), url=fresh_link[:100])
                                        raise
                                else:
                                    logger.error("No fresh link available")
                                    raise Exception("Could not get fresh download link from Jackett")
                        else:
                            raise
                    else:
                        raise
                
                files = {"torrents": ("torrent.torrent", torrent_response_content, "application/x-bittorrent")}
                
                logger.info("Uploading .torrent file to qBittorrent", url=add_url)
                response = await self.client.post(
                    add_url,
                    data=data,
                    files=files
                )
            
            logger.info("qBittorrent add response", status=response.status_code, text=response.text)
            response.raise_for_status()
            
            logger.info("Torrent added to qBittorrent successfully", link=link[:50])
            return True
            
        except httpx.HTTPError as e:
            logger.error("Failed to add torrent", error=str(e), is_magnet=is_magnet, status_code=getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None)
            return False
        except Exception as e:
            logger.error("Unexpected error adding torrent", error=str(e), error_type=type(e).__name__, is_magnet=is_magnet)
            return False
    
    async def _download_torrent_via_jackett(self, torrent_link: str, tracker_id: str, torrent_name: Optional[str] = None) -> Optional[bytes]:
        """Download .torrent file through Jackett's proxy download, falling back to direct download."""
        try:
            if not tracker_id:
                return None
            
            # Jackett proxy download URL format
            proxy_url = f"{self.settings.jackett_url}/dl/{tracker_id}"
            params = {"path": torrent_link}
            if torrent_name:
                params["file"] = torrent_name
            
            logger.info("Downloading .torrent via Jackett proxy", proxy_url=proxy_url, path=torrent_link[:100])
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
            logger.error("Unexpected error in Jackett proxy download", error=str(e))
            return None
    
    async def _get_fresh_jackett_link(self, old_link: str, torrent_name: Optional[str] = None) -> Optional[dict]:
        """Try to get a fresh download link from Jackett by searching again."""
        try:
            if not torrent_name:
                logger.warning("No torrent name provided, cannot search for fresh link")
                return None
            
            # Search Jackett for the torrent
            search_url = f"{self.settings.jackett_url}/api/v2.0/indexers/all/results"
            params = {
                "apikey": self.settings.jackett_api_key,
                "Query": torrent_name,
            }
            
            logger.info("Searching Jackett for fresh link", torrent_name=torrent_name)
            response = await self.client.get(search_url, params=params, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            
            # Find the matching torrent (exact match first, then partial)
            results = data.get("Results", [])
            
            def normalize(text):
                """Normalize text for comparison: lowercase and replace dots with spaces."""
                return text.lower().replace('.', ' ').replace('-', ' ').replace('_', ' ')
            
            normalized_torrent_name = normalize(torrent_name)
            torrent_words = set(normalized_torrent_name.split())
            
            logger.info("Looking for torrent match", torrent_name=torrent_name, normalized=normalized_torrent_name, words=torrent_words, total_results=len(results))
            
            # Strategy: First pass - look for MagnetUri (doesn't expire) in ALL results
            # Second pass - look for Link (expires quickly) in ALL results
            
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
    
    async def get_torrents_by_tag(self, tag: str) -> List[Dict]:
        """Get torrents filtered by tag."""
        if not await self._authenticate():
            return []
        
        try:
            response = await self.client.get(
                f"{self.settings.qbittorrent_host}/api/v2/torrents/info",
                params={"tag": tag}
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error("Failed to get torrents by tag", error=str(e), tag=tag)
            return []
    
    async def get_torrents(self) -> List[Dict]:
        """Get list of all torrents."""
        if not await self._authenticate():
            return []
        
        try:
            response = await self.client.get(
                f"{self.settings.qbittorrent_host}/api/v2/torrents/info"
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error("Failed to get torrents", error=str(e))
            return []
    
    async def get_torrent(self, torrent_hash: str) -> Optional[Dict]:
        """Get specific torrent by hash."""
        torrents = await self.get_torrents()
        for torrent in torrents:
            if torrent.get("hash") == torrent_hash:
                return torrent
        return None
    
    async def pause_torrent(self, torrent_hash: str) -> bool:
        """Pause a torrent."""
        if not await self._authenticate():
            return False
        
        try:
            response = await self.client.post(
                f"{self.settings.qbittorrent_host}/api/v2/torrents/pause",
                data={"hashes": torrent_hash}
            )
            response.raise_for_status()
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to pause torrent",
                torrent_hash=torrent_hash,
                status=e.response.status_code,
                response=e.response.text
            )
            return False
        except httpx.HTTPError as e:
            logger.error(
                "Failed to pause torrent",
                torrent_hash=torrent_hash,
                error=str(e)
            )
            return False
    
    async def resume_torrent(self, torrent_hash: str) -> bool:
        """Resume a torrent."""
        if not await self._authenticate():
            return False
        
        try:
            response = await self.client.post(
                f"{self.settings.qbittorrent_host}/api/v2/torrents/resume",
                data={"hashes": torrent_hash}
            )
            response.raise_for_status()
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to resume torrent",
                torrent_hash=torrent_hash,
                status=e.response.status_code,
                response=e.response.text
            )
            return False
        except httpx.HTTPError as e:
            logger.error(
                "Failed to resume torrent",
                torrent_hash=torrent_hash,
                error=str(e)
            )
            return False
    
    async def delete_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        """Delete a torrent."""
        if not await self._authenticate():
            return False
        
        try:
            response = await self.client.post(
                f"{self.settings.qbittorrent_host}/api/v2/torrents/delete",
                data={
                    "hashes": torrent_hash,
                    "deleteFiles": str(delete_files).lower()
                }
            )
            response.raise_for_status()
            return True
            
        except httpx.HTTPError as e:
            logger.error("Failed to delete torrent", error=str(e))
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
