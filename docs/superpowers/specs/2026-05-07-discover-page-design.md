# Discover Page: Netflix-style TMDB browsing

**Date:** 2026-05-07
**Status:** Design approved

## Overview

Add a `/discover` page that displays content cards organized by categories (horizontal scrollable rows), similar to Netflix. All data comes from the TMDB API. Users can apply global filters (genre, media type, sort order) that affect all sections. Clicking a card navigates to the existing `/detail/:mediaType/:id` page for torrent search and download.

## Backend

### Architecture: Hybrid sections (Approach C)

- `GET /api/discover/sections` — returns section **catalog** (which sections exist, their titles/ids) considering active filters.
- `GET /api/discover/sections/{section_id}?genre_id=X&media_type=Y&sort_by=Z` — returns **data** for one section with filters applied.
- `GET /api/discover/genres` — returns merged genre list from TMDB for the filter dropdown.

When no filters are active, sections use native TMDB endpoints (`/movie/popular`, `/tv/popular`, `/trending/all/week`, etc.). When filters are active, sections use the TMDB `/discover` endpoint. The `trending` section is omitted when any filter is active, since TMDB's `/trending` doesn't support filters and there's no discover equivalent for trending.

### New files

```
backend/app/
  routers/
    discover.py
  services/
    discover_service.py
  models/
    discover.py
```

### Models (`backend/app/models/discover.py`)

```python
class DiscoverParams(BaseModel):
    genre_id: int | None = None
    media_type: str | None = None   # "movie" | "series" | "anime"
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
    results: list[TMDBSearchResult]   # reuses existing model
    total_results: int

class Genre(BaseModel):
    id: int
    name: str
```

### Section catalog (hardcoded in `DiscoverService`)

| section_id | title | media_type | TMDB source (no filter) | Supports filters? |
|---|---|---|---|---|
| `popular-movies` | Filmes Populares | movie | `/movie/popular` | yes (via discover) |
| `popular-series` | Series Populares | series | `/tv/popular` | yes (via discover) |
| `popular-animes` | Animes Populares | anime | `/discover/tv?with_genres=16&with_origin_country=JP&sort_by=popularity.desc` | yes |
| `trending` | Tendencias da Semana | mixed | `/trending/all/week` | **no** |
| `top-rated-movies` | Filmes Melhor Avaliados | movie | `/movie/top_rated` | yes (via discover) |
| `top-rated-series` | Series Melhor Avaliadas | series | `/tv/top_rated` | yes (via discover) |
| `now-playing` | Nos Cinemas | movie | `/movie/now_playing` | yes (via discover) |
| `upcoming` | Em Breve | movie | `/movie/upcoming` | yes (via discover) |
| `genre-action` | Acao | mixed | `/discover/*?with_genres=28` | yes |
| `genre-comedy` | Comedia | mixed | `/discover/*?with_genres=35` | yes |
| `genre-drama` | Drama | mixed | `/discover/*?with_genres=18` | yes |
| `genre-horror` | Terror | mixed | `/discover/*?with_genres=27` | yes |
| `genre-scifi` | Ficcao Cientifica | mixed | `/discover/*?with_genres=878` | yes |

All sections return up to 20 results. Genre sections use 6 fixed popular genres. TMDB requests use `language=pt-BR`.

### `DiscoverService` logic

```
get_sections_catalog(params):
  base = all 13 sections
  if any filter is active:
    base = base - ["trending"]
  return SectionCatalog(sections=base)

get_section(section_id, params):
  if section_id == "trending" and filters_active(params):
    return DiscoverSection(results=[])
  if media_type == "anime":
    use /discover/tv + with_genres=16 + with_origin_country=JP
  if no filters:
    use native endpoint (popular, top_rated, trending, etc.)
  else:
    build /discover/{movie|tv} params from genre_id, sort_by
  map TMDB response to TMDBSearchResult[]
  return DiscoverSection with top 20
```

### Genre endpoint

`GET /genre/movie/list` + `GET /genre/tv/list` merged by id, cached for 1 hour server-side.

### Router integration

In `backend/app/main.py`, add:
```python
from app.routers import discover
app.include_router(discover.router, prefix="/api/discover")
```

