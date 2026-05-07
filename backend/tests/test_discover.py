"""Tests for discover router and service."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.discover import SectionCatalog, DiscoverSection, SectionInfo


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
async def test_get_genres():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/genres")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_get_section_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections/nonexistent-section")

    assert response.status_code == 404


@pytest.mark.anyio
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
async def test_sections_media_type_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections/popular-movies", params={"media_type": "movie"})

    assert response.status_code == 200
    data = response.json()
    assert "results" in data


@pytest.mark.anyio
async def test_genres_consistent_across_requests():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response1 = await client.get("/api/discover/genres")
        response2 = await client.get("/api/discover/genres")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert isinstance(response1.json(), list)
    assert isinstance(response2.json(), list)


@pytest.mark.anyio
async def test_anime_section_has_results():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections/popular-animes")

    assert response.status_code == 200
    data = response.json()
    section = DiscoverSection(**data)
    assert section.id == "popular-animes"
    assert section.media_type == "anime"


class TestDiscoverParams:
    def test_defaults(self):
        from app.models.discover import DiscoverParams
        p = DiscoverParams()
        assert p.genre_id is None
        assert p.media_type is None
        assert p.sort_by == "popularity.desc"

    def test_with_filters(self):
        from app.models.discover import DiscoverParams
        p = DiscoverParams(genre_id=28, media_type="movie", sort_by="vote_average.desc")
        assert p.genre_id == 28
        assert p.media_type == "movie"
        assert p.sort_by == "vote_average.desc"


class TestSectionInfo:
    def test_model(self):
        from app.models.discover import SectionInfo
        s = SectionInfo(id="popular-movies", title="Filmes Populares", media_type="movie")
        assert s.id == "popular-movies"
        assert s.media_type == "movie"


class TestGenre:
    def test_model(self):
        from app.models.discover import Genre
        g = Genre(id=28, name="Ação")
        assert g.id == 28
        assert g.name == "Ação"
