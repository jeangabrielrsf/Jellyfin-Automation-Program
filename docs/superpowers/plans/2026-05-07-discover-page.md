# Discover Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/discover` page with Netflix-style horizontal rows of TMDB content cards, filterable by genre, media type, and sort order.

**Architecture:** Backend exposes `/api/discover/sections` (catalog), `/api/discover/sections/{id}` (per-section data with filters), and `/api/discover/genres` (genre list). An in-memory TTL cache (5min) avoids redundant TMDB calls. Frontend uses `useQuery` per row for progressive loading. Reuses existing `MediaCard` component.

**Tech Stack:** FastAPI, httpx, TanStack Query, shadcn/ui Select, React Router

---

## File Structure

```
Create:
  backend/app/models/discover.py
  backend/app/services/discover_service.py
  backend/app/routers/discover.py
  backend/tests/test_discover.py
  frontend/src/pages/Discover.tsx
  frontend/src/components/DiscoverFilterBar.tsx
  frontend/src/components/DiscoverRow.tsx

Modify:
  backend/app/main.py
  frontend/src/types/index.ts
  frontend/src/services/api.ts
  frontend/src/App.tsx
  frontend/src/components/Header.tsx
```

---

### Task 1: Backend — Pydantic models

**Files:**
- Create: `backend/app/models/discover.py`

- [ ] **Step 1: Write the models file**

```python
"""Discover Pydantic models."""
from pydantic import BaseModel
from app.models.tmdb import TMDBSearchResult


class DiscoverParams(BaseModel):
    genre_id: int | None = None
    media_type: str | None = None  # "movie" | "series" | "anime"
    sort_by: str = "popularity.desc"


class SectionInfo(BaseModel):
    id: str
    title: str
    media_type: str


class SectionCatalog(BaseModel):
    sections: list[SectionInfo]


class DiscoverSection(BaseModel):
    id: str
    title: str
    media_type: str
    results: list[TMDBSearchResult]
    total_results: int


class Genre(BaseModel):
    id: int
    name: str
```

- [ ] **Step 2: Verify import works**

Run: `cd backend && source venv/bin/activate && python -c "from app.models.discover import DiscoverParams, SectionInfo, SectionCatalog, DiscoverSection, Genre; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/discover.py
git commit -m "feat: add discover Pydantic models"
```

---

### Task 2: Backend — DiscoverService with caching

**Files:**
- Create: `backend/app/services/discover_service.py`

- [ ] **Step 1: Write the service**

