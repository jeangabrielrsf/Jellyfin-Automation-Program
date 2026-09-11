"""qBittorrent Web API service."""
from typing import List, Optional, Dict
import httpx
from sqlalchemy.orm import Session
from app.clients.jackett_client import JackettClient
from app.services.config_service import get_config
from app.logging_config import get_logger

logger = get_logger(__name__)

class QBittorrentService:
    """Service to interact with qBittorrent Web API."""
    
    def __init__(self, db: Session | None = None, jackett_client: JackettClient | None = None):
        self.db = db
        self.host = get_config("qbittorrent_host", db, required=True)
        self.username = get_config("qbittorrent_username", db, required=True)
        self.password = get_config("qbittorrent_password", db, required=True)
        self.client = httpx.AsyncClient(timeout=30.0)
        self._authenticated = False
        self.jackett_client = jackett_client if jackett_client is not None else JackettClient(db=db)
    
    async def _authenticate(self) -> bool:
        """Authenticate with qBittorrent."""
        if self._authenticated:
            return True
        
        try:
            login_url = f"{self.host}/api/v2/auth/login"
            logger.info("Authenticating with qBittorrent", url=login_url, username=self.username)
            response = await self.client.post(
                login_url,
                data={
                    "username": self.username,
                    "password": self.password
                }
            )
            logger.info("qBittorrent auth response", status=response.status_code, text=response.text)
            if response.status_code in (200, 204) and response.text in ("Ok.", ""):
                self._authenticated = True
                logger.info("Authenticated with qBittorrent")
                return True
            else:
                logger.error("qBittorrent authentication failed", status=response.status_code, response=response.text)
                return False
        except httpx.HTTPError as e:
            logger.error("qBittorrent authentication error", error=str(e))
            return False
    
    async def add_torrent(self, magnet_link: Optional[str] = None, download_url: Optional[str] = None, save_path: Optional[str] = None, category: Optional[str] = None, torrent_name: Optional[str] = None, tags: Optional[str] = None) -> tuple[bool, bool]:
        """Add torrent to qBittorrent.
        
        Returns:
            tuple: (success: bool, already_exists: bool)
                - success: True if torrent was added or already exists
                - already_exists: True if torrent was already in qBittorrent (409 Conflict)
        """
        logger.info("Adding torrent to qBittorrent", magnet_link=magnet_link[:50] if magnet_link else None, download_url=download_url[:50] if download_url else None, save_path=save_path, category=category)
        if not await self._authenticate():
            logger.error("Cannot add torrent: authentication failed")
            return False, False
        
        # Determine which link to use
        link = magnet_link if magnet_link else download_url
        if not link:
            logger.error("No link provided for torrent")
            return False, False
        
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
            add_url = f"{self.host}/api/v2/torrents/add"
            
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
                    if download_url and self.jackett_client:
                        logger.info("Attempting to get fresh download link from Jackett")
                        fresh_result = await self.jackett_client.find_fresh_link(torrent_name)
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
                                return True, False
                            else:
                                # Try to download via Jackett proxy first, then direct link as fallback
                                torrent_content = await self.jackett_client.download_torrent_file(
                                    fresh_tracker, fresh_link, torrent_name
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
            
            logger.info(f"qBittorrent add response: status={response.status_code}, text={response.text[:200]}")
            response.raise_for_status()
            
            logger.info(f"Torrent added to qBittorrent successfully: link={link[:50]}")
            return True, False
            
        except httpx.HTTPStatusError as e:
            error_body = e.response.text[:500] if e.response else "No response"
            status_code = e.response.status_code if e.response else "N/A"
            
            # 409 Conflict means torrent already exists in qBittorrent
            if status_code == 409:
                logger.info(f"Torrent already exists in qBittorrent (409 Conflict), treating as success: is_magnet={is_magnet}")
                return True, True
            
            logger.error(f"Failed to add torrent: status={status_code}, body={error_body}, is_magnet={is_magnet}")
            return False, False
        except httpx.HTTPError as e:
            logger.error(f"Failed to add torrent: error={str(e)}, is_magnet={is_magnet}")
            return False, False
        except Exception as e:
            logger.error(f"Unexpected error adding torrent: error={str(e)}, error_type={type(e).__name__}, is_magnet={is_magnet}")
            return False, False
    
    async def get_torrents_by_tag(self, tag: str) -> List[Dict]:
        """Get torrents filtered by tag."""
        if not await self._authenticate():
            return []
        
        try:
            response = await self.client.get(
                f"{self.host}/api/v2/torrents/info",
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
                f"{self.host}/api/v2/torrents/info"
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error("Failed to get torrents", error=str(e))
            return []
    
    async def pause_torrent(self, torrent_hash: str) -> bool:
        """Pause a torrent."""
        if not await self._authenticate():
            return False
        
        try:
            response = await self.client.post(
                f"{self.host}/api/v2/torrents/pause",
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
                f"{self.host}/api/v2/torrents/resume",
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
                f"{self.host}/api/v2/torrents/delete",
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
