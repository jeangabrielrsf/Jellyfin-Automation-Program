"""Service to resolve save paths for downloads based on media type and metadata."""
import re
from typing import Optional, Dict
from pathlib import Path
from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class PathResolver:
    """Resolve save paths for media downloads."""
    
    # Compiled patterns to extract season/episode from torrent names
    SEASON_EPISODE_PATTERNS = [
        re.compile(r'[Ss](\d{1,2})[Ee](\d{1,2})'),      # S08E17, s01e05
        re.compile(r'(\d{1,2})[xX](\d{1,2})'),          # 8x17, 1x05
        re.compile(r'[Ss]eason[.\s]*(\d{1,2}).*[Ee]pisode[.\s]*(\d{1,2})'),  # Season 8 Episode 17
    ]
    
    def extract_season_episode(self, torrent_name: str) -> Dict[str, Optional[int]]:
        """Extract season and episode numbers from torrent name."""
        for pattern in self.SEASON_EPISODE_PATTERNS:
            match = pattern.search(torrent_name)
            if match:
                return {
                    "season": int(match.group(1)),
                    "episode": int(match.group(2))
                }
        return {"season": None, "episode": None}
    
    def resolve_path(
        self,
        title: str,
        media_type: str,
        torrent_name: Optional[str] = None,
        season: Optional[int] = None,
        episode: Optional[int] = None,
        year: Optional[int] = None,
        quality: Optional[str] = None
    ) -> str:
        """Resolve the save path for a download.
        
        Args:
            title: Media title (e.g., "Breaking Bad")
            media_type: "movie", "series", or "anime"
            torrent_name: Original torrent name (used to extract season/episode if not provided)
            season: Season number (optional, extracted from torrent_name if not provided)
            episode: Episode number (optional)
            year: Release year (for movies)
            quality: Video quality (for file naming)
        
        Returns:
            Absolute path where the torrent should be saved
        """
        settings = get_settings()
        
        # Extract season/episode from torrent name if not provided
        if media_type in ("series", "anime") and season is None and torrent_name:
            extracted = self.extract_season_episode(torrent_name)
            season = extracted.get("season")
            episode = extracted.get("episode")
        
        # Default season if still not found
        if media_type in ("series", "anime") and season is None:
            season = 1
            logger.warning("Could not extract season from torrent name, defaulting to 1", torrent_name=torrent_name)
        
        # Build path based on media type
        if media_type == "movie":
            folder_name = f"{title} ({year})" if year else title
            base_path = Path(settings.movies_path)
            save_path = base_path / self._sanitize_filename(folder_name)
        elif media_type == "series":
            base_path = Path(settings.series_path)
            show_folder = base_path / self._sanitize_filename(title)
            save_path = show_folder / f"Season {season:02d}"
        elif media_type == "anime":
            base_path = Path(settings.animes_path)
            show_folder = base_path / self._sanitize_filename(title)
            save_path = show_folder / f"Season {season:02d}"
        else:
            raise ValueError(f"Unknown media type: {media_type}")
        
        # Create directories if they don't exist
        save_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "Resolved save path",
            title=title,
            media_type=media_type,
            season=season,
            episode=episode,
            path=str(save_path)
        )
        
        return str(save_path)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Remove invalid characters from filename."""
        # Replace invalid filesystem characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        # Replace directory traversal sequences
        filename = filename.replace('..', '_')
        # Strip control characters
        filename = ''.join(char for char in filename if ord(char) >= 32)
        # Trim leading/trailing dots and spaces
        filename = filename.strip('. ')
        return filename
