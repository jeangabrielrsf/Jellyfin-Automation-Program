"""Tests for GET /api/search/discover/ endpoint — filtered discover search."""
import pytest
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import get_db
from app.models.settings import Setting


@pytest.fixture
def discover_filter_client(db_session):
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
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        pass


def _movie_item(id=1, title="Movie", vote_average=7.5, genre_ids=None, release_date="2023-06-01", popularity=100.0, vote_count=500):
    return {
        "id": id,
        "title": title,
        "overview": "Overview",
        "poster_path": "/poster.jpg",
        "backdrop_path": None,
        "release_date": release_date,
        "vote_average": vote_average,
        "popularity": popularity,
        "vote_count": vote_count,
        "media_type": "movie",
        "genre_ids": genre_ids or [28],
    }


def _tv_item(id=2, name="Show", vote_average=8.0, genre_ids=None, first_air_date="2023-06-01", popularity=100.0, vote_count=500):
    return {
        "id": id,
        "name": name,
        "overview": "Overview",
        "poster_path": "/poster.jpg",
        "backdrop_path": None,
        "first_air_date": first_air_date,
        "vote_average": vote_average,
        "popularity": popularity,
        "vote_count": vote_count,
        "media_type": "tv",
        "genre_ids": genre_ids or [18],
    }


class _TrackingClient:
    def __init__(self, movie_results=None, tv_results=None, movie_total=1, tv_total=1):
        self.calls = []
        self._movie_results = movie_results if movie_results is not None else [_movie_item()]
        self._tv_results = tv_results if tv_results is not None else [_tv_item()]
        self._movie_total = movie_total
        self._tv_total = tv_total

    async def get(self, url, **kwargs):
        self.calls.append((str(url), kwargs.get("params", {})))
        url_str = str(url)
        if "/discover/movie" in url_str:
            return _MockResponse({
                "results": self._movie_results,
                "total_results": self._movie_total,
                "total_pages": 1,
                "page": kwargs.get("params", {}).get("page", 1),
            })
        elif "/discover/tv" in url_str:
            return _MockResponse({
                "results": self._tv_results,
                "total_results": self._tv_total,
                "total_pages": 1,
                "page": kwargs.get("params", {}).get("page", 1),
            })
        return _MockResponse({"results": [], "total_results": 0, "total_pages": 0, "page": 1})

    async def aclose(self):
        pass


class TestDiscoverEndpointMediaType:
    @pytest.mark.anyio
    async def test_media_type_movie_calls_discover_movie(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "movie"})

        assert resp.status_code == 200
        assert len(client.calls) == 1
        assert "/discover/movie" in client.calls[0][0]

    @pytest.mark.anyio
    async def test_media_type_series_calls_discover_tv(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "series"})

        assert resp.status_code == 200
        assert len(client.calls) == 1
        assert "/discover/tv" in client.calls[0][0]

    @pytest.mark.anyio
    async def test_media_type_anime_calls_discover_tv_with_anime_params(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "anime"})

        assert resp.status_code == 200
        assert len(client.calls) == 1
        url, params = client.calls[0]
        assert "/discover/tv" in url
        assert params.get("with_genres") == "16"
        assert params.get("with_origin_country") == "JP"

    @pytest.mark.anyio
    async def test_media_type_all_calls_both_endpoints(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "all"})

        assert resp.status_code == 200
        assert len(client.calls) == 2
        urls = [c[0] for c in client.calls]
        assert any("/discover/movie" in u for u in urls)
        assert any("/discover/tv" in u for u in urls)

    @pytest.mark.anyio
    async def test_default_media_type_is_all(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/")

        assert resp.status_code == 200
        assert len(client.calls) == 2


class TestDiscoverEndpointGenreFilter:
    @pytest.mark.anyio
    async def test_genre_ids_single(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "movie", "genre_ids": [28]})

        assert resp.status_code == 200
        _, params = client.calls[0]
        assert params.get("with_genres") == "28"

    @pytest.mark.anyio
    async def test_genre_ids_multiple(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "movie", "genre_ids": [28, 12, 878]})

        assert resp.status_code == 200
        _, params = client.calls[0]
        assert params.get("with_genres") == "28|12|878"


