# Watched, Watchlist, and Recommendations

**Date:** 2026-05-31
**Status:** approved

## Summary

Add three tightly-scoped, single-user features on top of the existing TMDB integration:

1. **Watched** — manually mark a movie or whole TV series as watched.
2. **Watchlist** — manually add/remove a movie or whole TV series to a personal watchlist, with a dedicated `/watchlist` page.
3. **Recommendations on the detail page** — show a small row of TMDB suggestions (similar ∪ recommendations) on the detail page, excluding anything in the user's watched, watchlist, or already-completed downloads.

Source of truth is in-house: a new `user_lists` Postgres table. We do not sync to TMDB's account API.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| User model | Single-user (no `user_id`, no auth) | Current app has no auth; one operator household. |
| Watched granularity | Movie / whole TV series (no per-episode) | Simplest, matches watchlist granularity. |
| Watchlist granularity | Movie / whole TV series | Same. |
| When to mark watched | Manual only | No auto on download completion. Keeps download flow untouched. |
| Recommendation algorithm | TMDB pure: `/{id}/similar` ∪ `/{id}/recommendations`, deduped by tmdb_id+media_type | No scoring layer needed; both endpoints are pre-curated by TMDB. |
| Recommendation exclusion set | watched ∪ watchlist ∪ downloads_completed (unified media-type) | Avoids suggesting the same thing the user just finished or already wants. |
| Where to show recommendations | Only on the Detail page | Discover page is for exploration; recs are contextual to a title. |
| Watchlist auto-populate from downloads | No | Manual only — predictable, easy to test. |
| Where toggle buttons appear | Only on the Detail page (not on `MediaCard`) | Avoids clutter in grids; one focused place for "I've seen this" / "Save for later". |
| Dedicated pages | Only `/watchlist` (no `/watched` page) | Watched has no need to be browsed as a list right now. |
| Schema shape | Single `user_lists` table with a `kind` column | Watched and watchlist are the same shape; one table beats two. |
| Source of truth | In-house Postgres | No TMDB account, no sync complexity. |

## Data Model

### New table: `user_lists`

