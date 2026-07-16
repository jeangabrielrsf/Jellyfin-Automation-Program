# Disk Space Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a donut chart to the Settings page showing total free disk space across all unique disks hosting the configured media folders.

**Architecture:** New backend endpoint reads media paths, deduplicates by device ID using `os.statvfs`, and returns aggregated disk space. Frontend fetches data via TanStack Query and renders a donut chart using `recharts`.

**Tech Stack:** Python `os.statvfs`, FastAPI, React, TanStack Query, `recharts`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/app/routers/filesystem.py` | Add `GET /api/filesystem/disk-space/` endpoint |
| `backend/tests/test_filesystem_router.py` | Tests for the new endpoint |
| `frontend/src/services/api.ts` | Add `filesystemAPI.getDiskSpace()` |
| `frontend/src/components/DiskSpaceChart.tsx` | Donut chart component |
| `frontend/src/pages/Settings.tsx` | Integrate chart above "Caminhos" section |

---

### Task 1: Install recharts

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install recharts**

Run from `frontend/`:
```bash
npm install recharts
```

- [ ] **Step 2: Verify installation**

Check that `recharts` appears in `frontend/package.json` dependencies.

---

### Task 2: Backend — Disk Space Endpoint

**Files:**
- Modify: `backend/app/routers/filesystem.py`
- Test: `backend/tests/test_filesystem_router.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_filesystem_router.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


def test_disk_space_no_paths(client, db_session):
    """Test disk space returns zeros when no paths are configured."""
    with patch("app.routers.filesystem.get_config", return_value=""):
        response = client.get("/api/filesystem/disk-space/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_bytes"] == 0
    assert data["free_bytes"] == 0
    assert data["used_bytes"] == 0
    assert data["disks_count"] == 0


def test_disk_space_single_disk(client, db_session):
    """Test disk space returns correct values for a single disk."""
    # Mock statvfs result
    mock_statvfs = MagicMock()
    mock_statvfs.f_frsize = 4096
    mock_statvfs.f_blocks = 1000000  # 4GB total
    mock_statvfs.f_bavail = 600000   # ~2.4GB free
    mock_statvfs.f_fsid = (1, 2)     # device ID

    with patch("app.routers.filesystem.get_config") as mock_config:
        # All three paths point to the same disk
        mock_config.side_effect = lambda key, db, required=False: {
            "movies_path": "/media/movies",
            "series_path": "/media/series",
            "animes_path": "/media/animes",
        }.get(key, "")
        with patch("os.statvfs", return_value=mock_statvfs):
            response = client.get("/api/filesystem/disk-space/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_bytes"] == 4096 * 1000000
    assert data["free_bytes"] == 4096 * 600000
    assert data["used_bytes"] == data["total_bytes"] - data["free_bytes"]
    assert data["disks_count"] == 1  # deduplicated


def test_disk_space_multiple_disks(client, db_session):
    """Test disk space correctly sums multiple unique disks."""
    mock_statvfs_1 = MagicMock()
    mock_statvfs_1.f_frsize = 4096
    mock_statvfs_1.f_blocks = 1000000
    mock_statvfs_1.f_bavail = 500000
    mock_statvfs_1.f_fsid = (1, 1)

    mock_statvfs_2 = MagicMock()
    mock_statvfs_2.f_frsize = 4096
    mock_statvfs_2.f_blocks = 2000000
    mock_statvfs_2.f_bavail = 1500000
    mock_statvfs_2.f_fsid = (2, 2)

    with patch("app.routers.filesystem.get_config") as mock_config:
        mock_config.side_effect = lambda key, db, required=False: {
            "movies_path": "/media/movies",
            "series_path": "/media/series",
            "animes_path": "/media/animes",
        }.get(key, "")
        # movies and series on disk 1, animes on disk 2
        with patch("os.statvfs", side_effect=[
            mock_statvfs_1,  # movies
            mock_statvfs_1,  # series (same disk)
            mock_statvfs_2,  # animes (different disk)
        ]):
            response = client.get("/api/filesystem/disk-space/")
    assert response.status_code == 200
    data = response.json()
    # disk1: 4096*1000000, disk2: 4096*2000000
    expected_total = 4096 * 1000000 + 4096 * 2000000
    expected_free = 4096 * 500000 + 4096 * 1500000
    assert data["total_bytes"] == expected_total
    assert data["free_bytes"] == expected_free
    assert data["used_bytes"] == expected_total - expected_free
    assert data["disks_count"] == 2


