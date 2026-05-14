# Docker Services + Dynamic Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dockerize qBittorrent and Jackett services, and make all API keys/URLs configurable via the Settings UI with DB > .env > error priority chain.

**Architecture:** Add qBittorrent and Jackett containers to docker-compose. Create a unified `get_config()` function that reads from DB first, falls back to `.env`, and raises `ConfigurationError` if neither has the value. Refactor all services to accept `db` and use `get_config()`. Add "Serviços Externos" section to Settings page.

**Tech Stack:** FastAPI, SQLAlchemy, React, Docker Compose, linuxserver images

---

## File Map

### New Files
- `backend/app/exceptions.py` — `ConfigurationError` exception class
- `backend/app/services/config_service.py` — `get_config()` function
- `backend/tests/test_config_service.py` — Tests for config service

### Modified Files
- `docker-compose.yml` — Add qBittorrent, Jackett services; adjust backend network
- `.env.example` — Update defaults for Docker network names
- `backend/app/services/tmdb_service.py` — Accept `db`, use `get_config()`
- `backend/app/services/discover_service.py` — Accept `db`, use `get_config()`
- `backend/app/services/qbittorrent_service.py` — Accept `db`, use `get_config()`
- `backend/app/scrapers/jackett_scraper.py` — Accept `db`, use `get_config()`
- `backend/app/services/jellyfin_service.py` — Accept `db`, use `get_config()`
- `backend/app/services/organizer_service.py` — Replace `get_media_paths()` with `get_config()`
- `backend/app/services/path_resolver.py` — Replace `get_media_paths()` with `get_config()`
- `backend/app/services/settings_service.py` — Remove (functionality moved to config_service.py)
- `backend/app/services/download_worker.py` — Pass `db` to services
- `backend/app/routers/search.py` — Pass `db` to services; use `get_config()` for OMDB
- `backend/app/routers/downloads.py` — Pass `db` to PathResolver
- `backend/app/routers/discover.py` — Pass `db` to DiscoverService
- `backend/app/main.py` — Add seed initial config in lifespan
- `backend/app/routers/settings.py` — Remove dependency on `get_media_paths()`
- `frontend/src/pages/Settings.tsx` — Add "Serviços Externos" section
- `frontend/src/services/api.ts` — Add `getExternalServices()` to settingsAPI

---

### Task 1: Create ConfigurationError and ConfigService

**Files:**
- Create: `backend/app/exceptions.py`
- Create: `backend/app/services/config_service.py`
- Create: `backend/tests/test_config_service.py`

- [ ] **Step 1: Create the ConfigurationError exception**

Create `backend/app/exceptions.py`:

```python
"""Custom exceptions."""


class ConfigurationError(Exception):
    """Raised when a required configuration value is missing from both DB and .env."""

    def __init__(self, key: str, message: str | None = None):
        self.key = key
        self.message = message or f"Missing required config: '{key}'. Set it via UI or .env"
        super().__init__(self.message)
```

- [ ] **Step 2: Create the ConfigService**

Create `backend/app/services/config_service.py`:

```python
"""Unified configuration service — DB > .env > error priority chain."""
from typing import Any, Optional
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.settings import Setting
from app.exceptions import ConfigurationError


def get_config(key: str, db: Optional[Session] = None, required: bool = False) -> str:
    """Get configuration value with priority: DB > .env > error.

    Args:
        key: Configuration key (e.g., 'tmdb_api_key', 'jackett_url').
        db: Optional SQLAlchemy session for DB lookup.
        required: If True, raises ConfigurationError when value not found.

    Returns:
        Configuration value as string, or empty string if not required and not found.
    """
    # 1. Try DB first
    if db is not None:
        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting is not None and setting.value is not None:
            val: Any = setting.value
            # Setting.value is JSON — can be str, int, bool, etc.
            return str(val) if not isinstance(val, str) else val

    # 2. Fallback to .env
    env_settings = get_settings()
    env_value = getattr(env_settings, key, None)
    if env_value:
        return str(env_value)

    # 3. Error if required
    if required:
        raise ConfigurationError(key)

    return ""
```

- [ ] **Step 3: Create tests for ConfigService**

Create `backend/tests/test_config_service.py`:

