# AGENTS.md — Jellyfin Automation

Full-stack app (FastAPI + React) that automates media downloads for Jellyfin via TMDB search, Jackett torrent indexing, and qBittorrent management.

## Monorepo layout

| Directory | Purpose |
|-----------|---------|
| `backend/` | FastAPI app, entry `app/main.py` |
| `frontend/` | React 18 + Vite + Tailwind, entry `src/main.tsx` |
| `docs/superpowers/` | Implementation plans and specs (reference only) |
| `scripts/` | `build_windows.bat` (PyInstaller) |

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
- Frontend container exposes **3001**, backend 8000, Postgres 5432

## Backend architecture

- **Config:** Pydantic Settings in `app/config.py` loads `.env` from **repo root** (`env_file=".env"`).
- **DB:** SQLAlchemy 2.0 + PostgreSQL in prod; Alembic migrations in `backend/alembic/`.
- **Tests:** pytest + pytest-asyncio. `conftest.py` overrides `get_db` with SQLite in-memory (`StaticPool`).
- **Logging:** Loguru + structlog. Logs written to `backend/logs/app.log` with rotation.
- **Services:** `PathResolver` (`app/services/path_resolver.py`) computes save paths from torrent metadata; `DownloadWorker` (`app/services/download_worker.py`) monitors qBittorrent progress in a background loop; `OrganizerService` (`app/services/organizer_service.py`) moves completed downloads to library folders.
- **WebSocket:** `/ws` endpoint in `app/main.py` broadcasts download updates.
- **Static files:** `main.py` mounts `../frontend/dist` at `/` for production serving; if missing, app starts without it.
- **Background worker:** `DownloadWorker` is started in the FastAPI lifespan and syncs qBittorrent state every 10 seconds.

## Frontend architecture

- **Path alias:** `@/` → `src/` (configured in both `vite.config.ts` and `tsconfig.json`).
- **Proxy:** Vite dev server proxies `/api` and `/ws` to `localhost:8000`.
- **Stack:** React Router, TanStack Query, Axios, shadcn/ui components in `src/components/ui/`.
- **Strict TS:** `noUnusedLocals` and `noUnusedParameters` are enabled.
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

## Environment / gotchas

- `.env` must be at repo root; `backend/alembic.ini` hardcodes a fallback DB URL but the app uses `DATABASE_URL` from `.env`.
- Media paths (`MOVIES_PATH`, `SERIES_PATH`, `ANIMES_PATH`) must be absolute and writable.
- External services required for full functionality: qBittorrent (Web UI), Jackett, Jellyfin Server, TMDB API key.
- When running backend outside Docker but services on host, use `host.docker.internal` (Docker) or host IP (WSL2 native) for external service URLs.
- `dist/` is in `.gitignore`; frontend must be built before backend can serve static files.
- No pre-commit hooks, CI workflows, or formatting automation are configured yet.
- **Trailing slashes matter:** FastAPI routes are defined with trailing slashes (e.g., `/api/downloads/`). Frontend must use trailing slashes to avoid 307 redirects.
- **Jackett links expire:** `download_url` from Jackett search results may expire after a few minutes. The backend implements fallback logic to refresh expired links.
- **DownloadWorker runs on startup:** The background worker starts automatically with the FastAPI app and cannot be disabled without code changes.
- **OrganizerService moves files on completion:** Completed downloads are automatically organized into `MOVIES_PATH`, `SERIES_PATH`, or `ANIMES_PATH` based on media type. Ensure these paths are writable.

## Running a single test

```bash
cd backend
pytest tests/test_tmdb_service.py -v
pytest tests/test_scrapers.py::test_jackett_search -v
```