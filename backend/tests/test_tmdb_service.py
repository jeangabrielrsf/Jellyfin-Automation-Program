import httpx
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.tmdb_service import TMDBService


@pytest.fixture
def tmdb_service():
    with patch("app.services.tmdb_service.get_settings") as mock_settings:
        mock_settings.return_value.tmdb_api_key = "test-key"
        yield TMDBService()


@pytest.mark.asyncio
async def test_search_returns_results(tmdb_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "page": 1,
        "results": [
            {
                "id": 1,
                "title": "Test Movie",
                "overview": "A test movie",
                "media_type": "movie",
                "vote_average": 8.5,
                "poster_path": "/test.jpg",
                "release_date": "2023-01-01",
                "genre_ids": [28, 12]
            },
            {
                "id": 2,
                "name": "Test TV Show",
                "overview": "A test show",
                "media_type": "tv",
                "vote_average": 7.5,
                "poster_path": "/test2.jpg",
                "first_air_date": "2022-06-15",
                "genre_ids": [18]
            }
        ],
        "total_pages": 1,
        "total_results": 2
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(tmdb_service.client, 'get', AsyncMock(return_value=mock_response)):
        result = await tmdb_service.search("test")
        assert len(result.results) == 2
        assert result.results[0].display_title == "Test Movie"
        assert result.results[0].year == 2023
        assert result.results[1].display_title == "Test TV Show"
        assert result.results[1].year == 2022
        assert result.total_results == 2
        assert result.total_pages == 1


@pytest.mark.asyncio
async def test_search_filters_non_media(tmdb_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "page": 1,
        "results": [
            {
                "id": 1,
                "name": "Test Person",
                "overview": "A test person",
                "media_type": "person",
                "vote_average": 0.0
            },
            {
                "id": 2,
                "title": "Test Movie",
                "overview": "A test movie",
                "media_type": "movie",
                "vote_average": 8.5
            }
        ],
        "total_pages": 1,
        "total_results": 2
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(tmdb_service.client, 'get', AsyncMock(return_value=mock_response)):
        result = await tmdb_service.search("test")
        assert len(result.results) == 1
        assert result.results[0].media_type == "movie"


@pytest.mark.asyncio
async def test_get_movie_detail_returns_detail(tmdb_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": 1,
        "title": "Test Movie",
        "overview": "A test movie",
        "vote_average": 8.5,
        "poster_path": "/test.jpg",
        "release_date": "2023-01-01",
        "genres": [{"id": 16, "name": "Animation"}, {"id": 28, "name": "Action"}],
        "runtime": 120,
        "status": "Released",
        "tagline": "Test tagline"
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(tmdb_service.client, 'get', AsyncMock(return_value=mock_response)):
        result = await tmdb_service.get_movie_detail(1)
        assert result is not None
        assert result.display_title == "Test Movie"
        assert result.year == 2023
        assert result.is_animation is True
        assert result.runtime == 120
        assert result.status == "Released"
        assert result.tagline == "Test tagline"


@pytest.mark.asyncio
async def test_get_tv_detail_returns_detail(tmdb_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": 2,
        "name": "Test TV Show",
        "overview": "A test show",
        "vote_average": 7.5,
        "poster_path": "/test2.jpg",
        "first_air_date": "2022-06-15",
        "genres": [{"id": 18, "name": "Drama"}],
        "number_of_seasons": 3,
        "number_of_episodes": 30,
        "status": "Returning Series",
        "tagline": "Test tv tagline"
    }
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(tmdb_service.client, 'get', AsyncMock(return_value=mock_response)):
        result = await tmdb_service.get_tv_detail(2)
        assert result is not None
        assert result.display_title == "Test TV Show"
        assert result.year == 2022
        assert result.is_animation is False
        assert result.number_of_seasons == 3
        assert result.number_of_episodes == 30
        assert result.status == "Returning Series"


@pytest.mark.asyncio
async def test_search_http_error_raises(tmdb_service):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404 Not Found",
        request=MagicMock(),
        response=MagicMock(status_code=404)
    )
    
    with patch.object(tmdb_service.client, 'get', AsyncMock(return_value=mock_response)):
        with pytest.raises(httpx.HTTPStatusError):
            await tmdb_service.search("test")


@pytest.mark.asyncio
async def test_get_movie_detail_http_error_raises(tmdb_service):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    
    with patch.object(tmdb_service.client, 'get', AsyncMock(return_value=mock_response)):
        with pytest.raises(Exception):
            await tmdb_service.get_movie_detail(123)


@pytest.mark.asyncio
async def test_get_tv_detail_http_error_raises(tmdb_service):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    
    with patch.object(tmdb_service.client, 'get', AsyncMock(return_value=mock_response)):
        with pytest.raises(Exception):
            await tmdb_service.get_tv_detail(456)