```python
# backend/app/models/user_list.py
import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, Enum, CheckConstraint, UniqueConstraint
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
    media_type = Column(String(16), nullable=False)  # "movie" | "series" | "anime"
    tmdb_id = Column(Integer, nullable=False, index=True)
    title = Column(String(500), nullable=False)     # hydrated from TMDB, kept fresh-ish
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

Notes:
- One row per `(tmdb_id, media_type, kind)` triple. Adding a movie to the watchlist twice is a no-op.
- `media_type` matches the `ContentType` enum in `app/models/download.py` (the same `movie/series/anime` vocabulary already used across the app).
- `title` and poster/backdrop are denormalized for fast list rendering; they are re-hydrated on GET if a row was added without them.

### Alembic migration

New file: `backend/alembic/versions/<rev>_add_user_lists.py`

```python
def upgrade() -> None:
    op.create_table(
        "user_lists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.Enum("watched", "watchlist", name="listkind"), nullable=False),
        sa.Column("media_type", sa.String(length=16), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("poster_path", sa.String(length=255)),
        sa.Column("backdrop_path", sa.String(length=255)),
        sa.Column("year", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_user_lists_tmdb_id", "user_lists", ["tmdb_id"])
    op.create_unique_constraint(
        "uq_user_lists_tmdb_type_kind",
        "user_lists",
        ["tmdb_id", "media_type", "kind"],
    )
    op.create_check_constraint(
        "ck_user_lists_media_type",
        "user_lists",
        "media_type IN ('movie','series','anime')",
    )


def downgrade() -> None:
    op.drop_table("user_lists")
```

`down_revision` chains off the latest existing migration (currently `3a33a45e80a0`).

## Backend

### New service: `app/services/list_service.py`

Thin wrapper over `UserList` so the routers stay declarative and easy to test.

```python
class ListService:
    def __init__(self, db: Session):
        self.db = db

    def get_status(self, media_type: str, tmdb_id: int) -> dict:
        """Return {watched: bool, watchlist: bool} for the given content."""
        ...

    def add(self, kind: ListKind, media_type: str, tmdb_id: int, *, title: str,
            poster_path: str | None, backdrop_path: str | None, year: int | None) -> UserList:
        """Idempotent. If the row already exists, refreshes the denormalized fields and returns it."""
        ...

    def remove(self, kind: ListKind, media_type: str, tmdb_id: int) -> bool:
        """Returns True if a row was deleted, False if nothing matched."""
        ...

    def list_watchlist(self) -> list[UserList]:
        """All watchlist rows, newest first."""
        ...

    def list_watched(self) -> list[UserList]:
        """All watched rows, newest first."""
        ...

    def excluded_tmdb_ids(self, media_type: str) -> set[int]:
        """tmdb_ids to exclude from recommendations for this media_type.
        watched ∪ watchlist (in this media_type) ∪ completed downloads."""
        ...
```

`excluded_tmdb_ids` joins `user_lists` with the `downloads` table (filtered by `status = COMPLETED` and matching `type`) so recs skip anything the user already owns.

### New service: `app/services/recommendation_service.py`

```python
class RecommendationService:
    """Wraps TMDBService with a 1h in-memory cache per (media_type, tmdb_id)."""

    def __init__(self, db: Session, tmdb: TMDBService):
        self.db = db
        self.tmdb = tmdb
        self._cache: dict[tuple[str, int], tuple[float, list[dict]]] = {}

    async def get_recommendations(
        self, media_type: str, tmdb_id: int, *, limit: int = 10
    ) -> list[dict]:
        """
        1. Hit cache; return if fresh (< 1h).
        2. Fetch similar + recommendations from TMDB in parallel.
        3. Normalize each result into the same shape as TMDBSearchResult.
        4. Dedupe by (tmdb_id, media_type), dropping the source item.
        5. Exclude ids returned by ListService.excluded_tmdb_ids(media_type).
        6. Truncate to `limit`, cache for 1h, return.
        """
        ...

    async def _fetch_union(self, media_type: str, tmdb_id: int) -> list[dict]:
        """Call /similar and /recommendations concurrently, return combined raw list."""
        ...
```

Cache TTL: 3600 seconds. Key: `(media_type, tmdb_id)`. On any new add/remove in `user_lists`, the cache is not invalidated — recs re-render within an hour, which is fine.

### Extensions to `app/services/tmdb_service.py`

Four new async methods (re-using the existing `httpx.AsyncClient`):

```python
async def get_similar_movies(self, movie_id: int) -> list[dict]:
    """GET /movie/{id}/similar — returns the raw 'results' list."""

async def get_similar_tv(self, tv_id: int) -> list[dict]:
    """GET /tv/{id}/similar."""

async def get_recommendations_movies(self, movie_id: int) -> list[dict]:
    """GET /movie/{id}/recommendations."""

async def get_recommendations_tv(self, tv_id: int) -> list[dict]:
    """GET /tv/{id}/recommendations."""
```

All four accept the standard `api_key`, `language=pt-BR`, and forward `response.raise_for_status()`.

### New router: `app/routers/lists.py`

Prefix: `/api/lists`. All endpoints use `trailing_slash=True` (per project convention) and return JSON.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/status/{media_type}/{tmdb_id}/` | Status check used by the detail page to set the initial toggle state. |
| POST | `/{kind}/{media_type}/{tmdb_id}/` | Add to `kind` ∈ {`watched`, `watchlist`}. Body: `null` (server hydrates from TMDB). |
| DELETE | `/{kind}/{media_type}/{tmdb_id}/` | Remove from `kind`. 204 on success, 404 if nothing matched. |
| GET | `/watchlist/` | All watchlist rows. |
| GET | `/watched/` | All watched rows (kept for parity; not yet exposed in the UI). |

`POST` body for hydration (sent by the client because the router doesn't have the TMDB data cached yet, and we want to avoid one extra round-trip from the frontend on toggle):

```json
{
  "title": "Inception",
  "poster_path": "/abc.jpg",
  "backdrop_path": null,
  "year": 2010
}
```

The body is optional; if the client omits it, the router calls `TMDBService.get_movie_detail` / `get_tv_detail` to hydrate (single round-trip, in addition to the detail page's own call).

```python
# backend/app/routers/lists.py
router = APIRouter(prefix="/api/lists", tags=["lists"])


class ListItemPayload(BaseModel):
    title: str
    poster_path: str | None = None
    backdrop_path: str | None = None
    year: int | None = None


@router.get("/status/{media_type}/{tmdb_id}/")
def get_status(media_type: str, tmdb_id: int, db: Session = Depends(get_db)):
    if media_type not in {"movie", "series", "anime"}:
        raise HTTPException(status_code=400, detail="invalid media_type")
    return ListService(db).get_status(media_type, tmdb_id)


@router.post("/{kind}/{media_type}/{tmdb_id}/", status_code=204)
async def add_item(
    kind: ListKind,
    media_type: str,
    tmdb_id: int,
    payload: ListItemPayload | None = None,
    db: Session = Depends(get_db),
):
    if media_type not in {"movie", "series", "anime"}:
        raise HTTPException(status_code=400, detail="invalid media_type")
    if payload is None:
        # hydrate from TMDB
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
            raise HTTPException(status_code=502, detail=f"TMDB hydration failed: {exc}")
        finally:
            await tmdb.close()
    ListService(db).add(kind, media_type, tmdb_id, **payload.model_dump())
    return Response(status_code=204)


@router.delete("/{kind}/{media_type}/{tmdb_id}/", status_code=204)
def remove_item(kind: ListKind, media_type: str, tmdb_id: int, db: Session = Depends(get_db)):
    if media_type not in {"movie", "series", "anime"}:
        raise HTTPException(status_code=400, detail="invalid media_type")
    deleted = ListService(db).remove(kind, media_type, tmdb_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="not in list")
    return Response(status_code=204)


@router.get("/watchlist/", response_model=list[UserList])
def get_watchlist(db: Session = Depends(get_db)):
    return ListService(db).list_watchlist()


@router.get("/watched/", response_model=list[UserList])
def get_watched(db: Session = Depends(get_db)):
    return ListService(db).list_watched()
```

### New router: `app/routers/recommendations.py`

Prefix: `/api/recommendations`.

```python
@router.get("/{media_type}/{tmdb_id}/", response_model=list[dict])
async def get_recommendations(
    media_type: str,
    tmdb_id: int,
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    if media_type not in {"movie", "series", "anime"}:
        raise HTTPException(status_code=400, detail="invalid media_type")
    # series + anime both map to "tv" on TMDB
    tmdb_media_type = "movie" if media_type == "movie" else "tv"
    tmdb = TMDBService(db=db)
    try:
        service = RecommendationService(db=db, tmdb=tmdb)
        return await service.get_recommendations(tmdb_media_type, tmdb_id, limit=limit)
    finally:
        await tmdb.close()
```

The frontend never has to think about the `tv` vs `series` mapping; the router normalizes.

### Wire-in

`backend/app/main.py`:

```python
from app.routers import search, downloads, settings, logs, filesystem, discover, lists, recommendations

app.include_router(lists.router)
app.include_router(recommendations.router)
```

## Frontend

### Types — `frontend/src/types/index.ts`

Append:

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

### API client — `frontend/src/services/api.ts`

Add a new export alongside the existing ones:

```typescript
export const listsAPI = {
  getStatus: (mediaType: UserMediaType, tmdbId: number) =>
    api.get<ListStatus>(`/lists/status/${mediaType}/${tmdbId}/`),

  add: (
    kind: ListKind,
    mediaType: UserMediaType,
    tmdbId: number,
    payload?: { title: string; poster_path: string | null; backdrop_path: string | null; year: number | null },
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

`mapMediaType` continues to handle the `tv` → `series` direction; the new APIs take `UserMediaType` directly.

### New component: `frontend/src/components/MediaActions.tsx`

Two pill buttons that show the current watched/watchlist state and toggle on click. Used only on the detail page hero.

```typescript
// shape, not full implementation
interface MediaActionsProps {
  mediaType: UserMediaType;
  tmdbId: number;
  title: string;
  posterPath: string | null;
  backdropPath: string | null;
  year: number | null;
}

export const MediaActions: React.FC<MediaActionsProps> = ({ ... }) => {
  const queryClient = useQueryClient();
  const { data: status } = useQuery({
    queryKey: ['list-status', mediaType, tmdbId],
    queryFn: () => listsAPI.getStatus(mediaType, tmdbId).then(r => r.data),
  });

  const toggle = useMutation({
    mutationFn: async (kind: ListKind) => {
      const inList = status?.[kind] ?? false;
      if (inList) {
        await listsAPI.remove(kind, mediaType, tmdbId);
      } else {
        await listsAPI.add(kind, mediaType, tmdbId, {
          title, poster_path: posterPath, backdrop_path: backdropPath, year,
        });
      }
    },
    onSuccess: (_, kind) => {
      toast.success(kind === 'watched' ? 'Marcado como visto' : 'Adicionado à watchlist');
      queryClient.invalidateQueries({ queryKey: ['list-status', mediaType, tmdbId] });
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : 'Falha ao atualizar lista'),
  });

  return (
    <div className="flex items-center gap-2 mt-3">
      <button
        onClick={() => toggle.mutate('watchlist')}
        disabled={toggle.isPending}
        className={/* pill, Bookmark icon, primary tint when active */}
      >
        <Bookmark className="w-4 h-4" />
        {status?.watchlist ? 'Na watchlist' : 'Watchlist'}
      </button>
      <button
        onClick={() => toggle.mutate('watched')}
        disabled={toggle.isPending}
        className={/* pill, Eye icon, primary tint when active */}
      >
        <Eye className="w-4 h-4" />
        {status?.watched ? 'Visto' : 'Marcar como visto'}
      </button>
    </div>
  );
};
```

### New component: `frontend/src/components/RecommendationsRow.tsx`

Loads `/api/recommendations/...` for the current detail item and renders a horizontally-scrolling strip using the existing `MediaCard` shape (or a lightweight in-file card — see below). Shown below the tabs, regardless of which tab is active. If the list is empty (or the request fails), the section renders nothing — never an error block on a page that otherwise works.

```typescript
interface RecommendationsRowProps {
  mediaType: UserMediaType;
  tmdbId: number;
}

export const RecommendationsRow: React.FC<RecommendationsRowProps> = ({ mediaType, tmdbId }) => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['recommendations', mediaType, tmdbId],
    queryFn: () => recommendationsAPI.get(mediaType, tmdbId, 10).then(r => r.data),
    staleTime: 60 * 60 * 1000, // 1h — matches backend cache
  });

  if (isLoading || isError || !data || data.length === 0) return null;

  return (
    <section className="space-y-3">
      <h3 className="font-display text-lg font-bold text-foreground">Recomendações</h3>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {data.map((rec) => <RecommendationCard key={`${rec.media_type}-${rec.id}`} item={rec} />)}
      </div>
    </section>
  );
};
```

`RecommendationCard` is a small inline card (poster + title + year) — a stripped-down version of `MediaCard` so we don't pull in the full grid behavior. Each card links to `/detail/movie/{id}` or `/detail/tv/{id}` based on `rec.media_type`.

### Modifications: `frontend/src/pages/Detail.tsx`

1. Import `MediaActions` and `RecommendationsRow`.
2. Pass the `effectiveMediaType` and the relevant poster/title/year to `MediaActions`, mount it next to the trailer button in the hero.
3. After the tab content (after the closing `</div>` of the tabs), mount `<RecommendationsRow mediaType={effectiveMediaType} tmdbId={tmdbId} />`.

No changes to the tab structure, the trailer modal, or the torrent flow.

### New page: `frontend/src/pages/Watchlist.tsx`

Renders the user's watchlist in a grid (re-using the same poster-card style). Empty state: a friendly message pointing to the Search and Discover pages.

```typescript
const WatchlistPage: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => listsAPI.listWatchlist().then(r => r.data),
  });

  if (isLoading) return <SkeletonGrid />;

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-20 space-y-3">
        <Bookmark className="w-12 h-12 mx-auto text-muted-foreground" />
        <p className="text-muted-foreground">Sua watchlist está vazia.</p>
        <Link to="/discover" className="text-primary hover:underline">Explorar títulos</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl font-bold">Watchlist</h1>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {data.map((item) => <WatchlistCard key={item.id} item={item} />)}
      </div>
    </div>
  );
};
```

`WatchlistCard` shows the poster, title, year, and a small "Remover" button that calls `listsAPI.remove('watchlist', ...)` and invalidates the `['watchlist']` query. Card click navigates to the corresponding detail page.

### Modifications: `frontend/src/components/Header.tsx`

Add a "Watchlist" entry to `navItems` between "Downloads" and "Settings":

```typescript
{ path: '/watchlist', icon: Bookmark, label: 'Watchlist' },
```

`Bookmark` is added to the lucide-react import.

### Modifications: `frontend/src/App.tsx`

```typescript
import WatchlistPage from './pages/Watchlist';

