# AGENTS.md — Jellyfin Automation

Full-stack app (FastAPI + React) that automates media downloads for Jellyfin via TMDB search, Jackett torrent indexing, and qBittorrent management.

## Monorepo layout

| Directory           | Purpose                                          |
| ------------------- | ------------------------------------------------ |
| `backend/`          | FastAPI app, entry `app/main.py`                 |
| `frontend/`         | React 18 + Vite + Tailwind, entry `src/main.tsx` |
| `docs/`             | Installation guide (`INSTALL.md`) and plans/specs |
| `docker/`           | Docker configs (Avahi mDNS container)            |
| `scripts/`          | `build_windows.bat`, `open_firewall.ps1`, `start_jellyfin.bat` |

## Developer commands

**Backend (run from `backend/`)**

- `source venv/bin/activate`
- `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- `pytest tests/ -v` — run all tests (uses SQLite in-memory, not PostgreSQL)
- `alembic upgrade head` — run migrations

**Frontend (run from `frontend/`)**

- `npm run dev` — dev server on **port 3001** (Vite config overrides default 5173)
- `npm run build` — `tsc && vite build`; also serves as the frontend "test" step
- `npm run lint` — ESLint

**Docker**

- `docker-compose up --build -d` — full stack
- Frontend container exposes **3001**, backend 8000, Postgres 5432, qBittorrent 8082, Jackett 9117, FlareSolverr 8191

## Backend architecture

- **Config:** Pydantic Settings in `app/config.py` loads `.env` from **repo root** (`env_file=".env"`).
- **DB:** SQLAlchemy 2.0 + PostgreSQL in prod; Alembic migrations in `backend/alembic/`.
- **Tests:** pytest + pytest-asyncio. `conftest.py` overrides `get_db` with SQLite in-memory (`StaticPool`).
- **Logging:** Loguru + structlog. Logs written to `backend/logs/app.log` with rotation.
- **Models:** `download.py`, `settings.py`, `tmdb.py`, `torrent.py`, `discover.py` in `app/models/`.
- **Routers:** `search`, `downloads`, `settings`, `logs`, `filesystem`, `discover` in `app/routers/`.
- **Services:** `PathResolver` (`app/services/path_resolver.py`) computes save paths from torrent metadata; `DownloadWorker` (`app/services/download_worker.py`) monitors qBittorrent progress in a background loop; `OrganizerService` (`app/services/organizer_service.py`) moves completed downloads to library folders; `DiscoverService` (`app/services/discover_service.py`) provides TMDB browse sections; `JellyfinService` (`app/services/jellyfin_service.py`) triggers library scans; `OMDBService` (`app/services/omdb_service.py`) fetches Rotten Tomatoes ratings; `PathConverter` (`app/services/path_converter.py`) converts WSL2↔Windows paths; `SettingsService` (`app/services/settings_service.py`) manages settings CRUD; `ConfigService` (`app/services/config_service.py`) provides `get_config()` with DB→.env priority chain.
- **Scrapers:** `JackettScraper` (`app/scrapers/jackett_scraper.py`) with `BaseScraper` abstract interface.
- **Exceptions:** `ConfigurationError` in `app/exceptions.py`.
- **WebSocket:** `/ws` endpoint in `app/main.py` broadcasts download updates.
- **Health:** `/health` endpoint returns app status.
- **Static files:** `main.py` mounts `../frontend/dist` at `/` for production serving; if missing, app starts without it.
- **Background worker:** `DownloadWorker` is started in the FastAPI lifespan and syncs qBittorrent state every 10 seconds.

## Configuration system

- **Priority chain:** DB → `.env` → error. All API keys and service URLs are stored in the `settings` table and read via `get_config(key, db, required=True)` from `app/services/config_service.py`.
- **Seed on startup:** On first boot, `_seed_config_from_env()` in `main.py` populates the DB with values from `.env` for any missing keys.
- **Runtime updates:** Settings can be changed via the Settings UI (`PUT /api/settings/{key}`). Services pick up new values on their next instantiation (most services are created per-request; DownloadWorker creates fresh instances every 10s).
- **`@lru_cache()` on `get_settings()`:** The `.env` settings object is cached for the process lifetime. DB values override cached `.env` values via `get_config()`.

## Frontend architecture

- **Path alias:** `@/` → `src/` (configured in both `vite.config.ts` and `tsconfig.json`).
- **Proxy:** Vite dev server proxies `/api` and `/ws` to `localhost:8000`.
- **Stack:** React Router, TanStack Query, Axios, shadcn/ui components in `src/components/ui/`.
- **Strict TS:** `noUnusedLocals` and `noUnusedParameters` are enabled.
- **Pages:** `Home`, `Search`, `Discover`, `Detail`, `Downloads`, `Settings`, `Logs`.
- **Components:** `Header`, `SearchBar`, `MediaCard`, `TorrentList`, `DownloadMonitor`, `DiscoverFilterBar`, `DiscoverRow`, `FolderPickerDialog`, `ThemeToggle`, `ui/` (shadcn).
- **UI Components:** Uses shadcn/ui components. New components should be added via `npx shadcn@latest add <component>`.
    - Dialogs/modals must use the `Dialog` component from `@/components/ui/dialog` — no custom modal implementations.
    - Toast notifications use `sonner` (`toast.success()` / `toast.error()`) — never use native `alert()`.

## Download flow

1. User searches TMDB → selects media (and season/episode for TV) → sees torrent results from Jackett
2. Frontend calls `POST /api/downloads/` with:
    - `magnet_link` (optional) — magnet URI if available from indexer
    - `download_url` (optional) — Jackett proxy link for .torrent file
    - `season` / `episode` (optional) — for series/anime episodes
3. Backend uses `PathResolver` to compute the save path from title, media type, torrent name, and season/episode
4. Backend saves to DB with status `PENDING`, including `season`, `episode`, and `source_folder`
5. Backend immediately tries to add to qBittorrent with the computed `save_path`:
    - If `magnet_link` is present → sends magnet URI directly to qBittorrent
    - If only `download_url` is present → downloads .torrent file from Jackett and uploads to qBittorrent
    - If download fails (e.g., link expired) → attempts to refresh link via Jackett API
6. On success → status becomes `DOWNLOADING`; on failure → `FAILED` with `error_message`
7. `DownloadWorker` (background task) monitors qBittorrent every 10 seconds:
    - Updates `progress`, `speed`, `eta`, and `status` in the database
    - When a download reaches `COMPLETED`, triggers `OrganizerService` to move files to the appropriate library folder (`movies_path`, `series_path`, or `animes_path`)

## Docker services

| Service | Image | Ports | Notes |
|---------|-------|-------|-------|
| db | `postgres:15-alpine` | 5432 | PostgreSQL database |
| backend | Custom build | 8000 | FastAPI app |
| frontend | Custom build | 3001 | React + nginx |
| caddy | `caddy:alpine` | 80 | Reverse proxy (plain HTTP) |
| avahi | Custom build | — | mDNS for `jellyfin.local` (host network) |
| qbittorrent | `lscr.io/linuxserver/qbittorrent` | 8082, 6881 | Torrent client (host port 8082) |
| jackett | `lscr.io/linuxserver/jackett` | 9117 | Torrent indexer gateway |
| flaresolverr | `ghcr.io/flaresolverr/flaresolverr` | 8191 | Cloudflare bypass for Jackett |

**qBittorrent notes:**
- Generates a temporary password on first run. Set a permanent password via Web UI → Settings → Web UI → Authentication.
- CSRF protection and host header validation are disabled to allow localhost access.
- Backend connects via Docker network (`http://qbittorrent:8080`), not the host port.
- qBittorrent v5 returns HTTP 204 (empty body) on successful login, not HTTP 200 with "Ok." — `QBittorrentService._authenticate()` handles both.

