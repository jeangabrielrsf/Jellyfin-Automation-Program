# Watched, Watchlist, and Recommendations — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add manual watched/watchlist tracking (single-user, in-house) and a TMDB-powered recommendations row on the detail page.

**Architecture:**
- New `user_lists` table in Postgres; one row per `(tmdb_id, media_type, kind)` triple.
- New `lists.py` and `recommendations.py` FastAPI routers.
- `ListService` (sync) for CRUD on `user_lists` plus an exclusion-set helper that unions with `downloads` where `status=COMPLETED`.
- `RecommendationService` (async) that hits `/{id}/similar` and `/{id}/recommendations` on TMDB in parallel, dedupes, applies the exclusion set, and caches per `(media_type, tmdb_id)` for 1 hour.
- Frontend: two new components (`MediaActions`, `RecommendationsRow`) and one new page (`Watchlist`). Detail page mounts both. Header gets a new nav item, App.tsx a new route.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic, pytest + pytest-asyncio, httpx, React 18, TanStack Query, shadcn/ui (Button, Dialog already in use), lucide-react, sonner, TailwindCSS, Vite, TypeScript.

**Spec:** `docs/superpowers/specs/2026-05-31-watched-watchlist-recommendations-design.md`

---

## File Map

### Backend — new files
- `backend/app/models/user_list.py` — `UserList` model + `ListKind` enum.
- `backend/app/services/list_service.py` — `ListService`.
- `backend/app/services/recommendation_service.py` — `RecommendationService`.
- `backend/app/routers/lists.py` — `/api/lists/...` endpoints.
- `backend/app/routers/recommendations.py` — `/api/recommendations/...` endpoint.
- `backend/alembic/versions/<rev>_add_user_lists.py` — Alembic migration.
- `backend/tests/test_list_service.py`
- `backend/tests/test_recommendation_service.py`
- `backend/tests/test_lists_router.py`
- `backend/tests/test_recommendations_router.py`

### Backend — modified
- `backend/app/services/tmdb_service.py` — add 4 new methods (`get_similar_movies`, `get_similar_tv`, `get_recommendations_movies`, `get_recommendations_tv`).
- `backend/app/main.py` — register the two new routers.
- `backend/tests/conftest.py` — import the new model so `Base.metadata.create_all` registers the table in test DBs.

### Frontend — new files
- `frontend/src/components/MediaActions.tsx`
- `frontend/src/components/RecommendationsRow.tsx`
- `frontend/src/pages/Watchlist.tsx`

### Frontend — modified
- `frontend/src/types/index.ts` — add `ListKind`, `UserMediaType`, `ListStatus`, `ListItem`, `Recommendation`.
- `frontend/src/services/api.ts` — add `listsAPI` and `recommendationsAPI`.
- `frontend/src/pages/Detail.tsx` — mount `MediaActions` and `RecommendationsRow`.
- `frontend/src/components/Header.tsx` — add Watchlist nav item.
- `frontend/src/App.tsx` — add `/watchlist` route.

---

## Task 1: UserList model + conftest registration

**Files:**
- Create: `backend/app/models/user_list.py`
- Modify: `backend/tests/conftest.py` (add one import line)

- [ ] **Step 1: Create the model file**

Create `backend/app/models/user_list.py`:

```python
"""UserList model — single-user watched and watchlist tracking."""
import enum

from sqlalchemy import (
    CheckConstraint, Column, DateTime, Enum, Integer, String, UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database import Base


class ListKind(str, enum.Enum):
    WATCHED = "watched"
    WATCHLIST = "watchlist"


class UserList(Base):
    __tablename__ = "user_lists"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(Enum(ListKind), nullable=False)
    media_type = Column(String(16), nullable=False)
    tmdb_id = Column(Integer, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    poster_path = Column(String(255))
    backdrop_path = Column(String(255))
    year = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tmdb_id", "media_type", "kind", name="uq_user_lists_tmdb_type_kind"),
        CheckConstraint(
            "media_type IN ('movie','series','anime')",
            name="ck_user_lists_media_type",
        ),
    )
```

- [ ] **Step 2: Register the model in conftest**

In `backend/tests/conftest.py`, add the import after the existing model imports (around line 30):

```python
    from app.models.download import Download  # noqa: F401
    from app.models.settings import Setting  # noqa: F401
    from app.models.user_list import UserList  # noqa: F401
```

- [ ] **Step 3: Verify the model registers cleanly**

Run:
```bash
cd backend && pytest tests/ -v
```

Expected: all existing tests pass; no new behavior yet, but the `user_lists` table is now created in the in-memory test DB.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/user_list.py backend/tests/conftest.py
git commit -m "feat: add UserList model and kind enum"
```

---

## Task 2: Alembic migration

**Files:**
- Create: `backend/alembic/versions/<rev>_add_user_lists.py` (rev id generated by Alembic)

- [ ] **Step 1: Generate the migration**

From `backend/`:

```bash
cd backend && alembic revision --autogenerate -m "add user_lists"
```

Expected output ends with `Generating /.../alembic/versions/<rev>_add_user_lists.py ... done`.

- [ ] **Step 2: Inspect the generated file**

Open the new file at `backend/alembic/versions/<rev>_add_user_lists.py`. Verify it contains:

- `op.create_table("user_lists", ...)` with all columns (id, kind, media_type, tmdb_id, title, poster_path, backdrop_path, year, created_at, updated_at)
- An index on `tmdb_id`
- A `UniqueConstraint` on `(tmdb_id, media_type, kind)`
- A `CheckConstraint` on `media_type`

If any are missing, add them. The file's `down_revision` should be `3a33a45e80a0` (the latest existing revision). If Alembic picks something else, fix it.

- [ ] **Step 3: Apply the migration locally**

From `backend/`:

```bash
cd backend && alembic upgrade head
```

Expected: ends with `Running upgrade 3a33a45e80a0 -> <new rev>, add user_lists`.

- [ ] **Step 4: Verify the table exists**

From `backend/`, with the dev Postgres reachable:

```bash
psql "$DATABASE_URL" -c "\d user_lists"
```

Expected: a table definition showing all columns and the two constraints. (If `psql` isn't available, this step is optional — the migration applies cleanly to SQLite during test runs via `Base.metadata.create_all`.)

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/<rev>_add_user_lists.py
git commit -m "feat: add user_lists migration"
```

