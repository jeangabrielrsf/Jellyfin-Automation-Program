"""Tests for discover router and service — new curated sections architecture."""
import os
from datetime import datetime
from unittest.mock import patch, AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import get_db
from app.models.settings import Setting
from app.models.discover import SectionCatalog, DiscoverSection, SectionInfo, Genre
from app.services.discover_service import DiscoverService, SECTION_DEFS

SKIP_INTEGRATION = not os.environ.get("TMDB_API_KEY")


@pytest.fixture
def discover_client(db_session):
    db_session.add(Setting(key="tmdb_api_key", value="test-key"))
    db_session.commit()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with patch('app.main.init_db'):
        yield
    app.dependency_overrides.clear()


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
        elif "watch/providers" in url_str:
            return _MockResponse({"results": {"BR": {"flatrate": [{"provider_name": "Netflix"}]}}})
        elif "/movie/" in url_str or "/tv/" in url_str:
            return _MockResponse({
                "id": 1,
                "genres": [{"id": 28, "name": "Ação"}],
                "runtime": 120,
            })
        elif "trending/all/week" in url_str:
            return _MockResponse({
                "results": [
                    {
                        "id": i,
                        "title": f"Trending {i}",
                        "overview": f"Overview {i}",
                        "poster_path": f"/trending{i}.jpg",
                        "backdrop_path": None,
                        "release_date": "2024-01-01",
                        "vote_average": 8.0 + i * 0.1,
                        "media_type": "movie" if i % 2 == 0 else "tv",
                        "genre_ids": [28],
                    }
                    for i in range(1, 6)
                ],
                "total_results": 5,
            })
        else:
            return _MockResponse({
                "results": [
                    {
                        "id": 1, "title": "Test Movie", "overview": "Test overview",
                        "poster_path": "/test.jpg", "backdrop_path": None,
                        "release_date": "2023-01-01", "vote_average": 8.5,
                        "media_type": "movie", "genre_ids": [28, 12],
                    }
                ],
                "total_results": 1,
            })

    async def aclose(self):
        pass


@pytest.fixture
def mock_discover_http():
    with patch("app.services.discover_service.httpx.AsyncClient", return_value=_MockClient()):
        yield


class TestBannerRotation:
    def test_pick_banner_index_day_1(self):
        assert DiscoverService._pick_banner_index(datetime(2024, 1, 1)) == 0

    def test_pick_banner_index_day_2(self):
        assert DiscoverService._pick_banner_index(datetime(2024, 1, 2)) == 1

    def test_pick_banner_index_wraps_at_5(self):
        assert DiscoverService._pick_banner_index(datetime(2024, 1, 6)) == 0

    def test_pick_banner_index_day_366(self):
        assert DiscoverService._pick_banner_index(datetime(2024, 1, 3)) == 2
        assert DiscoverService._pick_banner_index(datetime(2024, 1, 8)) == 2

    @patch("app.services.discover_service.datetime")
    def test_fetch_banner_uses_current_day(self, mock_dt):
        mock_dt.now.return_value = datetime(2024, 1, 2)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        service = DiscoverService.__new__(DiscoverService)
        service.api_key = "test"
        service.client = _MockClient()

        import asyncio
        banner = asyncio.run(service._fetch_banner())

        assert banner is not None
        assert banner.id == 2

    def test_fetch_banner_returns_none_on_empty(self):
        class EmptyClient:
            async def get(self, url, **kwargs):
                return _MockResponse({"results": [], "total_results": 0})

            async def aclose(self):
                pass

        service = DiscoverService.__new__(DiscoverService)
        service.api_key = "test"
        service.client = EmptyClient()

        import asyncio
        banner = asyncio.run(service._fetch_banner())
        assert banner is None


class TestSectionDefs:
    def test_has_exactly_5_sections(self):
        assert len(SECTION_DEFS) == 5

    def test_section_ids(self):
        ids = {s.id for s in SECTION_DEFS}
        assert ids == {"trending", "recently-added", "streaming-hot", "seasonal-anime", "classics"}

    def test_no_old_sections(self):
        ids = {s.id for s in SECTION_DEFS}
        assert "now-playing" not in ids
        assert "upcoming" not in ids
        assert "genre-action" not in ids
        assert "genre-comedy" not in ids
        assert "genre-drama" not in ids
        assert "genre-horror" not in ids
        assert "genre-scifi" not in ids


