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


@pytest.fixture
def mock_jackett_client():
    """Mock JackettClient."""
    client = MagicMock()
    client.find_fresh_link = AsyncMock(return_value=None)
    client.download_torrent_file = AsyncMock(return_value=None)
    return client


@pytest.mark.asyncio
async def test_add_torrent_logs_error_details(mock_db, mock_config, mock_jackett_client):
    """Test that HTTP errors are logged with status code and response body."""
    service = QBittorrentService(db=mock_db, jackett_client=mock_jackett_client)
    
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
        
        success, already_exists = await service.add_torrent(
            magnet_link="magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678",
            save_path="/tmp/test"
        )
        
        assert success is False
        assert already_exists is False
        await service.close()


@pytest.mark.asyncio
async def test_add_torrent_success(mock_db, mock_config, mock_jackett_client):
    """Test that successful torrent addition is logged correctly."""
    service = QBittorrentService(db=mock_db, jackett_client=mock_jackett_client)
    
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
        success, already_exists = await service.add_torrent(
            magnet_link="magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678",
            save_path="/tmp/test"
        )
        
        assert success is True
        assert already_exists is False
        await service.close()


@pytest.mark.asyncio
async def test_add_torrent_connection_error(mock_db, mock_config, mock_jackett_client):
    """Test that connection errors are logged correctly."""
    service = QBittorrentService(db=mock_db, jackett_client=mock_jackett_client)
    
    # Mock authentication failure
    with patch.object(service.client, 'post') as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        
        success, already_exists = await service.add_torrent(
            magnet_link="magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678",
            save_path="/tmp/test"
        )
        
        assert success is False
        assert already_exists is False
        await service.close()


@pytest.mark.asyncio
async def test_add_torrent_duplicate_returns_success(mock_db, mock_config, mock_jackett_client):
    """Test that 409 Conflict (duplicate torrent) is treated as success."""
    service = QBittorrentService(db=mock_db, jackett_client=mock_jackett_client)
    
    # Mock authentication success
    auth_response = MagicMock()
    auth_response.status_code = 200
    auth_response.text = "Ok."
    
    # Mock 409 Conflict response (torrent already exists)
    conflict_response = MagicMock()
    conflict_response.status_code = 409
    conflict_response.text = "Conflict"
    
    # Create HTTPStatusError with 409
    error = httpx.HTTPStatusError(
        "Conflict",
        request=MagicMock(),
        response=conflict_response
    )
    
    async def mock_post(*args, **kwargs):
        if not service._authenticated:
            return auth_response
        raise error
    
    with patch.object(service.client, 'post', side_effect=mock_post):
        success, already_exists = await service.add_torrent(
            magnet_link="magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678",
            save_path="/tmp/test"
        )
        
        # Should return (True, True) because torrent already exists
        assert success is True
        assert already_exists is True
        await service.close()


@pytest.mark.asyncio
async def test_constructor_accepts_jackett_client(mock_db, mock_config, mock_jackett_client):
    """Test that QBittorrentService constructor accepts jackett_client parameter."""
    service = QBittorrentService(db=mock_db, jackett_client=mock_jackett_client)
    assert service.jackett_client is mock_jackett_client
    await service.close()


@pytest.mark.asyncio
async def test_constructor_creates_default_jackett_client(mock_db, mock_config):
    """Test that QBittorrentService creates a default JackettClient when none provided."""
    with patch('app.services.qbittorrent_service.JackettClient') as MockJackettClient:
        mock_instance = MagicMock()
        MockJackettClient.return_value = mock_instance
        service = QBittorrentService(db=mock_db)
        assert service.jackett_client is mock_instance
        MockJackettClient.assert_called_once_with(db=mock_db)
        await service.close()


@pytest.mark.asyncio
async def test_add_torrent_uses_jackett_find_fresh_link_on_download_failure(mock_db, mock_config, mock_jackett_client):
    """Test that add_torrent calls jackett_client.find_fresh_link when direct download fails."""
    service = QBittorrentService(db=mock_db, jackett_client=mock_jackett_client)
    
    auth_response = MagicMock()
    auth_response.status_code = 200
    auth_response.text = "Ok."
    
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.text = ""
    success_response.raise_for_status = MagicMock()
    
    mock_jackett_client.find_fresh_link.return_value = {
        "link": "magnet:?xt=urn:btih:fresh123",
        "tracker_id": None
    }
    
    async def mock_post(*args, **kwargs):
        if not service._authenticated:
            return auth_response
        return success_response
    
    with patch.object(service.client, 'post', side_effect=mock_post):
        with patch.object(service.client, 'get', side_effect=httpx.HTTPError("Link expired")):
            success, already_exists = await service.add_torrent(
                download_url="http://jackett:9117/dl/abc123",
                torrent_name="Test.Torrent",
                save_path="/tmp/test"
            )
            
            assert success is True
            mock_jackett_client.find_fresh_link.assert_called_once_with("Test.Torrent")
            await service.close()