```python
"""Tests for the unified config service."""
import os
import pytest
from app.services.config_service import get_config
from app.exceptions import ConfigurationError
from app.models.settings import Setting


class TestGetConfig:
    """Tests for get_config() priority chain."""

    def test_returns_db_value_when_present(self, db_session):
        """DB value takes priority over .env."""
        db_session.add(Setting(key="tmdb_api_key", value="db-value"))
        db_session.commit()

        result = get_config("tmdb_api_key", db=db_session)
        assert result == "db-value"

    def test_falls_back_to_env_when_db_empty(self, db_session):
        """When key not in DB, falls back to .env."""
        os.environ["TMDB_API_KEY"] = "env-value"
        try:
            result = get_config("tmdb_api_key", db=db_session)
            assert result == "env-value"
        finally:
            del os.environ["TMDB_API_KEY"]

    def test_falls_back_to_env_when_db_has_none_value(self, db_session):
        """When DB has key but value is None, falls back to .env."""
        db_session.add(Setting(key="tmdb_api_key", value=None))
        db_session.commit()

        os.environ["TMDB_API_KEY"] = "env-value"
        try:
            result = get_config("tmdb_api_key", db=db_session)
            assert result == "env-value"
        finally:
            del os.environ["TMDB_API_KEY"]

    def test_raises_error_when_required_and_not_found(self, db_session):
        """Raises ConfigurationError when required=True and value missing."""
        with pytest.raises(ConfigurationError) as exc_info:
            get_config("tmdb_api_key", db=db_session, required=True)
        assert "tmdb_api_key" in str(exc_info.value)

    def test_returns_empty_string_when_not_required(self, db_session):
        """Returns empty string when not required and value missing."""
        result = get_config("tmdb_api_key", db=db_session, required=False)
        assert result == ""

    def test_returns_int_as_string_from_db(self, db_session):
        """Integer values from DB are returned as strings."""
        db_session.add(Setting(key="jackett_timeout", value=120))
        db_session.commit()

        result = get_config("jackett_timeout", db=db_session)
        assert result == "120"
        assert isinstance(result, str)

    def test_db_priority_over_env(self, db_session):
        """DB value is returned even when .env also has a value."""
        db_session.add(Setting(key="jackett_url", value="http://db-jackett:9117"))
        db_session.commit()

        os.environ["JACKETT_URL"] = "http://env-jackett:9117"
        try:
            result = get_config("jackett_url", db=db_session)
            assert result == "http://db-jackett:9117"
        finally:
            del os.environ["JACKETT_URL"]

    def test_without_db_falls_back_to_env(self):
        """When db=None, skips DB lookup and goes straight to .env."""
        os.environ["OMDB_API_KEY"] = "test-key"
        try:
            result = get_config("omdb_api_key", db=None)
            assert result == "test-key"
        finally:
            del os.environ["OMDB_API_KEY"]

    def test_without_db_raises_when_required_and_missing(self):
        """When db=None and required=True, raises if .env has no value."""
        with pytest.raises(ConfigurationError):
            get_config("tmdb_api_key", db=None, required=True)
```

- [ ] **Step 4: Run tests to verify**

```bash
cd backend && pytest tests/test_config_service.py -v
```

Expected: All 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/exceptions.py backend/app/services/config_service.py backend/tests/test_config_service.py
git commit -m "feat: add ConfigurationError and unified get_config() service"
```

---

### Task 2: Add Exception Handler to FastAPI

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add ConfigurationError exception handler to main.py**

Read the current `backend/app/main.py`. After the existing imports and before the `@app.websocket("/ws")` route, add:

```python
from app.exceptions import ConfigurationError


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(request, exc: ConfigurationError):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={
            "error": "configuration_error",
            "key": exc.key,
            "message": exc.message,
        },
    )
```

Add the import at the top of the file:

```python
from app.exceptions import ConfigurationError
```

- [ ] **Step 2: Run existing tests to verify no regression**

```bash
cd backend && pytest tests/ -v
```

Expected: All existing tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: add ConfigurationError exception handler to FastAPI"
```

---

### Task 3: Refactor TMDBService

**Files:**
- Modify: `backend/app/services/tmdb_service.py`
- Modify: `backend/tests/test_tmdb_service.py`

- [ ] **Step 1: Refactor TMDBService to use get_config()**

Replace the current `__init__` in `backend/app/services/tmdb_service.py`:

**Before:**
```python
def __init__(self):
    self.settings = get_settings()
    self.api_key = self.settings.tmdb_api_key
    self.client = httpx.AsyncClient(timeout=30.0)
```

**After:**
```python
def __init__(self, db: Session | None = None):
    self.db = db
    self.api_key = get_config("tmdb_api_key", db, required=True)
    self.client = httpx.AsyncClient(timeout=30.0)
```

Update imports at the top — replace:
```python
from app.config import get_settings
```
With:
```python
from sqlalchemy.orm import Session
from app.services.config_service import get_config
```

- [ ] **Step 2: Update tests for TMDBService**