```python
"""Discover service — TMDB section data with in-memory TTL cache."""
import time
from typing import Optional
from app.config import get_settings
from app.models.discover import (
    DiscoverParams,
    SectionInfo,
    SectionCatalog,
    DiscoverSection,
    Genre,
)
from app.models.tmdb import TMDBSearchResult
from app.logging_config import get_logger

logger = get_logger(__name__)

SECTION_DEFS: list[SectionInfo] = [
    SectionInfo(id="popular-movies", title="Filmes Populares", media_type="movie"),
    SectionInfo(id="popular-series", title="Séries Populares", media_type="series"),
    SectionInfo(id="popular-animes", title="Animes Populares", media_type="anime"),
    SectionInfo(id="trending", title="Tendências da Semana", media_type="mixed"),
    SectionInfo(id="top-rated-movies", title="Filmes Melhor Avaliados", media_type="movie"),
    SectionInfo(id="top-rated-series", title="Séries Melhor Avaliadas", media_type="series"),
    SectionInfo(id="now-playing", title="Nos Cinemas", media_type="movie"),
    SectionInfo(id="upcoming", title="Em Breve", media_type="movie"),
    SectionInfo(id="genre-action", title="Ação", media_type="mixed"),
    SectionInfo(id="genre-comedy", title="Comédia", media_type="mixed"),
    SectionInfo(id="genre-drama", title="Drama", media_type="mixed"),
    SectionInfo(id="genre-horror", title="Terror", media_type="mixed"),
    SectionInfo(id="genre-scifi", title="Ficção Científica", media_type="mixed"),
]

GENRE_SECTION_IDS = {
    "genre-action": 28,
    "genre-comedy": 35,
    "genre-drama": 18,
    "genre-horror": 27,
    "genre-scifi": 878,
}

ANIME_GENRE_ID = 16


class DiscoverService:
    BASE_URL = "https://api.themoviedb.org/3"
    SECTION_TTL = 300   # 5 minutes
    GENRE_TTL = 3600    # 1 hour

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.tmdb_api_key
        self._section_cache: dict[str, tuple[float, DiscoverSection]] = {}
        self._genre_cache: Optional[tuple[float, list[Genre]]] = None

    def _filters_active(self, params: DiscoverParams) -> bool:
        return params.genre_id is not None or params.media_type is not None

    def _cache_key(self, section_id: str, params: DiscoverParams) -> str:
        return f"{section_id}:{params.genre_id}:{params.media_type}:{params.sort_by}"

    def get_sections_catalog(self, params: DiscoverParams) -> SectionCatalog:
        sections = list(SECTION_DEFS)
        if self._filters_active(params):
            sections = [s for s in sections if s.id != "trending"]
        return SectionCatalog(sections=sections)

    async def get_section(self, section_id: str, params: DiscoverParams) -> DiscoverSection:
        import httpx

        # Return cached if still valid
        key = self._cache_key(section_id, params)
        cached = self._section_cache.get(key)
        if cached:
            ts, data = cached
            if time.time() - ts < self.SECTION_TTL:
                return data

        # Find section definition
        section_def = next((s for s in SECTION_DEFS if s.id == section_id), None)
        if not section_def:
            return DiscoverSection(id=section_id, title="", media_type="", results=[], total_results=0)

        # Trending + filters = empty
        if section_id == "trending" and self._filters_active(params):
            return DiscoverSection(
                id=section_id,
                title=section_def.title,
                media_type=section_def.media_type,
                results=[],
                total_results=0,
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                results = await self._fetch_tmdb(client, section_id, section_def, params)
        except Exception:
            logger.exception("Failed to fetch section data", section_id=section_id)
            results = []

        section = DiscoverSection(
            id=section_id,
            title=section_def.title,
            media_type=section_def.media_type,
            results=results,
            total_results=len(results),
        )
        self._section_cache[key] = (time.time(), section)
        return section

    async def _fetch_tmdb(self, client, section_id: str, section_def: SectionInfo, params: DiscoverParams) -> list[TMDBSearchResult]:
        common = {"api_key": self.api_key, "language": "pt-BR"}

        use_discover = self._filters_active(params) or section_id.startswith("genre-") or section_def.media_type == "anime"

        if use_discover:
            media = "tv" if section_def.media_type in ("series", "anime", "mixed") else "movie"
            if section_def.media_type == "movie":
                media = "movie"
            elif section_def.media_type in ("series", "anime"):
                media = "tv"
            else:
                media = "tv" if params.media_type == "series" else "movie"

            url = f"{self.BASE_URL}/discover/{media}"
            query: dict = {**common, "sort_by": params.sort_by}

            # Genre
            if section_id.startswith("genre-"):
                genre_id = GENRE_SECTION_IDS.get(section_id)
                if genre_id:
                    query["with_genres"] = str(genre_id)
            elif params.genre_id:
                query["with_genres"] = str(params.genre_id)

            # Anime
            if section_def.media_type == "anime":
                query["with_genres"] = str(ANIME_GENRE_ID)
                query["with_origin_country"] = "JP"
                if params.genre_id and params.genre_id != ANIME_GENRE_ID:
                    query["with_genres"] = f"{ANIME_GENRE_ID},{params.genre_id}"

            if params.media_type == "movie":
                query["with_genres"] = query.get("with_genres", "")
                # already constrained by media=movie
            elif params.media_type == "series":
                query["with_genres"] = query.get("with_genres", "")
                # already constrained by media=tv
        else:
            # Native endpoints (no filters)
            path: str
            param_extra: dict = {}
            if section_id == "popular-movies":
                path = "/movie/popular"
            elif section_id == "popular-series":
                path = "/tv/popular"
            elif section_id == "trending":
                path = "/trending/all/week"
            elif section_id == "top-rated-movies":
                path = "/movie/top_rated"
            elif section_id == "top-rated-series":
                path = "/tv/top_rated"
            elif section_id == "now-playing":
                path = "/movie/now_playing"
            elif section_id == "upcoming":
                path = "/movie/upcoming"
            else:
                path = "/movie/popular"

            url = f"{self.BASE_URL}{path}"
            query = {**common, **param_extra}

        response = await client.get(url, params=query)
        response.raise_for_status()
        data = response.json()

        raw = data.get("results", [])[:20]
        results: list[TMDBSearchResult] = []
        for item in raw:
            mt = item.get("media_type", "")
            if not mt:
                mt = "movie" if "title" in item else "tv"
            results.append(TMDBSearchResult(
                id=item["id"],
                title=item.get("title"),
                name=item.get("name"),
                overview=item.get("overview", ""),
                poster_path=item.get("poster_path"),
                backdrop_path=item.get("backdrop_path"),
                release_date=item.get("release_date"),
                first_air_date=item.get("first_air_date"),
                vote_average=item.get("vote_average", 0.0),
                media_type=mt,
                genre_ids=item.get("genre_ids", []),
            ))
        return results

    async def get_genres(self) -> list[Genre]:
        import httpx

        # Check cache
        if self._genre_cache:
            ts, data = self._genre_cache
            if time.time() - ts < self.GENRE_TTL:
                return data

        common = {"api_key": self.api_key, "language": "pt-BR"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                movie_resp = await client.get(f"{self.BASE_URL}/genre/movie/list", params=common)
                movie_resp.raise_for_status()
                movie_genres = movie_resp.json().get("genres", [])

                tv_resp = await client.get(f"{self.BASE_URL}/genre/tv/list", params=common)
                tv_resp.raise_for_status()
                tv_genres = tv_resp.json().get("genres", [])

            seen: dict[int, str] = {}
            for g in movie_genres + tv_genres:
                gid = g["id"]
                if gid not in seen:
                    seen[gid] = g["name"]

            genres = [Genre(id=gid, name=name) for gid, name in sorted(seen.items())]
            self._genre_cache = (time.time(), genres)
            return genres
        except Exception:
            logger.exception("Failed to fetch genres")
            return []
```

