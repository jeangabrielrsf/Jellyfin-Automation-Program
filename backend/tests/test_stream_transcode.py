"""Tests for transcode decision (ffprobe detection + cache) and session management.

ffprobe/ffmpeg are mocked; temp dirs and files are real.
"""
import os
import time
from unittest.mock import patch

import pytest

from app.exceptions import StreamLimitError, StreamTranscodeError
from app.services.stream_service import StreamService, StreamSessionManager
from tests.stream_helpers import H264_PROBE, HEVC_PROBE, FakeProcess, make_fake_launch


@pytest.fixture
def service():
    return StreamService()


@pytest.fixture
def video(tmp_path):
    path = tmp_path / "movie.mkv"
    path.write_bytes(b"x" * 100)
    return path


@pytest.fixture
def mp4_video(tmp_path):
    path = tmp_path / "movie.mp4"
    path.write_bytes(b"x" * 100)
    return path


class TestTranscodeDecision:
    def test_h264_mp4_is_direct(self, service, mp4_video):
        with patch.object(StreamService, "_ffprobe", return_value=H264_PROBE) as probe:
            assert service.decide_mode(mp4_video) == "direct"
        assert probe.call_count == 1

    def test_hevc_mkv_is_transcode(self, service, video):
        with patch.object(StreamService, "_ffprobe", return_value=HEVC_PROBE) as probe:
            assert service.decide_mode(video) == "transcode"
        assert probe.call_count == 1

    def test_h264_mkv_is_transcode(self, service, video):
        probe = {
            "format": {"format_name": "matroska,webm"},
            "streams": [{"codec_type": "video", "codec_name": "h264"}],
        }
        with patch.object(StreamService, "_ffprobe", return_value=probe):
            assert service.decide_mode(video) == "transcode"

    def test_hevc_mp4_is_transcode(self, service, video):
        probe = {
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2"},
            "streams": [{"codec_type": "video", "codec_name": "hevc"}],
        }
        with patch.object(StreamService, "_ffprobe", return_value=probe):
            assert service.decide_mode(video) == "transcode"

    def test_second_call_does_not_reprobe(self, service, video):
        with patch.object(StreamService, "_ffprobe", return_value=HEVC_PROBE) as probe:
            assert service.decide_mode(video) == "transcode"
            assert service.decide_mode(video) == "transcode"
        assert probe.call_count == 1

    def test_cache_shared_across_instances(self, video):
        with patch.object(StreamService, "_ffprobe", return_value=HEVC_PROBE) as probe:
            assert StreamService().decide_mode(video) == "transcode"
            assert StreamService().decide_mode(video) == "transcode"
        assert probe.call_count == 1

    def test_cache_invalidated_on_mtime_change(self, service, video):
        with patch.object(StreamService, "_ffprobe", return_value=HEVC_PROBE) as probe:
            assert service.decide_mode(video) == "transcode"

            stat = video.stat()
            os.utime(video, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

            assert service.decide_mode(video) == "transcode"
        assert probe.call_count == 2

    def test_probe_failure_defaults_to_direct(self, service, video):
        with patch.object(StreamService, "_ffprobe", return_value=None):
            assert service.decide_mode(video) == "direct"

    def test_missing_file_raises(self, service, tmp_path):
        with pytest.raises(FileNotFoundError):
            service.decide_mode(tmp_path / "gone.mkv")


@pytest.fixture
def media_file(tmp_path):
    path = tmp_path / "episode.mkv"
    path.write_bytes(b"x" * 100)
    return path


class TestSessionLifecycle:
    def test_get_or_create_spawns_once_and_reuses(self, manager, media_file):
        launch = manager.launch_mock
        first = manager.get_or_create(1, None, media_file)
        second = manager.get_or_create(1, None, media_file)

        assert first is second
        assert launch.call_count == 1
        assert first.is_alive()
        assert first.playlist_path().exists()
        assert first.segment_path("segment_00000.ts").exists()

    def test_session_playlist_served_from_work_dir(self, manager, media_file):
        session = manager.get_or_create(1, None, media_file)
        playlist = session.playlist_path().read_text()
        assert "#EXTM3U" in playlist
        assert "segment_00000.ts" in playlist

    def test_timeout_sweep_kills_process_and_removes_dir(self, tmp_path, media_file):
        manager = StreamSessionManager(session_timeout=0.05, work_root=tmp_path, apply_config=False)
        with patch.object(manager, "_launch_ffmpeg", side_effect=make_fake_launch()):
            session = manager.get_or_create(1, None, media_file)
        work_dir = session.work_dir
        assert work_dir.exists()

        time.sleep(0.06)
        manager.sweep()

        assert session.process.terminated >= 1
        assert not work_dir.exists()
        assert manager.find_by_download(1) is None

    def test_expired_session_frees_capacity(self, tmp_path, media_file):
        manager = StreamSessionManager(max_sessions=1, session_timeout=0.05, work_root=tmp_path, apply_config=False)
        with patch.object(manager, "_launch_ffmpeg", side_effect=make_fake_launch()):
            manager.get_or_create(1, None, media_file)

        time.sleep(0.06)
        manager.sweep()

        with patch.object(manager, "_launch_ffmpeg", side_effect=make_fake_launch()):
            session = manager.get_or_create(2, None, media_file)
        assert session.download_id == 2

    def test_episode_switch_kills_previous_session(self, manager, media_file):
        launch = manager.launch_mock
        first = manager.get_or_create(1, 1, media_file)
        first_dir = first.work_dir

        second = manager.get_or_create(1, 2, media_file)

        assert first.process.terminated >= 1
        assert not first_dir.exists()
        assert second.download_id == 1
        assert second.episode == 2
        assert manager.find_by_download(1) is second
        assert launch.call_count == 2

    def test_fourth_session_rejected(self, tmp_path, media_file):
        manager = StreamSessionManager(max_sessions=3, work_root=tmp_path)
        with patch.object(manager, "_launch_ffmpeg", side_effect=make_fake_launch()):
            for i in range(3):
                manager.get_or_create(i + 1, None, media_file)

            with pytest.raises(StreamLimitError):
                manager.get_or_create(4, None, media_file)

    def test_closed_session_releases_limit(self, tmp_path, media_file):
        manager = StreamSessionManager(max_sessions=1, session_timeout=0.05, work_root=tmp_path, apply_config=False)
        with patch.object(manager, "_launch_ffmpeg", side_effect=make_fake_launch()):
            session = manager.get_or_create(1, None, media_file)

        manager.shutdown()

        assert not session.work_dir.exists()
        with patch.object(manager, "_launch_ffmpeg", side_effect=make_fake_launch()):
            assert manager.get_or_create(2, None, media_file).download_id == 2

    def test_crashed_session_is_recreated(self, manager, media_file):
        """A dead process without a playlist (crash) is recreated on next use."""
        launch = manager.launch_mock
        first = manager.get_or_create(1, None, media_file)
        first.process.kill()
        first.playlist_path().unlink()

        second = manager.get_or_create(1, None, media_file)

        assert second is not first
        assert launch.call_count == 2
        assert manager.find_by_download(1) is second

    def test_finished_transcode_keeps_serving_until_swept(self, manager, media_file):
        """A completed ffmpeg (dead process, playlist present) is still served."""
        session = manager.get_or_create(1, None, media_file)
        session.process.kill()

        assert manager.find_by_download(1) is session
        assert manager.find_by_download(1).segment_path("segment_00000.ts").exists()

    def test_find_by_download_touches_last_access(self, manager, media_file):
        session = manager.get_or_create(1, None, media_file)
        old = session.last_access
        time.sleep(0.01)

        found = manager.find_by_download(1)

        assert found is session
        assert session.last_access >= old

    def test_find_by_download_unknown_download_returns_none(self, manager, media_file):
        manager.get_or_create(1, None, media_file)
        assert manager.find_by_download(999) is None

    def test_ffmpeg_failure_raises_and_cleans(self, tmp_path, media_file):
        manager = StreamSessionManager(work_root=tmp_path)
        with patch.object(manager, "_launch_ffmpeg", return_value=FakeProcess(alive=False)):
            with pytest.raises(StreamTranscodeError):
                manager.get_or_create(1, None, media_file)
        assert manager.find_by_download(1) is None

    def test_config_override_read_from_db(self, media_file):
        with patch("app.services.stream_service.get_config") as get_config:
            get_config.side_effect = lambda key, db=None, required=False: (
                "1" if key == "stream_max_sessions" else ""
            )
            manager = StreamSessionManager()
            with patch.object(manager, "_launch_ffmpeg", side_effect=make_fake_launch()):
                manager.get_or_create(1, None, media_file)
                with pytest.raises(StreamLimitError):
                    manager.get_or_create(2, None, media_file)


@pytest.fixture
def manager(tmp_path):
    """A fresh session manager with mocked ffmpeg launching."""
    manager = StreamSessionManager(work_root=tmp_path)
    launch = patch.object(manager, "_launch_ffmpeg", side_effect=make_fake_launch())
    manager.launch_mock = launch.start()
    yield manager
    launch.stop()
    manager.shutdown()
