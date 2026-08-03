"""Integration tests exercising the HLS pipeline with real ffmpeg/ffprobe.

Skipped by default (see pytest.ini); run with: pytest -m integration
"""
import shutil
import subprocess

import pytest

from app.models.download import ContentType, Download, DownloadStatus
from app.services.stream_service import StreamService, StreamSessionManager, stream_manager

pytestmark = pytest.mark.integration


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def make_video(path, codec="libx264", container="mp4") -> None:
    """Generate a 2-second 320x240 test video with audio."""
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=24:duration=2",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-c:v", codec, "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip(f"ffmpeg could not encode with {codec}: {result.stderr.strip()[-200:]}")
    assert path.exists()


@pytest.fixture(scope="module")
def media_dir(tmp_path_factory):
    if not ffmpeg_available():
        pytest.skip("ffmpeg/ffprobe not installed")
    dir = tmp_path_factory.mktemp("media")
    make_video(dir / "direct.mp4", codec="libx264", container="mp4")
    make_video(dir / "transcode.mkv", codec="libx265", container="mkv")
    return dir


class TestRealPipeline:
    def test_h264_mp4_decided_direct(self, media_dir):
        assert StreamService().decide_mode(media_dir / "direct.mp4") == "direct"

    def test_hevc_mkv_decided_transcode(self, media_dir):
        assert StreamService().decide_mode(media_dir / "transcode.mkv") == "transcode"

    def test_transcode_produces_playable_hls(self, media_dir, tmp_path):
        manager = StreamSessionManager(work_root=tmp_path)
        try:
            session = manager.get_or_create(1, None, media_dir / "transcode.mkv")

            playlist = session.playlist_path()
            assert playlist.exists()
            content = playlist.read_text()
            assert "#EXTM3U" in content
            assert "segment_" in content

            segments = list((session.work_dir / "segments").glob("*.ts"))
            assert len(segments) >= 1

            import json
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=codec_name", "-of", "json", str(segments[0])],
                capture_output=True, text=True, check=True,
            )
            codecs = {
                stream["codec_name"]
                for stream in json.loads(probe.stdout).get("streams", [])
            }
            assert codecs == {"h264"}
        finally:
            manager.shutdown()


def create_download(db_session, **overrides):
    defaults = {
        "tmdb_id": 100,
        "title": "Test Movie",
        "type": ContentType.MOVIE,
        "status": DownloadStatus.ORGANIZED,
    }
    defaults.update(overrides)
    download = Download(**defaults)
    db_session.add(download)
    db_session.commit()
    db_session.refresh(download)
    return download


class TestEndToEnd:
    def test_hevc_plays_end_to_end_via_api(self, client, db_session, media_dir, tmp_path):
        download = create_download(
            db_session, destination_folder=str(media_dir / "transcode.mkv")
        )
        try:
            playback = client.get(f"/api/downloads/{download.id}/playback")
            assert playback.status_code == 200
            assert playback.json()["mode"] == "transcode"

            playlist = client.get(f"/api/stream/{download.id}/playlist.m3u8")
            assert playlist.status_code == 200
            assert playlist.headers["content-type"] == "application/vnd.apple.mpegurl"

            session = stream_manager.find_by_download(download.id)
            assert session is not None
            segment_name = next(
                f.name for f in (session.work_dir / "segments").glob("*.ts")
            )
            segment = client.get(f"/api/stream/{download.id}/{segment_name}")
            assert segment.status_code == 200
            assert segment.headers["content-type"] == "video/mp2t"
            assert len(segment.content) > 0
        finally:
            stream_manager.shutdown()

    def test_mp4_plays_direct_via_api(self, client, db_session, media_dir):
        download = create_download(
            db_session, destination_folder=str(media_dir / "direct.mp4")
        )
        playback = client.get(f"/api/downloads/{download.id}/playback")
        assert playback.status_code == 200
        assert playback.json()["mode"] == "direct"

        stream = client.get(f"/api/stream/{download.id}/playlist.m3u8")
        assert stream.status_code == 200
        assert stream.headers["content-type"] == "video/mp4"
        assert len(stream.content) > 0


class TestSubtitleConversion:
    def test_srt_converted_to_webvtt_with_preserved_timestamps(self, tmp_path):
        """Real ffmpeg conversion: SRT timestamps survive as WebVTT."""
        if not ffmpeg_available():
            pytest.skip("ffmpeg/ffprobe not installed")
        srt = tmp_path / "movie.srt"
        srt.write_text(
            "1\n00:00:01,000 --> 00:00:02,500\nOlá mundo\n\n"
            "2\n00:00:05,000 --> 00:00:07,250\nSegunda legenda\n"
        )

        webvtt = StreamService().to_webvtt(srt)

        # ffmpeg drops the leading hour field when zero (00:00:01.000 → 00:01.000).
        assert webvtt.startswith("WEBVTT")
        assert "00:01.000 --> 00:02.500" in webvtt
        assert "00:05.000 --> 00:07.250" in webvtt
        assert "Olá mundo" in webvtt
        assert "Segunda legenda" in webvtt