- [ ] **Step 2: Verify import works**

Run: `cd backend && source venv/bin/activate && python -c "from app.services.discover_service import DiscoverService, SECTION_DEFS; print(len(SECTION_DEFS), 'sections')"`
Expected: `13 sections`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/discover_service.py
git commit -m "feat: add DiscoverService with in-memory TTL cache"
```

---

### Task 3: Backend — Discover router

**Files:**
- Create: `backend/app/routers/discover.py`

- [ ] **Step 1: Write the router**

```python
"""Discover router."""
from fastapi import APIRouter, HTTPException, Query
from app.services.discover_service import DiscoverService
from app.models.discover import (
    DiscoverParams,
    SectionCatalog,
    DiscoverSection,
    Genre,
)

router = APIRouter(tags=["discover"])


@router.get("/sections", response_model=SectionCatalog)
async def get_discover_sections(
    genre_id: int | None = Query(None),
    media_type: str | None = Query(None),
    sort_by: str = Query("popularity.desc"),
):
    """Return the section catalog considering active filters."""
    params = DiscoverParams(genre_id=genre_id, media_type=media_type, sort_by=sort_by)
    service = DiscoverService()
    return service.get_sections_catalog(params)


@router.get("/sections/{section_id}", response_model=DiscoverSection)
async def get_discover_section(
    section_id: str,
    genre_id: int | None = Query(None),
    media_type: str | None = Query(None),
    sort_by: str = Query("popularity.desc"),
):
    """Return data for one discover section with filters applied."""
    params = DiscoverParams(genre_id=genre_id, media_type=media_type, sort_by=sort_by)
    service = DiscoverService()
    try:
        return await service.get_section(section_id, params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch section: {str(e)}")


@router.get("/genres", response_model=list[Genre])
async def get_discover_genres():
    """Return merged movie+TV genre list from TMDB."""
    service = DiscoverService()
    try:
        return await service.get_genres()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch genres: {str(e)}")
```

- [ ] **Step 2: Verify import works**

Run: `cd backend && source venv/bin/activate && python -c "from app.routers.discover import router; print(len(router.routes), 'routes')"`
Expected: `3 routes`

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/discover.py
git commit -m "feat: add discover router with sections, section data, and genres endpoints"
```

---

### Task 4: Backend — Register router in main.py

**Files:**
- Modify: `backend/app/main.py:13,98`

- [ ] **Step 1: Add import and router registration**

Two edits in `backend/app/main.py`:

**Edit 1 — add import (line 13):**
Old:
```python
from app.routers import search, downloads, settings, logs, filesystem
```
New:
```python
from app.routers import search, downloads, settings, logs, filesystem, discover
```

**Edit 2 — add router (after line 98):**
Old:
```python
app.include_router(filesystem.router)
```
New:
```python
app.include_router(filesystem.router)
app.include_router(discover.router, prefix="/api/discover")
```

- [ ] **Step 2: Verify app starts**

Run: `cd backend && source venv/bin/activate && timeout 3 uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 || true`
Expected: no import errors; server starts briefly then times out (expected)

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: register discover router in main app"
```

---

### Task 5: Backend — Tests

**Files:**
- Create: `backend/tests/test_discover.py`

- [ ] **Step 1: Write the tests**

```python
"""Tests for discover service and router."""
import time
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.discover_service import DiscoverService, SECTION_DEFS
from app.models.discover import DiscoverParams, SectionCatalog, SectionInfo, DiscoverSection


@pytest.fixture
def discover_service():
    with patch("app.services.discover_service.get_settings") as mock_settings:
        mock_settings.return_value.tmdb_api_key = "test-key"
        yield DiscoverService()


@pytest.fixture
def mock_httpx():
    with patch("app.services.discover_service.httpx.AsyncClient") as mock_client:
        yield mock_client


# --- Catalog tests ---

def test_get_catalog_returns_all_13_sections_no_filter(discover_service):
    params = DiscoverParams()
    catalog = discover_service.get_sections_catalog(params)
    assert len(catalog.sections) == 13
    ids = [s.id for s in catalog.sections]
    assert "trending" in ids
    assert "popular-movies" in ids
    assert "genre-scifi" in ids


def test_get_catalog_hides_trending_when_genre_filtered(discover_service):
    params = DiscoverParams(genre_id=28)
    catalog = discover_service.get_sections_catalog(params)
    ids = [s.id for s in catalog.sections]
    assert "trending" not in ids
    assert len(catalog.sections) == 12


def test_get_catalog_hides_trending_when_media_type_filtered(discover_service):
    params = DiscoverParams(media_type="movie")
    catalog = discover_service.get_sections_catalog(params)
    ids = [s.id for s in catalog.sections]
    assert "trending" not in ids
    assert len(catalog.sections) == 12


# --- Section data tests ---

@pytest.mark.asyncio
async def test_get_section_popular_movies_no_filter(discover_service):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "page": 1,
        "results": [
            {
                "id": 1, "title": "Test Movie", "overview": "desc",
                "poster_path": "/p.jpg", "backdrop_path": "/b.jpg",
                "release_date": "2024-01-01", "vote_average": 7.5,
                "media_type": "movie", "genre_ids": [28]
            }
        ],
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.discover_service.httpx.AsyncClient", return_value=mock_client):
        result = await discover_service.get_section("popular-movies", DiscoverParams())
        assert result.id == "popular-movies"
        assert result.title == "Filmes Populares"
        assert len(result.results) == 1
        assert result.results[0].display_title == "Test Movie"


@pytest.mark.asyncio
async def test_get_section_popular_movies_with_genre_filter(discover_service):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "page": 1,
        "results": [
            {
                "id": 2, "title": "Action Movie", "overview": "desc",
                "poster_path": "/p.jpg", "backdrop_path": "/b.jpg",
                "release_date": "2024-01-01", "vote_average": 8.0,
                "media_type": "movie", "genre_ids": [28]
            }
        ],
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.discover_service.httpx.AsyncClient", return_value=mock_client):
        result = await discover_service.get_section("popular-movies", DiscoverParams(genre_id=28))
        assert len(result.results) == 1

        # Verify it called discover, not popular
        call_args = mock_client.get.call_args
        url = call_args[0][0]
        assert "/discover/movie" in url


@pytest.mark.asyncio
async def test_get_section_trending_empty_when_filtered(discover_service):
    result = await discover_service.get_section("trending", DiscoverParams(genre_id=28))
    assert result.results == []
    assert result.total_results == 0


@pytest.mark.asyncio
async def test_get_section_trending_has_data_when_no_filter(discover_service):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "page": 1,
        "results": [
            {
                "id": 3, "title": "Trending Movie", "overview": "desc",
                "poster_path": "/p.jpg", "backdrop_path": "/b.jpg",
                "release_date": "2024-01-01", "vote_average": 6.0,
                "media_type": "movie", "genre_ids": []
            }
        ],
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.discover_service.httpx.AsyncClient", return_value=mock_client):
        result = await discover_service.get_section("trending", DiscoverParams())
        assert len(result.results) == 1


@pytest.mark.asyncio
async def test_get_section_anime_always_uses_discover(discover_service):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "page": 1,
        "results": [
            {
                "id": 4, "name": "Attack on Titan", "overview": "desc",
                "poster_path": "/p.jpg", "backdrop_path": "/b.jpg",
                "first_air_date": "2013-04-06", "vote_average": 8.5,
                "media_type": "tv", "genre_ids": [16, 10759]
            }
        ],
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.discover_service.httpx.AsyncClient", return_value=mock_client):
        result = await discover_service.get_section("popular-animes", DiscoverParams())
        assert result.title == "Animes Populares"
        assert len(result.results) == 1
        call_args = mock_client.get.call_args
        url = call_args[0][0]
        assert "/discover/tv" in url


# --- Genre tests ---

@pytest.mark.asyncio
async def test_get_genres_merges_movie_and_tv_lists(discover_service):
    mock_movie = MagicMock()
    mock_movie.json.return_value = {"genres": [{"id": 28, "name": "Ação"}]}
    mock_movie.raise_for_status = MagicMock()

    mock_tv = MagicMock()
    mock_tv.json.return_value = {"genres": [{"id": 28, "name": "Ação"}, {"id": 16, "name": "Animação"}]}
    mock_tv.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=[mock_movie, mock_tv])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.discover_service.httpx.AsyncClient", return_value=mock_client):
        genres = await discover_service.get_genres()
        assert len(genres) == 2
        names = {g.name for g in genres}
        assert names == {"Ação", "Animação"}