---

## Task 3: ListService (TDD)

**Files:**
- Test: `backend/tests/test_list_service.py`
- Create: `backend/app/services/list_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_list_service.py`:

```python
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
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run:
```bash
cd backend && pytest tests/test_list_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.list_service'` (or similar import error). All tests fail.

- [ ] **Step 3: Implement ListService**

Create `backend/app/services/list_service.py`:

```python
"""CRUD and exclusion logic for the user_lists table."""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.download import Download, DownloadStatus
from app.models.user_list import ListKind, UserList


class ListService:
    """Single-user wrapper around the user_lists table."""

    def __init__(self, db: Session):
        self.db = db

    def get_status(self, media_type: str, tmdb_id: int) -> dict:
        rows = (
            self.db.query(UserList)
            .filter(
                UserList.media_type == media_type,
                UserList.tmdb_id == tmdb_id,
            )
            .all()
        )
        return {
            "watched": any(r.kind == ListKind.WATCHED for r in rows),
            "watchlist": any(r.kind == ListKind.WATCHLIST for r in rows),
        }

    def add(
        self,
        kind: ListKind,
        media_type: str,
        tmdb_id: int,
        *,
        title: str,
        poster_path: Optional[str],
        backdrop_path: Optional[str],
        year: Optional[int],
    ) -> UserList:
        existing = (
            self.db.query(UserList)
            .filter(
                UserList.kind == kind,
                UserList.media_type == media_type,
                UserList.tmdb_id == tmdb_id,
            )
            .first()
        )
        if existing:
            existing.title = title
            existing.poster_path = poster_path
            existing.backdrop_path = backdrop_path
            existing.year = year
            self.db.commit()
            self.db.refresh(existing)
            return existing

        row = UserList(
            kind=kind,
            media_type=media_type,
            tmdb_id=tmdb_id,
            title=title,
            poster_path=poster_path,
            backdrop_path=backdrop_path,
            year=year,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def remove(self, kind: ListKind, media_type: str, tmdb_id: int) -> bool:
        existing = (
            self.db.query(UserList)
            .filter(
                UserList.kind == kind,
                UserList.media_type == media_type,
                UserList.tmdb_id == tmdb_id,
            )
            .first()
        )
        if not existing:
            return False
        self.db.delete(existing)
        self.db.commit()
        return True

    def list_watchlist(self) -> list[UserList]:
        return (
            self.db.query(UserList)
            .filter(UserList.kind == ListKind.WATCHLIST)
            .order_by(UserList.created_at.desc())
            .all()
        )

    def list_watched(self) -> list[UserList]:
        return (
            self.db.query(UserList)
            .filter(UserList.kind == ListKind.WATCHED)
            .order_by(UserList.created_at.desc())
            .all()
        )

    def excluded_tmdb_ids(self, media_type: str) -> set[int]:
        list_ids = {
            row.tmdb_id
            for row in self.db.query(UserList.tmdb_id)
            .filter(UserList.media_type == media_type)
            .all()
        }
        download_ids = {
            row.tmdb_id
            for row in self.db.query(Download.tmdb_id)
            .filter(
                Download.type == media_type,
                Download.status == DownloadStatus.COMPLETED,
            )
            .all()
        }
        return list_ids | download_ids
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run:
```bash
cd backend && pytest tests/test_list_service.py -v
```

Expected: 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/list_service.py backend/tests/test_list_service.py
git commit -m "feat: add ListService with CRUD and exclusion helpers"
```

---

## Task 4: TMDBService — 4 new async methods (TDD)

**Files:**
- Modify: `backend/app/services/tmdb_service.py`
- Modify: `backend/tests/test_tmdb_service.py` (append tests)

- [ ] **Step 1: Add failing tests**

Append to `backend/tests/test_tmdb_service.py`:

```python
@pytest.mark.asyncio
async def test_get_similar_movies_returns_results(tmdb_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "id": 11,
                "title": "Similar A",
                "overview": "...",
                "vote_average": 7.0,
                "poster_path": "/a.jpg",
                "release_date": "2021-01-01",
                "media_type": "movie",
                "genre_ids": [28],
            },
            {
                "id": 12,
                "title": "Similar B",
                "overview": "...",
                "vote_average": 6.5,
                "media_type": "movie",
                "genre_ids": [],
            },
        ]
    }
    mock_response.raise_for_status = MagicMock()
    with patch.object(tmdb_service.client, "get", AsyncMock(return_value=mock_response)):
        result = await tmdb_service.get_similar_movies(1)
    assert [r["id"] for r in result] == [11, 12]


@pytest.mark.asyncio
async def test_get_similar_tv_returns_results(tmdb_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "id": 21,
                "name": "TV A",
                "overview": "...",
                "vote_average": 8.0,
                "media_type": "tv",
                "genre_ids": [],
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    with patch.object(tmdb_service.client, "get", AsyncMock(return_value=mock_response)):
        result = await tmdb_service.get_similar_tv(1)
    assert [r["id"] for r in result] == [21]


@pytest.mark.asyncio
async def test_get_recommendations_movies_returns_results(tmdb_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "id": 31,
                "title": "Rec A",
                "overview": "...",
                "vote_average": 7.5,
                "media_type": "movie",
                "genre_ids": [],
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    with patch.object(tmdb_service.client, "get", AsyncMock(return_value=mock_response)):
        result = await tmdb_service.get_recommendations_movies(1)
    assert [r["id"] for r in result] == [31]


@pytest.mark.asyncio
async def test_get_recommendations_tv_returns_results(tmdb_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "id": 41,
                "name": "Rec TV A",
                "overview": "...",
                "vote_average": 7.2,
                "media_type": "tv",
                "genre_ids": [],
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    with patch.object(tmdb_service.client, "get", AsyncMock(return_value=mock_response)):
        result = await tmdb_service.get_recommendations_tv(1)
    assert [r["id"] for r in result] == [41]
```

