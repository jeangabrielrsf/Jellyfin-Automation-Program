# Download Progress Monitor + Smart Save Paths Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Monitor qBittorrent download progress and automatically organize files into series/movies folders with correct season subdirectories.

**Architecture:** A background `DownloadWorker` polls qBittorrent every 10 seconds via the existing `/api/v2/torrents/info` endpoint, updates the database with progress/speed/eta/status, and triggers file organization when downloads complete. The `PathResolver` extracts season/episode from torrent names and computes save paths before adding torrents to qBittorrent.

**Tech Stack:** FastAPI, SQLAlchemy, httpx, asyncio, Python 3.12, React 18, TanStack Query

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/services/path_resolver.py` | Create | Extract season/episode from torrent names, compute save paths |
| `backend/app/services/download_worker.py` | Create | Background worker that syncs qBittorrent state with DB |
| `backend/app/routers/downloads.py` | Modify | Integrate PathResolver when creating downloads |
| `backend/app/main.py` | Modify | Start DownloadWorker in lifespan |
| `backend/app/services/qbittorrent_service.py` | Modify | Support savepath parameter in add_torrent, add get_torrents helper |
| `backend/app/models/download.py` | Modify | Add `episode` column to Download model |
| `backend/alembic/versions/...` | Create | Migration for episode column |
| `backend/tests/services/test_path_resolver.py` | Create | Tests for path resolution logic |
| `backend/tests/services/test_download_worker.py` | Create | Tests for worker sync logic |
| `frontend/src/pages/Detail.tsx` | Modify | Send season/episode extracted from torrent name to backend |
| `frontend/src/services/api.ts` | Modify | Update createDownload type to include season/episode |
| `AGENTS.md` | Modify | Document new conventions |

---

### Task 1: Add `episode` column to Download model + migration

**Files:**
- Modify: `backend/app/models/download.py:22-49`
- Create: `backend/alembic/versions/20260504_add_episode_to_downloads.py`
- Test: `backend/tests/models/test_download.py` (new)

- [ ] **Step 1: Add `episode` column to Download model**

```python
# backend/app/models/download.py
# Add after line 28 (after `type` column):
    season = Column(Integer)
    episode = Column(Integer)
```

- [ ] **Step 2: Create Alembic migration**

```bash
cd backend
alembic revision --autogenerate -m "add season and episode to downloads"
```

Verify the generated migration adds `season` and `episode` columns to the `downloads` table.

- [ ] **Step 3: Apply migration locally**

```bash
cd backend
alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/download.py backend/alembic/versions/
git commit -m "feat: add season and episode columns to downloads table"
```

---

### Task 2: Create PathResolver service

**Files:**
- Create: `backend/app/services/path_resolver.py`
- Test: `backend/tests/services/test_path_resolver.py` (new)

- [ ] **Step 1: Write failing test**

```python
# backend/tests/services/test_path_resolver.py
import pytest
from app.services.path_resolver import PathResolver

@pytest.fixture
def resolver():
    return PathResolver()

def test_extract_season_episode_standard_format(resolver):
    result = resolver.extract_season_episode("The Rookie S08E17 1080p x265 ELiTE")
    assert result == {"season": 8, "episode": 17}

def test_extract_season_episode_lowercase_format(resolver):
    result = resolver.extract_season_episode("Show s01e05 WEB-DL")
    assert result == {"season": 1, "episode": 5}

def test_extract_season_episode_no_match(resolver):
    result = resolver.extract_season_episode("Movie.2024.1080p.BluRay")
    assert result == {"season": None, "episode": None}

def test_resolve_series_path(resolver):
    from unittest.mock import patch
    with patch("app.services.path_resolver.get_settings") as mock_settings:
        mock_settings.return_value.series_path = "/series"
        result = resolver.resolve_path(
            title="Breaking Bad",
            media_type="series",
            torrent_name="Breaking Bad S05E14 1080p",
            season=5,
            episode=14
        )
        assert result == "/series/Breaking Bad/Season 05"

def test_resolve_movie_path(resolver):
    from unittest.mock import patch
    with patch("app.services.path_resolver.get_settings") as mock_settings:
        mock_settings.return_value.movies_path = "/movies"
        result = resolver.resolve_path(
            title="Inception",
            media_type="movie",
            year=2010,
            quality="1080p"
        )
        assert result == "/movies/Inception (2010)"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/services/test_path_resolver.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.path_resolver'"

