# Streaming Filter on Discover Page — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a streaming service dropdown filter to the `/discover` page, using TMDB's `with_watch_providers` to show content available on Netflix, Amazon Prime, Disney+, etc.

**Architecture:** The backend exposes a static provider list endpoint and accepts `watch_provider_id` in existing discover routes. When set, incompatible sections (now-playing, upcoming, trending) are omitted from the catalog, and all remaining sections use TMDB's `/discover` endpoint with `with_watch_providers` and `watch_region=BR`. The frontend adds a provider dropdown to the existing filter bar.

**Tech Stack:** FastAPI + Pydantic + httpx (backend), React + TypeScript + TanStack Query + Axios (frontend)

---

### Task 1: Add `watch_provider_id` to `DiscoverParams` and add `StreamingProvider` model

**Files:**
- Modify: `backend/app/models/discover.py:9-12`

- [ ] **Step 1: Add `watch_provider_id` field to `DiscoverParams`**

```python
class DiscoverParams(BaseModel):
    genre_id: Optional[int] = None
    media_type: Optional[str] = None  # "movie" | "series" | "anime"
    sort_by: str = "popularity.desc"
    watch_provider_id: Optional[int] = None
```

- [ ] **Step 2: Add `StreamingProvider` model at end of file**

```python
class StreamingProvider(BaseModel):
    id: int
    name: str
    logo_path: Optional[str] = None
```

- [ ] **Step 3: Run existing tests to verify model change is backward-compatible**

Run: `cd backend && source venv/bin/activate && pytest tests/test_discover.py -v`
Expected: All tests pass (new optional field should not break existing tests)

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/discover.py
git commit -m "feat: add watch_provider_id to DiscoverParams and StreamingProvider model"
```

---

### Task 2: Update `DiscoverService` — provider list, cache key, and filter detection

**Files:**
- Modify: `backend/app/services/discover_service.py:4-4` (imports)
- Modify: `backend/app/services/discover_service.py:62-65` (_filters_active and _cache_key)

- [ ] **Step 1: Add `STREAMING_PROVIDERS` constant after `ANIME_GENRE_ID` (line 42)**

```python
STREAMING_PROVIDERS = [
    {"id": 8, "name": "Netflix", "logo_path": None},
    {"id": 119, "name": "Amazon Prime Video", "logo_path": None},
    {"id": 337, "name": "Disney+", "logo_path": None},
    {"id": 384, "name": "HBO Max", "logo_path": None},
    {"id": 350, "name": "Apple TV+", "logo_path": None},
    {"id": 307, "name": "Globoplay", "logo_path": None},
    {"id": 531, "name": "Paramount+", "logo_path": None},
]
```

- [ ] **Step 2: Update `_filters_active` to consider `watch_provider_id`**

Replace (line 61-62):
```python
    def _filters_active(self, params: DiscoverParams) -> bool:
        return params.genre_id is not None or params.media_type is not None
```

With:
```python
    def _filters_active(self, params: DiscoverParams) -> bool:
        return params.genre_id is not None or params.media_type is not None or params.watch_provider_id is not None
```

- [ ] **Step 3: Update `_cache_key` to include `watch_provider_id`**

Replace (line 64-65):
```python
    def _cache_key(self, section_id: str, params: DiscoverParams) -> str:
        return f"{section_id}:{params.genre_id}:{params.media_type}:{params.sort_by}"
```

With:
```python
    def _cache_key(self, section_id: str, params: DiscoverParams) -> str:
        return f"{section_id}:{params.genre_id}:{params.media_type}:{params.sort_by}:{params.watch_provider_id}"
```

- [ ] **Step 4: Run tests to verify no regressions**

Run: `cd backend && source venv/bin/activate && pytest tests/test_discover.py -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/discover_service.py
git commit -m "feat: update filter detection and cache key for watch_provider_id"
```

---

### Task 3: Update `_fetch_tmdb` to inject `with_watch_providers` + `watch_region=BR`

**Files:**
- Modify: `backend/app/services/discover_service.py:126-127` (query dict construction)

- [ ] **Step 1: Add `with_watch_providers` and `watch_region` to discover queries**

After line 127 (`query: dict = {**common, "sort_by": params.sort_by}`), insert:

```python
            # Streaming provider
            if params.watch_provider_id:
                query["with_watch_providers"] = str(params.watch_provider_id)
                query["watch_region"] = "BR"
