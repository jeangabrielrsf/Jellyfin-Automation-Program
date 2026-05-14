import httpx
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.omdb_service import OMDbService


@pytest.fixture
def omdb_service():
    return OMDbService(api_key="test-key")


@pytest.mark.asyncio
async def test_get_by_imdb_id_returns_rt_rating(omdb_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "Title": "Test Movie",
        "Year": "2023",
        "Rated": "PG",
        "Ratings": [
            {"Source": "Internet Movie Database", "Value": "8.5/10"},
            {"Source": "Rotten Tomatoes", "Value": "94%"},
            {"Source": "Metacritic", "Value": "82/100"},
        ],
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(omdb_service.client, "get", AsyncMock(return_value=mock_response)):
        result = await omdb_service.get_by_imdb_id("tt1234567")
        assert result is not None
        assert result["rt_rating"] == "94%"


@pytest.mark.asyncio
async def test_get_by_imdb_id_no_rt_rating_returns_none(omdb_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "Title": "Test Movie",
        "Ratings": [
            {"Source": "Internet Movie Database", "Value": "8.5/10"},
        ],
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(omdb_service.client, "get", AsyncMock(return_value=mock_response)):
        result = await omdb_service.get_by_imdb_id("tt1234567")
        assert result is None


@pytest.mark.asyncio
async def test_get_by_imdb_id_http_error_returns_none(omdb_service):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Error", request=MagicMock(), response=MagicMock(status_code=401)
    )

    with patch.object(omdb_service.client, "get", AsyncMock(return_value=mock_response)):
        result = await omdb_service.get_by_imdb_id("tt1234567")
        assert result is None


@pytest.mark.asyncio
async def test_get_by_imdb_id_empty_ratings_returns_none(omdb_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "Title": "Test Movie",
        "Ratings": [],
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(omdb_service.client, "get", AsyncMock(return_value=mock_response)):
        result = await omdb_service.get_by_imdb_id("tt1234567")
        assert result is None


@pytest.mark.asyncio
async def test_build_rt_url_movie_valid_returns_slug_url(omdb_service):
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(omdb_service.client, "head", AsyncMock(return_value=mock_response)):
        url = await omdb_service.build_rt_url("The Matrix", "movie")
        assert "rottentomatoes.com/m/the_matrix" in url


@pytest.mark.asyncio
async def test_build_rt_url_tv_valid_returns_slug_url(omdb_service):
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(omdb_service.client, "head", AsyncMock(return_value=mock_response)):
        url = await omdb_service.build_rt_url("Breaking Bad", "tv")
        assert "rottentomatoes.com/tv/breaking_bad" in url


@pytest.mark.asyncio
async def test_build_rt_url_404_falls_back_to_search(omdb_service):
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch.object(omdb_service.client, "head", AsyncMock(return_value=mock_response)):
        url = await omdb_service.build_rt_url("Some Obscure Title", "movie")
        assert "rottentomatoes.com/search" in url
        assert "Some+Obscure+Title" in url


@pytest.mark.asyncio
async def test_build_rt_url_head_error_falls_back_to_search(omdb_service):
    with patch.object(omdb_service.client, "head", AsyncMock(side_effect=Exception("timeout"))):
        url = await omdb_service.build_rt_url("Test Movie", "movie")
        assert "rottentomatoes.com/search" in url
        assert "Test+Movie" in url


@pytest.mark.asyncio
async def test_build_rt_url_removes_special_chars(omdb_service):
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(omdb_service.client, "head", AsyncMock(return_value=mock_response)):
        url = await omdb_service.build_rt_url("What's Up, Doc?", "movie")
        assert "whats_up_doc" in url
        assert "'" not in url
        assert "," not in url
        assert "?" not in url