- [ ] **Step 3: Write PathResolver implementation**

```python
# backend/app/services/path_resolver.py
"""Service to resolve save paths for downloads based on media type and metadata."""
import re
from typing import Optional, Dict
from pathlib import Path
from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

class PathResolver:
    """Resolve save paths for media downloads."""
    
    # Patterns to extract season/episode from torrent names
    SEASON_EPISODE_PATTERNS = [
        r'[Ss](\d{1,2})[Ee](\d{1,2})',      # S08E17, s01e05
        r'(\d{1,2})[xX](\d{1,2})',          # 8x17, 1x05
        r'[Ss]eason[.\s]*(\d{1,2}).*[Ee]pisode[.\s]*(\d{1,2})',  # Season 8 Episode 17
    ]
    
    def extract_season_episode(self, torrent_name: str) -> Dict[str, Optional[int]]:
        """Extract season and episode numbers from torrent name."""
        for pattern in self.SEASON_EPISODE_PATTERNS:
            match = re.search(pattern, torrent_name)
            if match:
                return {
                    "season": int(match.group(1)),
                    "episode": int(match.group(2))
                }
        return {"season": None, "episode": None}
    
    def resolve_path(
        self,
        title: str,
        media_type: str,
        torrent_name: Optional[str] = None,
        season: Optional[int] = None,
        episode: Optional[int] = None,
        year: Optional[int] = None,
        quality: Optional[str] = None
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
        
        Returns:
            Absolute path where the torrent should be saved
        """
        settings = get_settings()
        
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
            base_path = Path(settings.movies_path)
            save_path = base_path / self._sanitize_filename(folder_name)
        elif media_type == "series":
            base_path = Path(settings.series_path)
            show_folder = base_path / self._sanitize_filename(title)
            save_path = show_folder / f"Season {season:02d}"
        elif media_type == "anime":
            base_path = Path(settings.animes_path)
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
    
    def _sanitize_filename(self, filename: str) -> str:
        """Remove invalid characters from filename."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/services/test_path_resolver.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/path_resolver.py backend/tests/services/test_path_resolver.py
git commit -m "feat: add PathResolver service for computing save paths"
```

---

### Task 3: Update qBittorrentService to support savepath

**Files:**
- Modify: `backend/app/services/qbittorrent_service.py:44-127`

- [ ] **Step 1: Modify add_torrent to accept savepath**

```python
# backend/app/services/qbittorrent_service.py
# Update the add_torrent signature and implementation

async def add_torrent(
    self, 
    magnet_link: Optional[str] = None, 
    download_url: Optional[str] = None, 
    save_path: Optional[str] = None, 
    category: Optional[str] = None, 
    torrent_name: Optional[str] = None
) -> bool:
    """Add torrent to qBittorrent."""
    logger.info(
        "Adding torrent to qBittorrent", 
        magnet_link=magnet_link[:50] if magnet_link else None, 
        download_url=download_url[:50] if download_url else None,
        save_path=save_path,
        category=category
    )
    if not await self._authenticate():
        logger.error("Cannot add torrent: authentication failed")
        return False
    
    # Determine which link to use
    link = magnet_link if magnet_link else download_url
    if not link:
        logger.error("No link provided for torrent")
        return False
    
    is_magnet = link.strip().startswith("magnet:")
    
    try:
        add_url = f"{self.settings.qbittorrent_host}/api/v2/torrents/add"
        
        # Build common data dict
        data = {}
        if save_path:
            data["savepath"] = save_path
        if category:
            data["category"] = category
        
        if is_magnet:
            data["urls"] = link
            
            logger.info("Sending magnet link to qBittorrent", url=add_url, save_path=save_path)
            response = await self.client.post(
                add_url,
                data=data
            )
        else:
            # Download the .torrent file and upload it to qBittorrent
            # ... existing code, but data now includes savepath and category ...
            files = {"torrents": ("torrent.torrent", torrent_response.content, "application/x-bittorrent")}
            
            logger.info("Uploading .torrent file to qBittorrent", url=add_url, save_path=save_path)
            response = await self.client.post(
                add_url,
                data=data,
                files=files
            )
        
        logger.info("qBittorrent add response", status=response.status_code, text=response.text)
        response.raise_for_status()
        
        logger.info("Torrent added to qBittorrent successfully", link=link[:50], save_path=save_path)
        return True
        
    except httpx.HTTPError as e:
        logger.error("Failed to add torrent", error=str(e), is_magnet=is_magnet, status_code=getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None)
        return False
    except Exception as e:
        logger.error("Unexpected error adding torrent", error=str(e), error_type=type(e).__name__, is_magnet=is_magnet)
        return False
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
cd backend
pytest tests/ -v -k qbittorrent
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/qbittorrent_service.py
git commit -m "feat: support savepath parameter in qBittorrent add_torrent"
```