<Route path="/watchlist" element={<WatchlistPage />} />
```

## Data Flows

### Toggle a list item (watched or watchlist)

```
User clicks button on Detail.tsx
  │
  ▼
React Query mutation in MediaActions.toggle(kind)
  │
  ├─ inList === true  → DELETE /api/lists/{kind}/{media_type}/{tmdb_id}/
  └─ inList === false → POST   /api/lists/{kind}/{media_type}/{tmdb_id}/  (with payload)
  │
  ▼
Backend router → ListService.add / .remove → user_lists table
  │
  ▼
On success:
  - Invalidate ['list-status', mediaType, tmdbId]  → button label updates
  - Invalidate ['watchlist']                       → Watchlist page re-renders on next visit
  - toast.success
```

### View watchlist

```
User navigates to /watchlist
  │
  ▼
Watchlist.tsx useQuery → GET /api/lists/watchlist/
  │
  ▼
ListService.list_watchlist() → SELECT * FROM user_lists WHERE kind='watchlist' ORDER BY created_at DESC
  │
  ▼
Frontend renders grid of WatchlistCard
```

### View recommendations on Detail

```
User opens /detail/movie/1439930
  │
  ▼
Detail.tsx mounts <RecommendationsRow>
  │
  ▼
GET /api/recommendations/movie/1439930/?limit=10
  │
  ▼