class TestGetSectionsCatalog:
    @pytest.fixture
    def service_with_mock(self):
        service = DiscoverService.__new__(DiscoverService)
        service.api_key = "test"
        service.client = _MockClient()
        return service

    @pytest.mark.anyio
    async def test_catalog_has_5_sections(self, service_with_mock):
        catalog = await service_with_mock.get_sections_catalog()
        assert len(catalog.sections) == 5

    @pytest.mark.anyio
    async def test_catalog_has_banner(self, service_with_mock):
        catalog = await service_with_mock.get_sections_catalog()
        assert catalog.banner is not None

    @pytest.mark.anyio
    async def test_catalog_banner_is_trending_item(self, service_with_mock):
        catalog = await service_with_mock.get_sections_catalog()
        assert catalog.banner is not None
        assert catalog.banner.id in range(1, 6)

    @pytest.mark.anyio
    async def test_catalog_section_ids_match_defs(self, service_with_mock):
        catalog = await service_with_mock.get_sections_catalog()
        ids = [s.id for s in catalog.sections]
        assert ids == ["trending", "recently-added", "streaming-hot", "seasonal-anime", "classics"]


class TestGetSection:
    @pytest.mark.anyio
    async def test_trending_section(self, mock_discover_http):
        service = DiscoverService.__new__(DiscoverService)
        service.api_key = "test"
        service.client = _MockClient()

        section = await service.get_section("trending")
        assert section.id == "trending"
        assert section.title == "Tendências da Semana"
        assert section.media_type == "mixed"
        assert len(section.results) == 5

    @pytest.mark.anyio
    async def test_recently_added_section(self, mock_discover_http):
        service = DiscoverService.__new__(DiscoverService)
        service.api_key = "test"
        service.client = _MockClient()

        section = await service.get_section("recently-added")
        assert section.id == "recently-added"
        assert section.title == "Recém Adicionados"
        assert len(section.results) > 0

    @pytest.mark.anyio
    async def test_streaming_hot_section(self, mock_discover_http):
        service = DiscoverService.__new__(DiscoverService)
        service.api_key = "test"
        service.client = _MockClient()

        section = await service.get_section("streaming-hot")
        assert section.id == "streaming-hot"
        assert section.title == "Em Alta no Streaming"
        assert len(section.results) > 0

    @pytest.mark.anyio
    async def test_seasonal_anime_section(self, mock_discover_http):
        service = DiscoverService.__new__(DiscoverService)
        service.api_key = "test"
        service.client = _MockClient()

        section = await service.get_section("seasonal-anime")
        assert section.id == "seasonal-anime"
        assert section.title == "Animes da Temporada"
        assert section.media_type == "anime"
        assert len(section.results) > 0

    @pytest.mark.anyio
    async def test_classics_section(self, mock_discover_http):
        service = DiscoverService.__new__(DiscoverService)
        service.api_key = "test"
        service.client = _MockClient()

        section = await service.get_section("classics")
        assert section.id == "classics"
        assert section.title == "Clássicos Imperdíveis"
        assert len(section.results) > 0

    @pytest.mark.anyio
    async def test_unknown_section_returns_empty(self, mock_discover_http):
        service = DiscoverService.__new__(DiscoverService)
        service.api_key = "test"
        service.client = _MockClient()

        section = await service.get_section("nonexistent")
        assert section.title == ""
        assert section.results == []