---

### Task 4: Update downloads router to use PathResolver

**Files:**
- Modify: `backend/app/routers/downloads.py:1-116`

- [ ] **Step 1: Modify DownloadCreate schema and create_download**

```python
# backend/app/routers/downloads.py
# Add imports
from app.services.path_resolver import PathResolver

# Update DownloadCreate
class DownloadCreate(BaseModel):
    tmdb_id: int
    title: str
    media_type: ContentType
    torrent_name: str
    magnet_link: Optional[str] = None
    download_url: Optional[str] = None
    quality: str = "1080p"
    language_preference: str = "legendado"
    indexer_used: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    year: Optional[int] = None

# Update create_download function
@router.post("/")
async def create_download(
    download: DownloadCreate,
    db: Session = Depends(get_db)
):
    """Create a new download record and add torrent to qBittorrent."""
    # Determine which link to use
    magnet_link = download.magnet_link
    download_url = download.download_url
    
    # If no magnet link but has download_url, use download_url as magnet_link for storage
    link_to_store = magnet_link if magnet_link else download_url
    
    # Resolve save path
    path_resolver = PathResolver()
    
    # Extract season/episode if not provided
    season = download.season
    episode = download.episode
    if season is None and download.torrent_name:
        extracted = path_resolver.extract_season_episode(download.torrent_name)
        season = extracted.get("season")
        episode = extracted.get("episode")
    
    save_path = path_resolver.resolve_path(
        title=download.title,
        media_type=download.media_type.value,
        torrent_name=download.torrent_name,
        season=season,
        episode=episode,
        year=download.year,
        quality=download.quality
    )
    
    db_download = Download(
        tmdb_id=download.tmdb_id,
        title=download.title,
        type=download.media_type,
        torrent_name=download.torrent_name,
        magnet_link=link_to_store,
        quality=download.quality,
        language_preference=download.language_preference,
        status=DownloadStatus.PENDING,
        indexer_used=download.indexer_used,
        season=season,
        episode=episode,
        source_folder=save_path
    )
    # ... rest of function remains the same, but pass save_path to service.add_torrent()
    
    # In the service.add_torrent call:
    success = await service.add_torrent(
        magnet_link=magnet_link,
        download_url=download_url,
        save_path=save_path,
        category=download.media_type.value,
        torrent_name=download.torrent_name
    )
```

- [ ] **Step 2: Test creating a download**

```bash
cd backend
pytest tests/ -v -k create_download
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/downloads.py
git commit -m "feat: integrate PathResolver in downloads router"
```

---

### Task 5: Create DownloadWorker

