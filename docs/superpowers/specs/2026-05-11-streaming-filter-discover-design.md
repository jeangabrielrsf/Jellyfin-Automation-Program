# Streaming Filter on Discover Page

**Date:** 2026-05-11
**Status:** Draft

## Summary

Add a streaming service filter to the `/discover` page. Users can select a service (Netflix, Amazon Prime, etc.) and all compatible sections will show only content available on that service via TMDB's `with_watch_providers` parameter.

## Motivation

The discover page currently supports filtering by genre, media type, and sort order. Users want to discover content available on specific streaming platforms.

## User Flow

1. User opens `/discover`
2. A new "Streaming" dropdown appears in the filter bar, defaulting to "All services"
3. User selects e.g. "Netflix"
4. Sections "Nos Cinemas", "Em Breve", and "Tendências" are hidden
5. All remaining sections now show only content available on Netflix
6. User can still combine with genre and media type filters (e.g. Netflix + Ação)

## Scope Limitations

- **No time interval filter.** TMDB's `/discover` endpoint supports `with_watch_providers` but has no "last week/month" parameter. TMDB's `/trending` supports time windows but not `with_watch_providers`. The two cannot be combined.
- **No watch monetization filter** (free vs paid). Keeping it simple for now.
- **Region is fixed to BR.** `watch_region=BR` is hardcoded.

## Design

### Backend

#### New Endpoint

`GET /api/discover/providers/`

Returns a static list of streaming providers:

```json
[
  { "id": 8, "name": "Netflix", "logo_path": null },
  { "id": 119, "name": "Amazon Prime Video", "logo_path": null },
  { "id": 337, "name": "Disney+", "logo_path": null },
  { "id": 384, "name": "HBO Max", "logo_path": null },
  { "id": 350, "name": "Apple TV+", "logo_path": null },
  { "id": 307, "name": "Globoplay", "logo_path": null },
  { "id": 531, "name": "Paramount+", "logo_path": null }
]
```

No TMDB API call needed — the list is static.

#### DiscoverParams Model

Add field:

```python
watch_provider_id: Optional[int] = None
```

#### DiscoverService._fetch_tmdb Logic

When `watch_provider_id` is not None:

| Section ID | Old Endpoint | New Endpoint |
|---|---|---|
| `popular-movies` | `/movie/popular` | `/discover/movie` ?sort_by=popularity.desc&with_watch_providers={id}&watch_region=BR |
| `popular-series` | `/tv/popular` | `/discover/tv` ?sort_by=popularity.desc&with_watch_providers={id}&watch_region=BR |
| `top-rated-movies` | `/movie/top_rated` | `/discover/movie` ?sort_by=vote_average.desc&with_watch_providers={id}&watch_region=BR |
| `top-rated-series` | `/tv/top_rated` | `/discover/tv` ?sort_by=vote_average.desc&with_watch_providers={id}&watch_region=BR |
| Sections already using `/discover` | `/discover/{media}` | `/discover/{media}` + `with_watch_providers` & `watch_region=BR` |

#### Section Catalog Filtering

When `watch_provider_id` is not None, omit from `SectionCatalog`:

- `now-playing` — theatrical, no streaming equivalent
- `upcoming` — theatrical, no streaming equivalent
- `trending` — uses `/trending` endpoint which does not support `with_watch_providers`

#### Cache Key

Include `watch_provider_id` in the cache key: `{section_id}:{genre_id}:{media_type}:{sort_by}:{watch_provider_id}`

### Frontend

#### DiscoverFilterBar

Add a `<select>` dropdown for streaming services, placed after the media type filter and before sort:

```
[ Genre ▼ ] [ Type ▼ ] [ Streaming ▼ ] [ Sort ▼ ]
```

- Default value: "All services" (empty/null, no filter)
- Populated from `GET /api/discover/providers/` on page load

#### Discover Page

- Pass `watch_provider_id` to `GET /api/discover/sections/{id}/` calls
- When `watch_provider_id` is set, hide incompatible section rows
- When reset to "All services", show all sections again

#### TypeScript Types

```typescript
interface DiscoverParams {
  genre_id?: number
  media_type?: 'movie' | 'series' | 'anime'
  watch_provider_id?: number
  sort_by?: string
}

interface StreamingProvider {
  id: number
  name: string
  logo_path: string | null
}
```

#### API Client

New function in `frontend/src/services/api.ts`:

```typescript
getProviders: () => request.get<StreamingProvider[]>('/api/discover/providers/')
```

## Files Changed

| File | Change |
|---|---|
| `backend/app/models/discover.py` | Add `watch_provider_id` to `DiscoverParams`; add `StreamingProvider` model |
| `backend/app/services/discover_service.py` | Provider list constant; `_fetch_tmdb` routing logic; cache key update |
| `backend/app/routers/discover.py` | New `/providers/` endpoint; section catalog filtering |
| `backend/tests/test_discover.py` | Tests for new endpoint and filter behavior |
| `frontend/src/pages/Discover.tsx` | State + provider fetch + pass param to sections; hide incompatible sections |
| `frontend/src/components/DiscoverFilterBar.tsx` | New dropdown component and props |
| `frontend/src/services/api.ts` | `getProviders` function |
| `frontend/src/types/index.ts` | `StreamingProvider` type; update `DiscoverParams` |

## Testing

- `GET /api/discover/providers/` returns list of 7 providers
- When `watch_provider_id=8`, section catalog omits `now-playing`, `upcoming`, `trending`
- When `watch_provider_id` is not set, all 13 sections are present
- `_fetch_tmdb` correctly routes to `/discover` endpoint when `watch_provider_id` is set
- Cache key varies by `watch_provider_id`