class TestTMDBParams:
    @pytest.mark.anyio
    async def test_recently_added_uses_correct_params(self):
        calls = []

        class TrackingClient:
            async def get(self, url, **kwargs):
                calls.append((str(url), kwargs.get("params", {})))
                return _MockResponse({"results": [{"id": 1, "title": "T", "overview": "", "poster_path": None, "backdrop_path": None, "release_date": "2024-01-01", "vote_average": 7.0, "media_type": "movie", "genre_ids": []}], "total_results": 1})

            async def aclose(self):
                pass

        service = DiscoverService.__new__(DiscoverService)
        service.api_key = "test"
        service.client = TrackingClient()

        await service.get_section("recently-added")

        assert len(calls) == 1
        url, params = calls[0]
        assert "/discover/movie" in url
        assert "with_watch_providers" in params
        assert "primary_release_date.gte" in params
        assert params["watch_region"] == "BR"

    @pytest.mark.anyio
    async def test_streaming_hot_uses_correct_params(self):
        calls = []

        class TrackingClient:
            async def get(self, url, **kwargs):
                calls.append((str(url), kwargs.get("params", {})))
                return _MockResponse({"results": [{"id": 1, "title": "T", "overview": "", "poster_path": None, "backdrop_path": None, "release_date": "2024-01-01", "vote_average": 7.0, "media_type": "movie", "genre_ids": []}], "total_results": 1})

            async def aclose(self):
                pass

        service = DiscoverService.__new__(DiscoverService)
        service.api_key = "test"
        service.client = TrackingClient()

        await service.get_section("streaming-hot")

        assert len(calls) == 1
        url, params = calls[0]
        assert "/discover/movie" in url
        assert params["sort_by"] == "popularity.desc"
        assert "with_watch_providers" in params
        assert params["watch_region"] == "BR"

    @pytest.mark.anyio
    async def test_seasonal_anime_uses_correct_params(self):
        calls = []

        class TrackingClient:
            async def get(self, url, **kwargs):
                calls.append((str(url), kwargs.get("params", {})))
                return _MockResponse({"results": [{"id": 1, "name": "A", "overview": "", "poster_path": None, "backdrop_path": None, "first_air_date": "2024-01-01", "vote_average": 7.0, "media_type": "tv", "genre_ids": []}], "total_results": 1})

            async def aclose(self):
                pass

        service = DiscoverService.__new__(DiscoverService)
        service.api_key = "test"
        service.client = TrackingClient()

        await service.get_section("seasonal-anime")

        assert len(calls) == 1
        url, params = calls[0]
        assert "/discover/tv" in url
        assert params["with_genres"] == "16"
        assert params["with_origin_country"] == "JP"

    @pytest.mark.anyio
    async def test_classics_uses_correct_params(self):
        calls = []

        class TrackingClient:
            async def get(self, url, **kwargs):
                calls.append((str(url), kwargs.get("params", {})))
                return _MockResponse({"results": [{"id": 1, "title": "T", "overview": "", "poster_path": None, "backdrop_path": None, "release_date": "2024-01-01", "vote_average": 7.0, "media_type": "movie", "genre_ids": []}], "total_results": 1})

            async def aclose(self):
                pass

        service = DiscoverService.__new__(DiscoverService)
        service.api_key = "test"
        service.client = TrackingClient()

        await service.get_section("classics")

        assert len(calls) == 1
        url, params = calls[0]
        assert "/discover/movie" in url
        assert params["sort_by"] == "vote_average.desc"
        assert params["vote_count.gte"] == "1000"

    @pytest.mark.anyio
    async def test_trending_uses_trending_endpoint(self):
        calls = []

        class TrackingClient:
            async def get(self, url, **kwargs):
                calls.append((str(url), kwargs.get("params", {})))
                return _MockResponse({"results": [{"id": 1, "title": "T", "overview": "", "poster_path": None, "backdrop_path": None, "release_date": "2024-01-01", "vote_average": 7.0, "media_type": "movie", "genre_ids": []}], "total_results": 1})

            async def aclose(self):
                pass

        service = DiscoverService.__new__(DiscoverService)
        service.api_key = "test"
        service.client = TrackingClient()

        await service.get_section("trending")

        assert len(calls) == 1
        url, _ = calls[0]
        assert "/trending/all/week" in url


@pytest.mark.anyio
async def test_api_sections_catalog_has_banner(mock_discover_http, discover_client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections/")

    assert response.status_code == 200
    data = response.json()
    assert "banner" in data
    assert "sections" in data
    assert len(data["sections"]) == 5


@pytest.mark.anyio
async def test_api_sections_catalog_section_ids(mock_discover_http, discover_client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections/")

    assert response.status_code == 200
    data = response.json()
    section_ids = [s["id"] for s in data["sections"]]
    assert "trending" in section_ids
    assert "recently-added" in section_ids
    assert "streaming-hot" in section_ids
    assert "seasonal-anime" in section_ids
    assert "classics" in section_ids


@pytest.mark.anyio
async def test_api_old_sections_removed(mock_discover_http, discover_client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections/")

    assert response.status_code == 200
    data = response.json()
    section_ids = [s["id"] for s in data["sections"]]
    assert "now-playing" not in section_ids
    assert "upcoming" not in section_ids
    assert "genre-action" not in section_ids
    assert "genre-comedy" not in section_ids
    assert "genre-drama" not in section_ids
    assert "genre-horror" not in section_ids
    assert "genre-scifi" not in section_ids


@pytest.mark.anyio
async def test_api_old_section_ids_return_404(mock_discover_http, discover_client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for old_id in ["now-playing", "upcoming", "genre-action"]:
            response = await client.get(f"/api/discover/sections/{old_id}/")
            assert response.status_code == 404, f"Expected 404 for {old_id}"


@pytest.mark.anyio
async def test_api_genres_still_works(mock_discover_http, discover_client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/genres/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.anyio
async def test_api_providers_still_works(discover_client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/providers/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 7


@pytest.mark.anyio
async def test_api_each_section_returns_data(mock_discover_http, discover_client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for section_id in ["trending", "recently-added", "streaming-hot", "seasonal-anime", "classics"]:
            response = await client.get(f"/api/discover/sections/{section_id}/")
            assert response.status_code == 200, f"Failed for {section_id}"
            data = response.json()
            assert data["id"] == section_id
            assert len(data["results"]) > 0


class TestSectionInfo:
    def test_model(self):
        s = SectionInfo(id="trending", title="Tendências da Semana", media_type="mixed")
        assert s.id == "trending"
        assert s.media_type == "mixed"


class TestGenre:
    def test_model(self):
        g = Genre(id=28, name="Ação")
        assert g.id == 28
        assert g.name == "Ação"


@pytest.mark.anyio
async def test_genres_consistent_across_requests(mock_discover_http, discover_client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response1 = await client.get("/api/discover/genres/")
        response2 = await client.get("/api/discover/genres/")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()