@pytest.mark.asyncio
async def test_genres_endpoint_cached(discover_service):
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=MagicMock())
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.discover_service.httpx.AsyncClient", return_value=mock_client):
        # Set up the mock to return genres
        mock_movie = MagicMock()
        mock_movie.json.return_value = {"genres": [{"id": 28, "name": "Ação"}]}
        mock_movie.raise_for_status = MagicMock()
        mock_tv = MagicMock()
        mock_tv.json.return_value = {"genres": []}
        mock_tv.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(side_effect=[mock_movie, mock_tv])

        await discover_service.get_genres()
        # Second call should use cache, no additional httpx calls
        mock_client.get.reset_mock()
        genres = await discover_service.get_genres()
        mock_client.get.assert_not_called()
        assert len(genres) == 1


# --- Cache tests ---

@pytest.mark.asyncio
async def test_section_cache_hit_avoids_tmdb_call(discover_service):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "page": 1,
        "results": [
            {
                "id": 1, "title": "Cached Movie", "overview": "desc",
                "poster_path": "/p.jpg", "backdrop_path": "/b.jpg",
                "release_date": "2024-01-01", "vote_average": 7.0,
                "media_type": "movie", "genre_ids": []
            }
        ],
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.discover_service.httpx.AsyncClient", return_value=mock_client):
        # First call — hits TMDB
        result1 = await discover_service.get_section("popular-movies", DiscoverParams())
        assert len(result1.results) == 1
        mock_client.get.assert_called_once()

        # Second call — should hit cache
        mock_client.get.reset_mock()
        result2 = await discover_service.get_section("popular-movies", DiscoverParams())
        mock_client.get.assert_not_called()
        assert result2.results[0].display_title == "Cached Movie"


