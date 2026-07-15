"""Tests for JackettClient adapter."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.clients.jackett_client import JackettClient


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    return db


@pytest.fixture
def jackett_client(mock_db):
    """Create JackettClient instance with mocked config."""
    with patch('app.clients.jackett_client.get_config') as mock_config:
        mock_config.side_effect = lambda key, db, required=False: {
            'jackett_url': 'http://localhost:9117',
            'jackett_api_key': 'test-api-key',
            'jackett_timeout': '120'
        }.get(key, '')
        client = JackettClient(db=mock_db)
        yield client


class TestJackettClientSearch:
    """Tests for JackettClient.search() method."""
    
    @pytest.mark.asyncio
    async def test_search_returns_raw_results(self, jackett_client):
        """search() should return raw Jackett Results as list[dict]."""
        mock_response = {
            "Results": [
                {
                    "Title": "Test Movie 1080p",
                    "Size": 1073741824,
                    "Seeders": 100,
                    "Peers": 50,
                    "Link": "http://example.com/torrent.torrent",
                    "MagnetUri": "magnet:?xt=urn:btih:abc123",
                    "Tracker": "TestTracker"
                },
                {
                    "Title": "Test Movie 720p",
                    "Size": 536870912,
                    "Seeders": 50,
                    "Peers": 25,
                    "Link": "http://example.com/torrent2.torrent",
                    "MagnetUri": "magnet:?xt=urn:btih:def456",
                    "Tracker": "TestTracker"
                }
            ]
        }
        
        with patch.object(jackett_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
            
            results = await jackett_client.search("Test Movie", category=[2000])
            
            assert len(results) == 2
            assert results[0]["Title"] == "Test Movie 1080p"
            assert results[1]["Title"] == "Test Movie 720p"
            
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "apikey" in call_args.kwargs["params"]
            assert call_args.kwargs["params"]["Query"] == "Test Movie"
            assert call_args.kwargs["params"]["Category"] == [2000]
    
    @pytest.mark.asyncio
    async def test_search_with_empty_results(self, jackett_client):
        """search() should return empty list when no results found."""
        mock_response = {"Results": []}
        
        with patch.object(jackett_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
            
            results = await jackett_client.search("Nonexistent Movie", category=[2000])
            
            assert results == []
    
    @pytest.mark.asyncio
    async def test_search_handles_http_error(self, jackett_client):
        """search() should return empty list on HTTP error."""
        with patch.object(jackett_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection failed")
            
            results = await jackett_client.search("Test Movie", category=[2000])
            
            assert results == []


class TestJackettClientDownloadTorrentFile:
    """Tests for JackettClient.download_torrent_file() method."""
    
    @pytest.mark.asyncio
    async def test_download_torrent_file_returns_bytes(self, jackett_client):
        """download_torrent_file() should return torrent file bytes."""
        torrent_bytes = b"fake torrent content"
        
        with patch.object(jackett_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock(
                status_code=200,
                content=torrent_bytes,
                headers={'content-type': 'application/x-bittorrent'},
                raise_for_status=lambda: None
            )
            mock_get.return_value = mock_response
            
            result = await jackett_client.download_torrent_file(
                tracker_id="tracker123",
                path="http://example.com/torrent.torrent",
                filename="test.torrent"
            )
            
            assert result == torrent_bytes
            
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "/dl/tracker123" in call_args.args[0]
            assert call_args.kwargs["params"]["path"] == "http://example.com/torrent.torrent"
            assert call_args.kwargs["params"]["file"] == "test.torrent"
    
    @pytest.mark.asyncio
    async def test_download_torrent_file_without_filename(self, jackett_client):
        """download_torrent_file() should work without filename parameter."""
        torrent_bytes = b"fake torrent content"
        
        with patch.object(jackett_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock(
                status_code=200,
                content=torrent_bytes,
                headers={'content-type': 'application/x-bittorrent'},
                raise_for_status=lambda: None
            )
            mock_get.return_value = mock_response
            
            result = await jackett_client.download_torrent_file(
                tracker_id="tracker123",
                path="http://example.com/torrent.torrent",
                filename=None
            )
            
            assert result == torrent_bytes
    
    @pytest.mark.asyncio
    async def test_download_torrent_file_handles_http_error(self, jackett_client):
        """download_torrent_file() should return None on HTTP error."""
        with patch.object(jackett_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Download failed")
            
            result = await jackett_client.download_torrent_file(
                tracker_id="tracker123",
                path="http://example.com/torrent.torrent",
                filename="test.torrent"
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_download_torrent_file_rejects_html_content(self, jackett_client):
        """download_torrent_file() should return None if HTML is returned."""
        with patch.object(jackett_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock(
                status_code=200,
                content=b"<html>Error</html>",
                headers={'content-type': 'text/html'},
                raise_for_status=lambda: None
            )
            mock_get.return_value = mock_response
            
            result = await jackett_client.download_torrent_file(
                tracker_id="tracker123",
                path="http://example.com/torrent.torrent",
                filename="test.torrent"
            )
            
            assert result is None


class TestJackettClientFindFreshLink:
    """Tests for JackettClient.find_fresh_link() method."""
    
    @pytest.mark.asyncio
    async def test_find_fresh_link_exact_match_magnet(self, jackett_client):
        """find_fresh_link() should find exact match with magnet URI."""
        mock_response = {
            "Results": [
                {
                    "Title": "Test.Movie.2024.1080p.BluRay.x264-GROUP",
                    "MagnetUri": "magnet:?xt=urn:btih:abc123",
                    "Link": "http://example.com/torrent.torrent",
                    "TrackerId": "tracker1"
                }
            ]
        }
        
        with patch.object(jackett_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
            
            result = await jackett_client.find_fresh_link("Test.Movie.2024.1080p.BluRay.x264-GROUP")
            
            assert result is not None
            assert result["link"] == "magnet:?xt=urn:btih:abc123"
            assert result["tracker_id"] is None
    
    @pytest.mark.asyncio
    async def test_find_fresh_link_word_match_magnet(self, jackett_client):
        """find_fresh_link() should find word match with magnet URI."""
        mock_response = {
            "Results": [
                {
                    "Title": "Test.Movie.2024.1080p.BluRay.x264-GROUP",
                    "MagnetUri": "magnet:?xt=urn:btih:abc123",
                    "Link": "http://example.com/torrent.torrent",
                    "TrackerId": "tracker1"
                }
            ]
        }
        
        with patch.object(jackett_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
            
            result = await jackett_client.find_fresh_link("Test Movie 2024")
            
            assert result is not None
            assert result["link"] == "magnet:?xt=urn:btih:abc123"
            assert result["tracker_id"] is None
    
    @pytest.mark.asyncio
    async def test_find_fresh_link_substring_match_magnet(self, jackett_client):
        """find_fresh_link() should find substring match with magnet URI."""
        mock_response = {
            "Results": [
                {
                    "Title": "Test.Movie.2024.1080p.BluRay.x264-GROUP",
                    "MagnetUri": "magnet:?xt=urn:btih:abc123",
                    "Link": "http://example.com/torrent.torrent",
                    "TrackerId": "tracker1"
                }
            ]
        }
        
        with patch.object(jackett_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
            
            result = await jackett_client.find_fresh_link("Test.Movie")
            
            assert result is not None
            assert result["link"] == "magnet:?xt=urn:btih:abc123"
            assert result["tracker_id"] is None
    
    @pytest.mark.asyncio
    async def test_find_fresh_link_exact_match_link(self, jackett_client):
        """find_fresh_link() should fallback to Link when no magnet available."""
        mock_response = {
            "Results": [
                {
                    "Title": "Test.Movie.2024.1080p.BluRay.x264-GROUP",
                    "MagnetUri": "",
                    "Link": "http://example.com/torrent.torrent",
                    "TrackerId": "tracker1"
                }
            ]
        }
        
        with patch.object(jackett_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
            
            result = await jackett_client.find_fresh_link("Test.Movie.2024.1080p.BluRay.x264-GROUP")
            
            assert result is not None
            assert result["link"] == "http://example.com/torrent.torrent"
            assert result["tracker_id"] == "tracker1"
    
    @pytest.mark.asyncio
    async def test_find_fresh_link_no_match(self, jackett_client):
        """find_fresh_link() should return None when no match found."""
        mock_response = {
            "Results": [
                {
                    "Title": "Different.Movie.2024.1080p.BluRay.x264-GROUP",
                    "MagnetUri": "magnet:?xt=urn:btih:xyz789",
                    "Link": "http://example.com/torrent.torrent",
                    "TrackerId": "tracker1"
                }
            ]
        }
        
        with patch.object(jackett_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
            
            result = await jackett_client.find_fresh_link("Test.Movie.2024")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_find_fresh_link_empty_torrent_name(self, jackett_client):
        """find_fresh_link() should return None when torrent_name is empty."""
        result = await jackett_client.find_fresh_link("")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_find_fresh_link_handles_http_error(self, jackett_client):
        """find_fresh_link() should return None on HTTP error."""
        with patch.object(jackett_client.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection failed")
            
            result = await jackett_client.find_fresh_link("Test.Movie.2024")
            
            assert result is None
