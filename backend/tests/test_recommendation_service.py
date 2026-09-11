"""Tests for RecommendationService."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.download import ContentType, Download, DownloadStatus
from app.models.user_list import ListKind
from app.services.list_service import ListService
from app.services.recommendation_service import RecommendationService
from app.services.tmdb_service import TMDBService


@pytest.fixture
def tmdb_mock():
    tmdb = MagicMock(spec=TMDBService)
    tmdb.get_similar = AsyncMock(return_value=[])
    tmdb.get_recommendations = AsyncMock(return_value=[])
    return tmdb


@pytest.mark.asyncio
async def test_calls_both_endpoints_in_parallel(db_session, tmdb_mock):
    tmdb_mock.get_similar.return_value = [
        {"id": 1, "title": "A", "overview": "", "vote_average": 7.0, "media_type": "movie"}
    ]
    tmdb_mock.get_recommendations.return_value = [
        {"id": 2, "name": "B", "overview": "", "vote_average": 6.5, "media_type": "movie"}
    ]
    svc = RecommendationService(db=db_session, tmdb=tmdb_mock)
    result = await svc.get_recommendations("movie", 100, limit=10)

    assert [r["id"] for r in result] == [1, 2]
    tmdb_mock.get_similar.assert_awaited_once_with("movie", 100)
    tmdb_mock.get_recommendations.assert_awaited_once_with("movie", 100)


@pytest.mark.asyncio
async def test_dedupes_by_id_and_media_type(db_session, tmdb_mock):
    common = {"id": 5, "title": "Dup", "overview": "", "vote_average": 8.0, "media_type": "movie"}
    tmdb_mock.get_similar.return_value = [common]
    tmdb_mock.get_recommendations.return_value = [common]
    svc = RecommendationService(db=db_session, tmdb=tmdb_mock)
    result = await svc.get_recommendations("movie", 100, limit=10)
    assert len(result) == 1
    assert result[0]["id"] == 5


@pytest.mark.asyncio
async def test_drops_source_id(db_session, tmdb_mock):
    """The same item we asked for should not show up in its own recs."""
    tmdb_mock.get_similar.return_value = [
        {"id": 100, "title": "self", "overview": "", "vote_average": 7.0, "media_type": "movie"}
    ]
    tmdb_mock.get_recommendations.return_value = [
        {"id": 200, "title": "other", "overview": "", "vote_average": 7.0, "media_type": "movie"}
    ]
    svc = RecommendationService(db=db_session, tmdb=tmdb_mock)
    result = await svc.get_recommendations("movie", 100, limit=10)
    assert [r["id"] for r in result] == [200]


@pytest.mark.asyncio
async def test_filters_excluded_ids(db_session, tmdb_mock):
    # Mark id 5 as watched.
    ListService(db_session).add(
        ListKind.WATCHED, "movie", 5, title="X", poster_path=None, backdrop_path=None, year=None,
    )
    # Add a completed download with id 7.
    db_session.add(Download(
        tmdb_id=7, title="D", type=ContentType.MOVIE, torrent_name="d",
        status=DownloadStatus.COMPLETED,
    ))
    db_session.commit()

    tmdb_mock.get_similar.return_value = [
        {"id": 5, "title": "watched", "overview": "", "vote_average": 7.0, "media_type": "movie"},
        {"id": 7, "title": "owned", "overview": "", "vote_average": 7.0, "media_type": "movie"},
        {"id": 9, "title": "fresh", "overview": "", "vote_average": 7.0, "media_type": "movie"},
    ]
    tmdb_mock.get_recommendations.return_value = []
    svc = RecommendationService(db=db_session, tmdb=tmdb_mock)
    result = await svc.get_recommendations("movie", 100, limit=10)
    assert [r["id"] for r in result] == [9]


@pytest.mark.asyncio
async def test_respects_limit(db_session, tmdb_mock):
    tmdb_mock.get_similar.return_value = [
        {"id": i, "title": f"T{i}", "overview": "", "vote_average": 7.0, "media_type": "movie"}
        for i in range(50)
    ]
    tmdb_mock.get_recommendations.return_value = []
    svc = RecommendationService(db=db_session, tmdb=tmdb_mock)
    result = await svc.get_recommendations("movie", 100, limit=5)
    assert len(result) == 5


@pytest.mark.asyncio
async def test_uses_tv_endpoints_for_tv(db_session, tmdb_mock):
    tmdb_mock.get_similar.return_value = [
        {"id": 1, "name": "T", "overview": "", "vote_average": 7.0, "media_type": "tv"}
    ]
    svc = RecommendationService(db=db_session, tmdb=tmdb_mock)
    await svc.get_recommendations("tv", 200, limit=10)
    tmdb_mock.get_similar.assert_awaited_once_with("tv", 200)
    tmdb_mock.get_recommendations.assert_awaited_once_with("tv", 200)
