# Clear All Downloads — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Clear all" button on the Downloads page that deletes all completed/failed/cancelled download records from the database and removes corresponding torrents from qBittorrent (keeping files on disk). Active downloads (pending/downloading) are skipped.

**Architecture:** New `DELETE /api/downloads/` bulk endpoint on the existing downloads router. Frontend adds a `clearMutation` in the Downloads page and a confirmation Dialog + button in the DownloadMonitor component.

**Tech Stack:** FastAPI, SQLAlchemy, React + TanStack Query, shadcn/ui (Dialog, Button), sonner (toast)

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/routers/downloads.py:229` | Modify | Add `delete_all_downloads` endpoint |
| `backend/tests/test_routers.py:314` | Modify | Add test cases for the new endpoint |
| `frontend/src/services/api.ts:78` | Modify | Add `clearDownloads()` API method |
| `frontend/src/components/DownloadMonitor.tsx:16` | Modify | Add `onClear` prop and clear button with confirmation Dialog |
| `frontend/src/pages/Downloads.tsx:77` | Modify | Add `clearMutation`, wire `onClear` handler |

---

### Task 1: Backend — `DELETE /api/downloads/` endpoint

**Files:**
- Modify: `backend/app/routers/downloads.py`
- Test: `backend/tests/test_routers.py`

- [ ] **Step 1: Write failing tests**

Add to the `TestDownloadsRouter` class in `backend/tests/test_routers.py`:

```python
    def test_clear_all_downloads(self, client, db_session):
        """Test clearing all completed/failed downloads, skipping active."""
        # Add a completed download
        completed = Download(
            tmdb_id=1,
            title="Completed Movie",
            type=ContentType.MOVIE,
            torrent_name="Test Movie 1080p",
            torrent_hash="abc123abc123abc123abc123abc123abc123abc1",
            status=DownloadStatus.COMPLETED,
        )
        # Add a failed download
        failed = Download(
            tmdb_id=2,
            title="Failed Movie",
            type=ContentType.MOVIE,
            torrent_name="Bad Movie",
            status=DownloadStatus.FAILED,
            error_message="Something went wrong",
        )
        # Add an active download (should be skipped)
        active = Download(
            tmdb_id=3,
            title="Active Movie",
            type=ContentType.MOVIE,
            torrent_name="Downloading Movie",
            torrent_hash="def456def456def456def456def456def456def4",
            status=DownloadStatus.DOWNLOADING,
        )
        db_session.add_all([completed, failed, active])
        db_session.commit()

        with patch('app.routers.downloads.QBittorrentService') as mock_service_class:
            mock_instance = mock_service_class.return_value
            mock_instance.delete_torrent = AsyncMock(return_value=True)
            mock_instance.close = AsyncMock()
            response = client.delete("/api/downloads/")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == 2
        assert data["skipped"] == 1

        # Verify only active remains
        remaining = db_session.query(Download).all()
        assert len(remaining) == 1
        assert remaining[0].status == DownloadStatus.DOWNLOADING

        # Verify qBittorrent delete_torrent was called for completed (not failed, no hash)
        mock_instance.delete_torrent.assert_awaited_once_with("abc123abc123abc123abc123abc123abc123abc1", delete_files=False)
        mock_instance.close.assert_awaited_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && pytest tests/test_routers.py::TestDownloadsRouter::test_clear_all_downloads -v`
Expected: FAIL with 405 or 404 (endpoint not yet added)

- [ ] **Step 3: Implement the endpoint**

Add at the end of `backend/app/routers/downloads.py` (after line 229):

```python
@router.delete("/")
async def delete_all_downloads(db: Session = Depends(get_db)):
    """Delete all completed, failed, and cancelled downloads. Skips active downloads.
    Removes torrents from qBittorrent but keeps files on disk."""
    
    # Count active downloads that will be skipped
    active_count = db.query(Download).filter(
        Download.status.in_([DownloadStatus.PENDING, DownloadStatus.DOWNLOADING])
    ).count()
    
    # Get all removable downloads
    removable = db.query(Download).filter(
        Download.status.not_in([DownloadStatus.PENDING, DownloadStatus.DOWNLOADING])
    ).all()
    
    # Remove torrents from qBittorrent (keep files)
    service = QBittorrentService()
    for download in removable:
        if download.torrent_hash:
            try:
                await service.delete_torrent(download.torrent_hash, delete_files=False)
            except Exception:
                logger.warning(
                    "Failed to remove torrent from qBittorrent",
                    download_id=download.id,
                    torrent_hash=download.torrent_hash,
                )
    await service.close()
    
    # Delete all removable records in a single query
    deleted_count = db.query(Download).filter(
        Download.status.not_in([DownloadStatus.PENDING, DownloadStatus.DOWNLOADING])
    ).delete(synchronize_session=False)
    
    db.commit()
    
    logger.info("Cleared downloads", deleted=deleted_count, skipped=active_count)
    return {"deleted": deleted_count, "skipped": active_count}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && pytest tests/test_routers.py::TestDownloadsRouter::test_clear_all_downloads -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `cd backend && source venv/bin/activate && pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 6: Commit backend changes**

```bash
git add backend/app/routers/downloads.py backend/tests/test_routers.py
git commit -m "feat: add DELETE /api/downloads/ endpoint to clear all non-active downloads"
```

---

### Task 2: Frontend — API client

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Add `clearDownloads` method**

Add inside the `downloadAPI` object in `frontend/src/services/api.ts`, after line 77 (`resumeDownload`):

```ts
  clearDownloads: () =>
    api.delete('/downloads/'),