class TestDiscoverEndpointWatchProviderFilter:
    @pytest.mark.anyio
    async def test_watch_provider_ids_single(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "movie", "watch_provider_ids": [8]})

        assert resp.status_code == 200
        _, params = client.calls[0]
        assert params.get("with_watch_providers") == "8"
        assert params.get("watch_region") == "BR"

    @pytest.mark.anyio
    async def test_watch_provider_ids_multiple(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "movie", "watch_provider_ids": [8, 119, 337]})

        assert resp.status_code == 200
        _, params = client.calls[0]
        assert params.get("with_watch_providers") == "8,119,337"
        assert params.get("watch_region") == "BR"


class TestDiscoverEndpointYearFilter:
    @pytest.mark.anyio
    async def test_year_range_movie(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={
                    "media_type": "movie", "year_from": 2020, "year_to": 2024
                })

        assert resp.status_code == 200
        _, params = client.calls[0]
        assert params.get("primary_release_date.gte") == "2020-01-01"
        assert params.get("primary_release_date.lte") == "2024-12-31"

    @pytest.mark.anyio
    async def test_year_range_tv(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={
                    "media_type": "series", "year_from": 2020, "year_to": 2024
                })

        assert resp.status_code == 200
        _, params = client.calls[0]
        assert params.get("first_air_date.gte") == "2020-01-01"
        assert params.get("first_air_date.lte") == "2024-12-31"

    @pytest.mark.anyio
    async def test_year_from_only(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={
                    "media_type": "movie", "year_from": 2020
                })

        assert resp.status_code == 200
        _, params = client.calls[0]
        assert params.get("primary_release_date.gte") == "2020-01-01"
        assert "primary_release_date.lte" not in params

    @pytest.mark.anyio
    async def test_year_to_only(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={
                    "media_type": "movie", "year_to": 2024
                })

        assert resp.status_code == 200
        _, params = client.calls[0]
        assert params.get("primary_release_date.lte") == "2024-12-31"
        assert "primary_release_date.gte" not in params


class TestDiscoverEndpointRatingFilter:
    @pytest.mark.anyio
    async def test_min_rating(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={
                    "media_type": "movie", "min_rating": 7.5
                })

        assert resp.status_code == 200
        _, params = client.calls[0]
        assert params.get("vote_average.gte") == 7.5


class TestDiscoverEndpointSortBy:
    @pytest.mark.anyio
    async def test_default_sort_by(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "movie"})

        assert resp.status_code == 200
        _, params = client.calls[0]
        assert params.get("sort_by") == "popularity.desc"

    @pytest.mark.anyio
    @pytest.mark.parametrize("sort_value", [
        "popularity.desc",
        "vote_average.desc",
        "vote_count.desc",
        "release_date.desc",
        "original_title.asc",
    ])
    async def test_sort_by_options(self, sort_value, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={
                    "media_type": "movie", "sort_by": sort_value
                })

        assert resp.status_code == 200
        _, params = client.calls[0]
        assert params.get("sort_by") == sort_value


class TestDiscoverEndpointPagination:
    @pytest.mark.anyio
    async def test_default_page(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "movie"})

        assert resp.status_code == 200
        _, params = client.calls[0]
        assert params.get("page") == 1

    @pytest.mark.anyio
    async def test_custom_page(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "movie", "page": 3})

        assert resp.status_code == 200
        _, params = client.calls[0]
        assert params.get("page") == 3

    @pytest.mark.anyio
    async def test_response_has_pagination_metadata(self, discover_filter_client):
        client = _TrackingClient(movie_total=42)
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "movie"})

        assert resp.status_code == 200
        data = resp.json()
        assert "total_results" in data
        assert "total_pages" in data
        assert "page" in data
        assert "results" in data