@pytest.mark.asyncio
async def test_section_cache_expired_refetches(discover_service):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "page": 1,
        "results": [
            {
                "id": 2, "title": "Fresh Movie", "overview": "desc",
                "poster_path": "/p.jpg", "backdrop_path": "/b.jpg",
                "release_date": "2024-01-01", "vote_average": 7.0,
                "media_type": "movie", "genre_ids": []
            }
        ],
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.discover_service.httpx.AsyncClient", return_value=mock_client):
        with patch("app.services.discover_service.time.time", side_effect=[1000, 1001, 2000]):
            await discover_service.get_section("popular-movies", DiscoverParams())
            mock_client.get.assert_called_once()

            mock_client.get.reset_mock()
            # time is now 2000 > 1000 + 300 TTL → cache expired
            await discover_service.get_section("popular-movies", DiscoverParams())
            mock_client.get.assert_called_once()


# --- Router integration tests ---

class TestDiscoverRouter:
    def test_get_sections_catalog(self, client):
        response = client.get("/api/discover/sections")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sections"]) == 13
        assert data["sections"][0]["id"] == "popular-movies"

    def test_get_sections_catalog_with_filter_hides_trending(self, client):
        response = client.get("/api/discover/sections?genre_id=28")
        assert response.status_code == 200
        ids = [s["id"] for s in response.json()["sections"]]
        assert "trending" not in ids
        assert len(ids) == 12

    def test_get_section_data(self, client):
        mock_resp = {
            "page": 1,
            "results": [
                {
                    "id": 1, "title": "Test Movie", "overview": "desc",
                    "poster_path": "/p.jpg", "backdrop_path": "/b.jpg",
                    "release_date": "2024-01-01", "vote_average": 7.0,
                    "media_type": "movie", "genre_ids": []
                }
            ],
        }
        with patch("app.services.discover_service.DiscoverService.get_section") as mock_get:
            mock_get.return_value = DiscoverSection(
                id="popular-movies", title="Filmes Populares",
                media_type="movie", results=mock_resp["results"], total_results=1
            )
            response = client.get("/api/discover/sections/popular-movies")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "popular-movies"
            assert len(data["results"]) == 1

    def test_get_genres(self, client):
        from app.models.discover import Genre
        with patch("app.services.discover_service.DiscoverService.get_genres") as mock_get:
            mock_get.return_value = [Genre(id=28, name="Ação"), Genre(id=35, name="Comédia")]
            response = client.get("/api/discover/genres")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "Ação"