Read `backend/tests/test_tmdb_service.py`. Update any test that creates `TMDBService()` without arguments to pass `db=db_session`. For tests that mock `get_settings`, update to use the DB-based approach instead.

Specifically, add this fixture or setup where needed:
```python
db_session.add(Setting(key="tmdb_api_key", value="test-api-key"))
db_session.commit()
```

Then instantiate: `TMDBService(db=db_session)`

- [ ] **Step 3: Run tests**

```bash
cd backend && pytest tests/test_tmdb_service.py -v
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/tmdb_service.py backend/tests/test_tmdb_service.py
git commit -m "refactor: TMDBService uses get_config() with db parameter"
```

---

### Task 4: Refactor QBittorrentService

**Files:**
- Modify: `backend/app/services/qbittorrent_service.py`
- Modify: `backend/tests/test_qbittorrent_service.py`

- [ ] **Step 1: Refactor QBittorrentService to use get_config()**

Replace `__init__` in `backend/app/services/qbittorrent_service.py`:

**Before:**
```python
def __init__(self):
    self.settings = get_settings()
    self.client = httpx.AsyncClient(timeout=30.0)
    self._authenticated = False
```

**After:**
```python
def __init__(self, db: Session | None = None):
    self.db = db
    self.host = get_config("qbittorrent_host", db, required=True)
    self.username = get_config("qbittorrent_username", db, required=True)
    self.password = get_config("qbittorrent_password", db, required=True)
    self.client = httpx.AsyncClient(timeout=30.0)
    self._authenticated = False
```

Update all references from `self.settings.qbittorrent_host` to `self.host`, `self.settings.qbittorrent_username` to `self.username`, and `self.settings.qbittorrent_password` to `self.password`.

Also update `self.settings.jackett_url` and `self.settings.jackett_api_key` references in `_download_torrent_via_jackett` and `_get_fresh_jackett_link` to use `get_config()` directly (these methods create their own calls, so pass `self.db`):

In `_download_torrent_via_jackett`, replace:
```python
proxy_url = f"{self.settings.jackett_url}/dl/{tracker_id}"
```
With:
```python
jackett_url = get_config("jackett_url", self.db)
proxy_url = f"{jackett_url}/dl/{tracker_id}"
```

In `_get_fresh_jackett_link`, replace:
```python
search_url = f"{self.settings.jackett_url}/api/v2.0/indexers/all/results"
params = {
    "apikey": self.settings.jackett_api_key,
```
With:
```python
jackett_url = get_config("jackett_url", self.db)
jackett_api_key = get_config("jackett_api_key", self.db)
search_url = f"{jackett_url}/api/v2.0/indexers/all/results"
params = {
    "apikey": jackett_api_key,
```

Update imports — replace:
```python
from app.config import get_settings
```
With:
```python
from sqlalchemy.orm import Session
from app.services.config_service import get_config
```

- [ ] **Step 2: Update tests**

Read `backend/tests/test_qbittorrent_service.py`. Update tests to:
1. Add DB settings for `qbittorrent_host`, `qbittorrent_username`, `qbittorrent_password`
2. Instantiate `QBittorrentService(db=db_session)`

- [ ] **Step 3: Run tests**

```bash
cd backend && pytest tests/test_qbittorrent_service.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/qbittorrent_service.py backend/tests/test_qbittorrent_service.py
git commit -m "refactor: QBittorrentService uses get_config() with db parameter"
```

---

### Task 5: Refactor JackettScraper

**Files:**
- Modify: `backend/app/scrapers/jackett_scraper.py`
- Modify: `backend/tests/test_scrapers.py`

- [ ] **Step 1: Refactor JackettScraper to use get_config()**

Replace `__init__` in `backend/app/scrapers/jackett_scraper.py`:

**Before:**
```python
def __init__(self):
    self.settings = get_settings()
    self.client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, read=float(self.settings.jackett_timeout))
    )
```

**After:**
```python
def __init__(self, db: Session | None = None):
    self.db = db
    self.url = get_config("jackett_url", db, required=True)
    self.api_key = get_config("jackett_api_key", db, required=True)
    timeout_val = get_config("jackett_timeout", db, required=False) or "120"
    self.client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, read=float(timeout_val))
    )
```

Update the `search` method — replace all `self.settings.jackett_api_key` with `self.api_key` and `self.settings.jackett_url` with `self.url`.

Update imports — replace:
```python
from app.config import get_settings
```
With:
```python
from sqlalchemy.orm import Session
from app.services.config_service import get_config
```

- [ ] **Step 2: Update tests**

