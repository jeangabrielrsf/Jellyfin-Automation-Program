"""qBittorrent Web API service."""
import httpx
from typing import List, Optional, Dict
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
            response = await self.client.post(
                f"{self.settings.qbittorrent_host}/api/v2/auth/login",
                data={
                    "username": self.settings.qbittorrent_username,
                    "password": self.settings.qbittorrent_password
                }
            )
            if response.status_code == 200 and response.text == "Ok.":
                self._authenticated = True
                logger.info("Authenticated with qBittorrent")
                return True
            else:
                logger.error("qBittorrent authentication failed", response=response.text)
                return False
        except Exception as e:
            logger.error("qBittorrent authentication error", error=str(e))
            return False
    
    async def add_torrent(self, magnet_link: str, save_path: Optional[str] = None, category: Optional[str] = None) -> bool:
        """Add torrent to qBittorrent."""
        if not await self._authenticate():
            return False
        
        try:
            data = {"urls": magnet_link}
            if save_path:
                data["savepath"] = save_path
            if category:
                data["category"] = category
            
            response = await self.client.post(
                f"{self.settings.qbittorrent_host}/api/v2/torrents/add",
                data=data
            )
            response.raise_for_status()
            
            logger.info("Torrent added to qBittorrent", magnet=magnet_link[:50])
            return True
            
        except Exception as e:
            logger.error("Failed to add torrent", error=str(e))
            return False
    
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
            
        except Exception as e:
            logger.error("Failed to get torrents", error=str(e))
            return []
    
    async def get_torrent(self, hash: str) -> Optional[Dict]:
        """Get specific torrent by hash."""
        torrents = await self.get_torrents()
        for torrent in torrents:
            if torrent.get("hash") == hash:
                return torrent
        return None
    
    async def pause_torrent(self, hash: str) -> bool:
        """Pause a torrent."""
        if not await self._authenticate():
            return False
        
        try:
            response = await self.client.post(
                f"{self.settings.qbittorrent_host}/api/v2/torrents/pause",
                data={"hashes": hash}
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error("Failed to pause torrent", error=str(e))
            return False
    
    async def resume_torrent(self, hash: str) -> bool:
        """Resume a torrent."""
        if not await self._authenticate():
            return False
        
        try:
            response = await self.client.post(
                f"{self.settings.qbittorrent_host}/api/v2/torrents/resume",
                data={"hashes": hash}
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error("Failed to resume torrent", error=str(e))
            return False
    
    async def delete_torrent(self, hash: str, delete_files: bool = False) -> bool:
        """Delete a torrent."""
        if not await self._authenticate():
            return False
        
        try:
            response = await self.client.post(
                f"{self.settings.qbittorrent_host}/api/v2/torrents/delete",
                data={
                    "hashes": hash,
                    "deleteFiles": str(delete_files).lower()
                }
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error("Failed to delete torrent", error=str(e))
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