```

- [ ] **Step 2: Run the tests**

Run: `cd backend && source venv/bin/activate && pytest tests/test_discover.py -v`
Expected: all tests PASS (should be around 14 tests)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_discover.py
git commit -m "test: add discover service and router tests"
```

---

### Task 6: Frontend — Add TypeScript types

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Append types at end of file**

Add after the `AppSettings` interface (line 87):

```ts
export interface DiscoverParams {
  genre_id?: number | null
  media_type?: string | null
  sort_by?: string
}

export interface SectionInfo {
  id: string
  title: string
  media_type: string
}

export interface DiscoverSection extends SectionInfo {
  results: TMDBSearchResult[]
  total_results: number
}

export interface Genre {
  id: number
  name: string
}
```

- [ ] **Step 2: Verify no type errors**

Run: `cd frontend && npx tsc --noEmit 2>&1`
Expected: no new errors related to types

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add discover-related TypeScript types"
```

---

### Task 7: Frontend — Add API client methods

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Add discoverAPI after logsAPI**

Add after the `logsAPI` block (line 100):

```ts
export const discoverAPI = {
  getSections: (params?: {
    genre_id?: number | null;
    media_type?: string | null;
    sort_by?: string;
  }) => api.get('/discover/sections/', { params }),

  getSection: (id: string, params?: {
    genre_id?: number | null;
    media_type?: string | null;
    sort_by?: string;
  }) => api.get(`/discover/sections/${id}/`, { params }),

  getGenres: () => api.get('/discover/genres/'),
};
```

- [ ] **Step 2: Verify no type errors**

Run: `cd frontend && npx tsc --noEmit 2>&1`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat: add discoverAPI client methods"
```

---

### Task 8: Frontend — DiscoverFilterBar component

**Files:**
- Create: `frontend/src/components/DiscoverFilterBar.tsx`

- [ ] **Step 1: Write the component**

