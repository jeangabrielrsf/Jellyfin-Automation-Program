# Folder Picker for Settings Page — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add "Browse" buttons to media path inputs on the Settings page that open a shadcn Dialog with a server filesystem tree view, and refactor backend services to read paths from DB settings (with .env fallback).

**Architecture:** New backend router (`filesystem.py`) exposes directory listing via REST. A settings service helper reads media paths from DB settings table with `.env` fallback. `PathResolver` and `OrganizerService` are refactored to accept db sessions and use the helper. Frontend adds `FolderPickerDialog` component and `filesystemAPI`, integrated into Settings page via shadcn Button + Dialog.

**Tech Stack:** FastAPI, SQLAlchemy, React 18 + TypeScript, shadcn/ui (Dialog, Button), TanStack Query, lucide-react

---

### Task 1: Create settings service helper

**Files:**
- Create: `backend/app/services/settings_service.py`

- [ ] **Step 1: Write the file**

```python
"""Settings service for reading runtime settings from DB with .env fallback."""
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.settings import Setting


def get_media_paths(db: Session) -> dict:
    """Get media paths from DB settings, falling back to .env values."""
    db_settings = {s.key: s.value for s in db.query(Setting).all()}
    env = get_settings()
    return {
        "movies_path": db_settings.get("movies_path") or env.movies_path,
        "series_path": db_settings.get("series_path") or env.series_path,
        "animes_path": db_settings.get("animes_path") or env.animes_path,
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/settings_service.py
git commit -m "feat: add settings service helper for DB-backed media paths"
```

---

### Task 2: Refactor PathResolver to use db-backed paths

**Files:**
- Modify: `backend/app/services/path_resolver.py:52-97`

- [ ] **Step 1: Modify resolve_path signature and path resolution**

Replace the `resolve_path` method to accept an optional `db` parameter. When `db` is provided, use `get_media_paths(db)`. When not provided, fall back to `get_settings()`.

```python
def resolve_path(
    self,
    title: str,
    media_type: str,
    torrent_name: Optional[str] = None,
    season: Optional[int] = None,
    episode: Optional[int] = None,
    year: Optional[int] = None,
    quality: Optional[str] = None,
    db: Optional[Session] = None,
) -> str:
    """Resolve the save path for a download.
    
    Args:
        title: Media title (e.g., "Breaking Bad")
        media_type: "movie", "series", or "anime"
        torrent_name: Original torrent name (used to extract season/episode if not provided)
        season: Season number (optional, extracted from torrent_name if not provided)
        episode: Episode number (optional)
        year: Release year (for movies)
        quality: Video quality (for file naming)
        db: Database session (if provided, reads paths from DB with .env fallback)
    
    Returns:
        Absolute path where the torrent should be saved
    """
    if db:
        paths = get_media_paths(db)
        movies_path = paths["movies_path"]
        series_path = paths["series_path"]
        animes_path = paths["animes_path"]
    else:
        settings = get_settings()
        movies_path = settings.movies_path
        series_path = settings.series_path
        animes_path = settings.animes_path
    
    # Extract season/episode from torrent name if not provided
    if media_type in ("series", "anime") and season is None and torrent_name:
        extracted = self.extract_season_episode(torrent_name)
        season = extracted.get("season")
        episode = extracted.get("episode")
    
    # Default season if still not found
    if media_type in ("series", "anime") and season is None:
        season = 1
        logger.warning("Could not extract season from torrent name, defaulting to 1", torrent_name=torrent_name)
    
    # Build path based on media type
    if media_type == "movie":
        folder_name = f"{title} ({year})" if year else title
        base_path = Path(movies_path)
        save_path = base_path / self._sanitize_filename(folder_name)
    elif media_type == "series":
        base_path = Path(series_path)
        show_folder = base_path / self._sanitize_filename(title)
        save_path = show_folder / f"Season {season:02d}"
    elif media_type == "anime":
        base_path = Path(animes_path)
        show_folder = base_path / self._sanitize_filename(title)
        save_path = show_folder / f"Season {season:02d}"
    else:
        raise ValueError(f"Unknown media type: {media_type}")
    
    # Create directories if they don't exist
    save_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(
        "Resolved save path",
        title=title,
        media_type=media_type,
        season=season,
        episode=episode,
        path=str(save_path)
    )
    
    return str(save_path)
```

Also add the import at the top of the file (after the existing imports on line 6):

```python
from sqlalchemy.orm import Session
from app.services.settings_service import get_media_paths
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/path_resolver.py
git commit -m "feat: add db-backed media paths to PathResolver"
```

---

### Task 3: Refactor OrganizerService to use db-backed paths

