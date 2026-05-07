"""Tests for discover router and service."""
import os
import pytest
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.discover import SectionCatalog, DiscoverSection, SectionInfo, Genre, DiscoverParams

SKIP_INTEGRATION = not os.environ.get("TMDB_API_KEY")


class _MockResponse:
    def __init__(self, json_data):
        self._json = json_data

    def json(self):
        return self._json

    def raise_for_status(self):
        pass


class _MockClient:
    async def get(self, url, **kwargs):
        url_str = str(url)
        if "genre/movie/list" in url_str:
            return _MockResponse({"genres": [{"id": 28, "name": "Ação"}, {"id": 35, "name": "Comédia"}]})
        elif "genre/tv/list" in url_str:
            return _MockResponse({"genres": [{"id": 28, "name": "Ação"}, {"id": 18, "name": "Drama"}]})
        else:
            return _MockResponse({
                "results": [
                    {
                        "id": 1, "title": "Test Movie", "overview": "Test overview",
                        "poster_path": "/test.jpg", "backdrop_path": None,
                        "release_date": "2023-01-01", "vote_average": 8.5,
                        "media_type": "movie", "genre_ids": [28, 12]
                    }
                ],
                "total_results": 1
            })

    async def aclose(self):
        pass


@pytest.fixture
def mock_discover_http():
    """Mock httpx AsyncClient in discover_service to avoid real TMDB HTTP calls."""
    with patch("app.services.discover_service.httpx.AsyncClient", return_value=_MockClient()):
        yield


@pytest.mark.anyio
async def test_get_sections_catalog_no_filters():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections")

    assert response.status_code == 200
    data = response.json()
    catalog = SectionCatalog(**data)
    assert len(catalog.sections) == 13
    section_ids = [s["id"] for s in data["sections"]]
    assert "trending" in section_ids
    assert "popular-movies" in section_ids
    assert "popular-animes" in section_ids


@pytest.mark.anyio
async def test_get_sections_catalog_filtered_omits_trending():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections", params={"genre_id": 28})

    assert response.status_code == 200
    data = response.json()
    section_ids = [s["id"] for s in data["sections"]]
    assert "trending" not in section_ids
    assert len(data["sections"]) == 12


@pytest.mark.anyio
async def test_get_sections_catalog_invalid_media_type():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections", params={"media_type": "invalid"})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_get_genres(mock_discover_http):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/genres")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.anyio
async def test_get_section_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections/nonexistent-section")

    assert response.status_code == 404


@pytest.mark.anyio
@pytest.mark.skipif(SKIP_INTEGRATION, reason="TMDB_API_KEY not set")
async def test_get_popular_movies_section():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections/popular-movies")

    assert response.status_code == 200
    data = response.json()
    section = DiscoverSection(**data)
    assert section.id == "popular-movies"
    assert section.media_type == "movie"
    assert len(section.results) > 0


@pytest.mark.anyio
async def test_sections_media_type_validation(mock_discover_http):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections/popular-movies", params={"media_type": "movie"})

    assert response.status_code == 200
    data = response.json()
    assert "results" in data


@pytest.mark.anyio
async def test_genres_consistent_across_requests(mock_discover_http):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response1 = await client.get("/api/discover/genres")
        response2 = await client.get("/api/discover/genres")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert isinstance(response1.json(), list)
    assert isinstance(response2.json(), list)
    assert response1.json() == response2.json()


@pytest.mark.anyio
@pytest.mark.skipif(SKIP_INTEGRATION, reason="TMDB_API_KEY not set")
async def test_anime_section_has_results():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections/popular-animes")

    assert response.status_code == 200
    data = response.json()
    section = DiscoverSection(**data)
    assert section.id == "popular-animes"
    assert section.media_type == "anime"
    assert len(section.results) > 0


class TestDiscoverParams:
    def test_defaults(self):
        p = DiscoverParams()
        assert p.genre_id is None
        assert p.media_type is None
        assert p.sort_by == "popularity.desc"

    def test_with_filters(self):
        p = DiscoverParams(genre_id=28, media_type="movie", sort_by="vote_average.desc")
        assert p.genre_id == 28
        assert p.media_type == "movie"
        assert p.sort_by == "vote_average.desc"


class TestSectionInfo:
    def test_model(self):
        s = SectionInfo(id="popular-movies", title="Filmes Populares", media_type="movie")
        assert s.id == "popular-movies"
        assert s.media_type == "movie"


class TestGenre:
    def test_model(self):
        g = Genre(id=28, name="Ação")
        assert g.id == 28
        assert g.name == "Ação"


@pytest.mark.anyio
async def test_trending_with_filters_returns_empty():
    """Trending section + filters should return empty results, not 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections/trending", params={"genre_id": 28})

    assert response.status_code == 200
    data = response.json()
    assert data["results"] == []
    assert data["total_results"] == 0


@pytest.mark.anyio
@pytest.mark.skipif(SKIP_INTEGRATION, reason="TMDB_API_KEY not set")
async def test_genre_section_returns_data():
    """Integration test: verify genre-action section works."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections/genre-action")

    assert response.status_code == 200
    data = response.json()
    section = DiscoverSection(**data)
    assert section.id == "genre-action"
    assert isinstance(section.results, list)
