# Trailer Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add trailer playback to the media detail page using TMDB Videos API with a modal YouTube embed.

**Architecture:** Extend the existing TMDB detail response to include video data, then add a trailer button and modal player to the Detail page. Minimal backend changes (append `videos` to existing API call), frontend handles trailer selection and display.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript/TanStack Query (frontend), shadcn/ui Dialog (modal), YouTube iframe embed

---

## File Map

| File | Change | Responsibility |
|------|--------|----------------|
| `backend/app/models/tmdb.py` | Add `videos` field | Data model for TMDB response |
| `backend/app/services/tmdb_service.py` | Add `videos` to `append_to_response` | Fetch video data from TMDB |
| `frontend/src/types/index.ts` | Add `videos` type | TypeScript type definition |
| `frontend/src/pages/Detail.tsx` | Reorder tabs, add trailer button + modal | UI implementation |

---

### Task 1: Add `videos` field to backend TMDB model

**Files:**
- Modify: `backend/app/models/tmdb.py:48`

- [ ] **Step 1: Add `videos` field to `TMDBDetail`**

In `backend/app/models/tmdb.py`, add the `videos` field after `seasons`:

```python
class TMDBDetail(BaseModel):
    # ... existing fields ...
    seasons: Optional[List[dict]] = None
    videos: Optional[dict] = None  # TMDB videos (trailers, teasers)
```

- [ ] **Step 2: Verify model loads correctly**

Run: `cd backend && python -c "from app.models.tmdb import TMDBDetail; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/tmdb.py
git commit -m "feat: add videos field to TMDBDetail model"
```

---

### Task 2: Enable video fetching in TMDB service

**Files:**
- Modify: `backend/app/services/tmdb_service.py:66`
- Modify: `backend/app/services/tmdb_service.py:82`

- [ ] **Step 1: Add `videos` to `append_to_response` in `get_movie_detail`**

In `backend/app/services/tmdb_service.py`, line 66, change:

```python
"append_to_response": "credits,external_ids"
```

to:

```python
"append_to_response": "credits,external_ids,videos"
```

- [ ] **Step 2: Add `videos` to `append_to_response` in `get_tv_detail`**

In `backend/app/services/tmdb_service.py`, line 82, make the same change:

```python
"append_to_response": "credits,external_ids,videos"
```

- [ ] **Step 3: Verify the change**

Run: `cd backend && python -c "from app.services.tmdb_service import TMDBService; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/tmdb_service.py
git commit -m "feat: enable video fetching in TMDB service"
```

---

### Task 3: Add `videos` type to frontend TypeScript types

**Files:**
- Modify: `frontend/src/types/index.ts:37`

- [ ] **Step 1: Add `videos` type to `TMDBDetail` interface**

In `frontend/src/types/index.ts`, add after `rt_url`:

```typescript
export interface TMDBDetail {
  // ... existing fields ...
  rt_url?: string;
  videos?: {
    results?: Array<{
      key: string;
      site: string;
      type: string;
      name: string;
    }>;
  };
}
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add videos type to TMDBDetail interface"
```

---

### Task 4: Reorder tabs and set Info as default in Detail page

**Files:**
- Modify: `frontend/src/pages/Detail.tsx:14`
- Modify: `frontend/src/pages/Detail.tsx:228-247`

- [ ] **Step 1: Change default tab from `'torrents'` to `'info'`**

In `frontend/src/pages/Detail.tsx`, line 14, change:

```typescript
const [activeTab, setActiveTab] = useState<'torrents' | 'info'>('torrents');
```

to:

```typescript
const [activeTab, setActiveTab] = useState<'torrents' | 'info'>('info');
```

- [ ] **Step 2: Reorder tab buttons (Info first, Torrents second)**

In `frontend/src/pages/Detail.tsx`, replace lines 228-247 (the tab buttons section) with:

```tsx
<div className="flex gap-4 border-b border-border/50">
  <button
    onClick={() => setActiveTab('info')}
    className={`pb-2 text-sm font-medium transition-colors ${
      activeTab === 'info' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground'
    }`}
  >
    <Info className="w-4 h-4 inline mr-1" />
    Informações
  </button>
  <button
    onClick={() => setActiveTab('torrents')}
    className={`pb-2 text-sm font-medium transition-colors ${
      activeTab === 'torrents' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground'
    }`}
  >
    <Play className="w-4 h-4 inline mr-1" />
    Torrents
  </button>
</div>
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Detail.tsx
git commit -m "feat: reorder tabs and set Info as default"
```

