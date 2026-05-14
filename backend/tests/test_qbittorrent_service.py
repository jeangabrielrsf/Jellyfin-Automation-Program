"""Tests for qBittorrent service."""
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.qbittorrent_service import QBittorrentService
from app.models.settings import Setting

@pytest.fixture
def qb_service(db_session):
    db_session.add(Setting(key="qbittorrent_host", value="http://localhost:8080"))
    db_session.add(Setting(key="qbittorrent_username", value="admin"))
    db_session.add(Setting(key="qbittorrent_password", value="adminadmin"))
    db_session.commit()
    return QBittorrentService(db=db_session)

@pytest.mark.asyncio
async def test_authenticate_success(qb_service):
    """Test successful authentication."""
    with patch.object(qb_service.client, 'post') as mock_post:
        mock_post.return_value = AsyncMock()
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "Ok."
        mock_post.return_value.raise_for_status = Mock()
        
        result = await qb_service._authenticate()
        assert result is True
        assert qb_service._authenticated is True

@pytest.mark.asyncio
async def test_add_torrent(qb_service):
    """Test adding a torrent."""
    qb_service._authenticated = True
    
    with patch.object(qb_service.client, 'post') as mock_post:
        mock_post.return_value = AsyncMock()
        mock_post.return_value.raise_for_status = Mock()
        
        result = await qb_service.add_torrent("magnet:?xt=urn:btih:test")
        assert result is True

@pytest.mark.asyncio
async def test_get_torrents(qb_service):
    """Test getting torrents list."""
    qb_service._authenticated = True
    
    mock_torrents = [
        {"hash": "abc123", "name": "Test", "progress": 0.5, "state": "downloading"}
    ]
    
    with patch.object(qb_service.client, 'get') as mock_get:
        mock_get.return_value = AsyncMock()
        mock_get.return_value.json = Mock(return_value=mock_torrents)
        mock_get.return_value.raise_for_status = Mock()
        
        result = await qb_service.get_torrents()
        assert len(result) == 1
        assert result[0]["hash"] == "abc123"
