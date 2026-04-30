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
- **WebSocket:** `/ws` endpoint in `app/main.py` broadcasts download updates.
- **Static files:** `main.py` mounts `../frontend/dist` at `/` for production serving; if missing, app starts without it.

## Frontend architecture

- **Path alias:** `@/` → `src/` (configured in both `vite.config.ts` and `tsconfig.json`).
- **Proxy:** Vite dev server proxies `/api` and `/ws` to `localhost:8000`.
- **Stack:** React Router, TanStack Query, Axios, shadcn/ui components in `src/components/ui/`.
- **Strict TS:** `noUnusedLocals` and `noUnusedParameters` are enabled.

## Environment / gotchas

- `.env` must be at repo root; `backend/alembic.ini` hardcodes a fallback DB URL but the app uses `DATABASE_URL` from `.env`.
- Media paths (`MOVIES_PATH`, `SERIES_PATH`, `ANIMES_PATH`) must be absolute and writable.
- External services required for full functionality: qBittorrent (Web UI), Jackett, Jellyfin Server, TMDB API key.
- When running backend outside Docker but services on host, use `host.docker.internal` (Docker) or host IP (WSL2 native) for external service URLs.
- `dist/` is in `.gitignore`; frontend must be built before backend can serve static files.
- No pre-commit hooks, CI workflows, or formatting automation are configured yet.

## Running a single test

```bash
cd backend
pytest tests/test_tmdb_service.py -v
pytest tests/test_scrapers.py::test_jackett_search -v
```