**Jackett notes:**
- Comes with no indexers configured. User must add indexers via Web UI at `http://localhost:9117`.
- FlareSolverr must be configured in Jackett settings: URL = `http://flaresolverr:8191`.
- API key is generated on first run and displayed in the Web UI header.

## Environment / gotchas

- `.env` must be at repo root; `backend/alembic.ini` hardcodes a fallback DB URL but the app uses `DATABASE_URL` from `.env`.
- Media paths (`MOVIES_PATH`, `SERIES_PATH`, `ANIMES_PATH`) must be absolute and writable.
- Jellyfin runs externally (typically on Windows host). Use `http://host.docker.internal:8096` from Docker containers.
- `dist/` is in `.gitignore`; frontend must be built before backend can serve static files.
- `jackett/config/` and `qbittorrent/config/` are in `.gitignore` — they contain runtime state and credentials.
- **Trailing slashes matter:** FastAPI routes are defined with trailing slashes (e.g., `/api/downloads/`). Frontend must use trailing slashes to avoid 307 redirects.
- **Jackett links expire:** `download_url` from Jackett search results may expire after a few minutes. The backend implements fallback logic to refresh expired links.
- **DownloadWorker runs on startup:** The background worker starts automatically with the FastAPI app and cannot be disabled without code changes.
- **OrganizerService moves files on completion:** Completed downloads are automatically organized into `MOVIES_PATH`, `SERIES_PATH`, or `ANIMES_PATH` based on media type. Ensure these paths are writable.
- **ConfigError on missing settings:** If a required config key is missing from both DB and `.env`, the API returns HTTP 500 with `{"error": "configuration_error", "key": "...", "message": "..."}`.
- **nginx.conf uses Docker service names:** The frontend nginx proxies to `http://backend:8000`, not `backend-host`.
- **Caddy serves plain HTTP** on port 80 (auto-HTTPS disabled) and reverse-proxies to the frontend container.
- **Avahi mDNS** broadcasts `jellyfin.local` on the local network via host network mode — Debian-based container (Alpine avahi-daemon crashes).
- This project runs on WSL2.

## Running a single test

```bash
cd backend
pytest tests/test_tmdb_service.py -v
pytest tests/test_scrapers.py::test_jackett_search -v
```