---

### Task 5: Add trailer key extraction and modal state

**Files:**
- Modify: `frontend/src/pages/Detail.tsx:1-8` (imports)
- Modify: `frontend/src/pages/Detail.tsx:14-20` (state)

- [ ] **Step 1: Add `Dialog` import**

In `frontend/src/pages/Detail.tsx`, add to the imports at the top:

```typescript
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
```

- [ ] **Step 2: Add trailer modal state**

After the existing state declarations (around line 20), add:

```typescript
const [trailerOpen, setTrailerOpen] = useState(false);
```

- [ ] **Step 3: Add `trailerKey` memo**

After the `effectiveQueryWithSuffix` useMemo (around line 128), add:

```typescript
const trailerKey = useMemo(() => {
  const videos = media?.videos?.results;
  if (!videos?.length) return null;

  const youtubeVideos = videos.filter((v: { site: string }) => v.site === 'YouTube');
  const trailers = youtubeVideos.filter((v: { type: string }) => v.type === 'Trailer');
  const teasers = youtubeVideos.filter((v: { type: string }) => v.type === 'Teaser');

  return trailers[0]?.key || teasers[0]?.key || youtubeVideos[0]?.key || null;
}, [media]);
```

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Detail.tsx
git commit -m "feat: add trailer key extraction and modal state"
```

---

### Task 6: Add trailer button to hero section

**Files:**
- Modify: `frontend/src/pages/Detail.tsx:208-222` (RT rating section)

- [ ] **Step 1: Add trailer button after RT rating section**

In `frontend/src/pages/Detail.tsx`, after the RT rating block (after line 222, before the closing `</div>` of the flex-1 div), add:

```tsx
<div className="flex items-center gap-3 mt-3">
  {trailerKey ? (
    <button
      onClick={() => setTrailerOpen(true)}
      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/20 text-primary hover:bg-primary/30 transition-colors text-sm font-medium"
    >
      <Play className="w-4 h-4" />
      Trailer
    </button>
  ) : (
    <span className="flex items-center gap-2 px-4 py-2 rounded-xl bg-muted text-muted-foreground text-sm font-medium cursor-not-allowed">
      <Play className="w-4 h-4" />
      Trailer não disponível
    </span>
  )}
</div>
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Detail.tsx
git commit -m "feat: add trailer button to hero section"
```

---

### Task 7: Add trailer modal component

**Files:**
- Modify: `frontend/src/pages/Detail.tsx:500-501` (before closing tags)

- [ ] **Step 1: Add trailer modal at the end of the JSX**

In `frontend/src/pages/Detail.tsx`, just before the final closing `</div>` and `};` (around line 500), add:

```tsx
{/* Trailer Modal */}
<Dialog open={trailerOpen} onOpenChange={setTrailerOpen}>
  <DialogContent className="sm:max-w-[800px] p-0 bg-black border-none">
    <DialogHeader className="sr-only">
      <DialogTitle>Trailer - {media.display_title}</DialogTitle>
    </DialogHeader>
    <div className="relative w-full" style={{ paddingTop: '56.25%' }}>
      {trailerKey && (
        <iframe
          src={`https://www.youtube.com/embed/${trailerKey}?autoplay=1`}
          className="absolute inset-0 w-full h-full"
          allow="autoplay; encrypted-media"
          allowFullScreen
          title={`Trailer - ${media.display_title}`}
        />
      )}
    </div>
  </DialogContent>
</Dialog>
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Detail.tsx
git commit -m "feat: add trailer modal with YouTube embed"
```

---

### Task 8: Final verification

**Files:**
- None (verification only)

- [ ] **Step 1: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: No errors

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Run backend tests**

Run: `cd backend && pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 4: Verify the feature manually**

1. Start backend: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to a movie detail page (e.g., `/detail/movie/1439930`)
4. Verify: Info tab is default, trailer button appears in hero
5. Click trailer button → modal opens with YouTube embed
6. Close modal → returns to page
7. Navigate to a movie with no trailer → disabled button shows "Trailer não disponível"

- [ ] **Step 5: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "feat: trailer feature complete"
```
