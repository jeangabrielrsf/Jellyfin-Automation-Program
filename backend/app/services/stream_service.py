"""Stream service — resolves which media file to play for a finished download."""
import re
from pathlib import Path
from typing import Dict, List, Optional

from app.logging_config import get_logger
from app.models.download import ContentType

logger = get_logger(__name__)


class StreamService:
    """Resolve the playable file(s) for a Download.

    Direct playback only at this stage; transcoding decisions are added later.
    """

    VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.webm'}
    EXCLUDED_KEYWORDS = ('sample', 'trailer', 'extra', 'featurette')
    EPISODE_PATTERN = re.compile(r"[Ss](\d{1,2})[Ee](\d{1,2})")

    def resolve_folder(self, download) -> Path:
        """Return the file or folder where the download's media lives.

        Prefers destination_folder (organized) over source_folder, falling
        back to source when the destination no longer exists on disk. Raises
        FileNotFoundError with a clear message when nothing is registered
        or no registered path exists.
        """
        registered = [download.destination_folder, download.source_folder]
        for folder in registered:
            if not folder:
                continue
            path = Path(folder)
            if path.exists():
                return path

        folder = next((f for f in registered if f), None)
        if not folder:
            raise FileNotFoundError(
                f"Nenhum folder registrado para o download {download.id}"
            )
        raise FileNotFoundError(
            f"Arquivo de mídia não encontrado no disco para o download {download.id}: {folder}"
        )

    def resolve_files(self, download) -> List[Dict]:
        """Resolve the playable files for a download.

        Returns a list of entries: {path, season, episode, title}.
        - Movie: the largest video file, excluding sample/trailer/extra names.
        - Series/anime pack: every SxxExx episode of the download's season, sorted.
        - Single episode: the matching SxxExx file (or the lone video file).
        """
        folder = self.resolve_folder(download)
        return self._resolve_entries(download, folder)

    def resolve_file(self, download, episode: Optional[int] = None) -> Path:
        """Resolve the single file to stream for a download.

        Args:
            download: The download record.
            episode: Optional episode number (used for packs).

        Raises:
            FileNotFoundError: When the folder is gone or no file matches.
        """
        folder = self.resolve_folder(download)
        return self._resolve_entries(download, folder, requested_episode=episode)[0]["path"]

    def _resolve_entries(
        self, download, folder: Path, requested_episode: Optional[int] = None
    ) -> List[Dict]:
        if folder.is_file():
            return [self._entry(folder)]

        if download.type == ContentType.MOVIE:
            return [self._entry(self._pick_movie_file(folder))]

        return self._series_files(download, folder, requested_episode=requested_episode)

    def _series_files(
        self, download, folder: Path, requested_episode: Optional[int] = None
    ) -> List[Dict]:
        """Resolve series/anime entries for a folder."""
        target_episode = (
            requested_episode if requested_episode is not None else download.episode
        )

        if target_episode is not None:
            season = download.season or 1
            episodes = self._enumerate_episodes(folder)
            matched = [
                entry
                for entry in episodes
                if entry["season"] == season and entry["episode"] == target_episode
            ]
            if matched:
                return matched

            # Fallback: unparsed torrents (e.g. anime) may not carry SxxExx.
            lone_file = self._single_video(folder)
            if lone_file is not None and self._entry(lone_file)["season"] is None:
                return [self._entry(lone_file)]

            raise FileNotFoundError(
                f"Episódio S{season:02d}E{target_episode:02d} não encontrado para o download {download.id}"
            )

        episodes = self._enumerate_episodes(folder, season=download.season)
        if not episodes:
            raise FileNotFoundError(
                f"Nenhum episódio encontrado em {folder} para o download {download.id}"
            )
        return episodes

    def _pick_movie_file(self, folder: Path) -> Path:
        videos = self._candidate_videos(folder)
        if not videos:
            raise FileNotFoundError(f"Nenhum arquivo de vídeo encontrado em {folder}")
        return videos[0]

    def _single_video(self, folder: Path) -> Optional[Path]:
        videos = self._candidate_videos(folder)
        if len(videos) == 1:
            return videos[0]
        return None

    def _enumerate_episodes(self, folder: Path, season: Optional[int] = None) -> List[Dict]:
        """List video files with SxxExx in the name, sorted by season/episode.

        When season is given, only episodes of that season are returned.
        """
        entries = []
        for video in self._candidate_videos(folder):
            entry = self._entry(video)
            if entry["season"] is None:
                continue
            if season is not None and entry["season"] != season:
                continue
            entries.append(entry)
        entries.sort(key=lambda entry: (entry["season"], entry["episode"]))
        return entries

    def _candidate_videos(self, folder: Path) -> List[Path]:
        """All video files in folder (recursive), excluding extras, largest first."""
        videos = []
        for ext in self.VIDEO_EXTENSIONS:
            videos.extend(folder.rglob(f"*{ext}"))
            videos.extend(folder.rglob(f"*{ext.upper()}"))
        videos = [video for video in videos if not self._is_excluded(video, folder)]
        videos.sort(key=lambda path: path.stat().st_size, reverse=True)
        return videos

    def _is_excluded(self, path: Path, folder: Path) -> bool:
        """True for sample/trailer/extra files, including inside subfolders."""
        rel_path = str(path.relative_to(folder)).lower() if folder else path.name.lower()
        return any(keyword in rel_path for keyword in self.EXCLUDED_KEYWORDS)

    def _entry(self, path: Path) -> Dict:
        """Build an entry dict for a file, parsing SxxExx when present."""
        match = self.EPISODE_PATTERN.search(path.stem)
        if match:
            season, episode = int(match.group(1)), int(match.group(2))
        else:
            season = episode = None
        return {
            "path": path,
            "season": season,
            "episode": episode,
            "title": path.stem,
        }