```

- [ ] **Step 2: Add `StreamingProvider` import at top of file**

Add to the import block at line 6-12:
```python
from app.models.discover import (
    DiscoverParams,
    SectionInfo,
    SectionCatalog,
    DiscoverSection,
    Genre,
    StreamingProvider,
)
```

- [ ] **Step 3: Run tests**

Run: `cd backend && source venv/bin/activate && pytest tests/test_discover.py -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/discover_service.py
git commit -m "feat: inject with_watch_providers and watch_region in discover queries"
```

---

### Task 4: Update section catalog to omit incompatible sections when streaming filter is active

**Files:**
- Modify: `backend/app/services/discover_service.py:67-71` (get_sections_catalog)

- [ ] **Step 1: Add streaming-incompatible section filtering**

Replace `get_sections_catalog` (lines 67-71):
```python
    def get_sections_catalog(self, params: DiscoverParams) -> SectionCatalog:
        sections = list(SECTION_DEFS)
        if self._filters_active(params):
            sections = [s for s in sections if s.id != "trending"]
        return SectionCatalog(sections=sections)
```

With:
```python
    STREAMING_INCOMPATIBLE_SECTIONS = {"now-playing", "upcoming", "trending"}

    def get_sections_catalog(self, params: DiscoverParams) -> SectionCatalog:
        sections = list(SECTION_DEFS)
        if params.watch_provider_id:
            sections = [s for s in sections if s.id not in self.STREAMING_INCOMPATIBLE_SECTIONS]
        elif self._filters_active(params):
            sections = [s for s in sections if s.id != "trending"]
        return SectionCatalog(sections=sections)
```

- [ ] **Step 2: Run tests to verify catalog filtering**

Run: `cd backend && source venv/bin/activate && pytest tests/test_discover.py -v`
Expected: Existing catalog tests still pass; we haven't written streaming-specific tests yet

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/discover_service.py
git commit -m "feat: omit now-playing, upcoming, trending when streaming filter active"
```

---

### Task 5: Add `GET /api/discover/providers/` endpoint and update existing endpoints

**Files:**
- Modify: `backend/app/routers/discover.py:6-6` (imports)
- Modify: `backend/app/routers/discover.py:12-24` (get_sections_catalog params)
- Modify: `backend/app/routers/discover.py:27-33` (get_section params)
- Add: new endpoint at end of file

- [ ] **Step 1: Add `StreamingProvider` to imports**

Replace line 6:
```python
from app.models.discover import SectionCatalog, DiscoverSection, Genre, DiscoverParams
```

With:
```python
from app.models.discover import SectionCatalog, DiscoverSection, Genre, DiscoverParams, StreamingProvider
```

- [ ] **Step 2: Add `watch_provider_id` query param to `get_sections_catalog`**

Replace lines 13-17:
```python
async def get_sections_catalog(
    genre_id: Optional[int] = Query(None),
    media_type: Optional[str] = Query(None, pattern="^(movie|series|anime)$"),
    sort_by: str = Query("popularity.desc"),
):
```

With:
```python
async def get_sections_catalog(
    genre_id: Optional[int] = Query(None),
    media_type: Optional[str] = Query(None, pattern="^(movie|series|anime)$"),
    sort_by: str = Query("popularity.desc"),
    watch_provider_id: Optional[int] = Query(None),
):
```

- [ ] **Step 3: Pass `watch_provider_id` when constructing `DiscoverParams` in `get_sections_catalog`**

Replace line 21:
```python
        params = DiscoverParams(genre_id=genre_id, media_type=media_type, sort_by=sort_by)
```

With:
```python
        params = DiscoverParams(genre_id=genre_id, media_type=media_type, sort_by=sort_by, watch_provider_id=watch_provider_id)
```