Read `backend/tests/test_scrapers.py`. Update tests to add DB settings and pass `db=db_session` to `JackettScraper()`.

- [ ] **Step 3: Run tests**

```bash
cd backend && pytest tests/test_scrapers.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/scrapers/jackett_scraper.py backend/tests/test_scrapers.py
git commit -m "refactor: JackettScraper uses get_config() with db parameter"
```

---

### Task 6: Refactor JellyfinService and DiscoverService

**Files:**
- Modify: `backend/app/services/jellyfin_service.py`
- Modify: `backend/app/services/discover_service.py`
- Modify: `backend/tests/test_jellyfin_service.py`

- [ ] **Step 1: Refactor JellyfinService**

Replace `__init__` in `backend/app/services/jellyfin_service.py`:

**Before:**
```python
def __init__(self) -> None:
    self.settings = get_settings()
    self.client = httpx.AsyncClient(timeout=30.0)
```

**After:**
```python
def __init__(self, db: Session | None = None) -> None:
    self.db = db
    self.url = get_config("jellyfin_url", db, required=True)
    self.api_key = get_config("jellyfin_api_key", db, required=True)
    self.client = httpx.AsyncClient(timeout=30.0)
```

Replace all `self.settings.jellyfin_url` with `self.url` and `self.settings.jellyfin_api_key` with `self.api_key`.

Update imports:
```python
from sqlalchemy.orm import Session
from app.services.config_service import get_config
```

- [ ] **Step 2: Refactor DiscoverService**

Replace `__init__` in `backend/app/services/discover_service.py`:

**Before:**
```python
def __init__(self):
    self.settings = get_settings()
    self.api_key = self.settings.tmdb_api_key
    self.client = httpx.AsyncClient(timeout=10.0)
    self._section_cache: Dict[str, Tuple[float, DiscoverSection]] = {}
    self._genre_cache: Optional[Tuple[float, List[Genre]]] = None
```

**After:**
```python
def __init__(self, db: Session | None = None):
    self.db = db
    self.api_key = get_config("tmdb_api_key", db, required=True)
    self.client = httpx.AsyncClient(timeout=10.0)
    self._section_cache: Dict[str, Tuple[float, DiscoverSection]] = {}
    self._genre_cache: Optional[Tuple[float, List[Genre]]] = None
```

Update imports — replace:
```python
from app.config import get_settings
```
With:
```python
from sqlalchemy.orm import Session
from app.services.config_service import get_config
```

- [ ] **Step 3: Update tests**

Read `backend/tests/test_jellyfin_service.py` and `backend/tests/test_discover.py`. Update to add DB settings and pass `db=db_session`.

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_jellyfin_service.py tests/test_discover.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/jellyfin_service.py backend/app/services/discover_service.py backend/tests/test_jellyfin_service.py backend/tests/test_discover.py
git commit -m "refactor: JellyfinService and DiscoverService use get_config()"
```

---

### Task 7: Refactor OrganizerService and PathResolver

**Files:**
- Modify: `backend/app/services/organizer_service.py`
- Modify: `backend/app/services/path_resolver.py`
- Modify: `backend/tests/test_organizer_service.py`
- Modify: `backend/tests/services/test_path_resolver.py`

- [ ] **Step 1: Refactor OrganizerService**

Replace `__init__` in `backend/app/services/organizer_service.py`:

**Before:**
```python
def __init__(self, db: Optional[Session] = None):
    if db:
        paths = get_media_paths(db)
        self.movies_path = paths["movies_path"]
        self.series_path = paths["series_path"]
        self.animes_path = paths["animes_path"]
    else:
        settings = get_settings()
        self.movies_path = settings.movies_path
        self.series_path = settings.series_path
        self.animes_path = settings.animes_path
```

**After:**
```python
def __init__(self, db: Optional[Session] = None):
    self.movies_path = get_config("movies_path", db, required=True)
    self.series_path = get_config("series_path", db, required=True)
    self.animes_path = get_config("animes_path", db, required=True)
```

Update imports — remove:
```python
from app.config import get_settings
from app.services.settings_service import get_media_paths
```
Add:
```python
from app.services.config_service import get_config
```

- [ ] **Step 2: Refactor PathResolver**

Replace the path resolution logic in `resolve_path()` method. Find this block:

```python
if db:
    paths = get_media_paths(db)
    movies_path = paths["movies_path"]
    series_path = paths["series_path"]
    animes_path = paths["animes_path"]
else:
    settings = get_settings()
    movies_path = settings.movies_path
    series_path = settings.series_path
    animes_path = settings.animes_path