```tsx
import React from 'react';
import { Select, SelectItem } from './ui/select';
import { Genre } from '../types';

const CONTENT_TYPES = [
  { value: '', label: 'Todos' },
  { value: 'movie', label: 'Filme' },
  { value: 'series', label: 'Série' },
  { value: 'anime', label: 'Anime' },
];

const SORT_OPTIONS = [
  { value: 'popularity.desc', label: 'Popularidade' },
  { value: 'vote_average.desc', label: 'Nota' },
  { value: 'primary_release_date.desc', label: 'Lançamento' },
];

interface DiscoverFilterBarProps {
  genreId: number | null;
  mediaType: string | null;
  sortBy: string;
  genres: Genre[];
  onGenreChange: (genreId: number | null) => void;
  onMediaTypeChange: (mediaType: string | null) => void;
  onSortChange: (sortBy: string) => void;
}

export const DiscoverFilterBar: React.FC<DiscoverFilterBarProps> = ({
  genreId,
  mediaType,
  sortBy,
  genres,
  onGenreChange,
  onMediaTypeChange,
  onSortChange,
}) => {
  return (
    <div className="flex flex-wrap gap-3 mb-8">
      <Select
        value={genreId ?? ''}
        onChange={(e) => {
          const val = e.target.value;
          onGenreChange(val ? Number(val) : null);
        }}
        className="w-48"
      >
        <SelectItem value="">Todos os gêneros</SelectItem>
        {genres.map((g) => (
          <SelectItem key={g.id} value={String(g.id)}>
            {g.name}
          </SelectItem>
        ))}
      </Select>

      <Select
        value={mediaType ?? ''}
        onChange={(e) => {
          const val = e.target.value;
          onMediaTypeChange(val || null);
        }}
        className="w-36"
      >
        {CONTENT_TYPES.map((ct) => (
          <SelectItem key={ct.value} value={ct.value}>
            {ct.label}
          </SelectItem>
        ))}
      </Select>

      <Select
        value={sortBy}
        onChange={(e) => onSortChange(e.target.value)}
        className="w-44"
      >
        {SORT_OPTIONS.map((so) => (
          <SelectItem key={so.value} value={so.value}>
            {so.label}
          </SelectItem>
        ))}
      </Select>
    </div>
  );
};
```

- [ ] **Step 2: Verify no type errors**

Run: `cd frontend && npx tsc --noEmit 2>&1`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/DiscoverFilterBar.tsx
git commit -m "feat: add DiscoverFilterBar component"
```

---

### Task 9: Frontend — DiscoverRow component

**Files:**
- Create: `frontend/src/components/DiscoverRow.tsx`

- [ ] **Step 1: Write the component**

```tsx
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { discoverAPI } from '../services/api';
import { MediaCard } from './MediaCard';
import { SectionInfo, DiscoverParams, TMDBSearchResult } from '../types';

interface DiscoverRowProps {
  section: SectionInfo;
  filters: DiscoverParams;
}

export const DiscoverRow: React.FC<DiscoverRowProps> = ({ section, filters }) => {
  const navigate = useNavigate();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['discover', 'section', section.id, filters],
    queryFn: async () => {
      const res = await discoverAPI.getSection(section.id, filters);
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <div className="mb-8">
        <h2 className="font-display text-xl font-bold text-foreground mb-3">
          {section.title}
        </h2>
        <div className="flex gap-4 overflow-x-auto pb-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="flex-shrink-0 w-40 aspect-[2/3] rounded-xl bg-muted animate-shimmer"
            />
          ))}
        </div>
      </div>
    );
  }

  if (isError || !data || data.results.length === 0) {
    return null;
  }

  const handleClick = (media: TMDBSearchResult) => {
    navigate(`/detail/${media.media_type}/${media.id}`);
  };

  return (
    <div className="mb-8">
      <h2 className="font-display text-xl font-bold text-foreground mb-3">
        {section.title}
      </h2>
      <div className="flex gap-4 overflow-x-auto pb-2 scroll-smooth">
        {data.results.map((media: TMDBSearchResult) => (
          <div key={media.id} className="flex-shrink-0 w-40">
            <MediaCard media={media} onClick={handleClick} />
          </div>
        ))}
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Verify no type errors**

Run: `cd frontend && npx tsc --noEmit 2>&1`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/DiscoverRow.tsx
git commit -m "feat: add DiscoverRow component with progressive loading"
```

---

### Task 10: Frontend — Discover page

**Files:**
- Create: `frontend/src/pages/Discover.tsx`

- [ ] **Step 1: Write the page**

```tsx
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Compass } from 'lucide-react';
import { discoverAPI } from '../services/api';
import { DiscoverFilterBar } from '../components/DiscoverFilterBar';
import { DiscoverRow } from '../components/DiscoverRow';
import { DiscoverParams } from '../types';