- [ ] **Step 2: Run the new tests and confirm they fail**

Run:
```bash
cd backend && pytest tests/test_tmdb_service.py -v -k "get_similar or get_recommendations"
```

Expected: 4 failed (AttributeError on the new method).

- [ ] **Step 3: Add the four methods to TMDBService**

In `backend/app/services/tmdb_service.py`, add these four methods at the bottom of the `TMDBService` class (after `get_tv_season_detail`):

```python
    async def get_similar_movies(self, movie_id: int) -> list[dict]:
        """Fetch movies similar to the given movie id."""
        logger.info("Fetching similar movies", movie_id=movie_id)
        url = f"{self.BASE_URL}/movie/{movie_id}/similar"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR",
        }
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("results", [])

    async def get_similar_tv(self, tv_id: int) -> list[dict]:
        """Fetch TV shows similar to the given tv id."""
        logger.info("Fetching similar TV", tv_id=tv_id)
        url = f"{self.BASE_URL}/tv/{tv_id}/similar"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR",
        }
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("results", [])

    async def get_recommendations_movies(self, movie_id: int) -> list[dict]:
        """Fetch TMDB-curated movie recommendations for the given movie id."""
        logger.info("Fetching movie recommendations", movie_id=movie_id)
        url = f"{self.BASE_URL}/movie/{movie_id}/recommendations"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR",
        }
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("results", [])

    async def get_recommendations_tv(self, tv_id: int) -> list[dict]:
        """Fetch TMDB-curated TV recommendations for the given tv id."""
        logger.info("Fetching TV recommendations", tv_id=tv_id)
        url = f"{self.BASE_URL}/tv/{tv_id}/recommendations"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR",
        }
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("results", [])
```

- [ ] **Step 4: Run the new tests and confirm they pass**

Run:
```bash
cd backend && pytest tests/test_tmdb_service.py -v -k "get_similar or get_recommendations"
```

Expected: 4 passed.

- [ ] **Step 5: Run the full tmdb test file to make sure nothing else regressed**

Run:
```bash
cd backend && pytest tests/test_tmdb_service.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/tmdb_service.py backend/tests/test_tmdb_service.py
git commit -m "feat: add TMDB similar and recommendations methods"
```

---

## Task 5: lists router (TDD)

