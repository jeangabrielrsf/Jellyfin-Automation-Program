"""Tests for the /api/lists router."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.user_list import ListKind


@pytest.fixture
def list_settings(db_session):
    """TMDB key is needed if the router hydrates from TMDB."""
    from app.models.settings import Setting
    db_session.add(Setting(key="tmdb_api_key", value="test-key"))
    db_session.commit()


def test_status_returns_both_false_when_empty(client):
    response = client.get("/api/lists/status/movie/1/")
    assert response.status_code == 200
    assert response.json() == {"watched": False, "watchlist": False}


def test_status_reflects_added_items(client, db_session):
    from app.services.list_service import ListService
    svc = ListService(db_session)
    svc.add(ListKind.WATCHLIST, "movie", 7, title="X", poster_path=None, backdrop_path=None, year=None)
    response = client.get("/api/lists/status/movie/7/")
    assert response.status_code == 200
    assert response.json() == {"watched": False, "watchlist": True}


def test_series_media_type_accepted(client, db_session):
    from app.services.list_service import ListService
    ListService(db_session).add(
        ListKind.WATCHLIST, "series", 42, title="Show", poster_path=None, backdrop_path=None, year=2024,
    )
    response = client.get("/api/lists/status/series/42/")
    assert response.status_code == 200
    assert response.json() == {"watched": False, "watchlist": True}


def test_add_with_payload_creates_row(client):
    payload = {
        "title": "Inception",
        "poster_path": "/p.jpg",
        "backdrop_path": None,
        "year": 2010,
    }
    response = client.post("/api/lists/watchlist/movie/1/", json=payload)
    assert response.status_code == 204

    response = client.get("/api/lists/status/movie/1/")
    assert response.json() == {"watched": False, "watchlist": True}


def test_add_without_payload_hydrates_from_tmdb(client, list_settings):
    fake_detail = MagicMock()
    fake_detail.display_title = "Hydrated Title"
    fake_detail.poster_path = "/hyd.jpg"
    fake_detail.backdrop_path = "/bd.jpg"
    fake_detail.year = 2015

    with patch("app.routers.lists.TMDBService") as MockService:
        instance = MockService.return_value
        instance.get_movie_detail = AsyncMock(return_value=fake_detail)
        instance.close = AsyncMock()
        response = client.post("/api/lists/watchlist/movie/99/", json=None)
    assert response.status_code == 204

    response = client.get("/api/lists/status/movie/99/")
    assert response.json() == {"watched": False, "watchlist": True}


def test_add_is_idempotent(client):
    payload = {"title": "X", "poster_path": None, "backdrop_path": None, "year": None}
    client.post("/api/lists/watchlist/movie/1/", json=payload)
    client.post("/api/lists/watchlist/movie/1/", json=payload)
    response = client.get("/api/lists/watchlist/")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_remove_returns_204_when_present(client):
    payload = {"title": "X", "poster_path": None, "backdrop_path": None, "year": None}
    client.post("/api/lists/watchlist/movie/1/", json=payload)
    response = client.delete("/api/lists/watchlist/movie/1/")
    assert response.status_code == 204
    assert client.get("/api/lists/status/movie/1/").json()["watchlist"] is False


def test_remove_returns_404_when_absent(client):
    response = client.delete("/api/lists/watchlist/movie/999/")
    assert response.status_code == 404


def test_list_watchlist_returns_only_watchlist(client):
    p = {"title": "X", "poster_path": None, "backdrop_path": None, "year": None}
    client.post("/api/lists/watchlist/movie/1/", json=p)
    client.post("/api/lists/watched/movie/2/", json=p)
    response = client.get("/api/lists/watchlist/")
    assert response.status_code == 200
    assert [r["tmdb_id"] for r in response.json()] == [1]


def test_list_watched_returns_only_watched(client):
    p = {"title": "X", "poster_path": None, "backdrop_path": None, "year": None}
    client.post("/api/lists/watchlist/movie/1/", json=p)
    client.post("/api/lists/watched/movie/2/", json=p)
    response = client.get("/api/lists/watched/")
    assert response.status_code == 200
    assert [r["tmdb_id"] for r in response.json()] == [2]


def test_invalid_media_type_returns_400(client):
    response = client.get("/api/lists/status/bogus/1/")
    assert response.status_code == 400


def test_invalid_kind_returns_422(client):
    p = {"title": "X", "poster_path": None, "backdrop_path": None, "year": None}
    response = client.post("/api/lists/favorite/movie/1/", json=p)
    assert response.status_code == 422