Backend router:
  1. Build ListService, fetch excluded ids (watched ∪ watchlist ∪ COMPLETED downloads for media_type=movie)
  2. Check cache; if fresh, return cached list minus excluded ids
  3. Otherwise: TMDBService.get_similar_movies + get_recommendations_movies (asyncio.gather)
  4. Normalize, dedupe, exclude, truncate, cache
  │
  ▼
Frontend renders horizontal scroller (skips on empty/error)
```

## Error Handling

- **POST without payload when TMDB is down:** router returns 502 `TMDB hydration failed: <reason>`. Frontend surfaces a generic toast; the button stays in its previous state.
- **DELETE for a row that no longer exists:** router returns 404 `not in list`. Frontend treats this as success (idempotent feel) and invalidates the cache.
- **Recommendations fail (TMDB 5xx, network):** the `RecommendationsRow` returns `null` — the detail page still works. No toast.
- **Recommendations return 0 results after exclusion:** the section is hidden, no empty state.
- **DB integrity error on duplicate insert:** the `UniqueConstraint` makes the insert fail. The router catches it and returns the existing row instead (effectively idempotent). Implementation detail: `ListService.add` first does a `SELECT`, and only inserts if missing.
- **Invalid `media_type` or `kind`:** FastAPI's path validation returns 422 (Pydantic) or 400 (the manual checks in the router).
- **Migration on a DB with existing data:** pure `CREATE TABLE`, no backfill needed.

## Caching

| Where | What | TTL | Invalidation |
|-------|------|-----|--------------|
| Backend `RecommendationService._cache` | list of normalized recommendations for `(media_type, tmdb_id)` | 1h | never explicit; expires on TTL |
| Frontend `useQuery` for `['recommendations', ...]` | same | 1h via `staleTime: 60 * 60 * 1000` | never explicit |
| Frontend `useQuery` for `['list-status', ...]` | `{ watched, watchlist }` | 0 (always fresh) | invalidated after every toggle |
| Frontend `useQuery` for `['watchlist']` | watchlist rows | 0 | invalidated after every toggle (so the watchlist page reflects changes) |

## Testing Strategy

Tests live in `backend/tests/`, mirroring the file-per-module convention.

### `test_list_service.py` (new)
- `add` is idempotent: calling it twice creates one row, returns the same id, and refreshes denormalized fields on the second call.
- `remove` returns `True` for a present row, `False` for an absent one.
- `get_status` reflects the current `watched` and `watchlist` state.
- `list_watchlist` / `list_watched` return only rows of the requested `kind`, newest first.
- `excluded_tmdb_ids('movie')` returns the union of watched, watchlist, and `COMPLETED` download tmdb_ids where `downloads.type == 'movie'`. Other media types and statuses are not included.

### `test_recommendation_service.py` (new)
- Hits both `get_similar_movies` and `get_recommendations_movies` in parallel — verified by patching the TMDBService to record call order.
- Dedupe by `(tmdb_id, media_type)` — fixture returns the same id from both endpoints; assert the result has one entry.
- Source id is filtered out if TMDB includes it in similar/recommendations.
- Excluded ids (from `ListService.excluded_tmdb_ids`) are filtered out.
- Cache hit: second call within TTL does not re-hit TMDB.
- Result length is capped at `limit`.

### `test_lists_router.py` (new)
- `GET /api/lists/status/movie/1/` returns `{watched: false, watchlist: false}` on a fresh DB.
- `POST /api/lists/watchlist/movie/1/` with a payload creates a row; a second call is a no-op (204 either way, one row in DB).
- `POST /api/lists/watchlist/movie/1/` without a payload but with TMDB patched returns 204 and hydrates the row from the TMDB detail.
- `DELETE /api/lists/watchlist/movie/1/` returns 204 when present, 404 when absent.
- `GET /api/lists/watchlist/` returns only `watchlist` rows.
- Invalid `media_type` returns 400.
- Invalid `kind` (e.g. `kind=favorite`) returns 422 from Pydantic.

### `test_recommendations_router.py` (new)
- Returns at most `limit` items.
- Returns the exclusion-filtered list (asserts a known watched id is missing from the response).
- 400 on invalid `media_type`.

### Frontend
- `npm run build` (which runs `tsc && vite build`) must pass with no new errors. This is the project's de-facto TS check (see `frontend/package.json`).
- The implementation must not introduce any new ESLint warnings (`npm run lint` clean).

## Files Touched

### New
- `backend/app/models/user_list.py`
- `backend/app/services/list_service.py`
- `backend/app/services/recommendation_service.py`
- `backend/app/routers/lists.py`
- `backend/app/routers/recommendations.py`
- `backend/alembic/versions/<rev>_add_user_lists.py`
- `backend/tests/test_list_service.py`
- `backend/tests/test_recommendation_service.py`
- `backend/tests/test_lists_router.py`
- `backend/tests/test_recommendations_router.py`
- `frontend/src/components/MediaActions.tsx`
- `frontend/src/components/RecommendationsRow.tsx`
- `frontend/src/pages/Watchlist.tsx`

### Modified
- `backend/app/services/tmdb_service.py` — add the four similar/recommendations methods
- `backend/app/main.py` — register the two new routers
- `frontend/src/types/index.ts` — new interfaces
- `frontend/src/services/api.ts` — `listsAPI` and `recommendationsAPI` exports
- `frontend/src/pages/Detail.tsx` — mount `MediaActions` and `RecommendationsRow`
- `frontend/src/components/Header.tsx` — Watchlist nav item
- `frontend/src/App.tsx` — `/watchlist` route

## Out of Scope

- Multi-user support, authentication, per-user lists.
- Syncing to TMDB's account/watchlist API.
- Per-episode watched tracking.
- Auto-marking watched on download completion.
- Editing list items (rename, change cover). Lists are add/remove only.
- A dedicated `/watched` browse page (the data is still returned by `GET /api/lists/watched/` for future use).
- Importing/exporting lists.
