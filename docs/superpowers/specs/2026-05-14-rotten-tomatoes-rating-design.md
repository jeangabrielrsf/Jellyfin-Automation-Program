# Rotten Tomatoes Rating on Media Detail Page

**Date:** 2026-05-14
**Status:** approved

## Summary

Display Rotten Tomatoes rating with a conditional tomato icon and a link to the RT page in the hero section of the media detail page (`Detail.tsx`).

## Data Flow

```
Frontend (Detail.tsx)
  │
  ├─ GET /api/search/movie/{id}  (existing)
  └─ GET /api/search/tv/{id}     (existing)
       │
       ▼
  Backend Search Router
       │
       ├─ TMDBService.get_movie_detail(id)  ──▶  TMDB API (/movie/{id})
       │   or                                    └─ append_to_response=external_ids
       ├─ TMDBService.get_tv_detail(id)     ──▶  TMDB API (/tv/{id})
       │                                         └─ append_to_response=external_ids
       │
       ├─ Extract imdb_id from external_ids
       │
       ├─ OMDbService.get_by_imdb_id(imdb_id)  ──▶  OMDB API (?i=tt...)
       │    └─ Returns Rotten Tomatoes rating from Ratings array
       │
       └─ Return TMDBDetail + new fields (imdb_id, rt_rating, rt_url)
```

## RT URL Construction

1. Build slug URL: `https://www.rottentomatoes.com/{m|tv}/{slug}`
   - Slug: `display_title` → lowercase → spaces to `_` → remove special chars
   - `m` for movies, `tv` for TV shows
2. Validate with HEAD request
3. If 200 → use slug URL; otherwise → fallback to `https://www.rottentomatoes.com/search?search={encoded_title}`

## Backend Changes

### New file: `backend/app/services/omdb_service.py`

```python
class OMDbService:
    def __init__(self, api_key: str, base_url: str = "https://www.omdbapi.com")
    async def get_by_imdb_id(self, imdb_id: str) -> dict | None
        # Calls OMDB ?i={imdb_id}
        # Returns None if request fails or no RT rating found
        # Returns { "rt_rating": "94%", "ratings": [...] }

    async def build_rt_url(self, title: str, media_type: str) -> str
        # media_type: "movie" or "tv"
        # Constructs slug URL, validates, falls back to search URL
```

### Modified: `backend/app/services/tmdb_service.py`

- Add `append_to_response=external_ids` to `get_movie_detail()` and `get_tv_detail()`

### Modified: `backend/app/models/tmdb.py`

`TMDBDetail` gains:
- `imdb_id: Optional[str] = None`
- `rt_rating: Optional[str] = None` — e.g. "94%"
- `rt_url: Optional[str] = None`

### Modified: `backend/app/routers/search.py`

In movie/TV detail endpoints:
1. After getting TMDB detail, extract `imdb_id` from external_ids
2. If `imdb_id` present, call `OMDbService.get_by_imdb_id(imdb_id)`
3. If RT rating found, call `OMDbService.build_rt_url(title, media_type)`
4. Populate `rt_rating` and `rt_url` on the response model

### Modified: `backend/app/config.py`

- Add `omdb_api_key: str` field

### Modified: `backend/.env`

- Add `OMDB_API_KEY=`

## Frontend Changes

### Modified: `frontend/src/types/index.ts`

`TMDBDetail` gains:
```typescript
rt_rating?: string;  // e.g. "94%"
rt_url?: string;     // Rotten Tomatoes page URL
```

### Modified: `frontend/src/pages/Detail.tsx`

In the hero section (between overview and genres line), add:

```tsx
{media.rt_rating && (
  <div className="flex items-center gap-2 mt-3">
    <span className="text-lg">
      {parseInt(media.rt_rating) >= 60 ? "🍅" : "💀"}
      {/* or: conditional colored tomato SVG/emoji */}
    </span>
    <a
      href={media.rt_url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-white/80 hover:text-white underline underline-offset-2"
    >
      {media.rt_rating} no Rotten Tomatoes
    </a>
  </div>
)}
```

**Tomato icon logic:**
- ≥ 60% → 🍅 (fresh/red tomato)
- < 60% → green splat emoji or styled indicator

## Error Handling

- If `imdb_id` not available from TMDB → no RT data shown (graceful skip)
- If OMDB API call fails → no RT data shown, log warning
- If RT rating not in OMDB `Ratings` array → no RT data shown
- If RT URL validation fails → fallback to search URL
- Frontend: `rt_rating` is optional; if absent, nothing renders

## Testing

- Unit tests for `OMDbService.get_by_imdb_id()` — mock OMDB responses
- Unit tests for `OMDbService.build_rt_url()` — mock HTTP HEAD responses
- Integration test for movie/TV detail endpoints with OMDB data
- Frontend: verify conditional rendering when `rt_rating` present/absent

## Environment

- `OMDB_API_KEY` — free tier, 1000 requests/day
- Obtain at: https://www.omdbapi.com/apikey.aspx