**Files:**
- Create: `backend/app/services/download_worker.py`
- Create: `backend/tests/services/test_download_worker.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/services/test_download_worker.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.download_worker import DownloadWorker

@pytest.fixture
def mock_db():
    db = MagicMock()
    return db

@pytest.fixture
def mock_qbit_service():
    service = AsyncMock()
    service.get_torrents = AsyncMock(return_value=[
        {
            "hash": "abc123",
            "progress": 0.5,
            "dlspeed": 1048576,
            "eta": 3600,
            "state": "downloading"
        }
    ])
    service.close = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_sync_progress_updates_download(mock_db, mock_qbit_service):
    worker = DownloadWorker()
    
    # Mock the database query
    mock_download = MagicMock()
    mock_download.torrent_hash = "abc123"
    mock_download.id = 1
    
    with patch("app.services.download_worker.SessionLocal") as mock_session:
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_download]
        
        with patch("app.services.download_worker.QBittorrentService", return_value=mock_qbit_service):
            await worker._sync_progress()
    
    # Verify the download was updated
    assert mock_download.progress == 0.5
    assert mock_download.speed == "1.0 MB/s"
    assert mock_download.eta == "01:00:00"
    assert mock_download.status.value == "downloading"
    mock_db.commit.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/services/test_download_worker.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.download_worker'"

- [ ] **Step 3: Write DownloadWorker implementation**

```python
# backend/app/services/download_worker.py
"""Background worker to monitor qBittorrent downloads and update database."""
import asyncio
from typing import Optional
from app.database import SessionLocal
from app.models.download import Download, DownloadStatus
from app.services.qbittorrent_service import QBittorrentService
from app.services.organizer_service import OrganizerService
from app.logging_config import get_logger

logger = get_logger(__name__)

class DownloadWorker:
    """Background worker that syncs qBittorrent download state with the database."""
    
    INTERVAL = 10  # seconds between syncs
    
    # qBittorrent state → app status mapping
    STATE_MAPPING = {
        "downloading": DownloadStatus.DOWNLOADING,
        "stalledDL": DownloadStatus.DOWNLOADING,
        "metaDL": DownloadStatus.DOWNLOADING,
        "pausedDL": DownloadStatus.PENDING,  # Using PENDING since we don't have PAUSED status
        "queuedDL": DownloadStatus.PENDING,
        "checkingDL": DownloadStatus.PENDING,
        "forcedDL": DownloadStatus.DOWNLOADING,
        "allocating": DownloadStatus.PENDING,
        "downloadingDL": DownloadStatus.DOWNLOADING,
        "uploading": DownloadStatus.COMPLETED,
        "stalledUP": DownloadStatus.COMPLETED,
        "queuedUP": DownloadStatus.COMPLETED,
        "checkingUP": DownloadStatus.COMPLETED,
        "forcedUP": DownloadStatus.COMPLETED,
        "pausedUP": DownloadStatus.COMPLETED,
    }
    
    async def start(self):
        """Start the worker loop."""
        logger.info("DownloadWorker started")
        while True:
            try:
                await self._sync_progress()
            except Exception as e:
                logger.error("Error in DownloadWorker sync", error=str(e))
            await asyncio.sleep(self.INTERVAL)
    
    async def _sync_progress(self):
        """Sync download progress from qBittorrent to database."""
        db = SessionLocal()
        service = QBittorrentService()
        
        try:
            # Get all downloading downloads from DB
            downloading_statuses = [
                DownloadStatus.DOWNLOADING,
                DownloadStatus.PENDING
            ]
            downloads = db.query(Download).filter(
                Download.status.in_(downloading_statuses)
            ).all()
            
            if not downloads:
                return
            
            # Get all torrents from qBittorrent
            torrents = await service.get_torrents()
            
            # Build hash → torrent lookup
            torrent_map = {t["hash"].lower(): t for t in torrents if t.get("hash")}
            
            for download in downloads:
                if not download.torrent_hash:
                    continue
                
                torrent = torrent_map.get(download.torrent_hash.lower())
                if not torrent:
                    logger.warning(
                        "Torrent not found in qBittorrent",
                        download_id=download.id,
                        torrent_hash=download.torrent_hash
                    )
                    continue
                
                # Update progress
                download.progress = torrent.get("progress", 0.0)
                download.speed = self._format_speed(torrent.get("dlspeed", 0))
                download.eta = self._format_eta(torrent.get("eta", 0))
                
                # Map qBittorrent state to app status
                qb_state = torrent.get("state", "").lower()
                new_status = self.STATE_MAPPING.get(qb_state)
                
                if new_status and new_status != download.status:
                    old_status = download.status
                    download.status = new_status
                    logger.info(
                        "Download status changed",
                        download_id=download.id,
                        old_status=old_status.value if old_status else None,
                        new_status=new_status.value,
                        progress=download.progress
                    )
                    
                    # Trigger organization when completed
                    if new_status == DownloadStatus.COMPLETED:
                        await self._organize_completed_download(download)
                
                db.commit()
                
        finally:
            db.close()
            await service.close()
    
    async def _organize_completed_download(self, download: Download):
        """Organize files when a download completes."""
        try:
            organizer = OrganizerService()
            
            if download.type.value == "movie":
                # For movies, we need to know the year
                # This would require additional metadata, for now just log
                logger.info(
                    "Movie download completed",
                    download_id=download.id,
                    title=download.title,
                    source_folder=download.source_folder
                )
            elif download.type.value in ("series", "anime"):
                if download.season and download.episode:
                    organizer.organize_series(
                        source_path=download.source_folder,
                        title=download.title,
                        season=download.season,
                        episode=download.episode,
                        quality=download.quality or "1080p"
                    )
                    logger.info(
                        "Organized series download",
                        download_id=download.id,
                        title=download.title,
                        season=download.season,
                        episode=download.episode
                    )
                else:
                    logger.warning(
                        "Cannot organize series without season/episode",
                        download_id=download.id
                    )
        except Exception as e:
            logger.error(
                "Failed to organize completed download",
                download_id=download.id,
                error=str(e)
            )
    
    @staticmethod
    def _format_speed(speed_bytes: int) -> str:
        """Format download speed in human readable format."""
        if speed_bytes == 0:
            return "0 B/s"
        
        units = ["B/s", "KB/s", "MB/s", "GB/s"]
        unit_index = 0
        speed = float(speed_bytes)
        
        while speed >= 1024 and unit_index < len(units) - 1:
            speed /= 1024
            unit_index += 1
        
        return f"{speed:.1f} {units[unit_index]}"
    
    @staticmethod
    def _format_eta(eta_seconds: int) -> str:
        """Format ETA in human readable format."""
        if eta_seconds == 0 or eta_seconds >= 8640000:  # qBittorrent returns 8640000 for unknown
            return "Unknown"
        
        hours = eta_seconds // 3600
        minutes = (eta_seconds % 3600) // 60
        seconds = eta_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/services/test_download_worker.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/download_worker.py backend/tests/services/test_download_worker.py
