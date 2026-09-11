"""Stream service — file resolution, direct-vs-transcode decision, HLS sessions."""
import json
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.exceptions import StreamLimitError, StreamTranscodeError
from app.logging_config import get_logger
from app.models.download import ContentType
from app.services.config_service import get_config

logger = get_logger(__name__)


class StreamService:
    """Resolve the playable file(s) for a Download and decide direct vs transcode.

    Direct playback is served as-is; unsupported codecs (MKV/HEVC) go through
    an HLS transcode session managed by StreamSessionManager.
    """

    VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.webm'}
    SUBTITLE_EXTENSIONS = {'.srt'}
    EXCLUDED_KEYWORDS = ('sample', 'trailer', 'extra', 'featurette')
    EPISODE_PATTERN = re.compile(r"[Ss](\d{1,2})[Ee](\d{1,2})")

    DIRECT_VIDEO_CODECS = {"h264", "vp8", "vp9", "av1"}
    DIRECT_CONTAINERS = {".mp4", ".webm", ".m4v", ".mov"}

    # Cache keyed by (path, mtime_ns), shared across instances so ffprobe
    # runs once per file per modification.
    _probe_cache: Dict[Tuple[str, int], str] = {}

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

    def resolve_subtitle(self, download, episode: Optional[int] = None) -> Optional[Path]:
        """Resolve the .srt sidecar next to the video for a download.

        The video is resolved first (same rules as resolve_file), then the
        .srt in the video's directory is looked up: an exact basename match
        wins; otherwise a single .srt is used, but only when the folder has
        a single playable video (so a pack never attaches one episode's
        subtitles to another). Returns None when no .srt resolves.

        Raises:
            FileNotFoundError: When the video itself cannot be resolved.
        """
        video = self.resolve_file(download, episode)
        folder = video.parent
        srts = sorted(
            path
            for path in folder.iterdir()
            if path.is_file()
            and path.suffix.lower() in self.SUBTITLE_EXTENSIONS
            and not self._is_excluded(path, folder)
        )
        for srt in srts:
            if srt.stem.lower() == video.stem.lower():
                return srt
        videos = [
            path
            for path in folder.iterdir()
            if path.is_file()
            and path.suffix.lower() in self.VIDEO_EXTENSIONS
            and not self._is_excluded(path, folder)
        ]
        if len(srts) == 1 and len(videos) == 1:
            return srts[0]
        return None

    def to_webvtt(self, srt_path: Path) -> str:
        """Convert an .srt file to WebVTT text via ffmpeg (-f webvtt).

        Raises:
            StreamTranscodeError: When ffmpeg is missing, times out or fails.
        """
        cmd = [
            "ffmpeg", "-v", "error", "-nostdin",
            "-i", str(srt_path),
            "-f", "webvtt",
            "pipe:1",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise StreamTranscodeError(
                f"Falha ao converter a legenda {srt_path.name}: {exc}"
            ) from exc
        if result.returncode != 0:
            raise StreamTranscodeError(
                f"Falha ao converter a legenda {srt_path.name} para WebVTT"
            )
        return result.stdout

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

    def decide_mode(self, path: Path) -> str:
        """Return "direct" or "transcode" for a file, via ffprobe with cache.

        The probe result is cached in memory keyed by (path, mtime_ns), so a
        file is only probed again after it changes on disk.
        """
        if not path.exists():
            raise FileNotFoundError(f"Arquivo de mídia não encontrado no disco: {path}")
        stat = path.stat()
        key = (str(path), stat.st_mtime_ns)
        cached = self._probe_cache.get(key)
        if cached is not None:
            return cached
        mode = self._probe_mode(path)
        self._probe_cache[key] = mode
        return mode

    def _probe_mode(self, path: Path) -> str:
        """Run ffprobe and decide whether the browser can play the file as-is.

        The container comes from the file extension (ffprobe reports MKV as
        "matroska,webm", which would wrongly mark it direct); the codec comes
        from the first video stream.
        """
        info = self._ffprobe(path)
        if not info:
            logger.warning("ffprobe failed; falling back to direct playback", path=str(path))
            return "direct"

        codec = None
        for stream in info.get("streams") or []:
            if stream.get("codec_type") == "video":
                codec = stream.get("codec_name")
                break

        container = path.suffix.lower()
        if codec in self.DIRECT_VIDEO_CODECS and container in self.DIRECT_CONTAINERS:
            return "direct"
        return "transcode"

    def _ffprobe(self, path: Path) -> Optional[Dict]:
        """Probe the first video stream of a file; None when probing fails."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=format_name:stream=codec_type,codec_name",
            "-of", "json",
            str(path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if result.returncode != 0:
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None


class StreamSession:
    """An active HLS transcode: an ffmpeg process plus its segments directory."""

    def __init__(self, download_id: int, episode: Optional[int], input_path, work_dir, process):
        self.download_id = download_id
        self.episode = episode
        self.input_path = Path(input_path)
        self.work_dir = Path(work_dir)
        self.process = process
        self.last_access = time.monotonic()

    def touch(self) -> None:
        """Mark the session as recently used (playlist or segment request)."""
        self.last_access = time.monotonic()

    def is_alive(self) -> bool:
        """True while segments can still be served.

        Either ffmpeg is still running, or it finished and left a playlist
        behind (short videos transcode so fast the process is gone by the
        time the client asks for segments). Only a dead process without a
        playlist is treated as failed.
        """
        if self.process is None:
            return False
        if self.process.poll() is None:
            return True
        return self.playlist_path().exists()

    def playlist_path(self) -> Path:
        return self.work_dir / "index.m3u8"

    def segment_path(self, filename: str) -> Path:
        """Resolve a segment inside the session's segments dir.

        Returns None when the filename escapes the segments directory
        (path traversal attempt).
        """
        segments_dir = (self.work_dir / "segments").resolve()
        segment = (segments_dir / filename).resolve()
        if not segment.is_relative_to(segments_dir):
            return None
        return segment

    def kill(self) -> None:
        """Terminate the ffmpeg process, escalating to SIGKILL if needed."""
        _kill_process(self.process)


class StreamSessionManager:
    """Owns the HLS transcode sessions: lifecycle, capacity and sweeping.

    Sessions are keyed by (download_id, episode). At most one session per
    download survives: starting a different episode of the same download
    kills the previous session. Capacity (default 3) is enforced like a
    counting semaphore — StreamLimitError when full, freed when a session
    dies, times out or is shut down.
    """

    def __init__(
        self,
        max_sessions: int = 3,
        session_timeout: float = 60.0,
        work_root: Optional[Path] = None,
        ffmpeg_bin: str = "ffmpeg",
        apply_config: bool = True,
    ):
        self._max_sessions = max_sessions
        self._session_timeout = session_timeout
        self._config_enabled = apply_config
        self._work_root = work_root
        self.ffmpeg_bin = ffmpeg_bin
        self._sessions: Dict[Tuple[int, Optional[int]], StreamSession] = {}
        self._active = 0
        self._lock = threading.Lock()
        self._sweep_interval = 10.0
        self._sweeper_stop = threading.Event()
        self._sweeper_thread: Optional[threading.Thread] = None

    @property
    def max_sessions(self) -> int:
        return self._max_sessions

    @property
    def session_timeout(self) -> float:
        return self._session_timeout

    def _apply_config(self, db=None) -> None:
        """Pick up stream_max_sessions / stream_session_timeout from config.

        Disabled for instances constructed with apply_config=False (tests
        that want constructor values to stand).
        """
        if not self._config_enabled:
            return
        max_val = get_config("stream_max_sessions", db, required=False)
        timeout_val = get_config("stream_session_timeout", db, required=False)
        if max_val:
            self._max_sessions = int(max_val)
        if timeout_val:
            self._session_timeout = float(timeout_val)

    def get_or_create(
        self, download_id: int, episode: Optional[int], input_path, db=None
    ) -> StreamSession:
        """Return the live session for (download_id, episode), creating it lazily.

        Raises StreamLimitError when the capacity is full, or
        StreamTranscodeError when ffmpeg fails to produce a playlist.
        """
        with self._lock:
            self._apply_config(db)
            self._sweep_locked()

            key = (download_id, episode)
            existing = self._sessions.get(key)
            if existing is not None:
                if existing.is_alive():
                    existing.touch()
                    return existing
                self._remove_locked(existing)

            old = self._find_by_download_locked(download_id)
            if old is not None:
                self._remove_locked(old)

            if self._active >= self._max_sessions:
                raise StreamLimitError(self._max_sessions)

            session = self._spawn_session(download_id, episode, input_path)
            self._sessions[key] = session
            self._active += 1
            logger.info(
                "Stream session started",
                download_id=download_id,
                episode=episode,
                work_dir=str(session.work_dir),
            )
            return session

    def find_by_download(self, download_id: int) -> Optional[StreamSession]:
        """Return the live session for a download, touching it; None otherwise."""
        with self._lock:
            session = self._find_by_download_locked(download_id)
            if session is None:
                return None
            if not session.is_alive():
                self._remove_locked(session)
                return None
            session.touch()
            return session

    def _find_by_download_locked(self, download_id: int) -> Optional[StreamSession]:
        candidates = [
            session
            for (did, _episode), session in self._sessions.items()
            if did == download_id
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda session: session.last_access)

    def sweep(self, db=None) -> None:
        """Kill sessions idle past the timeout and remove their directories."""
        with self._lock:
            self._apply_config(db)
            self._sweep_locked()

    def _sweep_locked(self) -> None:
        now = time.monotonic()
        stale = [
            session
            for session in self._sessions.values()
            if now - session.last_access > self._session_timeout
        ]
        for session in stale:
            logger.info(
                "Stream session expired",
                download_id=session.download_id,
                episode=session.episode,
            )
            self._remove_locked(session)

    def shutdown(self) -> None:
        """Kill every session and clear all state."""
        with self._lock:
            for session in list(self._sessions.values()):
                self._remove_locked(session)
            self._active = 0

    def _remove_locked(self, session: StreamSession) -> None:
        key = (session.download_id, session.episode)
        if self._sessions.pop(key, None) is session:
            self._active -= 1
        session.kill()
        shutil.rmtree(session.work_dir, ignore_errors=True)

    def _spawn_session(
        self, download_id: int, episode: Optional[int], input_path
    ) -> StreamSession:
        work_dir = Path(tempfile.mkdtemp(prefix=f"stream-{download_id}-", dir=self._work_root))
        try:
            (work_dir / "segments").mkdir()
            process = self._launch_ffmpeg(input_path, work_dir)
        except Exception as exc:
            shutil.rmtree(work_dir, ignore_errors=True)
            raise StreamTranscodeError(f"Falha ao iniciar ffmpeg: {exc}") from exc

        if not self._wait_for_playlist(work_dir, process):
            _kill_process(process)
            shutil.rmtree(work_dir, ignore_errors=True)
            raise StreamTranscodeError(
                f"ffmpeg não produziu a playlist HLS a tempo para o download {download_id}"
            )

        return StreamSession(download_id, episode, input_path, work_dir, process)

    def _launch_ffmpeg(self, input_path, work_dir: Path):
        """Start ffmpeg transcoding input_path into HLS segments in work_dir."""
        cmd = [
            self.ffmpeg_bin, "-v", "error", "-nostdin",
            "-i", str(input_path),
            "-map", "0:v:0",
            "-map", "0:a:0?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-f", "hls",
            "-hls_time", "6",
            "-hls_list_size", "0",
            "-hls_segment_filename", str(work_dir / "segments" / "segment_%05d.ts"),
            str(work_dir / "index.m3u8"),
        ]
        return subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _wait_for_playlist(self, work_dir: Path, process, timeout: float = 15.0) -> bool:
        """Wait until ffmpeg wrote index.m3u8, or the process died/timed out.

        The playlist is checked first: a short input may finish transcoding
        (writing the playlist) and exit between polls.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if (work_dir / "index.m3u8").exists():
                return True
            if process.poll() is not None:
                return False
            time.sleep(0.1)
        return False

    def start_sweeper(self, interval: Optional[float] = None) -> None:
        """Start the periodic background sweep (idempotent)."""
        if interval is not None:
            self._sweep_interval = interval
        if self._sweeper_thread is not None and self._sweeper_thread.is_alive():
            return
        self._sweeper_stop.clear()
        self._sweeper_thread = threading.Thread(
            target=self._sweep_loop, name="stream-sweeper", daemon=True
        )
        self._sweeper_thread.start()

    def stop_sweeper(self) -> None:
        """Stop the background sweep thread if running."""
        self._sweeper_stop.set()
        thread, self._sweeper_thread = self._sweeper_thread, None
        if thread is not None:
            thread.join(timeout=5)

    def _sweep_loop(self) -> None:
        while not self._sweeper_stop.wait(self._sweep_interval):
            try:
                self.sweep()
            except Exception:
                logger.exception("Stream sweeper error")


def _kill_process(process) -> None:
    """Terminate a process, escalating to SIGKILL if it does not exit in time."""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


stream_manager = StreamSessionManager()