const DiscoverPage: React.FC = () => {
  const [genreId, setGenreId] = useState<number | null>(null);
  const [mediaType, setMediaType] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState('popularity.desc');

  const filters: DiscoverParams = { genre_id: genreId, media_type: mediaType, sort_by: sortBy };

  const { data: catalog, isLoading: catalogLoading, isError: catalogError } = useQuery({
    queryKey: ['discover', 'sections'],
    queryFn: async () => {
      const res = await discoverAPI.getSections(filters);
      return res.data;
    },
  });

  const { data: genres } = useQuery({
    queryKey: ['discover', 'genres'],
    queryFn: async () => {
      const res = await discoverAPI.getGenres();
      return res.data;
    },
    staleTime: 60 * 60 * 1000,
  });

  return (
    <div className="space-y-2 animate-fade-in">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <Compass className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="font-display text-3xl font-bold text-foreground">
            Explorar
          </h1>
          <p className="text-muted-foreground text-sm">
            Descubra novos filmes, séries e animes
          </p>
        </div>
      </div>

      <DiscoverFilterBar
        genreId={genreId}
        mediaType={mediaType}
        sortBy={sortBy}
        genres={genres ?? []}
        onGenreChange={setGenreId}
        onMediaTypeChange={setMediaType}
        onSortChange={setSortBy}
      />

      {catalogLoading && (
        <div className="space-y-8">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i}>
              <div className="h-7 w-48 bg-muted rounded-md mb-3 animate-shimmer" />
              <div className="flex gap-4 overflow-x-auto">
                {Array.from({ length: 6 }).map((_, j) => (
                  <div
                    key={j}
                    className="flex-shrink-0 w-40 aspect-[2/3] rounded-xl bg-muted animate-shimmer"
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {catalogError && (
        <div className="text-center py-16">
          <p className="text-muted-foreground text-lg mb-4">
            Erro ao carregar seções
          </p>
          <button
            onClick={() => window.location.reload()}
            className="text-primary text-sm font-medium hover:underline"
          >
            Tentar novamente
          </button>
        </div>
      )}

      {!catalogLoading && !catalogError && catalog && catalog.sections.length === 0 && (
        <div className="text-center py-16">
          <p className="text-muted-foreground">
            Nenhuma seção disponível com esses filtros
          </p>
        </div>
      )}

      {!catalogLoading && !catalogError && catalog && catalog.sections.map((section) => (
        <DiscoverRow key={section.id} section={section} filters={filters} />
      ))}
    </div>
  );
};

export default DiscoverPage;
```

- [ ] **Step 2: Verify no type errors**

Run: `cd frontend && npx tsc --noEmit 2>&1`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Discover.tsx
git commit -m "feat: add Discover page"
```

---

### Task 11: Frontend — Add route and header link

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Header.tsx`

- [ ] **Step 1: Add import and route in App.tsx**

Two edits:

**Edit 1 — add import (after line 8):**
Old:
```tsx
import LogsPage from './pages/Logs';
```
New:
```tsx
import LogsPage from './pages/Logs';
import DiscoverPage from './pages/Discover';
```

**Edit 2 — add route (after line 20):**
Old:
```tsx
          <Route path="/downloads" element={<DownloadsPage />} />
```
New:
```tsx
          <Route path="/discover" element={<DiscoverPage />} />
          <Route path="/downloads" element={<DownloadsPage />} />
```

- [ ] **Step 2: Add nav item in Header.tsx**

Two edits:

**Edit 1 — add Compass icon import (line 4):**
Old:
```tsx
import { Search, Download, Settings, Home, FileText, Play } from 'lucide-react';
```
New:
```tsx
import { Search, Download, Settings, Home, FileText, Play, Compass } from 'lucide-react';
```

**Edit 2 — add to navItems (after line 8):**
Old:
```tsx
  { path: '/search', icon: Search, label: 'Buscar' },
```
New:
```tsx
  { path: '/discover', icon: Compass, label: 'Explorar' },
  { path: '/search', icon: Search, label: 'Buscar' },
```

- [ ] **Step 3: Build to verify**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Header.tsx
git commit -m "feat: add /discover route and header navigation link"
```

---

### Task 12: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Run backend tests**

Run: `cd backend && source venv/bin/activate && pytest tests/ -v`
Expected: all tests pass, including new discover tests

- [ ] **Step 2: Build frontend**

Run: `cd frontend && npm run build`
Expected: build succeeds, no tsc or vite errors

- [ ] **Step 3: Start backend and smoke test**

Run: `cd backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 &`

Then test with curl:
```bash
curl -s http://localhost:8000/api/discover/sections | python -m json.tool | head -20
curl -s "http://localhost:8000/api/discover/sections/popular-movies" | python -m json.tool | head -20
curl -s http://localhost:8000/api/discover/genres | python -m json.tool | head -20
```

Expected: all return 200 with valid JSON

Kill background server: `kill %1`
