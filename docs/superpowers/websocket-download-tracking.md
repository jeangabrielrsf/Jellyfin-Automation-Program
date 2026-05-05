# Spec: Real-time Download Tracking via WebSocket

## Problem

Frontend polls `GET /api/downloads/` every 5s for download progress. Backend already has `ConnectionManager` with `broadcast()` but it's unused. Latency is up to 5s for progress updates.

## Goals

- Push download updates (progress, speed, ETA, status) from backend to frontend in real-time via WebSocket
- Remove HTTP polling from the frontend
- Keep all existing functionality (pause, resume, cancel) unchanged

## Non-goals

- No changes to `/ws` endpoint connection handling (ping/pong stays)
- No changes to `DownloadWorker` polling interval (10s to qBittorrent stays)
- No changes to download creation flow

## Architecture

```
qBittorrent ──10s poll──→ DownloadWorker ──broadcast──→ ConnectionManager ──WS──→ Frontend
                              │                                                      │
                              └── DB update ──→ PostgreSQL                   React Query Cache
```

### Message flow

1. `DownloadWorker._sync_progress()` fetches torrents from qBittorrent every 10s
2. For each tracked download, updates DB fields (progress, speed, eta, status)
3. Immediately broadcasts the updated download as a JSON message to all connected WebSocket clients
4. Frontend receives the message and updates React Query cache in-place
5. All components reading `['downloads']` re-render automatically

## Backend

### DownloadWorker (`backend/app/services/download_worker.py`)

- `__init__` accepts optional `broadcast_callback: Optional[Callable[[dict], Awaitable[None]]] = None`
- New `_download_to_dict(download: Download) -> dict` helper serializes a Download model to JSON-safe dict
- In `_sync_progress()`, after `db.commit()` for each download, if callback is set:
  ```python
  await self.broadcast_callback({"type": "download_update", "data": self._download_to_dict(download)})
  ```

### main.py

```python
download_worker = DownloadWorker(broadcast_callback=manager.broadcast)
```

### WebSocket message format

```json
{
  "type": "download_update",
  "data": {
    "id": 42,
    "tmdb_id": 123,
    "title": "Ted Lasso",
    "type": "series",
    "season": 1,
    "episode": null,
    "torrent_name": "Ted.Lasso.S01.1080p",
    "torrent_hash": "5a49c...",
    "magnet_link": "magnet:?...",
    "quality": "1080p",
    "language_preference": "legendado",
    "status": "downloading",
    "progress": 45.2,
    "speed": "2.5 MiB/s",
    "eta": "3m 20s",
    "source_folder": "/mnt/d/Séries/Ted Lasso/Season 01",
    "destination_folder": null,
    "indexer_used": "1337x",
    "error_message": null,
    "created_at": "2026-05-04T22:00:00",
    "updated_at": "2026-05-04T22:03:41",
    "completed_at": null
  }
}
```

All enum values serialized as strings. Datetime fields serialized as ISO 8601 strings.

## Frontend

### useWebSocket hook (`frontend/src/hooks/useWebSocket.ts`)

**Interface:**
```typescript
function useWebSocket(): {
  lastMessage: any;
  readyState: number;
  sendMessage: (data: any) => void;
}
```

**Behavior:**
- Single global connection (module-level singleton, not per-component)
- Connects to relative URL `/ws` (Vite proxy in dev, same origin via nginx in prod)
- Auto-reconnect on close with exponential backoff: 1s, 2s, 4s, 8s, max 30s
- Re-sends ping `{"type": "ping"}` every 30s to keep connection alive
- Parses JSON messages, logs errors without crashing
- `readyState` follows standard WebSocket states (0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED)

### useDownloadUpdates hook (`frontend/src/hooks/useDownloadUpdates.ts`)

**Behavior:**
- Renders nothing (side-effects only via `useEffect`)
- Uses `useWebSocket()` and `useQueryClient()`
- On `{"type": "download_update", "data": download}`:
  1. Get current `['downloads']` cache
  2. Find index of download with matching `id`
  3. If found → replace at that index
  4. If not found → prepend to array
  5. `queryClient.setQueryData(['downloads'], newList)`

### Downloads.tsx

- Render `<DownloadUpdates />` component (no visible output)
- Remove `refetchInterval: 5000` from `useQuery`

### DownloadMonitor.tsx

No changes — already reads from whatever `downloads` array is provided.

## Edge cases

| Scenario | Handling |
|----------|----------|
| WebSocket disconnected | Auto-reconnect with backoff. Cache stays frozen until reconnect + next worker cycle. |
| Page refresh / navigate away and back | Initial `useQuery` fetches fresh data via HTTP GET. WebSocket reconnects. |
| Multiple browser tabs | Each tab gets its own WS connection. No cross-tab state — React Query is per-tab. |
| Worker broadcasts while no clients connected | No-op — `broadcast()` iterates empty list. |
| Broadcast fails for one client | `ConnectionManager.broadcast()` catches exceptions and removes dead connections. |
| Download removed from qBittorrent | Worker won't match it by hash → status unchanged until next manual refresh. |
| DB fields exceed JSON size limit | Unlikely (download fields are small). If it happens, message is valid JSON. |

## Rollback

If WebSocket fails completely, data becomes stale in cache. User can navigate away and back to force HTTP refresh. Option to restore polling in future by re-adding `refetchInterval`.

## Files

| File | Change |
|------|--------|
| `backend/app/services/download_worker.py` | +broadcast_callback, +_download_to_dict |
| `backend/app/main.py` | Pass manager.broadcast to DownloadWorker |
| `frontend/src/hooks/useWebSocket.ts` | New |
| `frontend/src/hooks/useDownloadUpdates.ts` | New |
| `frontend/src/pages/Downloads.tsx` | Add DownloadUpdates, remove refetchInterval |