class TestDiscoverEndpointValidation:
    @pytest.mark.anyio
    async def test_invalid_media_type_rejected(self, discover_filter_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/search/discover/", params={"media_type": "invalid"})

        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_invalid_sort_by_rejected(self, discover_filter_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/search/discover/", params={"sort_by": "invalid.sort"})

        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_min_rating_below_zero_rejected(self, discover_filter_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/search/discover/", params={"min_rating": -1.0})

        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_min_rating_above_ten_rejected(self, discover_filter_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/search/discover/", params={"min_rating": 11.0})

        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_year_from_greater_than_year_to_rejected(self, discover_filter_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/search/discover/", params={"year_from": 2025, "year_to": 2020})

        assert resp.status_code == 422


class TestDiscoverEndpointResponse:
    @pytest.mark.anyio
    async def test_response_results_are_tmdb_items(self, discover_filter_client):
        client = _TrackingClient(
            movie_results=[_movie_item(id=1, title="Test Movie")],
            movie_total=1,
        )
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "movie"})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["title"] == "Test Movie"
        assert data["results"][0]["media_type"] == "movie"

    @pytest.mark.anyio
    async def test_media_type_all_combines_results(self, discover_filter_client):
        client = _TrackingClient(
            movie_results=[_movie_item(id=1, title="Movie 1"), _movie_item(id=2, title="Movie 2")],
            tv_results=[_tv_item(id=3, name="Show 1")],
            movie_total=2,
            tv_total=1,
        )
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "all"})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 3
        media_types = {r["media_type"] for r in data["results"]}
        assert "movie" in media_types
        assert "tv" in media_types


class TestDiscoverEndpointCombinedFilters:
    @pytest.mark.anyio
    async def test_all_filters_combined(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={
                    "media_type": "movie",
                    "genre_ids": [28, 12],
                    "watch_provider_ids": [8],
                    "year_from": 2020,
                    "year_to": 2024,
                    "min_rating": 7.0,
                    "sort_by": "vote_average.desc",
                    "page": 2,
                })

        assert resp.status_code == 200
        _, params = client.calls[0]
        assert params["with_genres"] == "28|12"
        assert params["with_watch_providers"] == "8"
        assert params["watch_region"] == "BR"
        assert params["primary_release_date.gte"] == "2020-01-01"
        assert params["primary_release_date.lte"] == "2024-12-31"
        assert params["vote_average.gte"] == 7.0
        assert params["sort_by"] == "vote_average.desc"
        assert params["page"] == 2

    @pytest.mark.anyio
    async def test_anime_with_genre_filter(self, discover_filter_client):
        client = _TrackingClient()
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={
                    "media_type": "anime",
                    "genre_ids": [16],
                })

        assert resp.status_code == 200
        url, params = client.calls[0]
        assert "/discover/tv" in url
        assert params.get("with_origin_country") == "JP"
        assert params.get("with_genres") == "16"


class TestDiscoverEndpointSortOrder:
    @pytest.mark.anyio
    async def test_sort_by_popularity_orders_by_popularity(self, discover_filter_client):
        client = _TrackingClient(
            movie_results=[
                _movie_item(id=1, title="Low", popularity=10.0),
                _movie_item(id=2, title="High", popularity=999.0),
            ],
            tv_results=[],
            movie_total=2,
            tv_total=0,
        )
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={
                    "media_type": "all", "sort_by": "popularity.desc"
                })

        assert resp.status_code == 200
        data = resp.json()
        assert data["results"][0]["title"] == "High"
        assert data["results"][1]["title"] == "Low"

    @pytest.mark.anyio
    async def test_sort_by_vote_count_orders_by_vote_count(self, discover_filter_client):
        client = _TrackingClient(
            movie_results=[
                _movie_item(id=1, title="Few", vote_count=10),
                _movie_item(id=2, title="Many", vote_count=9999),
            ],
            tv_results=[],
            movie_total=2,
            tv_total=0,
        )
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={
                    "media_type": "all", "sort_by": "vote_count.desc"
                })

        assert resp.status_code == 200
        data = resp.json()
        assert data["results"][0]["title"] == "Many"
        assert data["results"][1]["title"] == "Few"

    @pytest.mark.anyio
    async def test_sort_by_original_title_ascending(self, discover_filter_client):
        client = _TrackingClient(
            movie_results=[
                _movie_item(id=1, title="Zebra"),
                _movie_item(id=2, title="Apple"),
            ],
            tv_results=[],
            movie_total=2,
            tv_total=0,
        )
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={
                    "media_type": "all", "sort_by": "original_title.asc"
                })

        assert resp.status_code == 200
        data = resp.json()
        assert data["results"][0]["title"] == "Apple"
        assert data["results"][1]["title"] == "Zebra"


class TestDiscoverEndpointPaginationTruncation:
    @pytest.mark.anyio
    async def test_media_type_all_truncates_to_20(self, discover_filter_client):
        movies = [_movie_item(id=i, title=f"Movie {i}", popularity=float(100 - i)) for i in range(20)]
        tvs = [_tv_item(id=i + 100, name=f"Show {i}", popularity=float(100 - i)) for i in range(20)]
        client = _TrackingClient(
            movie_results=movies,
            tv_results=tvs,
            movie_total=20,
            tv_total=20,
        )
        with patch("app.services.tmdb_service.httpx.AsyncClient", return_value=client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/search/discover/", params={"media_type": "all"})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 20
