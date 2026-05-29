# Trailer Feature on Media Detail Page

**Date:** 2026-05-29
**Status:** approved

## Summary

Add trailer playback to the media detail page. Users can watch YouTube trailers via an embedded player in a modal overlay. The Info tab becomes the first and default tab, with a trailer button in the hero section.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Trailer source | TMDB Videos API | Already integrated, no extra API key, reliable official trailers |
| Display method | Modal overlay (shadcn Dialog) | Non-disruptive, consistent with project patterns |
| Tab order | Info first, Torrents second | User flow: browse content → decide → download |
| Default tab | Info | User sees synopsis and trailer first |
| Button position | Hero section (below title/genres) | High visibility, natural placement |
| No trailer available | Disabled button with message | Clear feedback without clutter |
| Video priority | Trailer > Teaser > first available | Official trailers preferred |

## Data Flow

```
User opens /detail/movie/1439930
  │
  ├─ Frontend calls GET /api/search/movie/1439930
  │
  ▼
Backend Search Router
  │
  ├─ TMDBService.get_movie_detail(id)
  │    └─ TMDB API (/movie/{id}?append_to_response=credits,external_ids,videos)
  │
  ├─ Enrich with RT data (existing)
  │
  └─ Return TMDBDetail (now includes videos field)
       │
       ▼
Frontend (Detail.tsx)
  │
  ├─ Extract trailerKey from media.videos
  │    └─ Filter: site === 'YouTube' && (type === 'Trailer' || type === 'Teaser')
  │    └─ Prioritize: type === 'Trailer' first
  │    └─ Result: YouTube video key or null
  │
  ├─ Hero section: trailer button
  │    ├─ Has key → "▶ Trailer" button → opens modal
  │    └─ No key → "Trailer não disponível" (disabled)
  │
  └─ Modal: iframe YouTube embed
       └─ https://www.youtube.com/embed/{key}?autoplay=1
```

## Backend Changes

### Modified: `backend/app/services/tmdb_service.py`

Add `videos` to `append_to_response` in both `get_movie_detail()` and `get_tv_detail()`:

```python
# Line 66 (get_movie_detail) and line 82 (get_tv_detail)
"append_to_response": "credits,external_ids,videos"
```

### Modified: `backend/app/models/tmdb.py`

Add `videos` field to `TMDBDetail`:

```python
videos: Optional[dict] = None
```

No new endpoints needed. The TMDB API returns video data as part of the detail response when `videos` is in `append_to_response`.

## Frontend Changes

### Modified: `frontend/src/types/index.ts`

Add `videos` field to `TMDBDetail`:

```typescript
videos?: {
  results?: Array<{
    key: string;      // YouTube video ID
    site: string;     // "YouTube"
    type: string;     // "Trailer", "Teaser", "Clip", etc.
    name: string;     // Display name
  }>;
};
```

### Modified: `frontend/src/pages/Detail.tsx`

**1. Default tab → `'info'`:**

```typescript
const [activeTab, setActiveTab] = useState<'torrents' | 'info'>('info');
```

**2. Reorder tabs (Info first, Torrents second):**

```tsx
{/* Info tab button first */}
<button onClick={() => setActiveTab('info')} ...>
  <Info className="w-4 h-4 inline mr-1" />
  Informações
</button>
{/* Torrents tab button second */}
<button onClick={() => setActiveTab('torrents')} ...>
  <Play className="w-4 h-4 inline mr-1" />
  Torrents
</button>
```

**3. Trailer key extraction (memoized):**

```typescript
const trailerKey = useMemo(() => {
  const videos = media?.videos?.results;
  if (!videos?.length) return null;

  const youtubeVideos = videos.filter(v => v.site === 'YouTube');
  const trailers = youtubeVideos.filter(v => v.type === 'Trailer');
  const teasers = youtubeVideos.filter(v => v.type === 'Teaser');

  return trailers[0]?.key || teasers[0]?.key || youtubeVideos[0]?.key || null;
}, [media]);
```

**4. Trailer button in hero section (below genres line):**

```tsx
{/* After the RT rating section, add trailer button */}
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

**5. Trailer modal state:**

```typescript
const [trailerOpen, setTrailerOpen] = useState(false);
```

**6. Modal component (at the end of the JSX, using shadcn Dialog):**

```tsx
<Dialog open={trailerOpen} onOpenChange={setTrailerOpen}>
  <DialogContent className="sm:max-w-[800px] p-0 bg-black border-none">
    <DialogHeader className="sr-only">
      <DialogTitle>Trailer - {media.display_title}</DialogTitle>
    </DialogHeader>
    <div className="relative w-full" style={{ paddingTop: '56.25%' }}>
      <iframe
        src={`https://www.youtube.com/embed/${trailerKey}?autoplay=1`}
        className="absolute inset-0 w-full h-full"
        allow="autoplay; encrypted-media"
        allowFullScreen
        title={`Trailer - ${media.display_title}`}
      />
    </div>
  </DialogContent>
</Dialog>
```

## UI Layout (After Changes)

```
┌─────────────────────────────────────────────┐
│  ← Voltar                                   │
├─────────────────────────────────────────────┤
│  ┌──────────────────────────────────────┐   │
│  │  [Backdrop Image]                    │   │
│  │  [Poster]  Title                     │   │
│  │           2024 • Action, Drama       │   │
│  │           Synopsis text...           │   │
│  │           🍅 94% RT                  │   │
│  │           [▶ Trailer]                │   │  ← NEW
│  └──────────────────────────────────────┘   │
│                                             │
│  [Informações] [Torrents]                   │  ← REORDERED
│  ─────────────────────────────              │
│  (Info content - default)                   │
│  (Torrents content - second)                │
└─────────────────────────────────────────────┘
```

## Error Handling

- TMDB returns no videos → `trailerKey` is null → disabled button shown
- TMDB videos array empty → same as above
- YouTube embed fails → iframe shows YouTube's default error (acceptable)
- Modal close → `setTrailerOpen(false)` stops playback (iframe removed from DOM)

## Testing

- Verify `videos` field is returned from TMDB detail endpoints
- Verify trailer key selection logic (Trailer > Teaser > first available)
- Verify disabled button renders when no trailer exists
- Verify modal opens/closes correctly
- Verify tab order and default tab behavior
- Frontend: `npm run build` (TypeScript compilation)

## Files Modified

| File | Change |
|------|--------|
| `backend/app/services/tmdb_service.py` | Add `videos` to `append_to_response` |
| `backend/app/models/tmdb.py` | Add `videos: Optional[dict] = None` to `TMDBDetail` |
| `frontend/src/types/index.ts` | Add `videos` type to `TMDBDetail` |
| `frontend/src/pages/Detail.tsx` | Reorder tabs, default to Info, add trailer button + modal |
