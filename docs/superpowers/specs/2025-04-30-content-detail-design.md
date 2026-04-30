# Content Detail & Torrent Search Enhancement — Design Spec

**Date:** 2025-04-30
**Status:** Approved

---

## Overview

Implement a content detail page, fix torrent search reliability, and improve search strategy by using both Portuguese and original titles, with optional season/episode refinement.

**Branches:**
- `fix/torrent-search` (backend)
- `feature/content-detail` (frontend)

---

## Goals

1. **Content Detail Page:** When a user clicks a TMDB search result, navigate to a dedicated detail page (`/detail/:mediaType/:id`) showing TMDB info, available torrents, and season/episode selectors for TV/anime.
2. **Fix 500 Error:** The `/api/search/torrents` endpoint currently throws unhandled exceptions. Wrap it in robust error handling so the real error is logged and a proper JSON response is returned.
3. **Dual Title Search:** Instead of relying on the frontend-provided `title`, the backend fetches both the Portuguese and original titles from TMDB, runs two Jackett searches, merges and deduplicates results.
4. **Season/Episode Refinement:** Allow users to search for a whole season, a specific episode, or multiple episodes. The backend formats search queries accordingly (e.g., `S01`, `S01E05`).
5. **Settings Quality/Language Selects:** Convert the free-text `default_quality` and `default_language` inputs in Settings to `<select>` elements with fixed options.
6. **Scroll Restoration:** When returning from the detail page to search, restore the previous search term and scroll position.

---

## Branch 1: Backend (`fix/torrent-search`)

### 1.1 Fix 500 Error on `/api/search/torrents`

**Current behavior:** Unhandled exceptions in `JackettScraper.search()` bubble up as opaque 500s.

**New behavior:** Wrap the entire handler body in `try/except`. Log the full traceback with Loguru. Return HTTP 500 with JSON `{"detail": "Torrent search failed: <error message>"}`.

**Files:**
- `backend/app/routers/search.py` — endpoint `search_torrents()`

### 1.2 Remove `title` Parameter, Fetch from TMDB

**Current endpoint:**
```
GET /api/search/torrents?tmdb_id=31910&title=Naruto+Shippuden&media_type=series
```

**New endpoint:**
```
GET /api/search/torrents?tmdb_id=31910&media_type=series&season=1&episode=5
```

Parameters:
- `tmdb_id` (int, required)
- `media_type` (str, required): `movie` or `tv` (the router already normalizes `series` → `tv` internally)
- `season` (int, optional)
- `episode` (int, optional)

**Logic:**
1. Use existing `TMDBService.get_movie_detail()` or `get_tv_detail()` to fetch the TMDB record.
2. Extract:
   - Portuguese title: `title` (movies) or `name` (TV)
   - Original title: `original_title` (movies) or `original_name` (TV)
3. For each title, build a query suffix based on `season`/`episode`:
   - Neither → no suffix
   - Only `season` → `S{season:02d}` or `Season {season}`
   - Both → `S{season:02d}E{episode:02d}`
4. Call `JackettScraper.search()` for each title (if titles differ; if identical, run once).
5. Merge results, deduplicate by `magnet` URL (fallback to `name` if no magnet).
6. Re-sort by score descending.

**Files:**
- `backend/app/routers/search.py` — rewrite `search_torrents()` logic
- `backend/app/services/scrapers.py` — ensure `JackettScraper.search()` accepts any query string cleanly

### 1.3 TMDB Season API

Add a new endpoint so the frontend can list seasons and episode counts:

```
GET /api/tv/{tmdb_id}/seasons
```

Response:
```json
[
  {"season_number": 1, "name": "Season 1", "episode_count": 220},
  {"season_number": 2, "name": "Season 2", "episode_count": 21}
]
```

**Implementation:** Uses TMDB API `tv/{id}` endpoint which already returns `seasons` array. The backend just passes it through, filtering to relevant fields.

**Files:**
- `backend/app/routers/search.py` — new endpoint `get_tv_seasons()`
- `backend/app/services/tmdb.py` — optional helper if not already covered by existing methods

---

## Branch 2: Frontend (`feature/content-detail`)

### 2.1 Detail Page (`/detail/:mediaType/:id`)

**Route:** React Router route `/detail/:mediaType/:id` where `mediaType` is `movie` or `tv`.

**Layout:**
- **Hero Section:** Backdrop image with dark overlay. Title, year, genres, rating, runtime (or episode count), and a short overview.
- **Tab: Torrents (default):**
  - For `tv`/`anime`:
    - Season `<Select>` populated from `GET /api/tv/{id}/seasons`
    - Episode `<Select>` (default option "Temporada inteira", then 1..N)
    - Multi-select checkboxes next to each episode for batch mode (only when multi-select is active)
    - "Buscar Torrents" button triggers `GET /api/search/torrents` with chosen params
  - For `movie`:
    - No season/episode UI. Torrents load automatically on mount.
  - Torrent list: same card style as current UI, showing name, size, seeders, leechers, score, download button.
- **Tab: Informações:** Full overview, cast, crew, etc.

**Navigation from Search:**
- In `Search.tsx`, `MediaCard.onClick` currently triggers torrent search directly.
- Change to: `navigate(`/detail/${mediaType}/${item.id}`)`.

**Files:**
- `frontend/src/pages/Detail.tsx` — new page
- `frontend/src/App.tsx` — add route
- `frontend/src/pages/Search.tsx` — change `MediaCard` click behavior
- `frontend/src/services/api.ts` — add `getTVSeasons()`, update `searchTorrents()` signature