**Files:**
- Modify: `backend/app/services/organizer_service.py:17-89`

- [ ] **Step 1: Modify __init__ to accept optional db session**

Replace the constructor and all `self.settings.movies_path` / `self.settings.series_path` / `self.settings.animes_path` references.

Add the import at the top (line 6, after `from app.config import get_settings`):

```python
from sqlalchemy.orm import Session
from app.services.settings_service import get_media_paths
```

Replace `__init__` (lines 17-18):

```python
def __init__(self, db: Optional[Session] = None):
    if db:
        paths = get_media_paths(db)
        self.movies_path = paths["movies_path"]
        self.series_path = paths["series_path"]
        self.animes_path = paths["animes_path"]
    else:
        settings = get_settings()
        self.movies_path = settings.movies_path
        self.series_path = settings.series_path
        self.animes_path = settings.animes_path
```

Replace `self.settings.movies_path` → `self.movies_path` (3 occurrences: lines 25, 48, 73):

- Line 25: `dest_folder = Path(self.settings.movies_path) / self._sanitize_filename(folder_name)`
  → `dest_folder = Path(self.movies_path) / self._sanitize_filename(folder_name)`

- Line 48: `show_folder = Path(self.settings.series_path) / self._sanitize_filename(title)`
  → `show_folder = Path(self.series_path) / self._sanitize_filename(title)`

- Line 73: `show_folder = Path(self.settings.animes_path) / self._sanitize_filename(title)`
  → `show_folder = Path(self.animes_path) / self._sanitize_filename(title)`

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/organizer_service.py
git commit -m "feat: add db-backed media paths to OrganizerService"
```

---

### Task 4: Update downloads.py to pass db to PathResolver

**Files:**
- Modify: `backend/app/routers/downloads.py:64-81`

- [ ] **Step 1: Pass db to resolve_path**

Replace line 73 (the `resolve_path` call) to pass `db`:

```python
save_path = path_resolver.resolve_path(
    title=download.title,
    media_type=download.media_type.value,
    torrent_name=download.torrent_name,
    season=season,
    episode=episode,
    year=download.year,
    quality=download.quality,
    db=db,
)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/downloads.py
git commit -m "feat: pass db session to PathResolver for live path updates"
```

---

### Task 5: Update download_worker.py to pass db to OrganizerService

**Files:**
- Modify: `backend/app/services/download_worker.py:116`

- [ ] **Step 1: Pass db to OrganizerService constructor**

Replace line 116:

```python
organizer = OrganizerService()
```

→

```python
organizer = OrganizerService(db=db)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/download_worker.py
git commit -m "feat: pass db session to OrganizerService for live path updates"
```

---

### Task 6: Create filesystem router

**Files:**
- Create: `backend/app/routers/filesystem.py`

- [ ] **Step 1: Write the router**

```python
"""Filesystem browser router — list directories on the server."""
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/filesystem", tags=["filesystem"])


def _is_wsl2() -> bool:
    """Check if running under WSL2 by looking for /mnt/ mounted drives."""
    mnt = Path("/mnt")
    if not mnt.exists() or not mnt.is_dir():
        return False
    try:
        for entry in mnt.iterdir():
            if entry.is_dir():
                return True
    except PermissionError:
        pass
    return False


