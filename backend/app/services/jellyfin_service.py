"""Jellyfin API service."""
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

class JellyfinService:
    """Service to interact with Jellyfin API."""
    
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def scan_library(self, library_name: Optional[str] = None) -> bool:
        """Trigger library scan in Jellyfin.

        Args:
            library_name: Name of the library to scan. If None, triggers a full scan.

        Returns:
            True if the scan was triggered successfully, False otherwise.
        """
        try:
            headers = {
                "X-Emby-Token": self.settings.jellyfin_api_key,
                "Content-Type": "application/json"
            }
            
            if library_name:
                libraries = await self.get_libraries()
                for lib in libraries:
                    if lib.get("Name") == library_name:
                        library_id = lib.get("Id")
                        response = await self.client.post(
                            f"{self.settings.jellyfin_url}/Items/{library_id}/Refresh",
                            headers=headers,
                            params={
                                "Recursive": "true",
                                "ImageRefreshMode": "Default",
                                "MetadataRefreshMode": "Default",
                            },
                        )
                        response.raise_for_status()
                        logger.info("Jellyfin library scan triggered", library=library_name)
                        return True
                
                logger.warning("Library not found", library=library_name)
                return False
            else:
                response = await self.client.post(
                    f"{self.settings.jellyfin_url}/Library/Refresh",
                    headers=headers
                )
                response.raise_for_status()
                logger.info("Jellyfin full library scan triggered")
                return True
                
        except httpx.HTTPError as e:
            logger.error("Failed to trigger Jellyfin scan", error=str(e))
            return False
    
    async def get_libraries(self) -> List[Dict[str, Any]]:
        """Get list of libraries.

        Returns:
            List of library dictionaries.
        """
        try:
            headers = {
                "X-Emby-Token": self.settings.jellyfin_api_key
            }

            response = await self.client.get(
                f"{self.settings.jellyfin_url}/Library/VirtualFolders",
                headers=headers
            )
            response.raise_for_status()
            return response.json()

        except (httpx.HTTPError, ValueError) as e:
            logger.error("Failed to get Jellyfin libraries", error=str(e))
            return []
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
