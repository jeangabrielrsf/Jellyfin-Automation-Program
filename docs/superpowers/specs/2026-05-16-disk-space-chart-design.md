# Disk Space Chart — Design Doc

**Date:** 2026-05-16
**Status:** Draft

## Overview

Add a donut chart to the Settings page showing total free disk space across all unique disks hosting the configured media folders (movies, series, animes).

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Chart type | Single gauge showing total free space | User wants a high-level disk overview, not per-folder breakdown |
| Location | Settings page, near "Caminhos" section | Contextually relevant — paths are configured there |
| Chart library | `recharts` | Popular, well-maintained React chart library |
| Disk aggregation | Deduplicate by device ID, sum unique disks | Avoids double-counting when multiple paths share the same disk |
| Refresh strategy | On-demand (page load) | Simple, sufficient for disk space which changes slowly |

## Backend

### New Endpoint

`GET /api/filesystem/disk-space/`

**Logic:**
1. Read `movies_path`, `series_path`, `animes_path` from settings via `get_config()`
2. For each configured path, call `os.statvfs(path)` to get device info
3. Extract `f_fsid` (device ID) to deduplicate — paths on the same disk share the same device
4. For each unique device, sum:
   - `total = frsize * blocks`
   - `free = frsize * bavail` (space available to non-root users)
5. Return JSON:

```json
{
  "total_bytes": 1000000000000,
  "free_bytes": 400000000000,
  "used_bytes": 600000000000,
  "disks_count": 1
}
```

**Error handling:**
- If no paths configured → return `{"total_bytes": 0, "free_bytes": 0, "used_bytes": 0, "disks_count": 0}`
- If a path doesn't exist → skip it and log warning
- If all paths invalid → return zeros with 200 OK (not an error)

### File: `backend/app/routers/filesystem.py`

Add the new endpoint to the existing filesystem router.

## Frontend

### New Dependency

- `recharts` — installed via `npm install recharts`

### New Component: `DiskSpaceChart.tsx`

Location: `frontend/src/components/DiskSpaceChart.tsx`

**Structure:**
- `ResponsiveContainer` wrapping a `PieChart`
- Donut chart with two segments: "used" and "free"
- Custom label in center showing "X GB livres de Y GB"
- Tooltip with formatted values
- Loading skeleton while fetching
- Error state with message if API fails

**Data fetch:**
- TanStack Query: `useQuery({ queryKey: ['disk-space'], queryFn: filesystemAPI.getDiskSpace })`
- No auto-refetch (default staleTime)

### Integration: `Settings.tsx`

Insert the `DiskSpaceChart` component above the "Caminhos" section in the settings grid.

### API Client: `frontend/src/services/api.ts`

Add `filesystemAPI.getDiskSpace()` method.

## Testing

- Backend: Unit test for `statvfs` logic with mocked paths
- Frontend: Component renders correctly with mock data, handles loading/error states

## Risks

- **WSL2 path resolution:** `os.statvfs` works on Linux paths (`/mnt/c/...`), which is what the backend container sees. No special handling needed.
- **Recharts bundle size:** Adds ~50kb to the frontend bundle. Acceptable trade-off for chart quality.
