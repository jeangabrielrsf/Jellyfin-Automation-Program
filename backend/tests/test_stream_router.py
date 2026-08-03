"""Tests for the playback and stream endpoints."""
import time
from unittest.mock import patch

import pytest

from app.exceptions import StreamTranscodeError
from app.models.download import ContentType, Download, DownloadStatus
from app.services.stream_service import StreamService, stream_manager
from tests.stream_helpers import H264_PROBE, HEVC_PROBE, make_fake_launch


@pytest.fixture(autouse=True)
def cleanup_stream_sessions():
    """Ensure no stream session leaks between API tests."""
    yield
    stream_manager.shutdown()


def create_download(db_session, **overrides):
    """Persist a Download row and return it with an id."""
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


class TestPlaybackEndpoint:
    def test_playback_movie_direct(self, client, db_session, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        (folder / "sample.mkv").write_bytes(b"x" * 9000)
        video = folder / "Movie (2023) - 1080p.mp4"
        video.write_bytes(b"x" * 1000)
        download = create_download(db_session, destination_folder=str(folder))

        with patch.object(StreamService, "_ffprobe", return_value=H264_PROBE):
            response = client.get(f"/api/downloads/{download.id}/playback")

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "direct"
        assert len(data["files"]) == 1
        file = data["files"][0]
        assert file["episode"] is None
        assert file["title"] == "Movie (2023) - 1080p"
        assert file["mode"] == "direct"
        assert file["url"] == f"/api/stream/{download.id}/playlist.m3u8"

    def test_playback_movie_transcode_for_hevc(self, client, db_session, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        video = folder / "Movie (2023) - 1080p.mkv"
        video.write_bytes(b"x" * 1000)
        download = create_download(db_session, destination_folder=str(folder))

        with patch.object(StreamService, "_ffprobe", return_value=HEVC_PROBE):
            response = client.get(f"/api/downloads/{download.id}/playback")

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "transcode"
        assert len(data["files"]) == 1
        assert data["files"][0]["mode"] == "transcode"

    def test_playback_series_pack(self, client, db_session, tmp_path):
        folder = tmp_path / "season"
        folder.mkdir()
        (folder / "Show - S01E02 - 1080p.mp4").write_bytes(b"e2")
        (folder / "Show - S01E01 - 1080p.mp4").write_bytes(b"e1")
        download = create_download(
            db_session,
            type=ContentType.SERIES,
            title="Show",
            season=1,
            status=DownloadStatus.COMPLETED,
            source_folder=str(folder),
        )

        with patch.object(StreamService, "_ffprobe", return_value=H264_PROBE):
            response = client.get(f"/api/downloads/{download.id}/playback")

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "direct"
        assert [f["episode"] for f in data["files"]] == [1, 2]
        assert data["files"][0]["url"] == f"/api/stream/{download.id}/playlist.m3u8?episode=1"
        assert data["files"][1]["url"] == f"/api/stream/{download.id}/playlist.m3u8?episode=2"

    def test_playback_mixed_pack_is_transcode(self, client, db_session, tmp_path):
        """A pack with any non-direct file reports transcode mode."""
        folder = tmp_path / "season"
        folder.mkdir()
        (folder / "Show - S01E01 - 1080p.mp4").write_bytes(b"e1")
        (folder / "Show - S01E02 - 1080p.mkv").write_bytes(b"e2")
        download = create_download(
            db_session,
            type=ContentType.SERIES,
            title="Show",
            season=1,
            source_folder=str(folder),
        )

        def probe_by_suffix(path):
            return H264_PROBE if path.suffix == ".mp4" else HEVC_PROBE

        with patch.object(StreamService, "_ffprobe", side_effect=probe_by_suffix):
            response = client.get(f"/api/downloads/{download.id}/playback")

        assert response.status_code == 200
        assert response.json()["mode"] == "transcode"
        assert [f["mode"] for f in response.json()["files"]] == ["direct", "transcode"]

    def test_playback_direct_pack_probes_every_file(self, client, db_session, tmp_path):
        """An all-direct pack probes each file (cached afterwards)."""
        folder = tmp_path / "season"
        folder.mkdir()
        (folder / "Show - S01E01 - 1080p.mp4").write_bytes(b"e1")
        (folder / "Show - S01E02 - 1080p.mp4").write_bytes(b"e2")
        download = create_download(
            db_session,
            type=ContentType.SERIES,
            title="Show",
            season=1,
            source_folder=str(folder),
        )

        with patch.object(StreamService, "_ffprobe", return_value=H264_PROBE) as probe:
            response = client.get(f"/api/downloads/{download.id}/playback")
            assert probe.call_count == 2

        assert response.status_code == 200
        assert response.json()["mode"] == "direct"

    def test_playback_single_episode(self, client, db_session, tmp_path):
        folder = tmp_path / "season"
        folder.mkdir()
        (folder / "Show - S01E02 - 1080p.mp4").write_bytes(b"e2")
        (folder / "Show - S01E05 - 1080p.mp4").write_bytes(b"e5")
        download = create_download(
            db_session,
            type=ContentType.SERIES,
            title="Show",
            season=1,
            episode=5,
            destination_folder=str(folder),
        )

        with patch.object(StreamService, "_ffprobe", return_value=H264_PROBE):
            response = client.get(f"/api/downloads/{download.id}/playback")

        assert response.status_code == 200
        data = response.json()
        assert len(data["files"]) == 1
        assert data["files"][0]["episode"] == 5
        assert data["files"][0]["url"] == f"/api/stream/{download.id}/playlist.m3u8?episode=5"

    def test_playback_download_not_found(self, client, db_session):
        response = client.get("/api/downloads/999/playback")
        assert response.status_code == 404
        assert response.json()["detail"] == "Download not found"

    def test_playback_missing_folder_404(self, client, db_session, tmp_path):
        download = create_download(db_session, destination_folder=str(tmp_path / "gone"))

        response = client.get(f"/api/downloads/{download.id}/playback")

        assert response.status_code == 404
        assert "não encontrado" in response.json()["detail"]


class TestSubtitleEndpoint:
    SAMPLE_WEBVTT = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nOi\n"

    def test_playback_includes_subtitle_url_with_srt(self, client, db_session, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        video = folder / "Movie (2023) - 1080p.mp4"
        video.write_bytes(b"x" * 1000)
        (folder / "Movie (2023) - 1080p.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\nOi\n")
        download = create_download(db_session, destination_folder=str(folder))

        with patch.object(StreamService, "_ffprobe", return_value=H264_PROBE):
            response = client.get(f"/api/downloads/{download.id}/playback")

        assert response.status_code == 200
        assert response.json()["subtitle_url"] == f"/api/stream/{download.id}/subtitle.vtt"

    def test_playback_omits_subtitle_url_without_srt(self, client, db_session, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        (folder / "Movie (2023) - 1080p.mp4").write_bytes(b"x" * 1000)
        download = create_download(db_session, destination_folder=str(folder))

        with patch.object(StreamService, "_ffprobe", return_value=H264_PROBE):
            response = client.get(f"/api/downloads/{download.id}/playback")

        assert response.status_code == 200
        assert "subtitle_url" not in response.json()

    def test_playback_subtitle_url_carries_episode_for_packs(
        self, client, db_session, tmp_path
    ):
        """A pack's subtitle_url targets the first episode's srt."""
        folder = tmp_path / "season"
        folder.mkdir()
        (folder / "Show - S01E01 - 1080p.mp4").write_bytes(b"e1")
        (folder / "Show - S01E02 - 1080p.mp4").write_bytes(b"e2")
        (folder / "Show - S01E01 - 1080p.srt").write_text("srt1")
        download = create_download(
            db_session,
            type=ContentType.SERIES,
            title="Show",
            season=1,
            destination_folder=str(folder),
        )

        with patch.object(StreamService, "_ffprobe", return_value=H264_PROBE):
            response = client.get(f"/api/downloads/{download.id}/playback")

        assert response.status_code == 200
        assert (
            response.json()["subtitle_url"]
            == f"/api/stream/{download.id}/subtitle.vtt?episode=1"
        )

    def test_subtitle_serves_webvtt(self, client, db_session, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        (folder / "Movie.mp4").write_bytes(b"x" * 1000)
        (folder / "Movie.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\nOi\n")
        download = create_download(db_session, destination_folder=str(folder))

        with patch.object(StreamService, "to_webvtt", return_value=self.SAMPLE_WEBVTT) as convert:
            response = client.get(f"/api/stream/{download.id}/subtitle.vtt")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/vtt")
        assert response.text == self.SAMPLE_WEBVTT
        convert.assert_called_once()

    def test_subtitle_honors_episode_param(self, client, db_session, tmp_path):
        """?episode=N resolves that episode's srt."""
        folder = tmp_path / "season"
        folder.mkdir()
        (folder / "Show - S01E01 - 1080p.mp4").write_bytes(b"e1")
        (folder / "Show - S01E02 - 1080p.mp4").write_bytes(b"e2")
        (folder / "Show - S01E02 - 1080p.srt").write_text("srt2")
        download = create_download(
            db_session,
            type=ContentType.SERIES,
            title="Show",
            season=1,
            destination_folder=str(folder),
        )

        with patch.object(StreamService, "to_webvtt", return_value=self.SAMPLE_WEBVTT) as convert:
            response = client.get(f"/api/stream/{download.id}/subtitle.vtt?episode=2")

        assert response.status_code == 200
        srt_arg = convert.call_args.args[0]
        assert srt_arg.name == "Show - S01E02 - 1080p.srt"

    def test_subtitle_without_srt_404(self, client, db_session, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        (folder / "Movie.mp4").write_bytes(b"x" * 1000)
        download = create_download(db_session, destination_folder=str(folder))

        response = client.get(f"/api/stream/{download.id}/subtitle.vtt")

        assert response.status_code == 404
        assert "Legenda" in response.json()["detail"]

    def test_subtitle_missing_folder_404(self, client, db_session, tmp_path):
        download = create_download(db_session, destination_folder=str(tmp_path / "gone"))

        response = client.get(f"/api/stream/{download.id}/subtitle.vtt")

        assert response.status_code == 404

    def test_subtitle_conversion_failure_500(self, client, db_session, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        (folder / "Movie.mp4").write_bytes(b"x" * 1000)
        (folder / "Movie.srt").write_text("broken")
        download = create_download(db_session, destination_folder=str(folder))

        with patch.object(
            StreamService,
            "to_webvtt",
            side_effect=StreamTranscodeError("Falha ao converter"),
        ):
            response = client.get(f"/api/stream/{download.id}/subtitle.vtt")

        assert response.status_code == 500

    def test_subtitle_download_not_found(self, client, db_session):
        response = client.get("/api/stream/999/subtitle.vtt")
        assert response.status_code == 404
        assert response.json()["detail"] == "Download not found"


class TestStreamEndpoint:
    def test_stream_serves_file(self, client, db_session, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        video = folder / "Movie.mp4"
        video.write_bytes(b"fake mp4 content bytes")
        download = create_download(db_session, destination_folder=str(folder))

        with patch.object(StreamService, "_ffprobe", return_value=H264_PROBE):
            response = client.get(f"/api/stream/{download.id}/playlist.m3u8")

        assert response.status_code == 200
        assert response.content == b"fake mp4 content bytes"
        assert response.headers["content-type"] == "video/mp4"

    def test_stream_range_request(self, client, db_session, tmp_path):
        """Seek support: a Range request returns 206 with the right slice."""
        folder = tmp_path / "movie"
        folder.mkdir()
        content = b"0123456789abcdef"
        (folder / "Movie.mp4").write_bytes(content)
        download = create_download(db_session, destination_folder=str(folder))

        with patch.object(StreamService, "_ffprobe", return_value=H264_PROBE):
            response = client.get(
                f"/api/stream/{download.id}/playlist.m3u8", headers={"Range": "bytes=4-7"}
            )

        assert response.status_code == 206
        assert response.content == b"4567"
        assert response.headers["content-range"] == f"bytes 4-7/{len(content)}"
        assert response.headers["accept-ranges"] == "bytes"

    def test_stream_open_ended_range(self, client, db_session, tmp_path):
        """An open-ended Range request (bytes=N-) serves from N to the end."""
        folder = tmp_path / "movie"
        folder.mkdir()
        content = b"0123456789abcdef"
        (folder / "Movie.mp4").write_bytes(content)
        download = create_download(db_session, destination_folder=str(folder))

        with patch.object(StreamService, "_ffprobe", return_value=H264_PROBE):
            response = client.get(
                f"/api/stream/{download.id}/playlist.m3u8", headers={"Range": "bytes=14-"}
            )

        assert response.status_code == 206
        assert response.content == b"ef"
        assert response.headers["content-range"] == f"bytes 14-15/{len(content)}"

    def test_stream_episode_param(self, client, db_session, tmp_path):
        folder = tmp_path / "season"
        folder.mkdir()
        (folder / "Show - S01E01 - 1080p.mp4").write_bytes(b"episode-one")
        (folder / "Show - S01E02 - 1080p.mp4").write_bytes(b"episode-two")
        download = create_download(
            db_session, type=ContentType.SERIES, title="Show", season=1, destination_folder=str(folder)
        )

        with patch.object(StreamService, "_ffprobe", return_value=H264_PROBE):
            response = client.get(f"/api/stream/{download.id}/playlist.m3u8?episode=2")

        assert response.status_code == 200
        assert response.content == b"episode-two"

    def test_stream_missing_file_404(self, client, db_session, tmp_path):
        download = create_download(db_session, destination_folder=str(tmp_path / "gone"))

        response = client.get(f"/api/stream/{download.id}/playlist.m3u8")

        assert response.status_code == 404
        assert "não encontrado" in response.json()["detail"]

    def test_stream_download_not_found(self, client, db_session):
        response = client.get("/api/stream/999/playlist.m3u8")
        assert response.status_code == 404
        assert response.json()["detail"] == "Download not found"


class TestTranscodeEndpoint:
    def test_playlist_transcode_serves_hls(self, client, db_session, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        (folder / "Movie.mkv").write_bytes(b"x" * 100)
        download = create_download(db_session, destination_folder=str(folder))

        with patch.object(StreamService, "_ffprobe", return_value=HEVC_PROBE):
            with patch.object(stream_manager, "_launch_ffmpeg", side_effect=make_fake_launch()):
                response = client.get(f"/api/stream/{download.id}/playlist.m3u8")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.apple.mpegurl"
        assert b"#EXTM3U" in response.content
        assert b"segment_00000.ts" in response.content

    def test_playlist_transcode_reuses_session(self, client, db_session, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        (folder / "Movie.mkv").write_bytes(b"x" * 100)
        download = create_download(db_session, destination_folder=str(folder))

        with patch.object(StreamService, "_ffprobe", return_value=HEVC_PROBE):
            with patch.object(
                stream_manager, "_launch_ffmpeg", side_effect=make_fake_launch()
            ) as launch:
                client.get(f"/api/stream/{download.id}/playlist.m3u8")
                response = client.get(f"/api/stream/{download.id}/playlist.m3u8")

        assert response.status_code == 200
        assert launch.call_count == 1

    def test_playlist_transcode_episode_switch_kills_previous(
        self, client, db_session, tmp_path
    ):
        folder = tmp_path / "season"
        folder.mkdir()
        (folder / "Show - S01E01 - 1080p.mkv").write_bytes(b"e1")
        (folder / "Show - S01E02 - 1080p.mkv").write_bytes(b"e2")
        download = create_download(
            db_session, type=ContentType.SERIES, title="Show", season=1, source_folder=str(folder)
        )

        with patch.object(StreamService, "_ffprobe", return_value=HEVC_PROBE):
            with patch.object(
                stream_manager, "_launch_ffmpeg", side_effect=make_fake_launch()
            ) as launch:
                first = client.get(f"/api/stream/{download.id}/playlist.m3u8?episode=1")
                first_session = stream_manager.find_by_download(download.id)
                second = client.get(f"/api/stream/{download.id}/playlist.m3u8?episode=2")

        assert first.status_code == 200
        assert second.status_code == 200
        assert launch.call_count == 2
        assert first_session is not None
        assert not first_session.work_dir.exists()
        current = stream_manager.find_by_download(download.id)
        assert current is not None and current.episode == 2

    def test_segment_served_from_session(self, client, db_session, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        (folder / "Movie.mkv").write_bytes(b"x" * 100)
        download = create_download(db_session, destination_folder=str(folder))

        with patch.object(StreamService, "_ffprobe", return_value=HEVC_PROBE):
            with patch.object(stream_manager, "_launch_ffmpeg", side_effect=make_fake_launch()):
                client.get(f"/api/stream/{download.id}/playlist.m3u8")
                response = client.get(f"/api/stream/{download.id}/segment_00000.ts")

        assert response.status_code == 200
        assert response.content == b"ts-data"
        assert response.headers["content-type"] == "video/mp2t"

    def test_segment_without_session_404(self, client, db_session, tmp_path):
        download = create_download(db_session, destination_folder=str(tmp_path / "movie-missing"))

        response = client.get(f"/api/stream/{download.id}/segment_00000.ts")

        assert response.status_code == 404

    def test_segment_path_traversal_blocked(self, client, db_session, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        (folder / "Movie.mkv").write_bytes(b"x" * 100)
        download = create_download(db_session, destination_folder=str(folder))

        with patch.object(StreamService, "_ffprobe", return_value=HEVC_PROBE):
            with patch.object(stream_manager, "_launch_ffmpeg", side_effect=make_fake_launch()):
                client.get(f"/api/stream/{download.id}/playlist.m3u8")
                response = client.get(f"/api/stream/{download.id}/..%2Findex.m3u8")

        assert response.status_code == 404

    def test_fourth_session_gets_503(self, client, db_session, tmp_path):
        for i in range(4):
            folder = tmp_path / f"movie{i}"
            folder.mkdir()
            (folder / "Movie.mkv").write_bytes(b"x" * 100)
            create_download(db_session, destination_folder=str(folder))

        with patch.object(StreamService, "_ffprobe", return_value=HEVC_PROBE):
            with patch.object(stream_manager, "_launch_ffmpeg", side_effect=make_fake_launch()):
                for i in range(3):
                    response = client.get(f"/api/stream/{i + 1}/playlist.m3u8")
                    assert response.status_code == 200
                response = client.get("/api/stream/4/playlist.m3u8")

        assert response.status_code == 503
        assert "streams" in response.json()["detail"]

    def test_expired_session_recreated_on_next_request(self, client, db_session, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        (folder / "Movie.mkv").write_bytes(b"x" * 100)
        download = create_download(db_session, destination_folder=str(folder))

        with patch.object(StreamService, "_ffprobe", return_value=HEVC_PROBE):
            with patch("app.services.stream_service.get_config") as get_config:
                get_config.side_effect = lambda key, db=None, required=False: (
                    "0.05" if key == "stream_session_timeout" else ""
                )
                with patch.object(
                    stream_manager, "_launch_ffmpeg", side_effect=make_fake_launch()
                ) as launch:
                    first = client.get(f"/api/stream/{download.id}/playlist.m3u8")
                    first_session = stream_manager.find_by_download(download.id)
                    assert first_session is not None
                    first_dir = first_session.work_dir

                    time.sleep(0.06)
                    second = client.get(f"/api/stream/{download.id}/playlist.m3u8")

        assert first.status_code == 200
        assert second.status_code == 200
        assert launch.call_count == 2
        assert not first_dir.exists()
