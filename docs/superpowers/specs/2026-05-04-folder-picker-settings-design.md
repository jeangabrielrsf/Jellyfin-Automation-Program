# Folder Picker for Settings Page — Design Spec

**Date:** 2026-05-04
**Status:** Approved

## Summary

Add a "Browse" button next to each media path input on the Settings page (`movies_path`, `series_path`, `animes_path`). Clicking it opens a shadcn Dialog with a navigable tree view of the server's filesystem. The user selects a folder and confirms to save the path. Additionally, refactor backend services to read media paths from the database settings table (with `.env` as fallback) so that path changes take effect immediately without restart.

## Motivation

- Current Settings page has plain text inputs for paths — user must type paths manually, error-prone
- Backend services read paths exclusively from `.env` via `get_settings()` — changing paths in the UI has no effect until `.env` is edited and the app is restarted
- WSL2 users need to browse Windows drives mounted at `/mnt/`

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Picker approach | Backend API + shadcn Dialog (Option B) | Universal browser support; shows real server paths |
| Navigation | Tree view (expand/collapse) | User sees full hierarchy at a glance |
| Save behavior | Select + Confirm button | Prevents accidental saves |
| WSL2 detection | Start at `/mnt/` if drives mounted, else `/` | Natural for WSL2 users |
| Backend sync | DB settings with `.env` fallback | Path changes take effect immediately |

## Architecture

### Backend: Filesystem Router (`backend/app/routers/filesystem.py`)

New router exposing a directory listing endpoint:

```
GET /api/filesystem/dirs?path=/mnt/c/
```

Response:
```json
{
  "path": "/mnt/c/",
  "dirs": ["Projetos", "Program Files", "Users", "Windows"],
  "parent": "/mnt/"
}
```

- `path` param: absolute directory path to list
- Returns only subdirectories (no files)
- `parent`: parent directory path, or `null` if at root
- Silently skips directories that raise `PermissionError`
- Validates `path` exists and is a directory (prevents path traversal)
- `GET /api/filesystem/root` returns the initial root path (`/` or `/mnt/` depending on WSL2 detection)

### Backend: Settings Refactor

Services (`PathResolver`, `OrganizerService`, `QbittorrentService`) currently call `get_settings()` which reads from `.env`. They need to read paths from the database settings table instead, with `.env` as fallback.

New helper in `backend/app/config.py` or a new `backend/app/services/settings_service.py`:

```python
def get_media_paths(db: Session) -> dict:
    """Return media paths from DB settings, falling back to .env."""
    db_settings = {s.key: s.value for s in db.query(Setting).all()}
    env = get_settings()
    return {
        "movies_path": db_settings.get("movies_path") or env.movies_path,
        "series_path": db_settings.get("series_path") or env.series_path,
        "animes_path": db_settings.get("animes_path") or env.animes_path,
    }
```

Services receive a `db` session and call this helper instead of `get_settings()` directly.

### Frontend: FolderPickerDialog Component

New component at `frontend/src/components/FolderPickerDialog.tsx`:

- Uses shadcn `Dialog`, `Button`
- Lazy-loads directory children on expand via `GET /api/filesystem/dirs`
- Each tree node shows folder name with expand/collapse chevron (Lucide `ChevronRight`/`ChevronDown`)
- Single-select: clicking a folder row highlights it (blue background)
- Clicking a folder name toggles expand/collapse (lazy fetch children on first expand)
- "Selecionar" button in Dialog footer saves the selected path and closes
- Breadcrumb bar at top for context
- Reusable: accepts `initialPath`, `onSelect(path)` props

### Frontend: Settings Page Changes

Each path field gains a "Browse" button (shadcn `Button variant="outline"` + Lucide `Folder` icon) next to the input. Clicking opens `FolderPickerDialog`. On confirm, the path is written to the input and `PUT /api/settings/{key}` is called (existing behavior via `onBlur`).

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `backend/app/routers/filesystem.py` | **New** | Directory listing endpoint |
| `backend/app/main.py` | Modify | Include `filesystem` router |
| `backend/app/services/path_resolver.py` | Modify | Read paths from DB, fallback `.env` |
| `backend/app/services/organizer_service.py` | Modify | Read paths from DB, fallback `.env` |
| `backend/app/services/qbittorrent_service.py` | Modify | Read paths from DB, fallback `.env` (if needed) |
| `frontend/src/components/FolderPickerDialog.tsx` | **New** | shadcn Dialog + tree view folder picker |
| `frontend/src/services/api.ts` | Modify | Add `filesystemAPI.getDirs(path)` and `filesystemAPI.getRoot()` |
| `frontend/src/pages/Settings.tsx` | Modify | Add Browse button, integrate FolderPickerDialog |

## Detailed Behavior

### Tree View
- **Lazy loading:** Children loaded on first expand via API call
- **Loading state:** Show spinner while fetching subdirectories
- **Empty state:** Show "Vazio" for directories with no subdirectories
- **Error state:** Silently skip directories that can't be read
- **Scroll:** Dialog body scrolls if tree is large; fixed header (breadcrumb) and footer (buttons)

### WSL2 Detection
- Backend checks if `/mnt/` exists and has subdirectories at startup
- `GET /api/filesystem/root` returns `{"root": "/mnt/"}` if WSL2, `{"root": "/"}` otherwise
- Frontend calls this on mount to know where to start

### Security
- `path` parameter validated: must be absolute, exist on disk, and be a directory
- No path traversal (`../` etc.)
- Only directory listing, no file content exposure

### Edge Cases
- Path longer than input width: input scrolls horizontally, Browse button stays fixed
- Very deep trees: Dialog scrolls, no max depth limit
- Network error on expand: show error icon, retry on next expand click
- Last item in tree: no ambiguity with adjacent rows

## Testing

### Backend Tests
- `GET /api/filesystem/root` returns correct root based on WSL2 presence
- `GET /api/filesystem/dirs?path=/tmp` returns subdirectories
- `GET /api/filesystem/dirs?path=/nonexistent` returns 404
- `GET /api/filesystem/dirs?path=/etc/shadow` returns 400 (not a directory, if applicable) or 403
- Path traversal attempt `?path=/etc/../../../` returns 400
- `PUT /api/settings/movies_path` with new value is reflected in subsequent `get_media_paths()` calls

### Frontend Tests
- TypeScript compilation succeeds (`npm run build` / `tsc`)
- ESLint passes (`npm run lint`)

## Dependencies

No new dependencies required. All needed libraries already in `package.json`:
- `@radix-ui/react-dialog` (already used by shadcn Dialog)
- `lucide-react` (Folder, ChevronRight, ChevronDown icons)
- `@tanstack/react-query` (existing data fetching pattern)
