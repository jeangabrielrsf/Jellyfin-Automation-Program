"""Tests for qBittorrent service logging."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from app.services.qbittorrent_service import QBittorrentService


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def mock_config():
    """Mock configuration."""
    with patch('app.services.qbittorrent_service.get_config') as mock:
        mock.side_effect = lambda key, db=None, required=False: {
            'qbittorrent_host': 'http://qbittorrent:8080',
            'qbittorrent_username': 'admin',
            'qbittorrent_password': 'adminadmin',
        }.get(key, '')
        yield mock


@pytest.mark.asyncio
async def test_add_torrent_logs_error_details(mock_db, mock_config):
    """Test that HTTP errors are logged with status code and response body."""
    service = QBittorrentService(db=mock_db)
    
    # Mock authentication success
    auth_response = MagicMock()
    auth_response.status_code = 200
    auth_response.text = "Ok."
    
    # Mock error response
    error_response = MagicMock()
    error_response.status_code = 415
    error_response.text = "Unsupported Media Type - Invalid torrent file"
    
    # Create HTTPStatusError
    error = httpx.HTTPStatusError(
        "Unsupported Media Type",
        request=MagicMock(),
        response=error_response
    )
    
    with patch.object(service.client, 'post') as mock_post:
        # First call is auth, second is add torrent
        mock_post.side_effect = [
            AsyncMock(return_value=auth_response),
            AsyncMock(side_effect=error)
        ]
        
        result = await service.add_torrent(
            magnet_link="magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678",
            save_path="/tmp/test"
        )
        
        assert result is False
        await service.close()


@pytest.mark.asyncio
async def test_add_torrent_success(mock_db, mock_config):
    """Test that successful torrent addition is logged correctly."""
    service = QBittorrentService(db=mock_db)
    
    # Mock authentication success
    auth_response = MagicMock()
    auth_response.status_code = 200
    auth_response.text = "Ok."
    
    # Mock add torrent success
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.text = ""
    success_response.raise_for_status = MagicMock()
    
    # Create async mock that returns different values
    async def mock_post(*args, **kwargs):
        if not service._authenticated:
            return auth_response
        return success_response
    
    with patch.object(service.client, 'post', side_effect=mock_post):
        result = await service.add_torrent(
            magnet_link="magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678",
            save_path="/tmp/test"
        )
        
        assert result is True
        await service.close()


@pytest.mark.asyncio
async def test_add_torrent_connection_error(mock_db, mock_config):
    """Test that connection errors are logged correctly."""
    service = QBittorrentService(db=mock_db)
    
    # Mock authentication failure
    with patch.object(service.client, 'post') as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        
        result = await service.add_torrent(
            magnet_link="magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678",
            save_path="/tmp/test"
        )
        
        assert result is False
        await service.close()