- [ ] **Step 4: Add `watch_provider_id` query param to `get_section`**

Replace lines 29-33:
```python
async def get_section(
    section_id: str,
    genre_id: Optional[int] = Query(None),
    media_type: Optional[str] = Query(None, pattern="^(movie|series|anime)$"),
    sort_by: str = Query("popularity.desc"),
):
```

With:
```python
async def get_section(
    section_id: str,
    genre_id: Optional[int] = Query(None),
    media_type: Optional[str] = Query(None, pattern="^(movie|series|anime)$"),
    sort_by: str = Query("popularity.desc"),
    watch_provider_id: Optional[int] = Query(None),
):
```

- [ ] **Step 5: Pass `watch_provider_id` to `DiscoverParams` in `get_section`**

Replace line 37:
```python
        params = DiscoverParams(genre_id=genre_id, media_type=media_type, sort_by=sort_by)
```

With:
```python
        params = DiscoverParams(genre_id=genre_id, media_type=media_type, sort_by=sort_by, watch_provider_id=watch_provider_id)
```

- [ ] **Step 6: Add providers endpoint at end of file (after line 54)**

```python
@router.get("/providers/", response_model=List[StreamingProvider])
async def get_providers():
    """Return the list of supported streaming providers."""
    from app.services.discover_service import STREAMING_PROVIDERS
    return [StreamingProvider(**p) for p in STREAMING_PROVIDERS]
```

- [ ] **Step 7: Run tests**

Run: `cd backend && source venv/bin/activate && pytest tests/test_discover.py -v`
Expected: All existing tests pass

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/discover.py
git commit -m "feat: add /api/discover/providers/ endpoint and watch_provider_id param"
```

---

### Task 6: Write backend tests for streaming filter

**Files:**
- Modify: `backend/tests/test_discover.py`

- [ ] **Step 1: Add test for `GET /api/discover/providers/` endpoint**

Add at end of file (before any class definitions):

```python
@pytest.mark.anyio
async def test_get_providers():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/providers/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 7
    provider_ids = [p["id"] for p in data]
    assert 8 in provider_ids  # Netflix
    assert 119 in provider_ids  # Amazon
    assert 337 in provider_ids  # Disney+
    for p in data:
        assert "id" in p
        assert "name" in p
```

- [ ] **Step 2: Add test for section catalog omitting streaming-incompatible sections**

Add:

```python
@pytest.mark.anyio
async def test_get_sections_catalog_with_streaming_omits_incompatible():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/discover/sections/", params={"watch_provider_id": 8})

    assert response.status_code == 200
    data = response.json()
    section_ids = [s["id"] for s in data["sections"]]
    assert "trending" not in section_ids
    assert "now-playing" not in section_ids
    assert "upcoming" not in section_ids
    assert "popular-movies" in section_ids
    assert "popular-series" in section_ids
    assert len(data["sections"]) == 10
```

- [ ] **Step 3: Add test for section fetch with streaming filter using discover endpoint**

Add:

```python
@pytest.mark.anyio
async def test_section_with_watch_provider_uses_discover(mock_discover_http):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/discover/sections/popular-movies/",
            params={"watch_provider_id": 8}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "popular-movies"
    assert len(data["results"]) > 0
```

- [ ] **Step 4: Add test for `DiscoverParams` with `watch_provider_id`**

Add to `TestDiscoverParams` class:

```python
    def test_with_watch_provider(self):
        p = DiscoverParams(watch_provider_id=8)
        assert p.watch_provider_id == 8
        assert p.genre_id is None
