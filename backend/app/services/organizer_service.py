"""File organizer service."""
import shutil
import re
from pathlib import Path
from typing import Optional, List
from app.config import get_settings
from app.logging_config import get_logger
from sqlalchemy.orm import Session
from app.services.settings_service import get_media_paths

logger = get_logger(__name__)

class OrganizerService:
    """Service to organize downloaded files into library folders."""
    
    VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v'}
    SUBTITLE_EXTENSIONS = {'.srt', '.ass', '.ssa', '.sub', '.idx'}
    
    def __init__(self, db: Optional[Session] = None):
        if db:
            paths = get_media_paths(db)
            self.movies_path = paths["movies_path"]
            self.series_path = paths["series_path"]
            self.animes_path = paths["animes_path"]
        else:
            settings = get_settings()
            self.movies_path = settings.movies_path
            self.series_path = settings.series_path
            self.animes_path = settings.animes_path
    
    def organize_movie(self, source_path: str, title: str, year: Optional[int], quality: str) -> str:
        """Organize a movie file."""
        source = Path(source_path)
        
        folder_name = f"{title} ({year})" if year else title
        dest_folder = Path(self.movies_path) / self._sanitize_filename(folder_name)
        dest_folder.mkdir(parents=True, exist_ok=True)
        
        video_files = self._get_video_files(source)
        if not video_files:
            logger.error("No video files found", source=source_path)
            raise ValueError(f"No video files found in {source_path}")
        
        main_file = video_files[0]
        file_name = f"{folder_name} - {quality}{main_file.suffix}"
        dest_path = dest_folder / self._sanitize_filename(file_name)
        
        self._move_file(main_file, dest_path)
        self._move_subtitles(source, dest_folder, folder_name)
        self._cleanup_source(source)
        
        logger.info("Movie organized", title=title, destination=str(dest_path))
        return str(dest_path)
    
    def organize_series(self, source_path: str, title: str, season: int, episode: int, quality: str) -> str:
        """Organize a TV episode file."""
        source = Path(source_path)
        
        show_folder = Path(self.series_path) / self._sanitize_filename(title)
        season_folder = show_folder / f"Season {season:02d}"
        season_folder.mkdir(parents=True, exist_ok=True)
        
        video_files = self._get_video_files(source)
        if not video_files:
            logger.error("No video files found", source=source_path)
            raise ValueError(f"No video files found in {source_path}")
        
        main_file = video_files[0]
        file_name = f"{title} - S{season:02d}E{episode:02d} - {quality}{main_file.suffix}"
        dest_path = season_folder / self._sanitize_filename(file_name)
        
        self._move_file(main_file, dest_path)
        self._move_subtitles(source, season_folder, f"{title} - S{season:02d}E{episode:02d}")
        self._cleanup_source(source)
        
        logger.info("Episode organized", title=title, season=season, episode=episode, destination=str(dest_path))
        return str(dest_path)
    
    def organize_anime(self, source_path: str, title: str, season: int, episode: int, quality: str) -> str:
        """Organize an anime episode file."""
        source = Path(source_path)
        
        show_folder = Path(self.animes_path) / self._sanitize_filename(title)
        season_folder = show_folder / f"Season {season:02d}"
        season_folder.mkdir(parents=True, exist_ok=True)
        
        video_files = self._get_video_files(source)
        if not video_files:
            logger.error("No video files found", source=source_path)
            raise ValueError(f"No video files found in {source_path}")
        
        main_file = video_files[0]
        file_name = f"{title} - S{season:02d}E{episode:02d} - {quality}{main_file.suffix}"
        dest_path = season_folder / self._sanitize_filename(file_name)
        
        self._move_file(main_file, dest_path)
        self._move_subtitles(source, season_folder, f"{title} - S{season:02d}E{episode:02d}")
        self._cleanup_source(source)
        
        logger.info("Anime organized", title=title, season=season, episode=episode, destination=str(dest_path))
        return str(dest_path)
    
    def _get_video_files(self, path: Path) -> List[Path]:
        """Get all video files in a path."""
        if path.is_file() and path.suffix.lower() in self.VIDEO_EXTENSIONS:
            return [path]
        
        video_files = []
        if path.is_dir():
            for ext in self.VIDEO_EXTENSIONS:
                video_files.extend(path.glob(f"*{ext}"))
                video_files.extend(path.glob(f"*{ext.upper()}"))
        
        video_files.sort(key=lambda x: x.stat().st_size, reverse=True)
        return video_files
    
    def _move_file(self, source: Path, destination: Path) -> None:
        """Move file from source to destination."""
        if destination.exists():
            source_size = source.stat().st_size
            dest_size = destination.stat().st_size
            
            if source_size <= dest_size:
                logger.warning("Destination file exists and is larger or equal, skipping", destination=str(destination))
                return
            else:
                logger.warning("Destination file exists but source is larger, replacing", destination=str(destination))
                destination.unlink()
        
        shutil.move(str(source), str(destination))
        logger.debug("File moved", source=str(source), destination=str(destination))
    
    def _move_subtitles(self, source: Path, dest_folder: Path, base_name: str) -> None:
        """Move subtitle files to destination."""
        if source.is_file():
            source_dir = source.parent
        else:
            source_dir = source
        
        for ext in self.SUBTITLE_EXTENSIONS:
            for sub_file in source_dir.glob(f"*{ext}"):
                dest_name = f"{base_name}{ext}"
                dest_path = dest_folder / self._sanitize_filename(dest_name)
                if dest_path.exists():
                    logger.warning("Subtitle already exists, skipping", destination=str(dest_path))
                    continue
                shutil.move(str(sub_file), str(dest_path))
                logger.debug("Subtitle moved", source=str(sub_file), destination=str(dest_path))
    
    def _cleanup_source(self, source: Path) -> None:
        """Remove empty source directories."""
        if source.is_file():
            source = source.parent
        
        for pattern in ['*.nfo', 'sample*', 'Sample*', '*.txt', '*.jpg', '*.png']:
            for file in source.glob(pattern):
                try:
                    file.unlink()
                    logger.debug("Removed unnecessary file", file=str(file))
                except (OSError, PermissionError) as e:
                    logger.warning("Failed to remove file", file=str(file), error=str(e))
        
        try:
            if source.exists() and not any(source.iterdir()):
                source.rmdir()
                logger.debug("Removed empty source directory", directory=str(source))
        except (OSError, PermissionError) as e:
            logger.warning("Failed to remove directory", directory=str(source), error=str(e))
    
    def _sanitize_filename(self, filename: str) -> str:
        """Remove invalid characters from filename."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