**Files:**
- Create: `backend/app/routers/lists.py`
- Create: `backend/tests/test_lists_router.py`
- Modify: `backend/app/main.py` (register router — but we'll do that in Task 8; tests use the same `client` fixture that mounts all routers)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_lists_router.py`:

```python
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
```

- [ ] **Step 2: Run tests, confirm failure**

Run:
```bash
cd backend && pytest tests/test_lists_router.py -v
```

Expected: 11 failures (404 or connection error — router not yet registered).

- [ ] **Step 3: Implement the router**

Create `backend/app/routers/lists.py`:

```python
"""User list endpoints — watched and watchlist."""
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_list import ListKind, UserList
from app.services.list_service import ListService


router = APIRouter(prefix="/api/lists", tags=["lists"])

_VALID_MEDIA_TYPES = {"movie", "series", "anime"}


class ListItemPayload(BaseModel):
    title: str
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    year: Optional[int] = None


def _check_media_type(media_type: str) -> None:
    if media_type not in _VALID_MEDIA_TYPES:
        raise HTTPException(status_code=400, detail="invalid media_type")


@router.get("/status/{media_type}/{tmdb_id}/")
def get_status(media_type: str, tmdb_id: int, db: Session = Depends(get_db)) -> dict:
    _check_media_type(media_type)
    return ListService(db).get_status(media_type, tmdb_id)


@router.post("/{kind}/{media_type}/{tmdb_id}/", status_code=204)
async def add_item(
    kind: ListKind,
    media_type: str,
    tmdb_id: int,
    payload: Optional[ListItemPayload] = Body(default=None),
    db: Session = Depends(get_db),
):
    _check_media_type(media_type)
    if payload is None:
        # Hydrate from TMDB.
        from app.services.tmdb_service import TMDBService

        tmdb = TMDBService(db=db)
        try:
            detail = (
                await tmdb.get_movie_detail(tmdb_id)
                if media_type == "movie"
                else await tmdb.get_tv_detail(tmdb_id)
            )
            payload = ListItemPayload(
                title=detail.display_title,
                poster_path=detail.poster_path,
                backdrop_path=detail.backdrop_path,
                year=detail.year,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"TMDB hydration failed: {exc}"
            ) from exc
        finally:
            await tmdb.close()

    ListService(db).add(
        kind,
        media_type,
        tmdb_id,
        title=payload.title,
        poster_path=payload.poster_path,
        backdrop_path=payload.backdrop_path,
        year=payload.year,
    )
    return Response(status_code=204)


@router.delete("/{kind}/{media_type}/{tmdb_id}/", status_code=204)
def remove_item(
    kind: ListKind,
    media_type: str,
    tmdb_id: int,
    db: Session = Depends(get_db),
):
    _check_media_type(media_type)
    deleted = ListService(db).remove(kind, media_type, tmdb_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="not in list")
    return Response(status_code=204)


@router.get("/watchlist/", response_model=list[UserList])
def get_watchlist(db: Session = Depends(get_db)) -> list[UserList]:
    return ListService(db).list_watchlist()


@router.get("/watched/", response_model=list[UserList])
def get_watched(db: Session = Depends(get_db)) -> list[UserList]:
    return ListService(db).list_watched()
```

- [ ] **Step 4: Register the router in main.py**

In `backend/app/main.py`, modify two places:

Top imports (around line 13), change:
```python
from app.routers import search, downloads, settings, logs, filesystem, discover
```
to:
```python
from app.routers import search, downloads, settings, logs, filesystem, discover, lists
```

In the `app.include_router(...)` block (around line 148), add:
```python
app.include_router(lists.router)
```

- [ ] **Step 5: Run tests, confirm they pass**

Run:
```bash
cd backend && pytest tests/test_lists_router.py -v
```

Expected: 11 passed.

- [ ] **Step 6: Run the full backend test suite to verify no regressions**

Run:
```bash
cd backend && pytest tests/ -v
```

Expected: all tests pass (the new 11 plus everything that existed before).

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/lists.py backend/app/main.py backend/tests/test_lists_router.py
git commit -m "feat: add /api/lists router and wire into main"
```

---

## Task 6: RecommendationService (TDD)

**Files:**
- Create: `backend/app/services/recommendation_service.py`
- Create: `backend/tests/test_recommendation_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_recommendation_service.py`:

```python
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
    tmdb.get_similar_movies = AsyncMock(return_value=[])
    tmdb.get_recommendations_movies = AsyncMock(return_value=[])
    tmdb.get_similar_tv = AsyncMock(return_value=[])
    tmdb.get_recommendations_tv = AsyncMock(return_value=[])
    return tmdb


@pytest.mark.asyncio
async def test_calls_both_endpoints_in_parallel(db_session, tmdb_mock):
    tmdb_mock.get_similar_movies.return_value = [
        {"id": 1, "title": "A", "overview": "", "vote_average": 7.0, "media_type": "movie"}
    ]
    tmdb_mock.get_recommendations_movies.return_value = [
        {"id": 2, "name": "B", "overview": "", "vote_average": 6.5, "media_type": "movie"}
    ]
    svc = RecommendationService(db=db_session, tmdb=tmdb_mock)
    result = await svc.get_recommendations("movie", 100, limit=10)

    assert [r["id"] for r in result] == [1, 2]
    tmdb_mock.get_similar_movies.assert_awaited_once_with(100)
    tmdb_mock.get_recommendations_movies.assert_awaited_once_with(100)


@pytest.mark.asyncio
async def test_dedupes_by_id_and_media_type(db_session, tmdb_mock):
    common = {"id": 5, "title": "Dup", "overview": "", "vote_average": 8.0, "media_type": "movie"}
    tmdb_mock.get_similar_movies.return_value = [common]
    tmdb_mock.get_recommendations_movies.return_value = [common]
    svc = RecommendationService(db=db_session, tmdb=tmdb_mock)
    result = await svc.get_recommendations("movie", 100, limit=10)
    assert len(result) == 1
    assert result[0]["id"] == 5


@pytest.mark.asyncio
async def test_drops_source_id(db_session, tmdb_mock):
    """The same item we asked for should not show up in its own recs."""
    tmdb_mock.get_similar_movies.return_value = [
        {"id": 100, "title": "self", "overview": "", "vote_average": 7.0, "media_type": "movie"}
    ]
    tmdb_mock.get_recommendations_movies.return_value = [
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

    tmdb_mock.get_similar_movies.return_value = [
        {"id": 5, "title": "watched", "overview": "", "vote_average": 7.0, "media_type": "movie"},
        {"id": 7, "title": "owned", "overview": "", "vote_average": 7.0, "media_type": "movie"},
        {"id": 9, "title": "fresh", "overview": "", "vote_average": 7.0, "media_type": "movie"},
    ]
    tmdb_mock.get_recommendations_movies.return_value = []
    svc = RecommendationService(db=db_session, tmdb=tmdb_mock)
    result = await svc.get_recommendations("movie", 100, limit=10)
    assert [r["id"] for r in result] == [9]


@pytest.mark.asyncio
async def test_caches_results(db_session, tmdb_mock):
    tmdb_mock.get_similar_movies.return_value = [
        {"id": 1, "title": "A", "overview": "", "vote_average": 7.0, "media_type": "movie"}
    ]
    svc = RecommendationService(db=db_session, tmdb=tmdb_mock)
    await svc.get_recommendations("movie", 100, limit=10)
    await svc.get_recommendations("movie", 100, limit=10)
    # Second call should not re-hit TMDB.
    tmdb_mock.get_similar_movies.assert_awaited_once()


@pytest.mark.asyncio
async def test_respects_limit(db_session, tmdb_mock):
    tmdb_mock.get_similar_movies.return_value = [
        {"id": i, "title": f"T{i}", "overview": "", "vote_average": 7.0, "media_type": "movie"}
        for i in range(50)
    ]
    tmdb_mock.get_recommendations_movies.return_value = []
    svc = RecommendationService(db=db_session, tmdb=tmdb_mock)
    result = await svc.get_recommendations("movie", 100, limit=5)
    assert len(result) == 5


@pytest.mark.asyncio
async def test_uses_tv_endpoints_for_tv(db_session, tmdb_mock):
    tmdb_mock.get_similar_tv.return_value = [
        {"id": 1, "name": "T", "overview": "", "vote_average": 7.0, "media_type": "tv"}
    ]
    svc = RecommendationService(db=db_session, tmdb=tmdb_mock)
    await svc.get_recommendations("tv", 200, limit=10)
    tmdb_mock.get_similar_tv.assert_awaited_once_with(200)
    tmdb_mock.get_recommendations_tv.assert_awaited_once_with(200)
```

- [ ] **Step 2: Run tests, confirm failure**

Run:
```bash
cd backend && pytest tests/test_recommendation_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.recommendation_service'` — all fail.

- [ ] **Step 3: Implement RecommendationService**

Create `backend/app/services/recommendation_service.py`:

```python
"""Combines TMDB similar + recommendations, dedupes, applies exclusion set, caches."""
import asyncio
import time

from app.services.list_service import ListService


class RecommendationService:
    CACHE_TTL_SECONDS = 3600

    def __init__(self, db, tmdb):
        self.db = db
        self.tmdb = tmdb
        self._cache: dict[tuple[str, int], tuple[float, list[dict]]] = {}

    async def get_recommendations(
        self, media_type: str, tmdb_id: int, *, limit: int = 10
    ) -> list[dict]:
        key = (media_type, tmdb_id)
        now = time.time()

        cached = self._cache.get(key)
        if cached is not None and now - cached[0] < self.CACHE_TTL_SECONDS:
            raw = cached[1]
        else:
            raw = await self._fetch_union(media_type, tmdb_id)
            self._cache[key] = (now, raw)

        excluded = ListService(self.db).excluded_tmdb_ids(media_type)

        seen: set[tuple[int, str]] = set()
        result: list[dict] = []
        for item in raw:
            item_id = item.get("id")
            if item_id is None or item_id == tmdb_id:
                continue
            if item_id in excluded:
                continue
            dedupe_key = (item_id, item.get("media_type", media_type))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            result.append(item)
            if len(result) >= limit:
                break
        return result

    async def _fetch_union(self, media_type: str, tmdb_id: int) -> list[dict]:
        if media_type == "movie":
            similar_task = self.tmdb.get_similar_movies(tmdb_id)
            recs_task = self.tmdb.get_recommendations_movies(tmdb_id)
        else:
            similar_task = self.tmdb.get_similar_tv(tmdb_id)
            recs_task = self.tmdb.get_recommendations_tv(tmdb_id)

        similar, recs = await asyncio.gather(similar_task, recs_task)
        return list(similar) + list(recs)
```

- [ ] **Step 4: Run tests, confirm they pass**

Run:
```bash
cd backend && pytest tests/test_recommendation_service.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/recommendation_service.py backend/tests/test_recommendation_service.py
git commit -m "feat: add RecommendationService with cache and exclusions"
```

---

## Task 7: recommendations router (TDD)

**Files:**
- Create: `backend/app/routers/recommendations.py`
- Create: `backend/tests/test_recommendations_router.py`
- Modify: `backend/app/main.py` (register router)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_recommendations_router.py`:

```python
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
```

- [ ] **Step 2: Run tests, confirm failure**

Run:
```bash
cd backend && pytest tests/test_recommendations_router.py -v
```

Expected: 5 failures (404 — router not registered).

- [ ] **Step 3: Implement the router**

Create `backend/app/routers/recommendations.py`:

```python
"""Recommendations endpoint — TMDB similar + recommendations, exclusion-filtered."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.recommendation_service import RecommendationService
from app.services.tmdb_service import TMDBService


router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

_VALID_MEDIA_TYPES = {"movie", "series", "anime"}


@router.get("/{media_type}/{tmdb_id}/")
async def get_recommendations(
    media_type: str,
    tmdb_id: int,
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[dict]:
    if media_type not in _VALID_MEDIA_TYPES:
        raise HTTPException(status_code=400, detail="invalid media_type")
    tmdb_media_type = "movie" if media_type == "movie" else "tv"
    tmdb = TMDBService(db=db)
    try:
        service = RecommendationService(db=db, tmdb=tmdb)
        return await service.get_recommendations(tmdb_media_type, tmdb_id, limit=limit)
    finally:
        await tmdb.close()
```

- [ ] **Step 4: Register the router in main.py**

In `backend/app/main.py`, change the import:
```python
from app.routers import search, downloads, settings, logs, filesystem, discover, lists, recommendations
```

And in the `include_router` block, add:
```python
app.include_router(recommendations.router)
```

- [ ] **Step 5: Run tests, confirm they pass**

Run:
```bash
cd backend && pytest tests/test_recommendations_router.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Run the full backend test suite**

Run:
```bash
cd backend && pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/recommendations.py backend/app/main.py backend/tests/test_recommendations_router.py
git commit -m "feat: add /api/recommendations router and wire into main"
```

---

## Task 8: Backend full-suite verification

This task exists to catch any cross-router regression before we touch the frontend.

**Files:** none.

- [ ] **Step 1: Run the full backend test suite with output**

Run:
```bash
cd backend && pytest tests/ -v 2>&1 | tail -60
```

Expected: every test passes. If anything fails, fix it before moving on.

- [ ] **Step 2: Lint (optional, if ruff is configured)**

Run:
```bash
cd backend && (ruff check app/ tests/ || true)
```

If ruff complains about unused imports or style, fix them.

- [ ] **Step 3: (Optional) Smoke-test the live server**

If the dev Postgres is reachable, start the server briefly:

```bash
cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8765 &
SERVER_PID=$!
sleep 2
curl -s http://127.0.0.1:8765/health
kill $SERVER_PID
```

Expected: `{"status":"healthy","version":"1.0.0"}`. If this fails, debug before moving on.

---

## Task 9: Frontend — types

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Append the new types**

Open `frontend/src/types/index.ts` and append at the end:

```typescript
export type ListKind = 'watched' | 'watchlist';
export type UserMediaType = 'movie' | 'series' | 'anime';

export interface ListStatus {
  watched: boolean;
  watchlist: boolean;
}

export interface ListItem {
  id: number;
  kind: ListKind;
  media_type: UserMediaType;
  tmdb_id: number;
  title: string;
  poster_path: string | null;
  backdrop_path: string | null;
  year: number | null;
  created_at: string;
}

export interface Recommendation {
  id: number;
  title?: string;
  name?: string;
  overview: string;
  poster_path: string | null;
  backdrop_path: string | null;
  release_date?: string;
  first_air_date?: string;
  vote_average: number;
  media_type: 'movie' | 'tv';
  genre_ids: number[];
}
```

- [ ] **Step 2: Verify the build still type-checks**

Run:
```bash
cd frontend && npm run build
```

Expected: TypeScript compiles cleanly and Vite produces `dist/`. No new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add list and recommendation types"
```

---

## Task 10: Frontend — API client

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Append the new API clients**

Open `frontend/src/services/api.ts` and add the following at the end (before the `export default api;` line):

```typescript
import type { ListKind, UserMediaType, ListStatus, ListItem, Recommendation } from '@/types';

export const listsAPI = {
  getStatus: (mediaType: UserMediaType, tmdbId: number) =>
    api.get<ListStatus>(`/lists/status/${mediaType}/${tmdbId}/`),

  add: (
    kind: ListKind,
    mediaType: UserMediaType,
    tmdbId: number,
    payload?: {
      title: string;
      poster_path: string | null;
      backdrop_path: string | null;
      year: number | null;
    },
  ) => api.post(`/lists/${kind}/${mediaType}/${tmdbId}/`, payload ?? null),

  remove: (kind: ListKind, mediaType: UserMediaType, tmdbId: number) =>
    api.delete(`/lists/${kind}/${mediaType}/${tmdbId}/`),

  listWatchlist: () => api.get<ListItem[]>('/lists/watchlist/'),
  listWatched: () => api.get<ListItem[]>('/lists/watched/'),
};

export const recommendationsAPI = {
  get: (mediaType: UserMediaType, tmdbId: number, limit = 10) =>
    api.get<Recommendation[]>(`/recommendations/${mediaType}/${tmdbId}/`, { params: { limit } }),
};
```

- [ ] **Step 2: Verify the build still type-checks**

Run:
```bash
cd frontend && npm run build
```

Expected: builds cleanly.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat: add listsAPI and recommendationsAPI clients"
```

---

## Task 11: MediaActions component

**Files:**
- Create: `frontend/src/components/MediaActions.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/MediaActions.tsx`:

```typescript
import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bookmark, Eye, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { listsAPI } from '@/services/api';
import type { ListKind, UserMediaType } from '@/types';

interface MediaActionsProps {
  mediaType: UserMediaType;
  tmdbId: number;
  title: string;
  posterPath: string | null;
  backdropPath: string | null;
  year: number | null;
}

export const MediaActions: React.FC<MediaActionsProps> = ({
  mediaType,
  tmdbId,
  title,
  posterPath,
  backdropPath,
  year,
}) => {
  const queryClient = useQueryClient();

  const { data: status } = useQuery({
    queryKey: ['list-status', mediaType, tmdbId],
    queryFn: () => listsAPI.getStatus(mediaType, tmdbId).then((r) => r.data),
  });

  const toggle = useMutation({
    mutationFn: async (kind: ListKind) => {
      const inList = status?.[kind] ?? false;
      if (inList) {
        await listsAPI.remove(kind, mediaType, tmdbId);
      } else {
        await listsAPI.add(kind, mediaType, tmdbId, {
          title,
          poster_path: posterPath,
          backdrop_path: backdropPath,
          year,
        });
      }
    },
    onSuccess: (_, kind) => {
      toast.success(
        kind === 'watched' ? 'Marcado como visto' : 'Adicionado à watchlist',
      );
      queryClient.invalidateQueries({ queryKey: ['list-status', mediaType, tmdbId] });
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    },
    onError: (e) => {
      const msg = e instanceof Error ? e.message : 'Falha ao atualizar lista';
      toast.error(msg);
    },
  });

  const pillBase =
    'flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors disabled:opacity-50';
  const pillActive = 'bg-primary/20 text-primary hover:bg-primary/30';
  const pillInactive = 'glass border border-border/50 text-muted-foreground hover:text-foreground';

  return (
    <div className="flex items-center gap-2 mt-3 flex-wrap">
      <button
        type="button"
        onClick={() => toggle.mutate('watchlist')}
        disabled={toggle.isPending}
        className={`${pillBase} ${status?.watchlist ? pillActive : pillInactive}`}
      >
        {toggle.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bookmark className="w-4 h-4" />}
        {status?.watchlist ? 'Na watchlist' : 'Watchlist'}
      </button>
      <button
        type="button"
        onClick={() => toggle.mutate('watched')}
        disabled={toggle.isPending}
        className={`${pillBase} ${status?.watched ? pillActive : pillInactive}`}
      >
        {toggle.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
        {status?.watched ? 'Visto' : 'Marcar como visto'}
      </button>
    </div>
  );
};
```

- [ ] **Step 2: Verify the build type-checks**

Run:
```bash
cd frontend && npm run build
```

Expected: builds cleanly.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/MediaActions.tsx
git commit -m "feat: add MediaActions toggle component"
```

---

## Task 12: RecommendationsRow component

**Files:**
- Create: `frontend/src/components/RecommendationsRow.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/RecommendationsRow.tsx`:

```typescript
import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Star } from 'lucide-react';
import { recommendationsAPI } from '@/services/api';
import type { Recommendation, UserMediaType } from '@/types';

interface RecommendationsRowProps {
  mediaType: UserMediaType;
  tmdbId: number;
}

const RecommendationCard: React.FC<{ item: Recommendation }> = ({ item }) => {
  const title = item.title || item.name || 'Sem título';
  const year =
    (item.release_date || item.first_air_date || '').slice(0, 4) || null;
  const detailPath =
    item.media_type === 'movie'
      ? `/detail/movie/${item.id}`
      : `/detail/tv/${item.id}`;
  return (
    <Link
      to={detailPath}
      className="shrink-0 w-36 sm:w-44 rounded-xl overflow-hidden border border-border/30 bg-background/50 hover:border-primary/30 transition-colors"
    >
      {item.poster_path ? (
        <img
          src={`https://image.tmdb.org/t/p/w300${item.poster_path}`}
          alt={title}
          className="w-full h-52 object-cover"
          loading="lazy"
        />
      ) : (
        <div className="w-full h-52 bg-muted flex items-center justify-center text-muted-foreground text-sm">
          Sem imagem
        </div>
      )}
      <div className="p-2 space-y-1">
        <p className="text-sm font-medium text-foreground line-clamp-2">{title}</p>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{year || '—'}</span>
          {item.vote_average > 0 && (
            <span className="flex items-center gap-0.5">
              <Star className="w-3 h-3 fill-current" />
              {item.vote_average.toFixed(1)}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
};

export const RecommendationsRow: React.FC<RecommendationsRowProps> = ({
  mediaType,
  tmdbId,
}) => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['recommendations', mediaType, tmdbId],
    queryFn: () => recommendationsAPI.get(mediaType, tmdbId, 10).then((r) => r.data),
    staleTime: 60 * 60 * 1000,
  });

  if (isLoading || isError) return null;
  if (!data || data.length === 0) return null;

  return (
    <section className="space-y-3">
      <h3 className="font-display text-lg font-bold text-foreground">Recomendações</h3>
      <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
        {data.map((rec) => (
          <RecommendationCard key={`${rec.media_type}-${rec.id}`} item={rec} />
        ))}
      </div>
    </section>
  );
};
```

- [ ] **Step 2: Verify the build type-checks**

Run:
```bash
cd frontend && npm run build
```

Expected: builds cleanly.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/RecommendationsRow.tsx
git commit -m "feat: add RecommendationsRow component"
```

---

## Task 13: Detail page integration

**Files:**
- Modify: `frontend/src/pages/Detail.tsx`

- [ ] **Step 1: Add imports**

In `frontend/src/pages/Detail.tsx`, add to the import block at the top:

```typescript
import { MediaActions } from '@/components/MediaActions';
import { RecommendationsRow } from '@/components/RecommendationsRow';
```

- [ ] **Step 2: Mount MediaActions in the hero**

Find the existing trailer button block inside the hero `<div className="flex items-center gap-3 mt-3">` (around line 236). Replace that entire div with:

```tsx
            <div className="flex items-center gap-3 mt-3 flex-wrap">
              {trailerKey ? (
                <button
                  onClick={() => setTrailerOpen(true)}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/20 text-primary hover:bg-primary/30 transition-colors text-sm font-medium"
                >
                  <Play className="w-4 h-4" />
                  Trailer
                </button>
              ) : (
                <span className="flex items-center gap-2 px-4 py-2 rounded-xl bg-muted text-muted-foreground text-sm font-medium cursor-not-allowed">
                  <Play className="w-4 h-4" />
                  Trailer não disponível
                </span>
              )}
              <MediaActions
                mediaType={(effectiveMediaType as 'movie' | 'series' | 'anime')}
                tmdbId={tmdbId}
                title={media.display_title}
                posterPath={media.poster_path}
                backdropPath={media.backdrop_path}
                year={media.year ?? null}
              />
            </div>
```

- [ ] **Step 3: Mount RecommendationsRow at the bottom of the page**

Find the closing `</div>` of the tab content (the one just before `<Dialog open={trailerOpen} ...`). Add this block right after the tab content `</div>` and before the `<Dialog>`:

```tsx
      <RecommendationsRow
        mediaType={(effectiveMediaType as 'movie' | 'series' | 'anime')}
        tmdbId={tmdbId}
      />
```

The exact placement: in the JSX, the structure ends with the Info tab block, then `<Dialog ...>`. The recommendations row should sit between them, so the user sees it regardless of the active tab.

- [ ] **Step 4: Verify the build type-checks**

Run:
```bash
cd frontend && npm run build
```

Expected: builds cleanly.

- [ ] **Step 5: Lint**

Run:
```bash
cd frontend && npm run lint
```

Expected: 0 errors, 0 warnings (`--max-warnings 0`).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Detail.tsx
git commit -m "feat: mount MediaActions and RecommendationsRow on detail page"
```

---

## Task 14: Watchlist page

**Files:**
- Create: `frontend/src/pages/Watchlist.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/pages/Watchlist.tsx`:

```typescript
import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bookmark, Loader2, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { listsAPI } from '@/services/api';
import type { ListItem } from '@/types';

const WatchlistCard: React.FC<{ item: ListItem }> = ({ item }) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const remove = useMutation({
    mutationFn: () => listsAPI.remove('watchlist', item.media_type, item.tmdb_id),
    onSuccess: () => {
      toast.success('Removido da watchlist');
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    },
    onError: (e) => {
      toast.error(e instanceof Error ? e.message : 'Falha ao remover');
    },
  });

  const detailPath = `/detail/${item.media_type === 'movie' ? 'movie' : 'tv'}/${item.tmdb_id}`;

  return (
    <div className="rounded-xl overflow-hidden border border-border/30 bg-background/50 hover:border-primary/30 transition-colors">
      <button
        type="button"
        onClick={() => navigate(detailPath)}
        className="block w-full text-left"
      >
        {item.poster_path ? (
          <img
            src={`https://image.tmdb.org/t/p/w300${item.poster_path}`}
            alt={item.title}
            className="w-full aspect-[2/3] object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full aspect-[2/3] bg-muted flex items-center justify-center text-muted-foreground text-sm">
            Sem imagem
          </div>
        )}
        <div className="p-3 space-y-1">
          <p className="text-sm font-medium text-foreground line-clamp-2">{item.title}</p>
          <p className="text-xs text-muted-foreground">{item.year || '—'}</p>
        </div>
      </button>
      <div className="px-3 pb-3">
        <button
          type="button"
          onClick={() => remove.mutate()}
          disabled={remove.isPending}
          className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent disabled:opacity-50 transition-colors"
        >
          {remove.isPending ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <Trash2 className="w-3 h-3" />
          )}
          Remover
        </button>
      </div>
    </div>
  );
};

const WatchlistPage: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => listsAPI.listWatchlist().then((r) => r.data),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Bookmark className="w-7 h-7 text-primary" />
        <h1 className="font-display text-3xl font-bold">Watchlist</h1>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="aspect-[2/3] rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : !data || data.length === 0 ? (
        <div className="text-center py-20 space-y-3">
          <Bookmark className="w-12 h-12 mx-auto text-muted-foreground" />
          <p className="text-muted-foreground">Sua watchlist está vazia.</p>
          <div className="flex items-center justify-center gap-3 text-sm">
            <Link to="/discover" className="text-primary hover:underline">
              Explorar títulos
            </Link>
            <span className="text-muted-foreground">•</span>
            <Link to="/search" className="text-primary hover:underline">
              Buscar
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {data.map((item) => (
            <WatchlistCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
};

export default WatchlistPage;
```

- [ ] **Step 2: Verify the build type-checks**

Run:
```bash
cd frontend && npm run build
```

Expected: builds cleanly.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Watchlist.tsx
git commit -m "feat: add Watchlist page"
```

---

## Task 15: Header nav + App.tsx route

**Files:**
- Modify: `frontend/src/components/Header.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add the Watchlist nav item in Header.tsx**

In `frontend/src/components/Header.tsx`, change the import line:

```typescript
import { Search, Download, Settings, Home, FileText, Play, Compass, Menu } from 'lucide-react';
```

to:

```typescript
import { Search, Download, Settings, Home, FileText, Play, Compass, Menu, Bookmark } from 'lucide-react';
```

Then in the `navItems` array, add a new entry between `'downloads'` and `'settings'`:

```typescript
const navItems = [
  { path: '/', icon: Home, label: 'Início' },
  { path: '/discover', icon: Compass, label: 'Explorar' },
  { path: '/search', icon: Search, label: 'Buscar' },
  { path: '/downloads', icon: Download, label: 'Downloads' },
  { path: '/watchlist', icon: Bookmark, label: 'Watchlist' },
  { path: '/settings', icon: Settings, label: 'Configurações' },
  { path: '/logs', icon: FileText, label: 'Logs' },
];
```

- [ ] **Step 2: Add the route in App.tsx**

In `frontend/src/App.tsx`, change the import line:

```typescript
import { Routes, Route } from 'react-router-dom';
import { Header } from './components/Header';
import HomePage from './pages/Home';
import SearchPage from './pages/Search';
import DetailPage from './pages/Detail';
import DownloadsPage from './pages/Downloads';
import SettingsPage from './pages/Settings';
import LogsPage from './pages/Logs';
import DiscoverPage from './pages/Discover';
```

to (add the WatchlistPage import):

```typescript
import { Routes, Route } from 'react-router-dom';
import { Header } from './components/Header';
import HomePage from './pages/Home';
import SearchPage from './pages/Search';
import DetailPage from './pages/Detail';
import DownloadsPage from './pages/Downloads';
import SettingsPage from './pages/Settings';
import LogsPage from './pages/Logs';
import DiscoverPage from './pages/Discover';
import WatchlistPage from './pages/Watchlist';
```

And inside `<Routes>`, add the new route after `/downloads`:

```tsx
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/discover" element={<DiscoverPage />} />
          <Route path="/detail/:mediaType/:id" element={<DetailPage />} />
          <Route path="/downloads" element={<DownloadsPage />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/logs" element={<LogsPage />} />
        </Routes>
```

- [ ] **Step 3: Verify build and lint**

Run:
```bash
cd frontend && npm run build && npm run lint
```

Expected: build succeeds; lint reports 0 errors, 0 warnings.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Header.tsx frontend/src/App.tsx
git commit -m "feat: add watchlist nav item and route"
```

---

## Task 16: Full end-to-end verification

**Files:** none. This task is a final gate.

- [ ] **Step 1: Run the full backend test suite**

Run:
```bash
cd backend && pytest tests/ -v
```

Expected: every test passes. Count the totals: should be the original set + 8 ListService + 4 TMDB methods + 11 lists router + 7 recommendation service + 5 recommendations router.

- [ ] **Step 2: Run the frontend build and lint**

Run:
```bash
cd frontend && npm run build && npm run lint
```

Expected: 0 TS errors, 0 lint errors.

- [ ] **Step 3: Smoke test (optional, requires Postgres + running TMDB service)**

If a dev environment is available:

```bash
# Terminal 1
cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8765

# Terminal 2
curl -s http://127.0.0.1:8765/api/lists/status/movie/1/
# expect: {"watched":false,"watchlist":false}

curl -s -X POST http://127.0.0.1:8765/api/lists/watchlist/movie/1/ \
  -H "Content-Type: application/json" \
  -d '{"title":"X","poster_path":null,"backdrop_path":null,"year":null}'
# expect: HTTP 204

curl -s http://127.0.0.1:8765/api/lists/watchlist/
# expect: JSON array with one item (id 1)
```

Skip this step if no dev DB is reachable.

- [ ] **Step 4: (Optional) Docker build smoke test**

If Docker is available, build the full stack:

```bash
docker-compose build
```

Expected: builds successfully. Do not bring it up; this is just to catch dependency issues.

- [ ] **Step 5: Final summary commit (only if fixes were needed)**

If any verification step required code changes, commit them now with a `chore:` or `fix:` message. If everything passed clean, there is nothing to commit — the work is done.

---

## Self-Review (already performed by the planner)

1. **Spec coverage:**
   - Data model (UserList + migration) → Tasks 1, 2
   - ListService CRUD + exclusion set → Task 3
   - TMDBService 4 new methods → Task 4
   - lists router (5 endpoints) → Task 5
   - RecommendationService (cache, dedupe, exclusion, parallel, limit) → Task 6
   - recommendations router → Task 7
   - main.py wiring → Tasks 5, 7
   - Frontend types → Task 9
   - Frontend API client → Task 10
   - MediaActions component → Task 11
   - RecommendationsRow component → Task 12
   - Detail.tsx integration → Task 13
   - Watchlist page → Task 14
   - Header nav + App.tsx route → Task 15
   - Caching strategy → Tasks 6, 12 (1h TTL on both sides)
   - Error handling → covered in routers and components (silent fail for recs, toast for toggle errors, 404 for missing delete, 400 for invalid media_type)
   - Testing strategy → unit tests on all new services and routers, build+lint for frontend

2. **Placeholder scan:** No "TBD", "TODO", "similar to", or "implement later" placeholders. Every code block is complete.

3. **Type consistency:**
   - `ListKind` defined in `backend/app/models/user_list.py` as `ListKind(str, enum.Enum)` with values `"watched"`/`"watchlist"` — matches the TypeScript `ListKind` and the `kind` query parameter in the router (Pydantic will validate it).
   - `UserMediaType` ('movie' | 'series' | 'anime') used in the frontend is enforced server-side by the `_check_media_type` helper, and matches `ContentType` values.
   - `Recommendation.media_type` is `'movie' | 'tv'` on the frontend, normalized from the backend's `media_type` parameter by the `media_type="movie" if media_type == "movie" else "tv"` mapping in the recommendations router.
   - The `tmdb_media_type` parameter to `RecommendationService.get_recommendations` is always `"movie"` or `"tv"` — this matches the internal `media_type` values used by the TMDBService methods.
   - The watchlist page's `detailPath` uses `tv` for `series` and `anime`, which matches the routing convention in the rest of the app (`/detail/tv/:id`).
   - The `ListItemPayload` fields (`title`, `poster_path`, `backdrop_path`, `year`) match the database columns and the frontend payload shape.
   - Cache key tuple `(media_type, tmdb_id)` — `media_type` here is the TMDB-side ("movie"/"tv") value, scoped per (user, item) which is correct since the cache is per process and we have a single user.