```

- [ ] **Step 5: Run the new tests**

Run: `cd backend && source venv/bin/activate && pytest tests/test_discover.py -v -k "providers or streaming or watch_provider"`
Expected: 4 tests pass

- [ ] **Step 6: Run full test suite to ensure no regressions**

Run: `cd backend && source venv/bin/activate && pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/tests/test_discover.py
git commit -m "test: add streaming filter tests for providers, catalog, and discover routing"
```

---

### Task 7: Update frontend TypeScript types

**Files:**
- Modify: `frontend/src/types/index.ts:89-93` (DiscoverParams)
- Add: after line 109 (StreamingProvider)

- [ ] **Step 1: Add `watch_provider_id` to `DiscoverParams`**

Replace (lines 89-93):
```typescript
export interface DiscoverParams {
  genre_id?: number | null
  media_type?: string | null
  sort_by?: string
}
```

With:
```typescript
export interface DiscoverParams {
  genre_id?: number | null
  media_type?: string | null
  sort_by?: string
  watch_provider_id?: number | null
}
```

- [ ] **Step 2: Add `StreamingProvider` type**

Add after Genre interface (after line 109):

```typescript
export interface StreamingProvider {
  id: number
  name: string
  logo_path: string | null
}
```

- [ ] **Step 3: Run frontend typecheck**

Run: `cd frontend && npm run build`
Expected: TypeScript compilation succeeds (may show unused import warnings from other files — those are pre-existing)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add StreamingProvider type and watch_provider_id to DiscoverParams"
```

---

### Task 8: Update frontend API client

**Files:**
- Modify: `frontend/src/services/api.ts:102-116`

- [ ] **Step 1: Add `watch_provider_id` to `getSections` and `getSection` params**

Replace `discoverAPI` (lines 102-116):
```typescript
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

With:
```typescript
export const discoverAPI = {
  getSections: (params?: {
    genre_id?: number | null;
    media_type?: string | null;
    sort_by?: string;
    watch_provider_id?: number | null;
  }) => api.get('/discover/sections/', { params }),

  getSection: (id: string, params?: {
    genre_id?: number | null;
    media_type?: string | null;
    sort_by?: string;
    watch_provider_id?: number | null;
  }) => api.get(`/discover/sections/${id}/`, { params }),

  getGenres: () => api.get('/discover/genres/'),

  getProviders: () => api.get<Array<{ id: number; name: string; logo_path: string | null }>>('/discover/providers/'),
};
```

- [ ] **Step 2: Run frontend typecheck**

Run: `cd frontend && npm run build`
Expected: TypeScript compilation succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat: add getProviders to discoverAPI and watch_provider_id param"
```

---

### Task 9: Update `DiscoverFilterBar` with streaming provider dropdown

**Files:**
- Modify: `frontend/src/components/DiscoverFilterBar.tsx`

- [ ] **Step 1: Add `StreamingProvider` import and props**

Replace lines 1-3:
```typescript
import React from 'react';
import { Select, SelectItem } from './ui/select';
import { Genre } from '../types';
```

With:
```typescript
import React from 'react';
import { Select, SelectItem } from './ui/select';
import { Genre, StreamingProvider } from '../types';
```

- [ ] **Step 2: Add streaming filter props to interface**

Replace lines 18-26:
```typescript
interface DiscoverFilterBarProps {
  genreId: number | null;
  mediaType: string | null;
  sortBy: string;
  genres: Genre[];
  onGenreChange: (genreId: number | null) => void;
  onMediaTypeChange: (mediaType: string | null) => void;
  onSortChange: (sortBy: string) => void;
}
```

With:
```typescript
interface DiscoverFilterBarProps {
  genreId: number | null;
  mediaType: string | null;
  watchProviderId: number | null;
  sortBy: string;
  genres: Genre[];
  providers: StreamingProvider[];
  onGenreChange: (genreId: number | null) => void;
  onMediaTypeChange: (mediaType: string | null) => void;
  onWatchProviderChange: (providerId: number | null) => void;
  onSortChange: (sortBy: string) => void;
}
```

- [ ] **Step 3: Update component destructuring**

Replace lines 28-36:
```typescript
export const DiscoverFilterBar: React.FC<DiscoverFilterBarProps> = ({
  genreId,
  mediaType,
  sortBy,
  genres,
  onGenreChange,
  onMediaTypeChange,
  onSortChange,
}) => {
```

With:
```typescript
export const DiscoverFilterBar: React.FC<DiscoverFilterBarProps> = ({
  genreId,
  mediaType,
  watchProviderId,
  sortBy,
  genres,
  providers,
  onGenreChange,
  onMediaTypeChange,
  onWatchProviderChange,
  onSortChange,
}) => {
```