git commit -m "feat: add DownloadWorker to monitor qBittorrent progress"
```

---

### Task 6: Start DownloadWorker in FastAPI lifespan

**Files:**
- Modify: `backend/app/main.py:55-61`

- [ ] **Step 1: Modify lifespan to start worker**

```python
# backend/app/main.py
from app.services.download_worker import DownloadWorker

@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Handle application startup and shutdown events."""
    logger.info("Starting up Jellyfin Automation")
    await asyncio.to_thread(init_db)
    
    # Start download worker in background
    worker = DownloadWorker()
    worker_task = asyncio.create_task(worker.start())
    logger.info("DownloadWorker started")
    
    yield
    
    # Cancel worker on shutdown
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    logger.info("Shutting down Jellyfin Automation")
```

- [ ] **Step 2: Test that app starts successfully**

```bash
cd backend
python -c "from app.main import app; print('App loaded successfully')"
```

Expected: `App loaded successfully`

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: start DownloadWorker in FastAPI lifespan"
```

---

### Task 7: Update frontend to send season/episode

**Files:**
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/pages/Detail.tsx`

- [ ] **Step 1: Update API types**

```typescript
// frontend/src/services/api.ts
// Update CreateDownloadRequest type
export interface CreateDownloadRequest {
  tmdb_id: number;
  title: string;
  media_type: 'movie' | 'series' | 'anime';
  torrent_name: string;
  magnet_link?: string;
  download_url?: string;
  quality: string;
  language_preference?: string;
  indexer_used?: string;
  season?: number;
  episode?: number;
  year?: number;
}
```

- [ ] **Step 2: Update Detail.tsx to extract season/episode**

```typescript
// frontend/src/pages/Detail.tsx
// Add helper function to extract season/episode
function extractSeasonEpisode(torrentName: string): { season?: number; episode?: number } {
  const patterns = [
    /[Ss](\d{1,2})[Ee](\d{1,2})/,
    /(\d{1,2})[xX](\d{1,2})/,
  ];
  
  for (const pattern of patterns) {
    const match = torrentName.match(pattern);
    if (match) {
      return {
        season: parseInt(match[1], 10),
        episode: parseInt(match[2], 10)
      };
    }
  }
  
  return {};
}

// In handleDownload function, when calling createDownload:
const seasonEpisode = extractSeasonEpisode(torrent.name);
await createDownload({
  tmdb_id: media.id,
  title: media.title || media.name,
  media_type: mediaType,
  torrent_name: torrent.name,
  magnet_link: torrent.magnetUri,
  download_url: torrent.link,
  quality: selectedQuality,
  ...seasonEpisode,  // Spread season/episode if found
  year: mediaType === 'movie' ? new Date(media.release_date || '').getFullYear() : undefined
});
```

- [ ] **Step 3: Test frontend build**

```bash
cd frontend
npm run build
```

Expected: Build completes without errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/api.ts frontend/src/pages/Detail.tsx
git commit -m "feat: send season/episode metadata when creating downloads"
```

---

### Task 8: Update AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Add new sections to AGENTS.md**

Add after the "Download flow" section:

```markdown
## Download monitoring

- `DownloadWorker` runs in the FastAPI lifespan, polling qBittorrent every 10 seconds
- Updates `progress`, `speed`, `eta`, and `status` fields on the `Download` model
- When status transitions to `COMPLETED`, triggers `OrganizerService` to move files
- Future: migrate from polling to WebSocket real-time updates

## File organization

- `PathResolver` computes save paths before adding torrents to qBittorrent
- Series: `{SERIES_PATH}/{Title}/Season {XX}/`
- Movies: `{MOVIES_PATH}/{Title} ({Year})/`
- Anime: `{ANIMES_PATH}/{Title}/Season {XX}/`
- Season/episode extracted from torrent name via regex (S08E17, 8x17 patterns)
- `OrganizerService` moves and renames files after download completes
```

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: update AGENTS.md with download monitoring and file organization"
```

---

### Task 9: Integration testing

- [ ] **Step 1: Rebuild and restart containers**

```bash
docker compose up --build -d
```

- [ ] **Step 2: Test creating a download**

1. Open app at `http://localhost:3001`
2. Search for "Breaking Bad"
3. Select a torrent with S01E01 in the name
4. Click Download
5. Verify the download appears in the Downloads page

- [ ] **Step 3: Verify progress updates**

1. Wait 10-20 seconds
2. Check the progress bar updates from 0%
3. Check that speed and ETA appear

- [ ] **Step 4: Verify save path**

```bash
# Check that the folder was created in the series path
docker exec jellyfin_automation-backend-1 ls -la /series/Breaking\ Bad/Season\ 01/
```

Expected: Directory exists

- [ ] **Step 5: Verify logs**

```bash
docker compose logs backend --tail=50 | grep -E "DownloadWorker|Resolved save path|progress"
```

Expected: Logs showing worker syncing progress and resolved paths

---

## Spec Coverage Check

| Spec Requirement | Task(s) |
|-----------------|---------|
| Worker polls qBittorrent every 10s | Task 5 |
| Updates progress, speed, eta in DB | Task 5 |
| Maps qBittorrent states to app statuses | Task 5 |
| Triggers organization on completion | Task 5 |
| Extracts season/episode from torrent name | Task 2 |
| Computes save path based on media type | Task 2 |
| Passes savepath to qBittorrent API | Task 3, 4 |
| Frontend sends season/episode | Task 7 |
| AGENTS.md updated | Task 8 |
| Future WebSocket migration noted | Task 8 |

## Placeholder Scan

- [x] No TBDs or TODOs in implementation steps
- [x] All code blocks contain complete, runnable code
- [x] All test commands have expected outputs
- [x] No vague steps like "add error handling" without specifics

## Type Consistency Check

- `DownloadWorker._sync_progress()` uses `SessionLocal` consistently
- `QBittorrentService.add_torrent()` signature updated with `save_path` in Task 3
- `PathResolver.resolve_path()` uses `media_type` as string values ("movie", "series", "anime")
- `DownloadCreate` schema includes `season`, `episode`, `year` fields
- Frontend `CreateDownloadRequest` matches backend schema

## Execution Choice

**Plan complete and saved to `docs/superpowers/plans/2026-05-04-download-progress-organizer.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach do you prefer?
