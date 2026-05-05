# Implementation Plan: WebSocket Download Tracking

## Step 1: Backend — DownloadWorker broadcast

**File:** `backend/app/services/download_worker.py`

### 1a. Add `broadcast_callback` to constructor

```python
def __init__(self, broadcast_callback=None):
    self.broadcast_callback = broadcast_callback
```

### 1b. Add `_download_to_dict` static method

Convert Download SQLAlchemy model to JSON-safe dict:

```python
@staticmethod
def _download_to_dict(download: Download) -> dict:
    return {
        "id": download.id,
        "tmdb_id": download.tmdb_id,
        "title": download.title,
        "type": download.type.value if download.type else None,
        "season": download.season,
        "episode": download.episode,
        "torrent_name": download.torrent_name,
        "torrent_hash": download.torrent_hash,
        "magnet_link": download.magnet_link,
        "quality": download.quality,
        "language_preference": download.language_preference,
        "status": download.status.value if download.status else None,
        "progress": download.progress,
        "speed": download.speed,
        "eta": download.eta,
        "source_folder": download.source_folder,
        "destination_folder": download.destination_folder,
        "indexer_used": download.indexer_used,
        "error_message": download.error_message,
        "created_at": download.created_at.isoformat() if download.created_at else None,
        "updated_at": download.updated_at.isoformat() if download.updated_at else None,
        "completed_at": download.completed_at.isoformat() if download.completed_at else None,
    }
```

### 1c. Call broadcast after db.commit() in _sync_progress

After each `db.commit()` inside the loop, add:

```python
if self.broadcast_callback:
    await self.broadcast_callback({
        "type": "download_update",
        "data": self._download_to_dict(download)
    })
```

Note: this should happen AFTER `_organize_completed_download` when status changes to COMPLETED.

---

## Step 2: Backend — main.py wiring

**File:** `backend/app/main.py`

In `lifespan()`, change:
```python
download_worker = DownloadWorker()
```
To:
```python
download_worker = DownloadWorker(broadcast_callback=manager.broadcast)
```

---

## Step 3: Frontend — useWebSocket hook

**File:** `frontend/src/hooks/useWebSocket.ts` (new)

```typescript
interface UseWebSocketReturn {
  lastMessage: any | null;
  readyState: number;
  sendMessage: (data: any) => void;
}
```

Logic:
- Module-level variables: `ws`, `listeners`, `reconnectTimer`, `pingTimer`
- On first `useWebSocket()` call → create connection
- On connection open → reset reconnect delay, start ping interval
- On message → parse JSON, set `lastMessage`, notify all hook instances
- On close → schedule reconnect with backoff
- On unmount of last listener → cleanup (close WS, clear timers)
- `sendMessage` → call `ws.send(JSON.stringify(data))`

Implementation detail — use a subscription pattern:
- Single WebSocket instance
- Each hook call registers a listener callback
- On message, call all listener callbacks
- Track reference count to cleanup on last unmount

---

## Step 4: Frontend — useDownloadUpdates hook

**File:** `frontend/src/hooks/useDownloadUpdates.ts` (new)

```typescript
export function DownloadUpdates() {
  const { lastMessage } = useWebSocket();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!lastMessage) return;
    if (lastMessage.type !== 'download_update') return;

    const updatedDownload = lastMessage.data;
    queryClient.setQueryData(['downloads'], (old: any[]) => {
      if (!Array.isArray(old)) return old;
      const index = old.findIndex((d: any) => d.id === updatedDownload.id);
      if (index >= 0) {
        const next = [...old];
        next[index] = updatedDownload;
        return next;
      }
      return [updatedDownload, ...old];
    });
  }, [lastMessage, queryClient]);
}
```

This is a component, not a hook (renders null, side-effect only).

---

## Step 5: Frontend — Downloads.tsx integration

**File:** `frontend/src/pages/Downloads.tsx`

Changes:
1. Import `DownloadUpdates` from the hook
2. Render `<DownloadUpdates />` inside the component (before any content)
3. Remove `refetchInterval: 5000` from `useQuery`

---

## Step 6: Verify

```bash
# Frontend
cd frontend && npm run build   # tsc + vite build

# Backend tests
cd backend && source venv/bin/activate && pytest tests/ -v
```

## Step 7: Deploy

```bash
docker compose up -d --build
```