```

Replace with:
```python
movies_path = get_config("movies_path", db, required=True)
series_path = get_config("series_path", db, required=True)
animes_path = get_config("animes_path", db, required=True)
```

Update imports — remove:
```python
from app.config import get_settings
from app.services.settings_service import get_media_paths
```
Add:
```python
from app.services.config_service import get_config
```

- [ ] **Step 3: Update tests**

Read `backend/tests/test_organizer_service.py` and `backend/tests/services/test_path_resolver.py`. Update to add DB settings for paths and pass `db=db_session`.

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_organizer_service.py tests/services/test_path_resolver.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/organizer_service.py backend/app/services/path_resolver.py backend/tests/test_organizer_service.py backend/tests/services/test_path_resolver.py
git commit -m "refactor: OrganizerService and PathResolver use get_config()"
```

---

### Task 8: Refactor Routers and DownloadWorker

**Files:**
- Modify: `backend/app/routers/search.py`
- Modify: `backend/app/routers/downloads.py`
- Modify: `backend/app/routers/discover.py`
- Modify: `backend/app/services/download_worker.py`
- Modify: `backend/app/services/settings_service.py`

- [ ] **Step 1: Refactor search.py router**

Read `backend/app/routers/search.py`. Make these changes:

1. Add imports:
```python
from sqlalchemy.orm import Session
from fastapi import Depends
from app.database import get_db
from app.services.config_service import get_config
```

2. Update `_enrich_with_rt_data` to accept `db` parameter:

**Before:**
```python
async def _enrich_with_rt_data(detail: TMDBDetail, media_type: str) -> TMDBDetail:
    ...
    from app.config import get_settings
    settings = get_settings()
    if not settings.omdb_api_key:
        return detail
    omdb = OMDbService(api_key=settings.omdb_api_key)
```

**After:**
```python
async def _enrich_with_rt_data(detail: TMDBDetail, media_type: str, db: Session | None = None) -> TMDBDetail:
    ...
    omdb_api_key = get_config("omdb_api_key", db, required=False)
    if not omdb_api_key:
        return detail
    omdb = OMDbService(api_key=omdb_api_key)
```

3. Update all endpoints to accept `db: Session = Depends(get_db)` and pass `db=db` to service constructors:

For `search_media`:
```python
async def search_media(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    service = TMDBService(db=db)
    ...
```

For `get_movie_detail`:
```python
async def get_movie_detail(
    movie_id: int,
    db: Session = Depends(get_db),
):
    service = TMDBService(db=db)
    ...
    result = await _enrich_with_rt_data(result, "movie", db=db)
```

Apply the same pattern to `get_tv_detail`, `get_tv_seasons`, `get_tv_season_detail`.

For `search_torrents`:
```python
async def search_torrents(
    tmdb_id: int = Query(...),
    media_type: str = Query(..., pattern="^(movie|series|anime)$"),
    season: Optional[int] = Query(None, ge=1),
    episode: Optional[int] = Query(None, ge=1),
    quality: Optional[str] = Query("1080p"),
    language: Optional[str] = Query("legendado"),
    query: Optional[str] = Query(None, description="Custom search query override"),
    db: Session = Depends(get_db),
):
    service = TMDBService(db=db)
    scraper = JackettScraper(db=db)
    ...
```

- [ ] **Step 2: Refactor downloads.py router**

Read `backend/app/routers/downloads.py`. Find where `PathResolver` is instantiated and pass `db=db`:

```python
resolver = PathResolver()
save_path = resolver.resolve_path(..., db=db)
```

Ensure the endpoint already has `db: Session = Depends(get_db)` — if not, add it.

- [ ] **Step 3: Refactor discover.py router**

Read `backend/app/routers/discover.py`. Update `DiscoverService` instantiation to pass `db=db`:

```python
service = DiscoverService(db=db)
```

- [ ] **Step 4: Refactor DownloadWorker**

Read `backend/app/services/download_worker.py`. Update to pass `db` to services:

In `_sync_progress`, the worker already creates `db = SessionLocal()`. Update:

```python
service = QBittorrentService(db=db)
```

In `_organize_completed_download`, the `OrganizerService` already receives `db=db` — no change needed there since it now uses `get_config()` internally.

- [ ] **Step 5: Simplify settings_service.py**

Read `backend/app/services/settings_service.py`. The `get_media_paths()` function is no longer needed since `get_config()` handles this. Replace the entire file content with a deprecation notice or remove the function. Since other code may still reference it, keep it but mark as deprecated:

```python
"""Settings service — DEPRECATED: use config_service.get_config() instead."""
from sqlalchemy.orm import Session
from app.services.config_service import get_config


def get_media_paths(db: Session) -> dict:
    """DEPRECATED: Use get_config() for individual path keys instead."""
    return {
        "movies_path": get_config("movies_path", db, required=True),
        "series_path": get_config("series_path", db, required=True),
        "animes_path": get_config("animes_path", db, required=True),
    }
```

- [ ] **Step 6: Run all tests**

```bash
cd backend && pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/search.py backend/app/routers/downloads.py backend/app/routers/discover.py backend/app/services/download_worker.py backend/app/services/settings_service.py
git commit -m "refactor: routers and DownloadWorker pass db to services"
```

---

### Task 9: Add Seed Initial Config on Startup

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add seed function to main.py**

Add this function before the `lifespan` function in `backend/app/main.py`:

```python
def _seed_config_from_env(db: Session) -> None:
    """Populate DB with .env values if keys are missing."""
    from app.config import get_settings
    from app.models.settings import Setting

    env = get_settings()
    critical_keys = [
        "tmdb_api_key", "omdb_api_key",
        "jackett_url", "jackett_api_key", "jackett_timeout",
        "qbittorrent_host", "qbittorrent_username", "qbittorrent_password",
        "jellyfin_url", "jellyfin_api_key",
        "movies_path", "series_path", "animes_path",
        "default_quality", "default_language",
    ]
    seeded = 0
    for key in critical_keys:
        existing = db.query(Setting).filter(Setting.key == key).first()
        if not existing:
            env_value = getattr(env, key, None)
            if env_value:
                db.add(Setting(key=key, value=env_value))
                seeded += 1
    if seeded:
        db.commit()
        logger.info("Seeded configuration from .env to DB", count=seeded)
```

- [ ] **Step 2: Call seed in lifespan**

Update the `lifespan` function to call `_seed_config_from_env(db)` after `init_db()` and before starting the `DownloadWorker`:

**Before:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    logger.info("Starting up Jellyfin Automation")
    await asyncio.to_thread(init_db)
    
    # Start DownloadWorker background task
    download_worker = DownloadWorker(broadcast_callback=manager.broadcast)
```

**After:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    logger.info("Starting up Jellyfin Automation")
    await asyncio.to_thread(init_db)

    # Seed config from .env if DB is empty
    db = SessionLocal()
    try:
        _seed_config_from_env(db)
    finally:
        db.close()
    
    # Start DownloadWorker background task
    download_worker = DownloadWorker(broadcast_callback=manager.broadcast)
```

Add the import at the top:
```python
from app.database import SessionLocal
```

- [ ] **Step 3: Run tests**

```bash
cd backend && pytest tests/ -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: seed config from .env to DB on startup"
```

---

### Task 10: Update docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env.example`

- [ ] **Step 1: Update docker-compose.yml**

Read the current `docker-compose.yml`. Make these changes:

1. **Add qBittorrent service** (after the `flaresolverr` service):

```yaml
  qbittorrent:
    image: lscr.io/linuxserver/qbittorrent:latest
    restart: always
    environment:
      - PUID=1000
      - PGID=1000
      - WEBUI_PORT=8080
      - TZ=America/Sao_Paulo
    volumes:
      - ./qbittorrent/config:/config
      - ${TORRENTS_PATH:-/mnt/d/Torrents}:/downloads
    ports:
      - "8080:8080"
      - "6881:6881"
      - "6881:6881/udp"
```

2. **Add Jackett service** (after qBittorrent):

```yaml
  jackett:
    image: lscr.io/linuxserver/jackett:latest
    restart: always
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/Sao_Paulo
    volumes:
      - ./jackett/config:/config
      - ${TORRENTS_PATH:-/mnt/d/Torrents}:/downloads
    ports:
      - "9117:9117"
```

3. **Update backend service**:
   - Remove `network_mode: "host"`
   - Add `ports: ["8000:8000"]`
   - Update `DATABASE_URL` to use `db` hostname instead of `localhost`
   - Update default values for `JACKETT_URL` and `QBITTORRENT_HOST` to use Docker service names
   - Add `depends_on` for qbittorrent and jackett

