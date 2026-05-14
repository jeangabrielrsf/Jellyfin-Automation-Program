"""Tests for Jellyfin service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.settings import Setting
from app.services.jellyfin_service import JellyfinService


@pytest.fixture
def jellyfin_service(db_session):
    db_session.add(Setting(key="jellyfin_url", value="http://localhost:8096"))
    db_session.add(Setting(key="jellyfin_api_key", value="test-api-key"))
    db_session.commit()
    return JellyfinService(db=db_session)


def _mock_response(json_data=None, status_code=200):
    """Helper to create a mocked httpx response."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status = MagicMock()
    return response


@pytest.mark.asyncio
async def test_scan_library_full_success(jellyfin_service):
    """Test triggering a full library scan."""
    with patch.object(jellyfin_service.client, 'post') as mock_post:
        mock_post.return_value = _mock_response()

        result = await jellyfin_service.scan_library()
        assert result is True
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_scan_library_specific_success(jellyfin_service):
    """Test triggering a scan for a specific library."""
    with patch.object(jellyfin_service.client, 'post') as mock_post:
        mock_post.return_value = _mock_response()

        with patch.object(jellyfin_service, 'get_libraries') as mock_get_libs:
            mock_get_libs.return_value = [
                {"Name": "Movies", "Id": "123"},
                {"Name": "Shows", "Id": "456"}
            ]

            result = await jellyfin_service.scan_library("Shows")
            assert result is True


@pytest.mark.asyncio
async def test_scan_library_not_found(jellyfin_service):
    """Test scanning a non-existent library."""
    with patch.object(jellyfin_service, 'get_libraries') as mock_get_libs:
        mock_get_libs.return_value = [{"Name": "Movies", "Id": "123"}]

        result = await jellyfin_service.scan_library("Music")
        assert result is False


@pytest.mark.asyncio
async def test_scan_library_http_error(jellyfin_service):
    """Test handling HTTP error during scan."""
    import httpx
    with patch.object(jellyfin_service.client, 'post') as mock_post:
        mock_post.side_effect = httpx.HTTPError("Connection refused")

        result = await jellyfin_service.scan_library()
        assert result is False


@pytest.mark.asyncio
async def test_get_libraries_success(jellyfin_service):
    """Test retrieving libraries."""
    mock_data = [
        {"Name": "Movies", "Id": "123"},
        {"Name": "Shows", "Id": "456"}
    ]
    with patch.object(jellyfin_service.client, 'get') as mock_get:
        mock_get.return_value = _mock_response(json_data=mock_data)

        result = await jellyfin_service.get_libraries()
        assert len(result) == 2
        assert result[0]["Name"] == "Movies"


@pytest.mark.asyncio
async def test_get_libraries_http_error(jellyfin_service):
    """Test handling HTTP error when getting libraries."""
    import httpx
    with patch.object(jellyfin_service.client, 'get') as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection refused")

        result = await jellyfin_service.get_libraries()
        assert result == []
