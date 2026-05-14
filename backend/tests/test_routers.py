"""Tests for API routers and WebSocket."""
import pytest
from unittest.mock import AsyncMock, patch
from app.models.download import Download, DownloadStatus, ContentType
from app.models.settings import Setting


def test_health_check(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


class TestSearchRouter:
    """Tests for search endpoints."""

    @pytest.fixture
    def search_settings(self, db_session):
        """Populate settings needed by TMDBService and JackettScraper."""
        db_session.add(Setting(key="tmdb_api_key", value="test-key"))
        db_session.add(Setting(key="jackett_url", value="http://localhost:9117"))
        db_session.add(Setting(key="jackett_api_key", value="test-api-key"))
        db_session.commit()

    def test_search_media(self, client, search_settings):
        """Test TMDB search endpoint."""
        mock_response = {
            "page": 1,
            "results": [
                {
                    "id": 1,
                    "title": "Test Movie",
                    "overview": "A test",
                    "poster_path": None,
                    "backdrop_path": None,
                    "release_date": "2023-01-01",
                    "vote_average": 8.0,
                    "media_type": "movie",
                    "genre_ids": []
                }
            ],
            "total_pages": 1,
            "total_results": 1
        }

        with patch('app.routers.search.TMDBService.search') as mock_search:
            mock_search.return_value = mock_response
            response = client.get("/api/search/?q=test")
            assert response.status_code == 200
            data = response.json()
            assert data["results"][0]["title"] == "Test Movie"

    def test_get_movie_detail(self, client, search_settings):
        """Test movie detail endpoint."""
        mock_detail = {
            "id": 1,
            "title": "Test Movie",
            "overview": "A test",
            "release_date": "2023-01-01",
            "vote_average": 8.0,
            "genres": [],
            "runtime": 120
        }

        with patch('app.routers.search.TMDBService.get_movie_detail') as mock_get:
            mock_get.return_value = mock_detail
            response = client.get("/api/search/movie/1")
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Test Movie"

    def test_get_tv_detail(self, client, search_settings):
        """Test TV detail endpoint."""
        mock_detail = {
            "id": 1,
            "name": "Test Show",
            "overview": "A test",
            "first_air_date": "2023-01-01",
            "vote_average": 8.0,
            "genres": [],
            "number_of_seasons": 1
        }

        with patch('app.routers.search.TMDBService.get_tv_detail') as mock_get:
            mock_get.return_value = mock_detail
            response = client.get("/api/search/tv/1")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Test Show"

    def test_search_torrents(self, client, search_settings):
        """Test torrent search endpoint with TMDB lookup."""
        from app.models.tmdb import TMDBDetail
        from app.models.torrent import TorrentResult
        mock_detail = TMDBDetail(
            id=1,
            title="Filme Teste",
            original_title="Test Movie",
            overview="A test",
            release_date="2023-01-01",
            vote_average=8.0,
            genres=[],
            runtime=120
        )
        mock_torrents = [
            TorrentResult(
                title="Test Movie 2023 1080p WEB-DL",
                indexer="1337x",
                size="1 GB",
                seeds=100,
                peers=50,
                download_url="http://example.com",
                magnet_url="magnet:?xt=urn:btih:test",
                score=100.0
            ),
            TorrentResult(
                title="Some Unrelated Anime S01E01 1080p",
                indexer="Nyaa",
                size="500 MB",
                seeds=10,
                peers=5,
                download_url="http://example.com/unrelated",
                magnet_url="magnet:?xt=urn:btih:unrelated",
                score=50.0
            ),
        ]

        with patch('app.routers.search.TMDBService.get_movie_detail') as mock_detail_fn:
            mock_detail_fn.return_value = mock_detail
            with patch('app.routers.search.JackettScraper.search') as mock_search:
                mock_search.return_value = mock_torrents
                response = client.get(
                    "/api/search/torrents?tmdb_id=1&media_type=movie"
                )
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["title"] == "Test Movie 2023 1080p WEB-DL"

    def test_get_tv_seasons(self, client, search_settings):
        """Test TV seasons endpoint."""
        from app.models.tmdb import TMDBDetail
        mock_detail = TMDBDetail(
            id=2,
            name="Test Show",
            overview="A test",
            first_air_date="2022-06-15",
            vote_average=7.5,
            genres=[],
            number_of_seasons=2,
            number_of_episodes=20,
            seasons=[
                {"season_number": 0, "name": "Specials", "episode_count": 2},
                {"season_number": 1, "name": "Season 1", "episode_count": 10},
                {"season_number": 2, "name": "Season 2", "episode_count": 10},
            ]
        )

        with patch('app.routers.search.TMDBService.get_tv_detail') as mock_get:
            mock_get.return_value = mock_detail
            response = client.get("/api/search/tv/2/seasons")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["season_number"] == 1
            assert data[0]["episode_count"] == 10
            assert data[1]["season_number"] == 2


class TestDownloadsRouter:
    """Tests for downloads endpoints."""

    def test_list_downloads_empty(self, client):
        """Test listing downloads when empty."""
        response = client.get("/api/downloads/")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_download(self, client, db_session):
        """Test creating a download."""
        payload = {
            "tmdb_id": 1,
            "title": "Test Movie",
            "media_type": "movie",
            "torrent_name": "Test Movie 1080p",
            "magnet_link": "magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12",
            "quality": "1080p",
            "language_preference": "legendado"
        }
        with patch('app.routers.downloads.QBittorrentService') as mock_service_class:
            mock_instance = mock_service_class.return_value
            mock_instance.add_torrent = AsyncMock(return_value=True)
            mock_instance.close = AsyncMock()
            response = client.post("/api/downloads/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Movie"
        assert data["status"] == "downloading"
        assert data["torrent_name"] == "Test Movie 1080p"
        assert data["type"] == "movie"
        mock_instance.add_torrent.assert_awaited_once()
        mock_instance.close.assert_awaited_once()

    def test_create_download_with_season_episode(self, client, db_session):
        """Test creating a download with season and episode."""
        payload = {
            "tmdb_id": 2,
            "title": "Test Show",
            "media_type": "series",
            "torrent_name": "Test.Show.S01E05.1080p",
            "magnet_link": "magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678",
            "quality": "1080p",
            "language_preference": "legendado",
            "season": 1,
            "episode": 5
        }
        with patch('app.routers.downloads.QBittorrentService') as mock_service_class:
            mock_instance = mock_service_class.return_value
            mock_instance.add_torrent = AsyncMock(return_value=True)
            mock_instance.close = AsyncMock()
            response = client.post("/api/downloads/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Show"
        assert data["status"] == "downloading"
        assert data["season"] == 1
        assert data["episode"] == 5
        assert data["source_folder"] is not None
        assert "Test Show" in data["source_folder"]
        mock_instance.add_torrent.assert_awaited_once()
        mock_instance.close.assert_awaited_once()

    def test_create_download_without_magnet_uses_tag_for_hash(self, client, db_session):
        """Test creating a download without magnet link gets hash via tag lookup."""
        payload = {
            "tmdb_id": 3,
            "title": "Test Movie No Magnet",
            "media_type": "movie",
            "torrent_name": "Test Movie No Magnet 1080p",
            "download_url": "http://example.com/torrent",
            "quality": "1080p",
            "language_preference": "legendado"
        }
        with patch('app.routers.downloads.QBittorrentService') as mock_service_class:
            mock_instance = mock_service_class.return_value
            mock_instance.add_torrent = AsyncMock(return_value=True)
            mock_instance.get_torrents_by_tag = AsyncMock(return_value=[
                {"hash": "deadbeef1234567890abcdef1234567890abcdef12"}
            ])
            mock_instance.close = AsyncMock()
            response = client.post("/api/downloads/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Movie No Magnet"
        assert data["status"] == "downloading"
        assert data["torrent_hash"] == "deadbeef1234567890abcdef1234567890abcdef12"
        mock_instance.add_torrent.assert_awaited_once()
        # Verify tag was passed
        call_kwargs = mock_instance.add_torrent.await_args.kwargs
        assert "tags" in call_kwargs
        assert call_kwargs["tags"].startswith("jellyfin-auto-")
        mock_instance.get_torrents_by_tag.assert_awaited_once()
        mock_instance.close.assert_awaited_once()

    def test_get_download(self, client, db_session):
        """Test getting a specific download."""
        download = Download(
            tmdb_id=1,
            title="Test",
            type=ContentType.MOVIE,
            torrent_name="Test",
            magnet_link="magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12",
            status=DownloadStatus.PENDING
        )
        db_session.add(download)
        db_session.commit()
        db_session.refresh(download)

        response = client.get(f"/api/downloads/{download.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test"

    def test_cancel_download(self, client, db_session):
        """Test cancelling a download."""
        download = Download(
            tmdb_id=1,
            title="Test",
            type=ContentType.MOVIE,
            torrent_name="Test",
            magnet_link="magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12",
            status=DownloadStatus.PENDING
        )
        db_session.add(download)
        db_session.commit()
        db_session.refresh(download)

        response = client.delete(f"/api/downloads/{download.id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Download cancelled"

    def test_get_download_not_found(self, client):
        """Test getting a non-existent download."""
        response = client.get("/api/downloads/9999")
        assert response.status_code == 404

    def test_clear_all_downloads(self, client, db_session):
        """Test clearing all completed/failed downloads, skipping active."""
        # Add a completed download
        completed = Download(
            tmdb_id=1,
            title="Completed Movie",
            type=ContentType.MOVIE,
            torrent_name="Test Movie 1080p",
            torrent_hash="abc123abc123abc123abc123abc123abc123abc1",
            status=DownloadStatus.COMPLETED,
        )
        # Add a failed download
        failed = Download(
            tmdb_id=2,
            title="Failed Movie",
            type=ContentType.MOVIE,
            torrent_name="Bad Movie",
            status=DownloadStatus.FAILED,
            error_message="Something went wrong",
        )
        # Add an active download (should be skipped)
        active = Download(
            tmdb_id=3,
            title="Active Movie",
            type=ContentType.MOVIE,
            torrent_name="Downloading Movie",
            torrent_hash="def456def456def456def456def456def456def4",
            status=DownloadStatus.DOWNLOADING,
        )
        db_session.add_all([completed, failed, active])
        db_session.commit()

        with patch('app.routers.downloads.QBittorrentService') as mock_service_class:
            mock_instance = mock_service_class.return_value
            mock_instance.delete_torrent = AsyncMock(return_value=True)
            mock_instance.close = AsyncMock()
            response = client.delete("/api/downloads/")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == 2
        assert data["skipped"] == 1

        # Verify only active remains
        remaining = db_session.query(Download).all()
        assert len(remaining) == 1
        assert remaining[0].status == DownloadStatus.DOWNLOADING

        # Verify qBittorrent delete_torrent was called for completed (not failed, no hash)
        mock_instance.delete_torrent.assert_awaited_once_with("abc123abc123abc123abc123abc123abc123abc1", delete_files=False)
        mock_instance.close.assert_awaited_once()


class TestSettingsRouter:
    """Tests for settings endpoints."""

    def test_get_settings_empty(self, client):
        """Test getting settings when empty."""
        response = client.get("/api/settings/")
        assert response.status_code == 200
        assert response.json() == {}

    def test_create_and_get_setting(self, client, db_session):
        """Test creating and retrieving a setting."""
        response = client.put("/api/settings/movies_path", json="/movies")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "movies_path"
        assert data["value"] == "/movies"

        response = client.get("/api/settings/movies_path")
        assert response.status_code == 200
        assert response.json()["value"] == "/movies"

    def test_get_setting_not_found(self, client):
        """Test getting a non-existent setting."""
        response = client.get("/api/settings/nonexistent")
        assert response.status_code == 404


class TestLogsRouter:
    """Tests for logs endpoints."""

    def test_get_logs_no_file(self, client, tmp_path, monkeypatch):
        """Test getting logs when log file doesn't exist."""
        monkeypatch.chdir(tmp_path)
        response = client.get("/api/logs/")
        assert response.status_code == 200
        data = response.json()
        assert data["logs"] == []
        assert data["total"] == 0


class TestWebSocket:
    """Tests for WebSocket endpoint."""

    def test_websocket_ping_pong(self, client):
        """Test WebSocket ping/pong."""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_websocket_connect_disconnect(self, client):
        """Test WebSocket connection and disconnection."""
        with client.websocket_connect("/ws") as websocket:
            pass  # Connection should open and close cleanly