**Backend service after changes:**
```yaml
  backend:
    build: ./backend
    restart: always
    init: true
    stop_grace_period: 10s
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://jfa_user:jfa_password@db:5432/jellyfin_automation
      TMDB_API_KEY: ${TMDB_API_KEY:-}
      OMDB_API_KEY: ${OMDB_API_KEY:-}
      JACKETT_URL: ${JACKETT_URL:-http://jackett:9117}
      JACKETT_API_KEY: ${JACKETT_API_KEY:-}
      QBITTORRENT_HOST: ${QBITTORRENT_HOST:-http://qbittorrent:8080}
      QBITTORRENT_USERNAME: ${QBITTORRENT_USERNAME:-admin}
      QBITTORRENT_PASSWORD: ${QBITTORRENT_PASSWORD:-adminadmin}
      JELLYFIN_URL: ${JELLYFIN_URL:-http://host.docker.internal:8096}
      JELLYFIN_API_KEY: ${JELLYFIN_API_KEY:-}
      MOVIES_PATH: ${MOVIES_PATH:-/mnt/d/Filmes}
      SERIES_PATH: ${SERIES_PATH:-/mnt/d/Séries}
      ANIMES_PATH: ${ANIMES_PATH:-/mnt/d/Animes}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - /mnt:/mnt
      - ./backend/logs:/app/logs
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Note: `JELLYFIN_URL` defaults to `http://host.docker.internal:8096` because Jellyfin stays on the Windows host.

4. **Update frontend service** — add dependency on backend:

```yaml
  frontend:
    restart: always
    build: ./frontend
    init: true
    stop_grace_period: 10s
    ports:
      - "3001:80"
    depends_on:
      - backend
```

Remove `extra_hosts` from frontend since backend is now on the Docker network.

- [ ] **Step 2: Update .env.example**

Update defaults in `.env.example`:

```
# Database
DATABASE_URL=postgresql://jfa_user:jfa_password@db:5432/jellyfin_automation

# TMDB API (get yours at https://www.themoviedb.org/settings/api)
TMDB_API_KEY=your_tmdb_api_key_here

# qBittorrent Web UI (Docker service)
QBITTORRENT_HOST=http://qbittorrent:8080
QBITTORRENT_USERNAME=admin
QBITTORRENT_PASSWORD=adminadmin

# Jackett (Docker service)
JACKETT_URL=http://jackett:9117
JACKETT_API_KEY=your_jackett_api_key_here

# Jellyfin (runs on Windows host)
JELLYFIN_URL=http://host.docker.internal:8096
JELLYFIN_API_KEY=your_jellyfin_api_key_here

# App
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-here-change-in-production

# Library paths (use absolute paths)
MOVIES_PATH=/mnt/d/Filmes
SERIES_PATH=/mnt/d/Séries
ANIMES_PATH=/mnt/d/Animes

# Default preferences
DEFAULT_QUALITY=1080p
DEFAULT_LANGUAGE=legendado

# OMDB API
OMDB_API_KEY=your_omdb_api_key_here
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "feat: add qBittorrent and Jackett to docker-compose"
```

---

### Task 11: Add "Serviços Externos" to Settings Page

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Add external service config groups to Settings.tsx**

Read `frontend/src/pages/Settings.tsx`. Add a new import for the `Eye` and `EyeOff` icons from lucide-react:

```typescript
import { Folder, Sparkles, Save, Eye, EyeOff, Server } from 'lucide-react';
```

Add a new group to `settingGroups` array (after the existing groups):

```typescript
{
  icon: Server,
  title: 'Serviços Externos',
  description: 'Configuração de APIs e serviços externos',
  settings: [
    { key: 'tmdb_api_key', label: 'TMDB API Key', placeholder: 'Sua chave do TMDB', sensitive: true },
    { key: 'omdb_api_key', label: 'OMDB API Key', placeholder: 'Sua chave do OMDB', sensitive: true },
    { key: 'jackett_url', label: 'Jackett URL', placeholder: 'http://jackett:9117' },
    { key: 'jackett_api_key', label: 'Jackett API Key', placeholder: 'Sua chave do Jackett', sensitive: true },
    { key: 'qbittorrent_host', label: 'qBittorrent Host', placeholder: 'http://qbittorrent:8080' },
    { key: 'qbittorrent_username', label: 'qBittorrent Username', placeholder: 'admin' },
    { key: 'qbittorrent_password', label: 'qBittorrent Password', placeholder: 'Senha do qBittorrent', sensitive: true, type: 'password' },
    { key: 'jellyfin_url', label: 'Jellyfin URL', placeholder: 'http://host.docker.internal:8096' },
    { key: 'jellyfin_api_key', label: 'Jellyfin API Key', placeholder: 'Sua chave do Jellyfin', sensitive: true },
  ],
},
```

- [ ] **Step 2: Update the Settings component to handle sensitive fields**

Add state for tracking which sensitive fields are visible:

```typescript
const [visibleFields, setVisibleFields] = useState<Set<string>>(new Set());

const toggleVisibility = (key: string) => {
  setVisibleFields((prev) => {
    const next = new Set(prev);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    return next;
  });
};
```