@router.get("/root")
def get_root():
    """Return the root directory for browsing."""
    if _is_wsl2():
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
    except PermissionError:
        pass

    parent = str(target.parent)
    if parent == str(target):
        parent = None

    return {
        "path": str(target) + ("/" if str(target) != "/" else ""),
        "dirs": dirs,
        "parent": parent,
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/filesystem.py
git commit -m "feat: add filesystem router for directory browsing"
```

---

### Task 7: Include filesystem router in main.py

**Files:**
- Modify: `backend/app/main.py:13,96`

- [ ] **Step 1: Import and include filesystem router**

Add to the `from app.routers import ...` line (line 13):

```python
from app.routers import search, downloads, settings, logs, filesystem
```

Add after `app.include_router(logs.router)` (line 97):

```python
app.include_router(filesystem.router)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: register filesystem router"
```

---

### Task 8: Write tests for filesystem router

**Files:**
- Create: `backend/tests/test_filesystem_router.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for the filesystem router."""
import tempfile
import os
import pytest
from unittest.mock import patch
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory structure for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "Movies"), exist_ok=True)
        os.makedirs(os.path.join(tmp, "Series"), exist_ok=True)
        os.makedirs(os.path.join(tmp, "hidden_folder"), exist_ok=True)
        with open(os.path.join(tmp, "file.txt"), "w") as f:
            f.write("test")
        yield tmp


def test_get_root_not_wsl2(client):
    """Test /api/filesystem/root returns / when not in WSL2."""
    with patch("app.routers.filesystem._is_wsl2", return_value=False):
        response = client.get("/api/filesystem/root")
    assert response.status_code == 200
    data = response.json()
    assert data["root"] == "/"


def test_get_root_wsl2(client):
    """Test /api/filesystem/root returns /mnt/ on WSL2."""
    with patch("app.routers.filesystem._is_wsl2", return_value=True):
        response = client.get("/api/filesystem/root")
    assert response.status_code == 200
    data = response.json()
    assert data["root"] == "/mnt/"


def test_list_dirs_success(client, temp_dir):
    """Test listing directories returns expected subdirectories."""
    response = client.get("/api/filesystem/dirs", params={"path": temp_dir})
    assert response.status_code == 200
    data = response.json()
    assert "Movies" in data["dirs"]
    assert "Series" in data["dirs"]
    assert "hidden_folder" not in data["dirs"]  # hidden directories excluded
    assert "file.txt" not in data["dirs"]        # files excluded
    assert "parent" in data


def test_list_dirs_nonexistent(client):
    """Test listing a nonexistent directory returns 404."""
    response = client.get("/api/filesystem/dirs", params={"path": "/nonexistent/path/xyz"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Directory not found"


def test_list_dirs_not_a_directory(client, temp_dir):
    """Test listing a file returns 400."""
    file_path = os.path.join(temp_dir, "file.txt")
    response = client.get("/api/filesystem/dirs", params={"path": file_path})
    assert response.status_code == 400
    assert response.json()["detail"] == "Path is not a directory"


def test_list_dirs_root(client):
    """Test listing root directory works (may have no dirs in test container but shouldn't 500)."""
    response = client.get("/api/filesystem/dirs", params={"path": "/"})
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "/"
    assert "dirs" in data
```

- [ ] **Step 2: Run tests to verify**

```bash
cd backend && source venv/bin/activate && pytest tests/test_filesystem_router.py -v
```

Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_filesystem_router.py
git commit -m "test: add filesystem router tests"
```

---

### Task 9: Write tests for settings service

**Files:**
- Create: `backend/tests/test_settings_service.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for the settings service."""
import pytest
from app.services.settings_service import get_media_paths
from app.models.settings import Setting


def test_get_media_paths_from_db(db_session):
    """Test that paths are read from DB when present."""
    db_session.add(Setting(key="movies_path", value="/custom/movies"))
    db_session.add(Setting(key="animes_path", value="/custom/anime"))
    db_session.commit()

    paths = get_media_paths(db_session)
    assert paths["movies_path"] == "/custom/movies"
    assert paths["animes_path"] == "/custom/anime"
    assert paths["series_path"] == "D:\\Séries"  # falls back to .env default
    # series_path not in DB, should use env fallback


def test_get_media_paths_empty_db(db_session):
    """Test that all paths fall back to .env when DB is empty."""
    paths = get_media_paths(db_session)
    assert paths["movies_path"] == "D:\\Filmes"
    assert paths["series_path"] == "D:\\Séries"
    assert paths["animes_path"] == "D:\\Animes"


def test_get_media_paths_partial_db(db_session):
    """Test partial DB settings still fall back for missing keys."""
    db_session.add(Setting(key="movies_path", value="/only/movies"))
    db_session.commit()

    paths = get_media_paths(db_session)
    assert paths["movies_path"] == "/only/movies"
    assert paths["series_path"] == "D:\\Séries"
    assert paths["animes_path"] == "D:\\Animes"
```

- [ ] **Step 2: Run tests to verify**

```bash
cd backend && source venv/bin/activate && pytest tests/test_settings_service.py -v
```

Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_settings_service.py
git commit -m "test: add settings service tests"
```

---

### Task 10: Add filesystem API to frontend api.ts

**Files:**
- Modify: `frontend/src/services/api.ts:84-91`

- [ ] **Step 1: Add filesystemAPI export**

Add after the `settingsAPI` block (after line 84):

```typescript
export const filesystemAPI = {
  getRoot: () => api.get('/filesystem/root'),
  getDirs: (path: string) => api.get('/filesystem/dirs', { params: { path } }),
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat: add filesystem API client"
```

---

### Task 11: Create FolderPickerDialog component

**Files:**
- Create: `frontend/src/components/FolderPickerDialog.tsx`

- [ ] **Step 1: Write the component**

```tsx
import React, { useState, useCallback, useEffect } from 'react';
import { Folder, ChevronRight, ChevronDown, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { filesystemAPI } from '@/services/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

interface FolderPickerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (path: string) => void;
}

interface TreeNode {
  name: string;
  path: string;
  children: TreeNode[] | null;
  loaded: boolean;
}

const FolderPickerDialog: React.FC<FolderPickerDialogProps> = ({
  open,
  onOpenChange,
  onSelect,
}) => {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [rootNode, setRootNode] = useState<TreeNode | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());

  const { data: rootData } = useQuery({
    queryKey: ['filesystem-root'],
    queryFn: () => filesystemAPI.getRoot(),
    staleTime: Infinity,
  });

  useEffect(() => {
    if (rootData?.data?.root) {
      setRootNode({
        name: rootData.data.root,
        path: rootData.data.root,
        children: null,
        loaded: false,
      });
    }
  }, [rootData]);

  const loadChildren = useCallback(
    async (path: string): Promise<TreeNode[]> => {
      const response = await filesystemAPI.getDirs(path);
      return response.data.dirs.map((dir: string) => ({
        name: dir,
        path: path.endsWith('/') ? path + dir : path + '/' + dir,
        children: null,
        loaded: false,
      }));
    },
    []
  );

  const toggleExpand = useCallback(
    async (node: TreeNode) => {
      if (expandedPaths.has(node.path)) {
        setExpandedPaths((prev) => {
          const next = new Set(prev);
          next.delete(node.path);
          return next;
        });
        return;
      }

      setExpandedPaths((prev) => new Set(prev).add(node.path));

      if (!node.loaded) {
        const children = await loadChildren(node.path);
        node.children = children;
        node.loaded = true;
        setRootNode({ ...rootNode! });
      }
    },
    [expandedPaths, loadChildren, rootNode]
  );

  const handleSelect = () => {
    if (selectedPath) {
      onSelect(selectedPath);
      onOpenChange(false);
    }
  };

  const renderNode = (node: TreeNode, depth: number): React.ReactNode => {
    const isExpanded = expandedPaths.has(node.path);
    const isSelected = selectedPath === node.path;
    const isLoading = isExpanded && !node.loaded;

    return (
      <div key={node.path}>
        <div
          className={`flex items-center gap-1 py-1 px-1 rounded cursor-pointer transition-colors
            ${isSelected ? 'bg-primary/20 text-primary' : 'hover:bg-accent'}`}
          style={{ paddingLeft: depth * 20 + 4 }}
          onClick={() => {
            setSelectedPath(node.path);
            toggleExpand(node);
          }}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin shrink-0" />
          ) : isExpanded ? (
            <ChevronDown className="h-4 w-4 shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0" />
          )}
          <Folder className="h-4 w-4 shrink-0 text-yellow-500" />
          <span className="text-sm truncate ml-1">{node.name}</span>
        </div>
        {isExpanded &&
          node.children?.map((child) => renderNode(child, depth + 1))}
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[70vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Selecionar Pasta</DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto min-h-[300px] border rounded-lg p-2">
          {rootNode ? (
            renderNode(rootNode, 0)
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSelect} disabled={!selectedPath}>
            Selecionar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default FolderPickerDialog;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/FolderPickerDialog.tsx
git commit -m "feat: add FolderPickerDialog component with tree view"
```

---

### Task 12: Update Settings page with Browse buttons

**Files:**
- Modify: `frontend/src/pages/Settings.tsx:1-167`

- [ ] **Step 1: Add imports and integrate FolderPickerDialog**

Replace the entire file content:

```tsx
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Folder, Sparkles, Save } from 'lucide-react';
import { settingsAPI } from '../services/api';
import { Button } from '@/components/ui/button';
import FolderPickerDialog from '@/components/FolderPickerDialog';

const pathKeys = ['movies_path', 'series_path', 'animes_path'];

const settingGroups = [
  {
    icon: Folder,
    title: 'Caminhos',
    description: 'Diretórios onde o conteúdo será salvo',
    settings: [
      { key: 'movies_path', label: 'Pasta de Filmes', placeholder: '/media/movies' },
      { key: 'series_path', label: 'Pasta de Séries', placeholder: '/media/series' },
      { key: 'animes_path', label: 'Pasta de Animes', placeholder: '/media/animes' },
    ],
  },
  {
    icon: Sparkles,
    title: 'Preferências',
    description: 'Configurações padrão para novos downloads',
    settings: [
      { key: 'default_quality', label: 'Qualidade Padrão', placeholder: '1080p' },
      { key: 'default_language', label: 'Idioma Padrão', placeholder: 'legendado' },
    ],
  },
];

const SettingsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [pickerOpen, setPickerOpen] = useState<string | null>(null);

  const { data: currentSettings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => settingsAPI.getSettings(),
  });

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      settingsAPI.updateSetting(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });

  const handleUpdate = (key: string, value: string) => {
    if (value) {
      updateMutation.mutate({ key, value });
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
            Configurações
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2].map((i) => (
            <div key={i} className="glass rounded-2xl p-6 h-64 animate-shimmer" />
          ))}
        </div>
      </div>
    );
  }

  const currentValues = currentSettings?.data || {};

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="text-center space-y-4">
        <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
          Configurações
        </h2>
        <p className="text-muted-foreground max-w-xl mx-auto">
          Configure os caminhos de mídia e preferências de download
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {settingGroups.map((group) => (
          <div
            key={group.title}
            className="glass rounded-2xl p-6 space-y-6
                     transition-all duration-300 hover:border-primary/20"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <group.icon className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-display text-lg font-bold text-foreground">
                  {group.title}
                </h3>
                <p className="text-sm text-muted-foreground">{group.description}</p>
              </div>
            </div>

            <div className="space-y-4">
              {group.settings.map((setting) => (
                <div key={setting.key} className="space-y-2">
                  <label className="text-sm font-medium text-foreground">
                    {setting.label}
                  </label>
                  <div className="relative group">
                    {setting.key === 'default_quality' ? (
                      <select
                        defaultValue={currentValues[setting.key] || '1080p'}
                        onChange={(e) => handleUpdate(setting.key, e.target.value)}
                        className="w-full px-4 py-3 rounded-xl glass bg-transparent
                                 border border-border/50
                                 focus:outline-none focus:ring-2 focus:ring-primary/30
                                 focus:border-primary/30
                                 text-foreground
                                 font-mono text-sm
                                 transition-all duration-200"
                      >
                        <option value="720p">720p</option>
                        <option value="1080p">1080p</option>
                        <option value="1440p">1440p</option>
                        <option value="2160p">2160p</option>
                      </select>
                    ) : setting.key === 'default_language' ? (
                      <select
                        defaultValue={currentValues[setting.key] || 'legendado'}
                        onChange={(e) => handleUpdate(setting.key, e.target.value)}
                        className="w-full px-4 py-3 rounded-xl glass bg-transparent
                                 border border-border/50
                                 focus:outline-none focus:ring-2 focus:ring-primary/30
                                 focus:border-primary/30
                                 text-foreground
                                 font-mono text-sm
                                 transition-all duration-200"
                      >
                        <option value="legendado">Legendado</option>
                        <option value="dublado">Dublado</option>
                      </select>
                    ) : (
                      <div className="flex gap-2">
                        <input
                          type="text"
                          defaultValue={currentValues[setting.key] || ''}
                          placeholder={setting.placeholder}
                          onBlur={(e) => handleUpdate(setting.key, e.target.value)}
                          className="flex-1 px-4 py-3 rounded-xl glass bg-transparent
                                   border border-border/50
                                   focus:outline-none focus:ring-2 focus:ring-primary/30
                                   focus:border-primary/30
                                   text-foreground placeholder:text-muted-foreground/50
                                   font-mono text-sm
                                   transition-all duration-200"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="default"
                          className="shrink-0"
                          onClick={() => setPickerOpen(setting.key)}
                        >
                          <Folder className="w-4 h-4 mr-1" />
                          Browse
                        </Button>
                      </div>
                    )}
                    {updateMutation.isPending && updateMutation.variables?.key === setting.key && (
                      <Save className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-primary animate-pulse" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {pickerOpen && (
        <FolderPickerDialog
          open={!!pickerOpen}
          onOpenChange={(open) => {
            if (!open) setPickerOpen(null);
          }}
          onSelect={(path) => {
            handleUpdate(pickerOpen, path);
          }}
        />
      )}
    </div>
  );
};

export default SettingsPage;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat: add Browse buttons with folder picker to Settings page"
```

---

### Task 13: Verify — run tests, lint, and build

- [ ] **Step 1: Run backend tests**

```bash
cd backend && source venv/bin/activate && pytest tests/ -v
```

Expected: all tests PASS (including existing + new filesystem and settings_service tests)

- [ ] **Step 2: Run frontend lint**

```bash
cd frontend && npm run lint
```

Expected: no ESLint errors

- [ ] **Step 3: Run frontend type check / build**

```bash
cd frontend && npm run build
```

Expected: TypeScript compilation succeeds, no errors

- [ ] **Step 4: Commit (if any fixes were needed)**

```bash
git add -A
git commit -m "chore: fix lint/type issues from folder picker implementation"
```