@pytest.mark.asyncio
async def test_add_torrent_uses_jackett_download_torrent_file_with_tracker_id(mock_db, mock_config, mock_jackett_client):
    """Test that add_torrent calls jackett_client.download_torrent_file when fresh link has tracker_id."""
    service = QBittorrentService(db=mock_db, jackett_client=mock_jackett_client)
    
    auth_response = MagicMock()
    auth_response.status_code = 200
    auth_response.text = "Ok."
    
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.text = ""
    success_response.raise_for_status = MagicMock()
    
    mock_jackett_client.find_fresh_link.return_value = {
        "link": "http://tracker.com/torrent/123",
        "tracker_id": "tracker123"
    }
    mock_jackett_client.download_torrent_file.return_value = b"torrent-content-bytes"
    
    async def mock_post(*args, **kwargs):
        if not service._authenticated:
            return auth_response
        return success_response
    
    with patch.object(service.client, 'post', side_effect=mock_post):
        with patch.object(service.client, 'get', side_effect=httpx.HTTPError("Link expired")):
            success, already_exists = await service.add_torrent(
                download_url="http://jackett:9117/dl/abc123",
                torrent_name="Test.Torrent",
                save_path="/tmp/test"
            )
            
            assert success is True
            mock_jackett_client.download_torrent_file.assert_called_once_with(
                "tracker123",
                "http://tracker.com/torrent/123",
                "Test.Torrent"
            )
            await service.close()


@pytest.mark.asyncio
async def test_add_torrent_sends_fresh_magnet_directly(mock_db, mock_config, mock_jackett_client):
    """Test that add_torrent sends fresh magnet link directly to qBittorrent."""
    service = QBittorrentService(db=mock_db, jackett_client=mock_jackett_client)
    
    auth_response = MagicMock()
    auth_response.status_code = 200
    auth_response.text = "Ok."
    
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.text = ""
    success_response.raise_for_status = MagicMock()
    
    mock_jackett_client.find_fresh_link.return_value = {
        "link": "magnet:?xt=urn:btih:freshmagnet123",
        "tracker_id": None
    }
    
    async def mock_post(*args, **kwargs):
        if not service._authenticated:
            return auth_response
        return success_response
    
    with patch.object(service.client, 'post', side_effect=mock_post) as mock_post_obj:
        with patch.object(service.client, 'get', side_effect=httpx.HTTPError("Link expired")):
            success, already_exists = await service.add_torrent(
                download_url="http://jackett:9117/dl/abc123",
                torrent_name="Test.Torrent",
                save_path="/tmp/test"
            )
            
            assert success is True
            # Verify that the magnet link was sent via POST (not file upload)
            calls = mock_post_obj.call_args_list
            # Last call should be the add torrent with magnet URL in data
            last_call = calls[-1]
            assert 'data' in last_call.kwargs
            assert last_call.kwargs['data']['urls'] == "magnet:?xt=urn:btih:freshmagnet123"
            await service.close()


@pytest.mark.asyncio
async def test_add_torrent_no_jackett_client_skips_fresh_link(mock_db, mock_config):
    """Test that add_torrent does not attempt fresh link search without jackett_client."""
    with patch('app.services.qbittorrent_service.JackettClient', return_value=None):
        service = QBittorrentService(db=mock_db, jackett_client=None)
        
        auth_response = MagicMock()
        auth_response.status_code = 200
        auth_response.text = "Ok."
        
        with patch.object(service.client, 'post', return_value=AsyncMock(return_value=auth_response)):
            with patch.object(service.client, 'get', side_effect=httpx.HTTPError("Link expired")):
                success, already_exists = await service.add_torrent(
                    download_url="http://jackett:9117/dl/abc123",
                    torrent_name="Test.Torrent",
                    save_path="/tmp/test"
                )
                
                assert success is False
                await service.close()