- [ ] **Step 4: Add streaming provider dropdown between media type and sort selects**

After the media type `<Select>` block (line 68 closing `</Select>`) and before the sort `<Select>` block (line 70 opening `<Select`), insert:

```jsx
      <Select
        value={watchProviderId ?? ''}
        onChange={(e) => {
          const val = e.target.value;
          onWatchProviderChange(val ? Number(val) : null);
        }}
        className="w-48"
      >
        <SelectItem value="">Todos os streamings</SelectItem>
        {providers.map((p) => (
          <SelectItem key={p.id} value={String(p.id)}>
            {p.name}
          </SelectItem>
        ))}
      </Select>
```

- [ ] **Step 5: Run frontend typecheck**

Run: `cd frontend && npm run build`
Expected: Error — `DiscoverPage` still doesn't pass the new props (expected, fixed in next task)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/DiscoverFilterBar.tsx
git commit -m "feat: add streaming provider dropdown to DiscoverFilterBar"
```

---

### Task 10: Update `DiscoverPage` to integrate streaming filter

**Files:**
- Modify: `frontend/src/pages/Discover.tsx`

- [ ] **Step 1: No import changes needed — `DiscoverParams` and `SectionInfo` already imported**

(The `StreamingProvider` type is used implicitly through TanStack Query's inferred return types; no explicit import needed.)

- [ ] **Step 2: Add state for `watchProviderId`**

After line 12 (`const [sortBy, setSortBy] = useState('popularity.desc');`), add:

```typescript
  const [watchProviderId, setWatchProviderId] = useState<number | null>(null);
```

- [ ] **Step 3: Include `filters` in the catalog query key so it refetches when streaming provider changes**

Replace lines 17-18:
```typescript
    queryKey: ['discover', 'sections'],
```

With:
```typescript
    queryKey: ['discover', 'sections', filters],
```

- [ ] **Step 4: Fetch providers on page load**

After the genres `useQuery` block (line 31 `});`), add:

```typescript
  const { data: providers } = useQuery({
    queryKey: ['discover', 'providers'],
    queryFn: async () => {
      const res = await discoverAPI.getProviders();
      return res.data;
    },
    staleTime: 60 * 60 * 1000,
  });
```

- [ ] **Step 5: Update `filters` object to include `watch_provider_id`**

Replace line 14:
```typescript
  const filters: DiscoverParams = { genre_id: genreId, media_type: mediaType, sort_by: sortBy };
```

With:
```typescript
  const filters: DiscoverParams = { genre_id: genreId, media_type: mediaType, sort_by: sortBy, watch_provider_id: watchProviderId };
```

- [ ] **Step 6: Update `DiscoverFilterBar` usage to pass new props**

Replace lines 49-57:
```jsx
      <DiscoverFilterBar
        genreId={genreId}
        mediaType={mediaType}
        sortBy={sortBy}
        genres={genres ?? []}
        onGenreChange={setGenreId}
        onMediaTypeChange={setMediaType}
        onSortChange={setSortBy}
      />
```

With:
```jsx
      <DiscoverFilterBar
        genreId={genreId}
        mediaType={mediaType}
        watchProviderId={watchProviderId}
        sortBy={sortBy}
        genres={genres ?? []}
        providers={providers ?? []}
        onGenreChange={setGenreId}
        onMediaTypeChange={setMediaType}
        onWatchProviderChange={setWatchProviderId}
        onSortChange={setSortBy}
      />
```

- [ ] **Step 7: Run frontend typecheck and build**

Run: `cd frontend && npm run build`
Expected: TypeScript compilation and Vite build succeed

- [ ] **Step 8: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: No new linting errors

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/Discover.tsx
git commit -m "feat: integrate streaming provider filter in Discover page"
```

---

### Task 11: Final verification

- [ ] **Step 1: Run backend test suite**

Run: `cd backend && source venv/bin/activate && pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Run frontend build (acts as test + typecheck)**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 3: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: No lint errors