def test_disk_space_path_does_not_exist(client, db_session):
    """Test disk space skips paths that don't exist."""
    with patch("app.routers.filesystem.get_config") as mock_config:
        mock_config.side_effect = lambda key, db, required=False: {
            "movies_path": "/nonexistent/path",
            "series_path": "",
            "animes_path": "",
        }.get(key, "")
        response = client.get("/api/filesystem/disk-space/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_bytes"] == 0
    assert data["free_bytes"] == 0
    assert data["disks_count"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `backend/`:
```bash
pytest tests/test_filesystem_router.py -v
```
Expected: Tests fail with endpoint not found (404) or import error.

- [ ] **Step 3: Implement the endpoint**

Add to `backend/app/routers/filesystem.py`:

```python
import os
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from app.services.path_converter import is_wsl2
from app.services.config_service import get_config
from app.database import get_db
from app.logging_config import get_logger

router = APIRouter(prefix="/api/filesystem", tags=["filesystem"])
logger = get_logger(__name__)


@router.get("/root")
def get_root():
    """Return the root directory for browsing."""
    if is_wsl2():
        return {"root": "/mnt/"}
    return {"root": "/"}


@router.get("/dirs")
def list_dirs(path: str = Query("/")):
    """List immediate subdirectories of the given path."""
    target = Path(path).resolve()

    if not target.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    dirs = []
    try:
        for entry in sorted(target.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                dirs.append(entry.name)
    except PermissionError as e:
        logger.warning("Permission error listing directory", path=str(target), error=str(e))
    except OSError as e:
        logger.warning("OS error listing directory", path=str(target), error=str(e))

    parent = str(target.parent)
    if parent == str(target):
        parent = None

    return {
        "path": str(target) + ("/" if str(target) != "/" else ""),
        "dirs": dirs,
        "parent": parent,
    }


@router.get("/disk-space/")
def get_disk_space(db: Session = Depends(get_db)):
    """Return aggregated disk space for all unique disks hosting media folders."""
    path_keys = ["movies_path", "series_path", "animes_path"]
    paths = []
    for key in path_keys:
        val = get_config(key, db=db)
        if val:
            paths.append(val)

    if not paths:
        return {"total_bytes": 0, "free_bytes": 0, "used_bytes": 0, "disks_count": 0}

    unique_disks: dict[tuple, dict] = {}

    for path in paths:
        try:
            stat = os.statvfs(path)
        except (OSError, FileNotFoundError) as e:
            logger.warning(f"Cannot statvfs path '{path}': {e}")
            continue

        device_id = stat.f_fsid
        if device_id not in unique_disks:
            unique_disks[device_id] = {
                "total": stat.f_frsize * stat.f_blocks,
                "free": stat.f_frsize * stat.f_bavail,
            }

    total_bytes = sum(d["total"] for d in unique_disks.values())
    free_bytes = sum(d["free"] for d in unique_disks.values())
    used_bytes = total_bytes - free_bytes

    return {
        "total_bytes": total_bytes,
        "free_bytes": free_bytes,
        "used_bytes": used_bytes,
        "disks_count": len(unique_disks),
    }
```

Note: The existing imports at the top of the file need to be updated. The current file has `from pathlib import Path` and other imports. Make sure `Path` is imported at the top since it's used in `list_dirs`. The current file already uses `Path` on line 22 but doesn't import it — verify the existing imports are correct before adding.

- [ ] **Step 4: Run tests to verify they pass**

Run from `backend/`:
```bash
pytest tests/test_filesystem_router.py -v
```
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/filesystem.py backend/tests/test_filesystem_router.py
git commit -m "feat: add disk space endpoint with device deduplication"
```

---

### Task 3: Frontend — API Client Method

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Add getDiskSpace method to filesystemAPI**

Modify `frontend/src/services/api.ts`, update the `filesystemAPI` object:

```typescript
export const filesystemAPI = {
  getRoot: () => api.get('/filesystem/root'),
  getDirs: (path: string) => api.get('/filesystem/dirs', { params: { path } }),
  getDiskSpace: () => api.get('/filesystem/disk-space/'),
};
```

- [ ] **Step 2: Add TypeScript type for disk space response**

Add near the top of `frontend/src/services/api.ts` (after the imports):

```typescript
export interface DiskSpaceResponse {
  total_bytes: number;
  free_bytes: number;
  used_bytes: number;
  disks_count: number;
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run from `frontend/`:
```bash
npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat: add getDiskSpace API method and type"
```

---

### Task 4: Frontend — DiskSpaceChart Component

**Files:**
- Create: `frontend/src/components/DiskSpaceChart.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/DiskSpaceChart.tsx`:

```tsx
import { useQuery } from '@tanstack/react-query';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { filesystemAPI, DiskSpaceResponse } from '../services/api';

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 GB';
  const gb = bytes / (1024 * 1024 * 1024);
  if (gb >= 1000) return `${(gb / 1024).toFixed(2)} TB`;
  return `${gb.toFixed(1)} GB`;
};

const DiskSpaceChart: React.FC = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['disk-space'],
    queryFn: () => filesystemAPI.getDiskSpace().then(res => res.data as DiskSpaceResponse),
  });

  if (isLoading) {
    return (
      <div className="glass rounded-2xl p-6 animate-shimmer h-64" />
    );
  }

  if (isError || !data || data.disks_count === 0) {
    return (
      <div className="glass rounded-2xl p-6">
        <p className="text-center text-muted-foreground text-sm">
          {isError
            ? 'Erro ao carregar informações do disco'
            : 'Nenhum caminho de mídia configurado'}
        </p>
      </div>
    );
  }

  const chartData = [
    { name: 'Usado', value: data.used_bytes },
    { name: 'Livre', value: data.free_bytes },
  ];

  const COLORS = ['#ef4444', '#22c55e'];

  return (
    <div className="glass rounded-2xl p-6">
      <h3 className="font-display text-lg font-bold text-foreground mb-4">
        Espaço em Disco
      </h3>
      <div className="flex items-center justify-center">
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={80}
              paddingAngle={5}
              dataKey="value"
            >
              {chartData.map((_entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => formatBytes(value)}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute flex flex-col items-center justify-center">
          <p className="text-2xl font-bold text-foreground">
            {formatBytes(data.free_bytes)}
          </p>
          <p className="text-xs text-muted-foreground">
            livres de {formatBytes(data.total_bytes)}
          </p>
        </div>
      </div>
      <div className="flex justify-center gap-6 mt-2">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <span className="text-sm text-muted-foreground">Usado</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-sm text-muted-foreground">Livre</span>
        </div>
      </div>
    </div>
  );
};

export default DiskSpaceChart;
```

- [ ] **Step 2: Verify TypeScript compiles**

Run from `frontend/`:
```bash
npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/DiskSpaceChart.tsx
git commit -m "feat: add DiskSpaceChart component with recharts donut"
```

---

### Task 5: Frontend — Integrate Chart into Settings Page

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Import and place the chart**

Add import at the top of `frontend/src/pages/Settings.tsx`:

```tsx
import DiskSpaceChart from '@/components/DiskSpaceChart';
```

Insert the chart above the settings grid. Find this section in the return:

```tsx
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
```

And place the chart before it:

```tsx
<DiskSpaceChart />

<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
```

- [ ] **Step 2: Verify TypeScript compiles**

Run from `frontend/`:
```bash
npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 3: Build the frontend**

Run from `frontend/`:
```bash
npm run build
```
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat: integrate DiskSpaceChart into Settings page"
```

---

### Task 6: Final Verification

- [ ] **Step 1: Run all backend tests**

Run from `backend/`:
```bash
pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 2: Run frontend lint**

Run from `frontend/`:
```bash
npm run lint
```
Expected: No lint errors.