## Frontend

### New route

```tsx
<Route path="/discover" element={<DiscoverPage />} />
```

Added to `App.tsx`. Link in `Header` between Search and Downloads.

### New files

```
frontend/src/
  pages/
    Discover.tsx
  components/
    DiscoverFilterBar.tsx
    DiscoverRow.tsx
```

### Components

**`DiscoverPage`** — top-level page component. Holds filter state (`DiscoverParams`), fetches section catalog, renders filter bar and section rows.

**`DiscoverFilterBar`** — three `Select` components (shadcn/ui) side by side:
- Genre (populated from `GET /api/discover/genres`)
- Media type (Todos, Filme, Serie, Anime)
- Sort (Popularidade, Nota, Lancamento)

Default: all filters at "Todos" / "Popularidade".

**`DiscoverRow`** — one horizontal scrollable row. Receives `section: SectionInfo` and `filters: DiscoverParams`. Uses `useQuery` with key `["discover", "section", section.id, filters]`. Reuses existing `MediaCard` component.

States per row:
- **Loading**: shimmer placeholder cards (reuse existing `.shimmer` CSS)
- **Error**: inline "Erro ao carregar" text
- **Empty**: row not rendered (omit entirely)
- **Success**: horizontal scroll with `overflow-x: auto`

Clicking a card navigates to `/detail/{mediaType}/{id}` (existing behavior, uses `MediaCard`'s existing click handler).

### API client additions (`frontend/src/services/api.ts`)

```ts
discoverAPI: {
  getSections: () => api.get("/discover/sections/"),
  getSection: (id: string, params: DiscoverParams) =>
    api.get(`/discover/sections/${id}/`, { params }),
  getGenres: () => api.get("/discover/genres/"),
}
```

### New TypeScript types (`frontend/src/types/index.ts`)

```ts
interface DiscoverParams {
  genre_id?: number | null
  media_type?: string | null
  sort_by?: string
}

interface SectionInfo {
  id: string
  title: string
  media_type: string
}

interface DiscoverSection extends SectionInfo {
  results: TMDBSearchResult[]
  total_results: number
}

interface Genre {
  id: number
  name: string
}
```

### Data flow

```
DiscoverPage
  ├── state: DiscoverParams { genre_id, media_type, sort_by }
  ├── useQuery(["discover", "sections"]) → SectionCatalog
  ├── DiscoverFilterBar ← filters, onChange
  └── catalog.sections.map(section =>
        DiscoverRow(section, filters)
          └── useQuery(["discover", "section", section.id, filters])
                → DiscoverSection
                → render MediaCard[]
      )
```

When any filter changes → all `DiscoverRow` queries refetch automatically (TanStack Query key invalidation via changing `filters` reference).

## Error handling

### Backend

- TMDB rate limit (429) or server errors → caught by `DiscoverService`, logged via loguru, section returns empty `results: []`. Other sections unaffected.
- TMDB API key missing → 503 with clear message.
- 10s timeout on all httpx calls to TMDB.

### Frontend

- Section query failure → inline error text. Other sections continue rendering.
- Catalog query failure → centered error message with retry button.
- Empty catalog → "Nenhuma secao disponivel com esses filtros" message.

## Testing

### Backend (`tests/test_discover.py`)

- `test_get_catalog_returns_all_13_sections_no_filter`
- `test_get_catalog_hides_trending_when_filtered`
- `test_get_section_popular_movies_no_filter` — mock `/movie/popular`
- `test_get_section_popular_movies_with_genre_filter` — mock `/discover/movie?with_genres=X`
- `test_get_section_anime_always_uses_discover`
- `test_get_section_trending_empty_when_filtered`
- `test_get_genres_merges_movie_and_tv_lists`
- `test_genres_endpoint_cached`

### Frontend

- `npm run build` (runs `tsc`) as type-check gate.
- Manual verification: page loads, sections appear progressively, filter changes update rows, card click navigates to Detail.

## Out of scope (future iterations)

- Infinite scroll / load more per row
- Scroll arrow buttons on row edges
- Watchlist / favorites
- Backdrop hero banner at top of page
- Custom section configuration by user
- Year filter and rating filter (only genre/type/sort for v1)
