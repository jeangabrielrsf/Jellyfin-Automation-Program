"""Tests for the playback and stream endpoints."""
from app.models.download import ContentType, Download, DownloadStatus


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

        response = client.get(f"/api/downloads/{download.id}/playback")

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "direct"
        assert len(data["files"]) == 1
        file = data["files"][0]
        assert file["episode"] is None
        assert file["title"] == "Movie (2023) - 1080p"
        assert file["url"] == f"/api/stream/{download.id}/playlist.m3u8"

    def test_playback_series_pack(self, client, db_session, tmp_path):
        folder = tmp_path / "season"
        folder.mkdir()
        (folder / "Show - S01E02 - 1080p.mkv").write_bytes(b"e2")
        (folder / "Show - S01E01 - 1080p.mkv").write_bytes(b"e1")
        download = create_download(
            db_session,
            type=ContentType.SERIES,
            title="Show",
            season=1,
            status=DownloadStatus.COMPLETED,
            source_folder=str(folder),
        )

        response = client.get(f"/api/downloads/{download.id}/playback")

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "direct"
        assert [f["episode"] for f in data["files"]] == [1, 2]
        assert data["files"][0]["url"] == f"/api/stream/{download.id}/playlist.m3u8?episode=1"
        assert data["files"][1]["url"] == f"/api/stream/{download.id}/playlist.m3u8?episode=2"

    def test_playback_single_episode(self, client, db_session, tmp_path):
        folder = tmp_path / "season"
        folder.mkdir()
        (folder / "Show - S01E02 - 1080p.mkv").write_bytes(b"e2")
        (folder / "Show - S01E05 - 1080p.mkv").write_bytes(b"e5")
        download = create_download(
            db_session,
            type=ContentType.SERIES,
            title="Show",
            season=1,
            episode=5,
            destination_folder=str(folder),
        )

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


class TestStreamEndpoint:
    def test_stream_serves_file(self, client, db_session, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        video = folder / "Movie.mp4"
        video.write_bytes(b"fake mp4 content bytes")
        download = create_download(db_session, destination_folder=str(folder))

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

        response = client.get(
            f"/api/stream/{download.id}/playlist.m3u8", headers={"Range": "bytes=14-"}
        )

        assert response.status_code == 206
        assert response.content == b"ef"
        assert response.headers["content-range"] == f"bytes 14-15/{len(content)}"

    def test_stream_episode_param(self, client, db_session, tmp_path):
        folder = tmp_path / "season"
        folder.mkdir()
        (folder / "Show - S01E01 - 1080p.mkv").write_bytes(b"episode-one")
        (folder / "Show - S01E02 - 1080p.mkv").write_bytes(b"episode-two")
        download = create_download(
            db_session, type=ContentType.SERIES, title="Show", season=1, destination_folder=str(folder)
        )

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
