"""Tests for ListService."""
from app.models.download import Download, DownloadStatus, ContentType
from app.models.user_list import ListKind, UserList
from app.services.list_service import ListService


def _add_download(db, *, tmdb_id, media_type, status):
    d = Download(
        tmdb_id=tmdb_id,
        title=f"Title {tmdb_id}",
        type=media_type,
        torrent_name=f"t{tmdb_id}",
        status=status,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def test_add_is_idempotent(db_session):
    svc = ListService(db_session)
    svc.add(ListKind.WATCHLIST, "movie", 1, title="X", poster_path=None, backdrop_path=None, year=2020)
    svc.add(ListKind.WATCHLIST, "movie", 1, title="X (updated)", poster_path="/p.jpg", backdrop_path=None, year=2020)
    rows = db_session.query(UserList).all()
    assert len(rows) == 1
    assert rows[0].title == "X (updated)"
    assert rows[0].poster_path == "/p.jpg"


def test_add_separates_kinds(db_session):
    svc = ListService(db_session)
    svc.add(ListKind.WATCHED, "movie", 1, title="X", poster_path=None, backdrop_path=None, year=None)
    svc.add(ListKind.WATCHLIST, "movie", 1, title="X", poster_path=None, backdrop_path=None, year=None)
    assert db_session.query(UserList).count() == 2


def test_remove_returns_true_when_present(db_session):
    svc = ListService(db_session)
    svc.add(ListKind.WATCHLIST, "movie", 1, title="X", poster_path=None, backdrop_path=None, year=None)
    assert svc.remove(ListKind.WATCHLIST, "movie", 1) is True
    assert db_session.query(UserList).count() == 0


def test_remove_returns_false_when_absent(db_session):
    svc = ListService(db_session)
    assert svc.remove(ListKind.WATCHLIST, "movie", 1) is False


def test_get_status_reflects_state(db_session):
    svc = ListService(db_session)
    assert svc.get_status("movie", 1) == {"watched": False, "watchlist": False}
    svc.add(ListKind.WATCHLIST, "movie", 1, title="X", poster_path=None, backdrop_path=None, year=None)
    assert svc.get_status("movie", 1) == {"watched": False, "watchlist": True}
    svc.add(ListKind.WATCHED, "movie", 1, title="X", poster_path=None, backdrop_path=None, year=None)
    assert svc.get_status("movie", 1) == {"watched": True, "watchlist": True}


def test_list_watchlist_orders_by_created_desc(db_session):
    svc = ListService(db_session)
    svc.add(ListKind.WATCHLIST, "movie", 1, title="First", poster_path=None, backdrop_path=None, year=None)
    svc.add(ListKind.WATCHLIST, "series", 2, title="Second", poster_path=None, backdrop_path=None, year=None)
    svc.add(ListKind.WATCHED, "movie", 3, title="Watched one", poster_path=None, backdrop_path=None, year=None)

    out = svc.list_watchlist()
    assert [r.tmdb_id for r in out] == [2, 1]
    assert all(r.kind == ListKind.WATCHLIST for r in out)


def test_list_watched_returns_only_watched(db_session):
    svc = ListService(db_session)
    svc.add(ListKind.WATCHLIST, "movie", 1, title="W", poster_path=None, backdrop_path=None, year=None)
    svc.add(ListKind.WATCHED, "movie", 2, title="S", poster_path=None, backdrop_path=None, year=None)
    out = svc.list_watched()
    assert [r.tmdb_id for r in out] == [2]


def test_excluded_tmdb_ids_unions_watched_watchlist_and_completed(db_session):
    svc = ListService(db_session)
    svc.add(ListKind.WATCHED, "movie", 10, title="A", poster_path=None, backdrop_path=None, year=None)
    svc.add(ListKind.WATCHLIST, "movie", 20, title="B", poster_path=None, backdrop_path=None, year=None)
    svc.add(ListKind.WATCHED, "series", 30, title="C", poster_path=None, backdrop_path=None, year=None)
    _add_download(db_session, tmdb_id=40, media_type=ContentType.MOVIE, status=DownloadStatus.COMPLETED)
    _add_download(db_session, tmdb_id=50, media_type=ContentType.MOVIE, status=DownloadStatus.FAILED)
    _add_download(db_session, tmdb_id=60, media_type=ContentType.SERIES, status=DownloadStatus.COMPLETED)

    assert svc.excluded_tmdb_ids("movie") == {10, 20, 40}
    assert svc.excluded_tmdb_ids("series") == {30, 60}
    assert svc.excluded_tmdb_ids("anime") == set()
