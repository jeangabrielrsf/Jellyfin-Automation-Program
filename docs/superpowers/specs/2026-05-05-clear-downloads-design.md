# Clear All Downloads — Design

## Goal
Add a "Clear all" button on the Downloads page that deletes all completed, failed, and cancelled download records from the database, removes corresponding torrents from qBittorrent (keeping files on disk), and skips active (PENDING/DOWNLOADING) downloads.

## Backend

### New endpoint: `DELETE /api/downloads/`

**File:** `backend/app/routers/downloads.py`

**Logic:**
1. Query all downloads where `status NOT IN ('pending', 'downloading')` (i.e., completed, failed, cancelled, organized)
2. Count active downloads (pending + downloading) for the response
3. For each removable download that has a `torrent_hash`, remove it from qBittorrent with `delete_files=False`
4. Delete all removable records from DB in a single `delete()` statement
5. Return `{ deleted: N, skipped: M }`

**Response:**
```json
{ "deleted": 5, "skipped": 2 }
```

## Frontend

### API Client — `frontend/src/services/api.ts`
Add `clearDownloads()` calling `DELETE /api/downloads/`.

### Component — `frontend/src/components/DownloadMonitor.tsx`
- Add "Clear all" button in the component header area
- Uses shadcn `Dialog` for confirmation: "Are you sure you want to clear all completed, failed, and cancelled downloads? Active downloads will not be affected."
- Disable button when downloads list is empty
- On success: `toast.success()` with count of deleted downloads

### Page — `frontend/src/pages/Downloads.tsx`
- Add `clearMutation` using TanStack Query `useMutation`, invalidates `['downloads']` on success
- Pass `onClear` callback to `DownloadMonitor`

## Decisions
- Active downloads (pending/downloading) are skipped, not cancelled
- Torrents are removed from qBittorrent with `delete_files=False` (files kept)
- Confirmation via shadcn Dialog, not native `confirm()`
- Single `DELETE` to the existing `/api/downloads/` endpoint (no body needed)