### 2.2 Scroll Restoration & Search State

**Problem:** User clicks a result, goes to detail, clicks back — search results and scroll position are lost.

**Solution:**
- Before navigating to detail, save to `sessionStorage`:
  - `searchQuery`: current search input value
  - `searchResults`: current results array
  - `scrollY`: `window.scrollY`
- On `Search.tsx` mount, check `sessionStorage` for saved state. If present, restore query, results, and call `window.scrollTo(0, savedScrollY)`. Then clear the saved state.

**Alternative:** Use React Router's `ScrollRestoration` if upgrading is viable; otherwise, the manual approach above is explicit and works with the current stack.

**Files:**
- `frontend/src/pages/Search.tsx` — add save/restore logic

### 2.3 Settings Selects

In `frontend/src/pages/Settings.tsx`, replace the free-text inputs for `default_quality` and `default_language` with shadcn/ui `<Select>` components.

**Options:**
- `default_quality`: `720p`, `1080p`, `1440p`, `2160p`
- `default_language`: `legendado`, `dublado`

No backend changes needed; the settings API already accepts strings.

**Files:**
- `frontend/src/pages/Settings.tsx`

---

## Data Flow

### Torrent Search (New Flow)

```
User on Detail Page (TV)
    ↓
Selects Season 1, Episodes 3 & 4 (batch mode)
    ↓
Clicks "Buscar Torrents"
    ↓
Frontend: GET /api/search/torrents?tmdb_id=31910&media_type=tv&season=1&episode=3
Frontend: GET /api/search/torrents?tmdb_id=31910&media_type=tv&season=1&episode=4
    ↓
Backend: Fetches TMDB detail → gets PT title + original title
Backend: Builds queries:
    "Naruto Shippuden S01E03" (PT)
    "Naruto: Shippuden S01E03" (original)
Backend: Calls JackettScraper.search() for each
Backend: Merges, deduplicates, sorts by score
    ↓
Returns JSON list of TorrentResult
    ↓
Frontend displays merged list
```

*Note on batch:* The frontend can fire parallel requests per selected episode and merge the UI results, or we can extend the backend to accept a list of episodes. For simplicity (v1), the frontend fires one request per episode and merges in UI state.

### Scroll Restoration Flow

```
Search Page
    ↓
User clicks MediaCard
    ↓
Save {query, results, scrollY} to sessionStorage
    ↓
Navigate to Detail Page
    ↓
User clicks "Voltar"
    ↓
Search Page mounts → reads sessionStorage
    ↓
Restores query, results, calls window.scrollTo(0, scrollY)
    ↓
Clears sessionStorage
```

---

## Error Handling

### Backend
- **TMDB fetch fails:** Return `503 Service Unavailable` with `{"detail": "TMDB unavailable"}`.
- **Jackett fetch fails:** Log error, return empty torrent list (not 500) so the user sees "Nenhum torrent encontrado".
- **Unexpected exception:** Return `500` with sanitized error message and full traceback in server logs.

### Frontend
- **Detail fetch fails:** Show inline error banner with retry button.
- **No torrents found:** Show empty state message with suggestion to adjust season/episode or try original title.
- **Season API fails:** Disable season selector, show generic error.

---

## Testing Strategy

### Backend Tests
- Test `search_torrents()` with mocked TMDB and Jackett responses.
- Assert deduplication logic when PT and original titles return overlapping magnets.
- Assert season/episode suffix formatting (`S01`, `S01E05`).
- Assert 500 is returned gracefully on unexpected exceptions.
- Test new `GET /api/tv/{id}/seasons` endpoint.

### Frontend Tests
- Build passes (`npm run build`).
- Lint passes (`npm run lint`).
- Manual verification:
  - Click movie → detail page loads, torrents appear.
  - Click TV show → season selector works, episode selector updates, search triggers.
  - Back button restores search state and scroll.
  - Settings selects have correct options and save correctly.

---

## Files Summary

| File | Action | Branch |
|------|--------|--------|
| `backend/app/routers/search.py` | Modify torrent endpoint + add season endpoint | `fix/torrent-search` |
| `backend/app/services/scrapers.py` | Ensure query string acceptance is clean | `fix/torrent-search` |
| `backend/app/services/tmdb.py` | Add season detail helper if needed | `fix/torrent-search` |
| `backend/tests/test_search.py` | Add tests for new logic | `fix/torrent-search` |
| `frontend/src/pages/Detail.tsx` | Create new page | `feature/content-detail` |
| `frontend/src/App.tsx` | Add `/detail/:mediaType/:id` route | `feature/content-detail` |
| `frontend/src/pages/Search.tsx` | Change click behavior + scroll restoration | `feature/content-detail` |
| `frontend/src/pages/Settings.tsx` | Convert inputs to Selects | `feature/content-detail` |
| `frontend/src/services/api.ts` | Add `getTVSeasons()`, update `searchTorrents()` | `feature/content-detail` |

---

## Open Questions / Decisions

1. **Batch episodes:** For v1, the frontend fires parallel requests per episode. A future optimization could send an array of episodes to the backend in a single request.
2. **Deduplication key:** Primary key is `magnet` URL; if absent, fall back to exact `name` string match. This is acceptable for Jackett results.
3. **Scroll restoration scope:** Only the immediate back-from-detail-to-search scenario is covered. Refreshing the search page does not persist state (by design, to avoid stale data).
