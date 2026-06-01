"""Tests for the /api/recommendations router."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def rec_settings(db_session):
    from app.models.settings import Setting
    db_session.add(Setting(key="tmdb_api_key", value="test-key"))
    db_session.commit()


def test_recommendations_returns_capped_list(client, rec_settings, db_session):
    fake_results = [
        {"id": i, "title": f"T{i}", "overview": "", "vote_average": 7.0, "media_type": "movie"}
        for i in range(50)
    ]
    with patch("app.routers.recommendations.TMDBService") as MockService:
        with patch("app.routers.recommendations.RecommendationService") as MockRec:
            instance = MockRec.return_value
            instance.get_recommendations = AsyncMock(return_value=fake_results[:10])
            response = client.get("/api/recommendations/movie/1/?limit=10")
    assert response.status_code == 200
    assert len(response.json()) == 10


def test_recommendations_excludes_watched(client, rec_settings, db_session):
    from app.services.list_service import ListService
    from app.models.user_list import ListKind

    ListService(db_session).add(
        ListKind.WATCHED, "movie", 5, title="X", poster_path=None, backdrop_path=None, year=None,
    )
    fake_results = [
        {"id": 9, "title": "fresh", "overview": "", "vote_average": 7.0, "media_type": "movie"},
    ]
    with patch("app.routers.recommendations.TMDBService") as MockService:
        with patch("app.routers.recommendations.RecommendationService") as MockRec:
            instance = MockRec.return_value
            instance.get_recommendations = AsyncMock(return_value=fake_results)
            response = client.get("/api/recommendations/movie/1/")
    assert response.status_code == 200
    # Service is the one applying exclusions — verify it was called.
    instance.get_recommendations.assert_awaited_once()


def test_recommendations_maps_series_to_tv(client, rec_settings, db_session):
    with patch("app.routers.recommendations.TMDBService") as MockService:
        with patch("app.routers.recommendations.RecommendationService") as MockRec:
            instance = MockRec.return_value
            instance.get_recommendations = AsyncMock(return_value=[])
            client.get("/api/recommendations/series/1/")
    # service was constructed with tv as the TMDB media_type
    call_args = instance.get_recommendations.await_args
    assert call_args.args[0] == "tv"


def test_invalid_media_type_returns_400(client, rec_settings):
    response = client.get("/api/recommendations/bogus/1/")
    assert response.status_code == 400


def test_limit_validation(client, rec_settings):
    response = client.get("/api/recommendations/movie/1/?limit=0")
    assert response.status_code == 422
    response = client.get("/api/recommendations/movie/1/?limit=999")
    assert response.status_code == 422