```

- [ ] **Step 2: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds (might fail on unused code until wired up — that's fine, proceed)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat: add clearDownloads API method"
```

---

### Task 3: Frontend — DownloadMonitor clear button + Dialog

**Files:**
- Modify: `frontend/src/components/DownloadMonitor.tsx`

- [ ] **Step 1: Add `onClear` prop and update interface**

Change the `DownloadMonitorProps` interface (line 11-16):

```tsx
interface DownloadMonitorProps {
  downloads: DownloadType[];
  onPause: (id: number) => void;
  onResume: (id: number) => void;
  onCancel: (id: number) => void;
  onClear: () => void;
}
```

- [ ] **Step 2: Add imports for Dialog, Button, and toast**

Add to the imports at the top (lines 1-9):

```tsx
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
```

Also need `DialogFooter` in the Dialog import (line 5-9):

```tsx
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
```

- [ ] **Step 3: Add clear confirmation state and handler**

Add after the existing `useState` (after line 33, before `if (downloads.length === 0)`):

```tsx
  const [clearDialogOpen, setClearDialogOpen] = useState(false);

  const clearableCount = downloads.filter(
    (d) => d.status !== 'pending' && d.status !== 'downloading'
  ).length;
```

- [ ] **Step 4: Add clear button above the download list**

Replace the `if (downloads.length === 0)` block return with:

```tsx
  if (downloads.length === 0) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center mx-auto mb-6">
          <Download className="w-10 h-10 text-muted-foreground/40" />
        </div>
        <p className="text-xl font-display font-bold mb-2">Nenhum download ativo</p>
        <p className="text-sm">Vá para a página de busca para adicionar downloads</p>
      </div>
    );
  }
```

No change needed to this part — the button goes in the main return. Add before the `<div className="space-y-4">`:

```tsx
  return (
    <div className="space-y-4">
      {clearableCount > 0 && (
        <div className="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setClearDialogOpen(true)}
            className="text-muted-foreground hover:text-red-400 hover:border-red-400/30"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Limpar todos ({clearableCount})
          </Button>
        </div>
      )}
```

Wait — the current return already starts with `<div className="space-y-4">`. I need to insert the clear button between the return statement and the `{downloads.map(...)}` call.

So in the main `return` block at line 47-48, insert after `<div className="space-y-4">`:

```tsx
      {clearableCount > 0 && (
        <div className="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setClearDialogOpen(true)}
            className="text-muted-foreground hover:text-red-400 hover:border-red-400/30"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Limpar todos ({clearableCount})
          </Button>
        </div>
      )}
```

- [ ] **Step 5: Add confirmation Dialog**

Add right before the closing `</div>` of the main return (before the existing Detail Dialog at line 155):

```tsx
      {/* Clear confirmation Dialog */}
      <Dialog open={clearDialogOpen} onOpenChange={setClearDialogOpen}>
        <DialogContent className="glass rounded-2xl p-6 max-w-md w-full space-y-4 border-none">
          <DialogHeader>
            <DialogTitle className="font-display text-xl font-bold text-foreground">
              Limpar downloads
            </DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground text-sm">
            Isso removerá {clearableCount} download{clearableCount !== 1 ? 's' : ''} concluído{clearableCount !== 1 ? 's' : ''}, falho{clearableCount !== 1 ? 's' : ''} ou cancelado{clearableCount !== 1 ? 's' : ''} do banco de dados.
            Downloads ativos não serão afetados.
          </p>
          <p className="text-muted-foreground text-xs">
            Os arquivos baixados serão mantidos no disco.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setClearDialogOpen(false)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                setClearDialogOpen(false);
                onClear();
              }}
            >
              Limpar {clearableCount} download{clearableCount !== 1 ? 's' : ''}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
```

- [ ] **Step 6: Verify frontend typechecks**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/DownloadMonitor.tsx
git commit -m "feat: add clear all button and confirmation dialog to DownloadMonitor"
```

---

### Task 4: Frontend — Wire up mutation in Downloads page

**Files:**
- Modify: `frontend/src/pages/Downloads.tsx`

- [ ] **Step 1: Add `clearMutation`**

Add after `cancelMutation`, around line 27:

```tsx
  const clearMutation = useMutation({
    mutationFn: () => downloadAPI.clearDownloads(),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
      const result = response.data as { deleted: number; skipped: number };
      toast.success(`${result.deleted} download(s) removido(s)`);
    },
    onError: () => {
      toast.error('Erro ao limpar downloads');
    },
  });

  const handleClear = () => clearMutation.mutate();
```

- [ ] **Step 2: Add `onClear` prop to DownloadMonitor**

Add at line 68 (`<DownloadMonitor`):

```tsx
      <DownloadMonitor
        downloads={downloads?.data || []}
        onPause={handlePause}
        onResume={handleResume}
        onCancel={handleCancel}
        onClear={handleClear}
      />
```

- [ ] **Step 3: Add sonner toast import**

Add to imports (line 1):

```tsx
import { toast } from 'sonner';
```

This should already be there or added. Check line 5 — if not present, add it.

- [ ] **Step 4: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Downloads.tsx
git commit -m "feat: wire up clear all downloads mutation in Downloads page"
```

---

### Task 5: End-to-end verification

- [ ] **Step 1: Run backend tests**

Run: `cd backend && source venv/bin/activate && pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: No errors

- [ ] **Step 4: Commit final verification**

```bash
git add -A
git commit -m "chore: final verification for clear all downloads feature"
```