Update the input rendering in the settings groups loop. Find the section that renders path inputs and update to handle the new `sensitive` and `type` properties:

Replace the input rendering for non-select fields with:

```typescript
{group.settings.map((setting) => {
  const isSensitive = (setting as any).sensitive;
  const inputType = (setting as any).type === 'password' ? 'password' : 'text';
  const isVisible = visibleFields.has(setting.key);

  return (
    <div key={setting.key} className="space-y-2">
      <label className="text-sm font-medium text-foreground">
        {setting.label}
      </label>
      <div className="relative group">
        <div className="flex gap-2">
          <input
            type={isSensitive && !isVisible ? 'password' : inputType}
            value={pathValues[setting.key] ?? currentValues[setting.key] ?? ''}
            placeholder={setting.placeholder}
            onChange={(e) => setPathValues((prev) => ({ ...prev, [setting.key]: e.target.value }))}
            onBlur={(e) => handleUpdate(setting.key, e.target.value)}
            className="flex-1 px-4 py-3 rounded-xl glass bg-transparent
                     border border-border/50
                     focus:outline-none focus:ring-2 focus:ring-primary/30
                     focus:border-primary/30
                     text-foreground placeholder:text-muted-foreground/50
                     font-mono text-sm
                     transition-all duration-200"
          />
          {isSensitive && (
            <button
              type="button"
              onClick={() => toggleVisibility(setting.key)}
              className="px-3 py-3 rounded-xl glass border border-border/50
                       hover:bg-primary/10 transition-colors"
            >
              {isVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          )}
        </div>
        {updateMutation.isPending && updateMutation.variables?.key === setting.key && (
          <Save className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-primary animate-pulse" />
        )}
      </div>
    </div>
  );
})}
```

- [ ] **Step 3: Update useEffect to include external service values**

Update the useEffect that syncs `currentSettings` to `pathValues` to include all keys, not just path keys:

**Before:**
```typescript
useEffect(() => {
  if (currentSettings?.data) {
    const newValues = {
      movies_path: currentSettings.data.movies_path || '',
      series_path: currentSettings.data.series_path || '',
      animes_path: currentSettings.data.animes_path || '',
    };
    setPathValues((prev) => {
      if (
        prev.movies_path === newValues.movies_path &&
        prev.series_path === newValues.series_path &&
        prev.animes_path === newValues.animes_path
      ) {
        return prev;
      }
      return { ...prev, ...newValues };
    });
  }
}, [currentSettings?.data?.movies_path, currentSettings?.data?.series_path, currentSettings?.data?.animes_path]);
```

**After:**
```typescript
useEffect(() => {
  if (currentSettings?.data) {
    setPathValues((prev) => ({ ...prev, ...currentSettings.data }));
  }
}, [currentSettings?.data]);
```

- [ ] **Step 4: Build frontend to verify**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Settings.tsx frontend/src/services/api.ts
git commit -m "feat: add external services section to Settings page"
```

---

### Task 12: Final Verification

**Files:**
- All modified files

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: Run frontend build**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Run frontend lint**

```bash
cd frontend && npm run lint
```

Expected: No lint errors.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: dockerize qBittorrent/Jackett and add dynamic config via UI"
```

---

## Self-Review

### Spec Coverage Check

| Spec Requirement | Task |
|---|---|
| qBittorrent in Docker | Task 10 |
| Jackett in Docker | Task 10 |
| Backend Docker network (no host mode) | Task 10 |
| get_config() with DB > .env > error | Task 1 |
| ConfigurationError exception | Task 1 |
| FastAPI exception handler | Task 2 |
| TMDBService refactored | Task 3 |
| QBittorrentService refactored | Task 4 |
| JackettScraper refactored | Task 5 |
| JellyfinService refactored | Task 6 |
| DiscoverService refactored | Task 6 |
| OrganizerService refactored | Task 7 |
| PathResolver refactored | Task 7 |
| Routers pass db to services | Task 8 |
| DownloadWorker passes db | Task 8 |
| Seed initial config from .env | Task 9 |
| Settings page "Serviços Externos" | Task 11 |
| Sensitive field masking | Task 11 |
| .env.example updated | Task 10 |

### Placeholder Scan
No "TBD", "TODO", or "implement later" found. All code blocks contain actual implementation code.

### Type Consistency
- `get_config()` returns `str` consistently
- All services accept `db: Session | None = None`
- `ConfigurationError` has `key: str` and `message: str` attributes
- `Setting.value` is JSON type — handled with `isinstance(val, str)` check

### No Ambiguity
All file paths, function signatures, and import statements are explicitly defined.
