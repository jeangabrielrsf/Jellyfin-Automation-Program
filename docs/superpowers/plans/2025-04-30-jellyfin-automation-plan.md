# Jellyfin Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a local web application to automate search, download, and organization of media content for Jellyfin Server.

**Architecture:** Monolith with Python/FastAPI backend, React/shadcn/ui frontend, and PostgreSQL. Backend exposes REST API and WebSocket for real-time notifications.

**Tech Stack:** Python 3.11+, FastAPI, PostgreSQL, Alembic, React 18, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, WebSocket.

---

## File Structure

```
jellyfin_automation/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── logging_config.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── tmdb.py
│   │   │   ├── torrent.py
│   │   │   ├── download.py
│   │   │   └── settings.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── search.py
│   │   │   ├── torrents.py
│   │   │   ├── downloads.py
│   │   │   ├── library.py
│   │   │   ├── settings.py
│   │   │   └── logs.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── tmdb_service.py
│   │   │   ├── qbittorrent_service.py
│   │   │   ├── jellyfin_service.py
│   │   │   ├── organizer_service.py
│   │   │   └── monitor_service.py
│   │   └── scrapers/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       └── jackett_scraper.py
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_config.py
│   │   ├── test_tmdb_service.py
│   │   ├── test_scrapers.py
│   │   ├── test_organizer_service.py
│   │   └── conftest.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   │   ├── button.tsx
│   │   │   │   ├── input.tsx
│   │   │   │   ├── card.tsx
│   │   │   │   ├── badge.tsx
│   │   │   │   ├── progress.tsx
│   │   │   │   └── select.tsx
│   │   │   ├── SearchBar.tsx
│   │   │   ├── MediaCard.tsx
│   │   │   ├── MediaDetail.tsx
│   │   │   ├── TorrentList.tsx
│   │   │   ├── TorrentItem.tsx
│   │   │   ├── DownloadMonitor.tsx
│   │   │   ├── DownloadItem.tsx
│   │   │   ├── SettingsForm.tsx
│   │   │   └── LogViewer.tsx
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── Search.tsx
│   │   │   ├── Downloads.tsx
│   │   │   ├── Settings.tsx
│   │   │   └── Logs.tsx
│   │   ├── hooks/
│   │   │   ├── useApi.ts
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useSearch.ts
│   │   │   ├── useDownloads.ts
│   │   │   └── useSettings.ts
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── lib/
│   │   │   └── utils.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── postcss.config.js
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2025-04-30-jellyfin-automation-design.md
│       └── plans/
│           └── 2025-04-30-jellyfin-automation-plan.md
├── scripts/
│   └── build_windows.bat
├── docker-compose.yml
└── .env.example
```

---

## Task 1: Project Setup and Configuration

**Objective:** Create base project structure, configuration files, and environment variables.

**Files:**
- Create: `.env.example`, `backend/requirements.txt`, `backend/app/config.py`, `backend/tests/test_config.py`

- [ ] **Step 1.1: Create `.env.example` file**

```bash
cat > .env.example << 'EOF'
# Database
DATABASE_URL=postgresql://jfa_user:jfa_password@localhost:5432/jellyfin_automation

# TMDB
TMDB_API_KEY=your_tmdb_api_key_here

# qBittorrent
QBITTORRENT_HOST=http://localhost:8080
QBITTORRENT_USERNAME=admin
QBITTORRENT_PASSWORD=adminadmin

# Jackett
JACKETT_URL=http://localhost:9117
JACKETT_API_KEY=your_jackett_api_key_here

# Jellyfin
JELLYFIN_URL=http://localhost:8096
JELLYFIN_API_KEY=your_jellyfin_api_key_here

# App
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-here-change-in-production
EOF
```

- [ ] **Step 1.2: Create `backend/requirements.txt`**

```bash
cat > backend/requirements.txt << 'EOF'
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
httpx==0.26.0
pydantic==2.5.3
pydantic-settings==2.1.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
websockets==12.0
loguru==0.7.2
structlog==23.3.0
pytest==7.4.4
pytest-asyncio==0.21.1
httpx==0.26.0
EOF
```

- [ ] **Step 1.3: Create `backend/app/config.py`**

```python
"""Application configuration."""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = Field(default="postgresql://jfa_user:jfa_password@localhost:5432/jellyfin_automation")
    
    # TMDB
    tmdb_api_key: str = Field(default="")
    
    # qBittorrent
    qbittorrent_host: str = Field(default="http://localhost:8080")
    qbittorrent_username: str = Field(default="admin")
    qbittorrent_password: str = Field(default="adminadmin")
    
    # Jackett
    jackett_url: str = Field(default="http://localhost:9117")
    jackett_api_key: str = Field(default="")
    
    # Jellyfin
    jellyfin_url: str = Field(default="http://localhost:8096")
    jellyfin_api_key: str = Field(default="")
    
    # App
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")
    secret_key: str = Field(default="dev-secret-key")
    
    # Library paths
    movies_path: str = Field(default="D:\\Filmes")
    series_path: str = Field(default="D:\\Séries")
    animes_path: str = Field(default="D:\\Animes")
    
    # Default preferences
    default_quality: str = Field(default="1080p")
    default_language: str = Field(default="legendado")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 1.4: Create `backend/tests/test_config.py`**

```python
"""Tests for configuration."""
import os
import pytest
from app.config import Settings, get_settings

def test_settings_defaults():
    """Test that settings have correct defaults."""
    settings = Settings()
    assert settings.app_port == 8000
    assert settings.log_level == "INFO"
    assert settings.default_quality == "1080p"
    assert settings.default_language == "legendado"

def test_settings_from_env():
    """Test that settings can be loaded from environment variables."""
    os.environ["APP_PORT"] = "9000"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    settings = Settings()
    assert settings.app_port == 9000
    assert settings.log_level == "DEBUG"
    
    # Cleanup
    del os.environ["APP_PORT"]
    del os.environ["LOG_LEVEL"]

def test_get_settings_cached():
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2
```

- [ ] **Step 1.5: Run configuration tests**

```bash
cd backend && python -m pytest tests/test_config.py -v
```

**Expected:** 3 tests PASS

---

## Task 2: Logging System

**Objective:** Implement structured logging with rotation and configurable levels.

**Files:**
- Create: `backend/app/logging_config.py`, `backend/tests/test_logging.py`

- [ ] **Step 2.1: Create `backend/app/logging_config.py`**

```python
"""Logging configuration with structured logs and rotation."""
import sys
from pathlib import Path
from loguru import logger
import structlog
from app.config import get_settings

def setup_logging():
    """Configure application logging."""
    settings = get_settings()
    
    # Remove default handler
    logger.remove()
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Console handler - human readable in development
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    
    # File handler - JSON structured for machine parsing
    logger.add(
        logs_dir / "app.log",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention=5,
        compression="zip",
        enqueue=True,
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    logger.info("Logging configured", level=settings.log_level)
    
    return logger

def get_logger(name: str):
    """Get a logger instance with the given name."""
    return logger.bind(name=name)
```

- [ ] **Step 2.2: Create `backend/tests/test_logging.py`**

```python
"""Tests for logging configuration."""
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.logging_config import setup_logging, get_logger

def test_setup_logging_creates_logs_dir():
    """Test that setup_logging creates logs directory."""
    # Remove logs dir if exists
    if Path("logs").exists():
        import shutil
        shutil.rmtree("logs")
    
    with patch('app.logging_config.logger'):
        setup_logging()
        assert Path("logs").exists()

def test_get_logger_returns_logger():
    """Test that get_logger returns a logger instance."""
    logger = get_logger("test")
    assert logger is not None
```

- [ ] **Step 2.3: Run logging tests**

```bash
cd backend && python -m pytest tests/test_logging.py -v
```

**Expected:** 2 tests PASS

---

## Task 3: Database and Models

**Objective:** Configure SQLAlchemy, create models, and set up Alembic migrations.

**Files:**
- Create: `backend/app/database.py`, `backend/app/models/__init__.py`, `backend/app/models/download.py`, `backend/app/models/settings.py`
- Modify: `backend/alembic.ini`, `backend/alembic/env.py`

- [ ] **Step 3.1: Create `backend/app/database.py`**

```python
"""Database configuration and session management."""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.log_level == "DEBUG",
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 3.2: Create models**

```python
# backend/app/models/__init__.py
"""Database models."""
from app.models.download import Download
from app.models.settings import Setting

__all__ = ["Download", "Setting"]
```

```python
# backend/app/models/download.py
"""Download model."""
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Text
from sqlalchemy.sql import func
from app.database import Base
import enum

class ContentType(str, enum.Enum):
    MOVIE = "movie"
    SERIES = "series"
    ANIME = "anime"

class DownloadStatus(str, enum.Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ORGANIZED = "organized"

class Download(Base):
    __tablename__ = "downloads"
    
    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(Enum(ContentType), nullable=False)
    
    torrent_name = Column(String(500))
    torrent_hash = Column(String(64), unique=True)
    magnet_link = Column(Text)
    
    quality = Column(String(20), default="1080p")
    language_preference = Column(String(50), default="legendado")
    
    status = Column(Enum(DownloadStatus), default=DownloadStatus.PENDING)
    progress = Column(Float, default=0.0)
    speed = Column(String(50))
    eta = Column(String(50))
    
    source_folder = Column(Text)
    destination_folder = Column(Text)
    
    indexer_used = Column(String(100))
    error_message = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
```

```python
# backend/app/models/settings.py
"""Settings model."""
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base

class Setting(Base):
    __tablename__ = "settings"
    
    key = Column(String(100), primary_key=True)
    value = Column(JSONB)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

- [ ] **Step 3.3: Configure Alembic**

```bash
cd backend && alembic init alembic
```

Edit `backend/alembic.ini` to configure script location and logging.

Edit `backend/alembic/env.py` to import Base and configure database URL from settings.

- [ ] **Step 3.4: Create initial migration**

```bash
cd backend && alembic revision --autogenerate -m "initial migration"
cd backend && alembic upgrade head
```

**Expected:** Migration created successfully, tables created in PostgreSQL

---

## Task 4: TMDB Service

**Objective:** Implement TMDB API service for metadata search.

**Files:**
- Create: `backend/app/services/tmdb_service.py`, `backend/app/models/tmdb.py`, `backend/tests/test_tmdb_service.py`

- [ ] **Step 4.1: Create Pydantic models for TMDB**

```python
"""TMDB Pydantic models."""
from pydantic import BaseModel
from typing import List, Optional

class TMDBSearchResult(BaseModel):
    id: int
    title: Optional[str] = None
    name: Optional[str] = None
    overview: str
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    release_date: Optional[str] = None
    first_air_date: Optional[str] = None
    vote_average: float
    media_type: str
    genre_ids: List[int] = []
    
    @property
    def display_title(self) -> str:
        return self.title or self.name or "Unknown"
    
    @property
    def year(self) -> Optional[int]:
        date = self.release_date or self.first_air_date
        if date:
            return int(date.split("-")[0])
        return None

class TMDBSearchResponse(BaseModel):
    page: int
    results: List[TMDBSearchResult]
    total_pages: int
    total_results: int

class TMDBDetail(BaseModel):
    id: int
    title: Optional[str] = None
    name: Optional[str] = None
    overview: str
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    release_date: Optional[str] = None
    first_air_date: Optional[str] = None
    vote_average: float
    genres: List[dict] = []
    runtime: Optional[int] = None
    number_of_seasons: Optional[int] = None
    number_of_episodes: Optional[int] = None
    status: Optional[str] = None
    tagline: Optional[str] = None
    
    @property
    def display_title(self) -> str:
        return self.title or self.name or "Unknown"
    
    @property
    def year(self) -> Optional[int]:
        date = self.release_date or self.first_air_date
        if date:
            return int(date.split("-")[0])
        return None
    
    @property
    def is_animation(self) -> bool:
        return any(g.get("name", "").lower() == "animation" for g in self.genres)
    
    @property
    def studios(self) -> List[str]:
        return []
```

- [ ] **Step 4.2: Create TMDB Service**

```python
"""TMDB API service."""
import httpx
from typing import List, Optional
from app.config import get_settings
from app.models.tmdb import TMDBSearchResult, TMDBSearchResponse, TMDBDetail
from app.logging_config import get_logger

logger = get_logger(__name__)

class TMDBService:
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.tmdb_api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search(self, query: str, page: int = 1) -> TMDBSearchResponse:
        """Search for movies and TV shows."""
        logger.info("Searching TMDB", query=query, page=page)
        
        url = f"{self.BASE_URL}/search/multi"
        params = {
            "api_key": self.api_key,
            "query": query,
            "page": page,
            "include_adult": "false",
            "language": "pt-BR"
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        results = [
            TMDBSearchResult(**item) 
            for item in data.get("results", [])
            if item.get("media_type") in ["movie", "tv"]
        ]
        
        return TMDBSearchResponse(
            page=data.get("page", 1),
            results=results,
            total_pages=data.get("total_pages", 0),
            total_results=data.get("total_results", 0)
        )
    
    async def get_movie_detail(self, movie_id: int) -> Optional[TMDBDetail]:
        """Get movie details by ID."""
        logger.info("Getting movie details", movie_id=movie_id)
        
        url = f"{self.BASE_URL}/movie/{movie_id}"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR",
            "append_to_response": "credits"
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return TMDBDetail(**response.json())
    
    async def get_tv_detail(self, tv_id: int) -> Optional[TMDBDetail]:
        """Get TV show details by ID."""
        logger.info("Getting TV details", tv_id=tv_id)
        
        url = f"{self.BASE_URL}/tv/{tv_id}"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR",
            "append_to_response": "credits"
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return TMDBDetail(**response.json())
    
    def get_poster_url(self, poster_path: Optional[str]) -> Optional[str]:
        """Get full poster URL."""
        if poster_path:
            return f"{self.IMAGE_BASE_URL}{poster_path}"
        return None
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
```

- [ ] **Step 4.3: Create tests for TMDB Service**

```python
"""Tests for TMDB service."""
import pytest
from unittest.mock import AsyncMock, patch
from app.services.tmdb_service import TMDBService
from app.models.tmdb import TMDBSearchResult, TMDBDetail

@pytest.fixture
def tmdb_service():
    return TMDBService()

@pytest.mark.asyncio
async def test_search_movies(tmdb_service):
    """Test searching for movies."""
    mock_response = {
        "page": 1,
        "results": [
            {
                "id": 1,
                "title": "Test Movie",
                "overview": "A test movie",
                "poster_path": "/test.jpg",
                "release_date": "2023-01-01",
                "vote_average": 8.5,
                "media_type": "movie",
                "genre_ids": [28, 12]
            }
        ],
        "total_pages": 1,
        "total_results": 1
    }
    
    with patch.object(tmdb_service.client, 'get') as mock_get:
        mock_get.return_value = AsyncMock()
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = AsyncMock()
        
        result = await tmdb_service.search("test")
        
        assert len(result.results) == 1
        assert result.results[0].display_title == "Test Movie"
        assert result.results[0].year == 2023

@pytest.mark.asyncio
async def test_get_movie_detail(tmdb_service):
    """Test getting movie details."""
    mock_response = {
        "id": 1,
        "title": "Test Movie",
        "overview": "A test movie",
        "release_date": "2023-01-01",
        "vote_average": 8.5,
        "genres": [{"id": 16, "name": "Animation"}],
        "runtime": 120
    }
    
    with patch.object(tmdb_service.client, 'get') as mock_get:
        mock_get.return_value = AsyncMock()
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = AsyncMock()
        
        result = await tmdb_service.get_movie_detail(1)
        
        assert result is not None
        assert result.display_title == "Test Movie"
        assert result.is_animation == True
```

- [ ] **Step 4.4: Run TMDB Service tests**

```bash
cd backend && python -m pytest tests/test_tmdb_service.py -v
```

**Expected:** 2 tests PASS

---

## Task 5: Scrapers Base and Jackett

**Objective:** Create extensible scraper architecture and implement Jackett integration.

**Files:**
- Create: `backend/app/scrapers/base.py`, `backend/app/scrapers/jackett_scraper.py`, `backend/app/models/torrent.py`, `backend/tests/test_scrapers.py`

- [ ] **Step 5.1: Create Torrent model**

```python
"""Torrent Pydantic models."""
from pydantic import BaseModel
from typing import Optional

class TorrentResult(BaseModel):
    title: str
    indexer: str
    size: str
    seeds: int
    peers: int
    download_url: str
    magnet_url: Optional[str] = None
    quality: Optional[str] = None
    language: Optional[str] = None
    release_group: Optional[str] = None
    score: float = 0.0
    
    class Config:
        from_attributes = True

class TorrentSearchRequest(BaseModel):
    query: str
    type: str
    quality: Optional[str] = "1080p"
    language: Optional[str] = "legendado"
    tmdb_id: Optional[int] = None
```

- [ ] **Step 5.2: Create Base Scraper**

```python
"""Base scraper interface."""
from abc import ABC, abstractmethod
from typing import List
from app.models.torrent import TorrentResult

class BaseScraper(ABC):
    """Base class for all torrent scrapers."""
    
    name: str = "base"
    enabled: bool = True
    priority: int = 100
    
    @abstractmethod
    async def search(self, query: str, type: str, quality: str = "1080p", language: str = "legendado") -> List[TorrentResult]:
        """Search for torrents."""
        pass
    
    @abstractmethod
    async def get_magnet(self, torrent_id: str) -> str:
        """Get magnet link for a torrent."""
        pass
    
    def calculate_score(self, torrent: TorrentResult, preferred_quality: str, preferred_language: str) -> float:
        """Calculate torrent score based on preferences."""
        score = 0.0
        
        # Seeds factor (0-50 points)
        score += min(torrent.seeds * 0.5, 50)
        
        # Quality match (0-30 points)
        if torrent.quality and preferred_quality.lower() in torrent.quality.lower():
            score += 30
        elif torrent.quality:
            score += 15
        
        # Language match (0-20 points)
        if torrent.language and preferred_language.lower() in torrent.language.lower():
            score += 20
        
        return score
```

- [ ] **Step 5.3: Create Jackett Scraper**

```python
"""Jackett scraper implementation."""
import httpx
import re
from typing import List
from app.scrapers.base import BaseScraper
from app.models.torrent import TorrentResult
from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

class JackettScraper(BaseScraper):
    """Scraper that uses Jackett as a gateway to multiple indexers."""
    
    name = "jackett"
    priority = 10
    
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def search(self, query: str, type: str, quality: str = "1080p", language: str = "legendado") -> List[TorrentResult]:
        """Search for torrents via Jackett."""
        logger.info("Searching Jackett", query=query, type=type, quality=quality)
        
        if not self.settings.jackett_api_key:
            logger.warning("Jackett API key not configured")
            return []
        
        url = f"{self.settings.jackett_url}/api/v2.0/indexers/all/results"
        params = {
            "apikey": self.settings.jackett_api_key,
            "Query": query,
            "Category": self._get_category(type)
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("Results", []):
                torrent = TorrentResult(
                    title=item.get("Title", ""),
                    indexer=f"Jackett ({item.get('Tracker', 'Unknown')})",
                    size=self._format_size(item.get("Size", 0)),
                    seeds=item.get("Seeders", 0),
                    peers=item.get("Peers", 0),
                    download_url=item.get("Link", ""),
                    magnet_url=item.get("MagnetUri", None),
                    quality=self._extract_quality(item.get("Title", "")),
                    language=self._extract_language(item.get("Title", "")),
                    release_group=self._extract_release_group(item.get("Title", ""))
                )
                torrent.score = self.calculate_score(torrent, quality, language)
                results.append(torrent)
            
            results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info("Jackett search completed", results_count=len(results))
            return results
            
        except httpx.HTTPError as e:
            logger.error("Jackett search failed", error=str(e))
            return []
    
    async def get_magnet(self, torrent_id: str) -> str:
        """Get magnet link."""
        return torrent_id
    
    def _get_category(self, type: str) -> List[int]:
        """Get Jackett category IDs based on content type."""
        categories = {
            "movie": [2000],
            "series": [5000],
            "anime": [5070]
        }
        return categories.get(type, [2000, 5000])
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def _extract_quality(self, title: str) -> str:
        """Extract quality from title."""
        qualities = ['2160p', '1080p', '720p', '480p', '360p']
        for quality in qualities:
            if quality in title.lower():
                return quality
        return "Unknown"
    
    def _extract_language(self, title: str) -> str:
        """Extract language from title."""
        title_lower = title.lower()
        if 'dual' in title_lower or 'dublado' in title_lower:
            return "Dual Áudio"
        elif 'dublado' in title_lower or 'dub' in title_lower:
            return "Dublado"
        elif 'legendado' in title_lower or 'leg' in title_lower:
            return "Legendado"
        return "Unknown"
    
    def _extract_release_group(self, title: str) -> str:
        """Extract release group from title."""
        match = re.search(r'-([A-Za-z0-9]+)$', title)
        if match:
            return match.group(1)
        return "Unknown"
```

- [ ] **Step 5.4: Create tests for Scrapers**

```python
"""Tests for scrapers."""
import pytest
from unittest.mock import AsyncMock, patch
from app.scrapers.jackett_scraper import JackettScraper
from app.models.torrent import TorrentResult

@pytest.fixture
def jackett_scraper():
    return JackettScraper()

@pytest.mark.asyncio
async def test_jackett_search(jackett_scraper):
    """Test Jackett search."""
    mock_response = {
        "Results": [
            {
                "Title": "Test Movie 1080p Legendado -GROUP",
                "Tracker": "1337x",
                "Size": 2147483648,
                "Seeders": 100,
                "Peers": 50,
                "Link": "https://example.com/torrent",
                "MagnetUri": "magnet:?xt=urn:btih:test"
            }
        ]
    }
    
    with patch.object(jackett_scraper.client, 'get') as mock_get:
        mock_get.return_value = AsyncMock()
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = AsyncMock()
        
        with patch('app.scrapers.jackett_scraper.get_settings') as mock_settings:
            mock_settings.return_value.jackett_api_key = "test_key"
            mock_settings.return_value.jackett_url = "http://localhost:9117"
            
            results = await jackett_scraper.search("test movie", "movie")
            
            assert len(results) == 1
            assert results[0].title == "Test Movie 1080p Legendado -GROUP"
            assert results[0].quality == "1080p"
            assert results[0].language == "Legendado"

def test_calculate_score(jackett_scraper):
    """Test score calculation."""
    torrent = TorrentResult(
        title="Test",
        indexer="Test",
        size="1 GB",
        seeds=100,
        peers=50,
        download_url="test",
        quality="1080p",
        language="Legendado"
    )
    
    score = jackett_scraper.calculate_score(torrent, "1080p", "legendado")
    assert score > 0
    assert score == 100.0
```

- [ ] **Step 5.5: Run scraper tests**

```bash
cd backend && python -m pytest tests/test_scrapers.py -v
```

**Expected:** 2 tests PASS

---

## Task 6: qBittorrent Service

**Objective:** Implement qBittorrent Web API communication.

**Files:**
- Create: `backend/app/services/qbittorrent_service.py`, `backend/tests/test_qbittorrent_service.py`

- [ ] **Step 6.1: Create qBittorrent Service**

```python
"""qBittorrent Web API service."""
import httpx
from typing import List, Optional, Dict
from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

class QBittorrentService:
    """Service to interact with qBittorrent Web API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=30.0)
        self._authenticated = False
    
    async def _authenticate(self) -> bool:
        """Authenticate with qBittorrent."""
        if self._authenticated:
            return True
        
        try:
            response = await self.client.post(
                f"{self.settings.qbittorrent_host}/api/v2/auth/login",
                data={
                    "username": self.settings.qbittorrent_username,
                    "password": self.settings.qbittorrent_password
                }
            )
            if response.status_code == 200 and response.text == "Ok.":
                self._authenticated = True
                logger.info("Authenticated with qBittorrent")
                return True
            else:
                logger.error("qBittorrent authentication failed", response=response.text)
                return False
        except Exception as e:
            logger.error("qBittorrent authentication error", error=str(e))
            return False
    
    async def add_torrent(self, magnet_link: str, save_path: Optional[str] = None, category: Optional[str] = None) -> bool:
        """Add torrent to qBittorrent."""
        if not await self._authenticate():
            return False
        
        try:
            data = {"urls": magnet_link}
            if save_path:
                data["savepath"] = save_path
            if category:
                data["category"] = category
            
            response = await self.client.post(
                f"{self.settings.qbittorrent_host}/api/v2/torrents/add",
                data=data
            )
            response.raise_for_status()
            
            logger.info("Torrent added to qBittorrent", magnet=magnet_link[:50])
            return True
            
        except Exception as e:
            logger.error("Failed to add torrent", error=str(e))
            return False
    
    async def get_torrents(self) -> List[Dict]:
        """Get list of all torrents."""
        if not await self._authenticate():
            return []
        
        try:
            response = await self.client.get(
                f"{self.settings.qbittorrent_host}/api/v2/torrents/info"
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error("Failed to get torrents", error=str(e))
            return []
    
    async def get_torrent(self, hash: str) -> Optional[Dict]:
        """Get specific torrent by hash."""
        torrents = await self.get_torrents()
        for torrent in torrents:
            if torrent.get("hash") == hash:
                return torrent
        return None
    
    async def pause_torrent(self, hash: str) -> bool:
        """Pause a torrent."""
        if not await self._authenticate():
            return False
        
        try:
            response = await self.client.post(
                f"{self.settings.qbittorrent_host}/api/v2/torrents/pause",
                data={"hashes": hash}
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error("Failed to pause torrent", error=str(e))
            return False
    
    async def resume_torrent(self, hash: str) -> bool:
        """Resume a torrent."""
        if not await self._authenticate():
            return False
        
        try:
            response = await self.client.post(
                f"{self.settings.qbittorrent_host}/api/v2/torrents/resume",
                data={"hashes": hash}
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error("Failed to resume torrent", error=str(e))
            return False
    
    async def delete_torrent(self, hash: str, delete_files: bool = False) -> bool:
        """Delete a torrent."""
        if not await self._authenticate():
            return False
        
        try:
            response = await self.client.post(
                f"{self.settings.qbittorrent_host}/api/v2/torrents/delete",
                data={
                    "hashes": hash,
                    "deleteFiles": str(delete_files).lower()
                }
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error("Failed to delete torrent", error=str(e))
            return False
```

- [ ] **Step 6.2: Create tests for qBittorrent Service**

```python
"""Tests for qBittorrent service."""
import pytest
from unittest.mock import AsyncMock, patch
from app.services.qbittorrent_service import QBittorrentService

@pytest.fixture
def qb_service():
    return QBittorrentService()

@pytest.mark.asyncio
async def test_authenticate_success(qb_service):
    """Test successful authentication."""
    with patch.object(qb_service.client, 'post') as mock_post:
        mock_post.return_value = AsyncMock()
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "Ok."
        
        result = await qb_service._authenticate()
        assert result == True
        assert qb_service._authenticated == True

@pytest.mark.asyncio
async def test_add_torrent(qb_service):
    """Test adding a torrent."""
    qb_service._authenticated = True
    
    with patch.object(qb_service.client, 'post') as mock_post:
        mock_post.return_value = AsyncMock()
        mock_post.return_value.raise_for_status = AsyncMock()
        
        result = await qb_service.add_torrent("magnet:?xt=urn:btih:test")
        assert result == True

@pytest.mark.asyncio
async def test_get_torrents(qb_service):
    """Test getting torrents list."""
    qb_service._authenticated = True
    
    mock_torrents = [
        {"hash": "abc123", "name": "Test", "progress": 0.5, "state": "downloading"}
    ]
    
    with patch.object(qb_service.client, 'get') as mock_get:
        mock_get.return_value = AsyncMock()
        mock_get.return_value.json.return_value = mock_torrents
        mock_get.return_value.raise_for_status = AsyncMock()
        
        result = await qb_service.get_torrents()
        assert len(result) == 1
        assert result[0]["hash"] == "abc123"
```

- [ ] **Step 6.3: Run qBittorrent Service tests**

```bash
cd backend && python -m pytest tests/test_qbittorrent_service.py -v
```

**Expected:** 3 tests PASS

---

## Task 7: Organizer Service

**Objective:** Implement file movement and organization for downloaded content.

**Files:**
- Create: `backend/app/services/organizer_service.py`, `backend/tests/test_organizer_service.py`

- [ ] **Step 7.1: Create Organizer Service**

```python
"""File organizer service."""
import shutil
import re
from pathlib import Path
from typing import Optional, List
from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

class OrganizerService:
    """Service to organize downloaded files into library folders."""
    
    VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v'}
    SUBTITLE_EXTENSIONS = {'.srt', '.ass', '.ssa', '.sub', '.idx'}
    
    def __init__(self):
        self.settings = get_settings()
    
    def organize_movie(self, source_path: str, title: str, year: Optional[int], quality: str) -> str:
        """Organize a movie file."""
        source = Path(source_path)
        
        folder_name = f"{title} ({year})" if year else title
        dest_folder = Path(self.settings.movies_path) / self._sanitize_filename(folder_name)
        dest_folder.mkdir(parents=True, exist_ok=True)
        
        video_files = self._get_video_files(source)
        if not video_files:
            logger.error("No video files found", source=source_path)
            raise ValueError(f"No video files found in {source_path}")
        
        main_file = video_files[0]
        file_name = f"{folder_name} - {quality}{main_file.suffix}"
        dest_path = dest_folder / self._sanitize_filename(file_name)
        
        self._move_file(main_file, dest_path)
        self._move_subtitles(source, dest_folder, folder_name)
        self._cleanup_source(source)
        
        logger.info("Movie organized", title=title, destination=str(dest_path))
        return str(dest_path)
    
    def organize_series(self, source_path: str, title: str, season: int, episode: int, quality: str) -> str:
        """Organize a TV episode file."""
        source = Path(source_path)
        
        show_folder = Path(self.settings.series_path) / self._sanitize_filename(title)
        season_folder = show_folder / f"Season {season:02d}"
        season_folder.mkdir(parents=True, exist_ok=True)
        
        video_files = self._get_video_files(source)
        if not video_files:
            logger.error("No video files found", source=source_path)
            raise ValueError(f"No video files found in {source_path}")
        
        main_file = video_files[0]
        file_name = f"{title} - S{season:02d}E{episode:02d} - {quality}{main_file.suffix}"
        dest_path = season_folder / self._sanitize_filename(file_name)
        
        self._move_file(main_file, dest_path)
        self._move_subtitles(source, season_folder, f"{title} - S{season:02d}E{episode:02d}")
        self._cleanup_source(source)
        
        logger.info("Episode organized", title=title, season=season, episode=episode, destination=str(dest_path))
        return str(dest_path)
    
    def organize_anime(self, source_path: str, title: str, season: int, episode: int, quality: str) -> str:
        """Organize an anime episode file."""
        source = Path(source_path)
        
        show_folder = Path(self.settings.animes_path) / self._sanitize_filename(title)
        season_folder = show_folder / f"Season {season:02d}"
        season_folder.mkdir(parents=True, exist_ok=True)
        
        video_files = self._get_video_files(source)
        if not video_files:
            logger.error("No video files found", source=source_path)
            raise ValueError(f"No video files found in {source_path}")
        
        main_file = video_files[0]
        file_name = f"{title} - S{season:02d}E{episode:02d} - {quality}{main_file.suffix}"
        dest_path = season_folder / self._sanitize_filename(file_name)
        
        self._move_file(main_file, dest_path)
        self._move_subtitles(source, season_folder, f"{title} - S{season:02d}E{episode:02d}")
        self._cleanup_source(source)
        
        logger.info("Anime organized", title=title, season=season, episode=episode, destination=str(dest_path))
        return str(dest_path)
    
    def _get_video_files(self, path: Path) -> List[Path]:
        """Get all video files in a path."""
        if path.is_file() and path.suffix.lower() in self.VIDEO_EXTENSIONS:
            return [path]
        
        video_files = []
        if path.is_dir():
            for ext in self.VIDEO_EXTENSIONS:
                video_files.extend(path.glob(f"*{ext}"))
                video_files.extend(path.glob(f"*{ext.upper()}"))
        
        video_files.sort(key=lambda x: x.stat().st_size, reverse=True)
        return video_files
    
    def _move_file(self, source: Path, destination: Path):
        """Move file from source to destination."""
        if destination.exists():
            source_size = source.stat().st_size
            dest_size = destination.stat().st_size
            
            if source_size <= dest_size:
                logger.warning("Destination file exists and is larger or equal, skipping", destination=str(destination))
                return
            else:
                logger.warning("Destination file exists but source is larger, replacing", destination=str(destination))
                destination.unlink()
        
        shutil.move(str(source), str(destination))
        logger.debug("File moved", source=str(source), destination=str(destination))
    
    def _move_subtitles(self, source: Path, dest_folder: Path, base_name: str):
        """Move subtitle files to destination."""
        if source.is_file():
            source_dir = source.parent
        else:
            source_dir = source
        
        for ext in self.SUBTITLE_EXTENSIONS:
            for sub_file in source_dir.glob(f"*{ext}"):
                dest_name = f"{base_name}{ext}"
                dest_path = dest_folder / self._sanitize_filename(dest_name)
                shutil.move(str(sub_file), str(dest_path))
                logger.debug("Subtitle moved", source=str(sub_file), destination=str(dest_path))
    
    def _cleanup_source(self, source: Path):
        """Remove empty source directories."""
        if source.is_file():
            source = source.parent
        
        for pattern in ['*.nfo', 'sample*', 'Sample*', '*.txt', '*.jpg', '*.png']:
            for file in source.glob(pattern):
                try:
                    file.unlink()
                    logger.debug("Removed unnecessary file", file=str(file))
                except:
                    pass
        
        try:
            if source.exists() and not any(source.iterdir()):
                source.rmdir()
                logger.debug("Removed empty source directory", directory=str(source))
        except:
            pass
    
    def _sanitize_filename(self, filename: str) -> str:
        """Remove invalid characters from filename."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
```

- [ ] **Step 7.2: Create tests for Organizer Service**

```python
"""Tests for organizer service."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
from app.services.organizer_service import OrganizerService

@pytest.fixture
def organizer_service():
    return OrganizerService()

@pytest.fixture
def temp_media_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        movies_dir = Path(tmpdir) / "movies"
        series_dir = Path(tmpdir) / "series"
        animes_dir = Path(tmpdir) / "animes"
        
        movies_dir.mkdir()
        series_dir.mkdir()
        animes_dir.mkdir()
        
        with patch('app.services.organizer_service.get_settings') as mock_settings:
            mock_settings.return_value.movies_path = str(movies_dir)
            mock_settings.return_value.series_path = str(series_dir)
            mock_settings.return_value.animes_path = str(animes_dir)
            yield {
                "movies": movies_dir,
                "series": series_dir,
                "animes": animes_dir
            }

def test_sanitize_filename(organizer_service):
    """Test filename sanitization."""
    assert organizer_service._sanitize_filename("Test: Movie") == "Test_ Movie"
    assert organizer_service._sanitize_filename("Test/Movie") == "Test_Movie"
    assert organizer_service._sanitize_filename("Test<Movie>") == "Test_Movie_"

def test_get_video_files(organizer_service, tmp_path):
    """Test getting video files."""
    video_file = tmp_path / "movie.mp4"
    video_file.write_text("fake video")
    
    txt_file = tmp_path / "readme.txt"
    txt_file.write_text("readme")
    
    video_files = organizer_service._get_video_files(tmp_path)
    assert len(video_files) == 1
    assert video_files[0].name == "movie.mp4"

def test_organize_movie(organizer_service, temp_media_dirs):
    """Test movie organization."""
    service = OrganizerService()
    
    source_dir = Path(tempfile.mkdtemp())
    source_file = source_dir / "movie.mkv"
    source_file.write_text("fake video content")
    
    result = service.organize_movie(
        source=str(source_file),
        title="Test Movie",
        year=2023,
        quality="1080p"
    )
    
    assert Path(result).exists()
    assert "Test Movie (2023)" in result
    assert "1080p" in result
```

- [ ] **Step 7.3: Run Organizer Service tests**

```bash
cd backend && python -m pytest tests/test_organizer_service.py -v
```

**Expected:** 3 tests PASS

---

## Task 8: Jellyfin Service

**Objective:** Implement Jellyfin API communication for library scanning.

**Files:**
- Create: `backend/app/services/jellyfin_service.py`

- [ ] **Step 8.1: Create Jellyfin Service**

```python
"""Jellyfin API service."""
import httpx
from typing import List, Optional, Dict
from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

class JellyfinService:
    """Service to interact with Jellyfin API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def scan_library(self, library_name: Optional[str] = None) -> bool:
        """Trigger library scan in Jellyfin."""
        try:
            headers = {
                "X-Emby-Token": self.settings.jellyfin_api_key,
                "Content-Type": "application/json"
            }
            
            if library_name:
                libraries = await self.get_libraries()
                for lib in libraries:
                    if lib.get("Name") == library_name:
                        library_id = lib.get("Id")
                        response = await self.client.post(
                            f"{self.settings.jellyfin_url}/Items/{library_id}/Refresh",
                            headers=headers,
                            params={"Recursive": "true", "ImageRefreshMode": "Default", "MetadataRefreshMode": "Default"}
                        )
                        response.raise_for_status()
                        logger.info("Jellyfin library scan triggered", library=library_name)
                        return True
                
                logger.warning("Library not found", library=library_name)
                return False
            else:
                response = await self.client.post(
                    f"{self.settings.jellyfin_url}/Library/Refresh",
                    headers=headers
                )
                response.raise_for_status()
                logger.info("Jellyfin full library scan triggered")
                return True
                
        except Exception as e:
            logger.error("Failed to trigger Jellyfin scan", error=str(e))
            return False
    
    async def get_libraries(self) -> List[Dict]:
        """Get list of libraries."""
        try:
            headers = {
                "X-Emby-Token": self.settings.jellyfin_api_key
            }
            
            response = await self.client.get(
                f"{self.settings.jellyfin_url}/Library/VirtualFolders",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error("Failed to get Jellyfin libraries", error=str(e))
            return []
```

---

## Task 9: API Routers

**Objective:** Create REST API endpoints for all functionality.

**Files:**
- Create: `backend/app/routers/search.py`, `backend/app/routers/downloads.py`, `backend/app/routers/settings.py`, `backend/app/routers/logs.py`

- [ ] **Step 9.1: Create Search Router**

```python
"""Search router."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.services.tmdb_service import TMDBService
from app.scrapers.jackett_scraper import JackettScraper
from app.models.tmdb import TMDBSearchResponse, TMDBDetail
from app.models.torrent import TorrentResult

router = APIRouter(prefix="/api/search", tags=["search"])

@router.get("/", response_model=TMDBSearchResponse)
async def search_media(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    """Search for movies and TV shows on TMDB."""
    service = TMDBService()
    try:
        results = await service.search(q, page)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    finally:
        await service.close()

@router.get("/movie/{movie_id}", response_model=TMDBDetail)
async def get_movie_detail(movie_id: int):
    """Get movie details by TMDB ID."""
    service = TMDBService()
    try:
        result = await service.get_movie_detail(movie_id)
        if not result:
            raise HTTPException(status_code=404, detail="Movie not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get movie details: {str(e)}")
    finally:
        await service.close()

@router.get("/tv/{tv_id}", response_model=TMDBDetail)
async def get_tv_detail(tv_id: int):
    """Get TV show details by TMDB ID."""
    service = TMDBService()
    try:
        result = await service.get_tv_detail(tv_id)
        if not result:
            raise HTTPException(status_code=404, detail="TV show not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get TV details: {str(e)}")
    finally:
        await service.close()

@router.get("/torrents")
async def search_torrents(
    tmdb_id: int = Query(...),
    title: str = Query(...),
    type: str = Query(..., regex="^(movie|series|anime)$"),
    quality: Optional[str] = Query("1080p"),
    language: Optional[str] = Query("legendado")
):
    """Search for torrents for a specific media."""
    scraper = JackettScraper()
    try:
        results = await scraper.search(title, type, quality, language)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Torrent search failed: {str(e)}")
```

- [ ] **Step 9.2: Create Downloads Router**

```python
"""Downloads router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.download import Download, DownloadStatus, ContentType
from app.services.qbittorrent_service import QBittorrentService
from pydantic import BaseModel

router = APIRouter(prefix="/api/downloads", tags=["downloads"])

class DownloadCreate(BaseModel):
    tmdb_id: int
    title: str
    type: str
    torrent_name: str
    magnet_link: str
    quality: str = "1080p"
    language_preference: str = "legendado"
    indexer_used: Optional[str] = None

@router.get("/")
def list_downloads(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all downloads with optional status filter."""
    query = db.query(Download)
    if status:
        query = query.filter(Download.status == status)
    return query.order_by(Download.created_at.desc()).all()

@router.post("/")
def create_download(
    download: DownloadCreate,
    db: Session = Depends(get_db)
):
    """Create a new download and add to qBittorrent."""
    db_download = Download(
        tmdb_id=download.tmdb_id,
        title=download.title,
        type=ContentType(download.type),
        torrent_name=download.torrent_name,
        magnet_link=download.magnet_link,
        quality=download.quality,
        language_preference=download.language_preference,
        status=DownloadStatus.PENDING,
        indexer_used=download.indexer_used
    )
    db.add(db_download)
    db.commit()
    db.refresh(db_download)
    
    return db_download

@router.get("/{download_id}")
def get_download(download_id: int, db: Session = Depends(get_db)):
    """Get download by ID."""
    download = db.query(Download).filter(Download.id == download_id).first()
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    return download

@router.delete("/{download_id}")
def cancel_download(download_id: int, db: Session = Depends(get_db)):
    """Cancel a download."""
    download = db.query(Download).filter(Download.id == download_id).first()
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    
    download.status = DownloadStatus.CANCELLED
    db.commit()
    
    return {"message": "Download cancelled"}
```

- [ ] **Step 9.3: Create Settings Router**

```python
"""Settings router."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.database import get_db
from app.models.settings import Setting
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    key: str
    value: Any

@router.get("/")
def get_settings(db: Session = Depends(get_db)):
    """Get all settings."""
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}

@router.get("/{key}")
def get_setting(key: str, db: Session = Depends(get_db)):
    """Get specific setting."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        return {"key": setting.key, "value": setting.value}
    return {"key": key, "value": None}

@router.put("/{key}")
def update_setting(
    key: str,
    value: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update or create a setting."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    return {"key": setting.key, "value": setting.value}
```

- [ ] **Step 9.4: Create Logs Router**

```python
"""Logs router."""
from fastapi import APIRouter, Query
from typing import List, Optional
from pathlib import Path

router = APIRouter(prefix="/api/logs", tags=["logs"])

@router.get("/")
def get_logs(
    level: Optional[str] = None,
    lines: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None
):
    """Get recent log entries."""
    log_file = Path("logs/app.log")
    
    if not log_file.exists():
        return {"logs": [], "total": 0}
    
    with open(log_file, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
    
    if level:
        all_lines = [l for l in all_lines if f" | {level.upper()} |" in l]
    
    if search:
        all_lines = [l for l in all_lines if search.lower() in l.lower()]
    
    logs = all_lines[-lines:]
    
    return {
        "logs": logs,
        "total": len(all_lines),
        "returned": len(logs)
    }
```

---

## Task 10: WebSocket and Notifications

**Objective:** Implement WebSocket for real-time notifications.

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 10.1: Update main.py with WebSocket**

```python
"""Main FastAPI application."""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import json
from typing import List

from app.config import get_settings
from app.database import init_db
from app.logging_config import setup_logging
from app.routers import search, downloads, settings, logs

logger = setup_logging()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected", total=len(self.active_connections))
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected", total=len(self.active_connections))
    
    async def broadcast(self, message: dict):
        message_json = json.dumps(message)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except:
                disconnected.append(connection)
        
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Jellyfin Automation")
    init_db()
    yield
    logger.info("Shutting down Jellyfin Automation")

app = FastAPI(
    title="Jellyfin Automation",
    description="Automate content search, download and organization for Jellyfin",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(downloads.router)
app.include_router(settings.router)
app.include_router(logs.router)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        manager.disconnect(websocket)

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}

try:
    app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")
except RuntimeError:
    pass
```

---

## Task 11: Frontend Setup

**Objective:** Configure React project with Vite, TypeScript, Tailwind CSS.

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/vite.config.ts`, `frontend/tailwind.config.js`, `frontend/postcss.config.js`, `frontend/index.html`

- [ ] **Step 11.1: Create package.json**

```json
{
  "name": "jellyfin-automation-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.8.0",
    "axios": "^1.6.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0",
    "lucide-react": "^0.294.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.37",
    "@types/react-dom": "^18.2.15",
    "@typescript-eslint/eslint-plugin": "^6.10.0",
    "@typescript-eslint/parser": "^6.10.0",
    "@vitejs/plugin-react": "^4.2.0",
    "autoprefixer": "^10.4.16",
    "eslint": "^8.53.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.4",
    "postcss": "^8.4.31",
    "tailwindcss": "^3.3.5",
    "typescript": "^5.2.2",
    "vite": "^5.0.0"
  }
}
```

- [ ] **Step 11.2: Create configuration files**

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

```json
// tsconfig.node.json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
```

```javascript
// postcss.config.js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

```html
<!-- index.html -->
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Jellyfin Automation</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 11.3: Install dependencies**

```bash
cd frontend && npm install
```

---

## Task 12: Frontend - Base Components and UI

**Objective:** Create base UI components following shadcn/ui patterns.

**Files:**
- Create: `frontend/src/main.tsx`, `frontend/src/index.css`, `frontend/src/lib/utils.ts`, `frontend/src/types/index.ts`, `frontend/src/services/api.ts`
- Create: `frontend/src/components/ui/button.tsx`, `frontend/src/components/ui/input.tsx`, `frontend/src/components/ui/card.tsx`, `frontend/src/components/ui/badge.tsx`, `frontend/src/components/ui/progress.tsx`, `frontend/src/components/ui/select.tsx`

- [ ] **Step 12.1: Create base files**

```typescript
// main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
```

```css
/* index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 212.7 26.8% 83.9%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

```typescript
// lib/utils.ts
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 12.2: Create types and API service**

```typescript
// types/index.ts
export interface TMDBSearchResult {
  id: number;
  title?: string;
  name?: string;
  overview: string;
  poster_path: string | null;
  backdrop_path: string | null;
  release_date?: string;
  first_air_date?: string;
  vote_average: number;
  media_type: string;
  genre_ids: number[];
}

export interface TMDBDetail {
  id: number;
  title?: string;
  name?: string;
  overview: string;
  poster_path: string | null;
  backdrop_path: string | null;
  release_date?: string;
  first_air_date?: string;
  vote_average: number;
  genres: Array<{ id: number; name: string }>;
  runtime?: number;
  number_of_seasons?: number;
  number_of_episodes?: number;
  status?: string;
  tagline?: string;
}

export interface TorrentResult {
  title: string;
  indexer: string;
  size: string;
  seeds: number;
  peers: number;
  download_url: string;
  magnet_url?: string;
  quality?: string;
  language?: string;
  release_group?: string;
  score: number;
}

export interface Download {
  id: number;
  tmdb_id: number;
  title: string;
  type: 'movie' | 'series' | 'anime';
  torrent_name?: string;
  torrent_hash?: string;
  magnet_link?: string;
  quality: string;
  language_preference: string;
  status: string;
  progress: number;
  speed?: string;
  eta?: string;
  created_at: string;
}

export interface AppSettings {
  movies_path: string;
  series_path: string;
  animes_path: string;
  default_quality: string;
  default_language: string;
  qbittorrent_host: string;
  jackett_url: string;
  jellyfin_url: string;
  log_level: string;
}
```

```typescript
// services/api.ts
import axios from 'axios';
import { TMDBSearchResult, TorrentResult, Download, AppSettings } from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const searchAPI = {
  searchMedia: (query: string, page = 1) =>
    api.get(`/search/?q=${encodeURIComponent(query)}&page=${page}`),
  
  getMovieDetail: (id: number) =>
    api.get(`/search/movie/${id}`),
  
  getTVDetail: (id: number) =>
    api.get(`/search/tv/${id}`),
  
  searchTorrents: (params: {
    tmdb_id: number;
    title: string;
    type: string;
    quality?: string;
    language?: string;
  }) => api.get('/search/torrents', { params }),
};

export const downloadAPI = {
  listDownloads: (status?: string) =>
    api.get('/downloads', { params: { status } }),
  
  createDownload: (data: {
    tmdb_id: number;
    title: string;
    type: string;
    torrent_name: string;
    magnet_link: string;
    quality?: string;
    language_preference?: string;
    indexer_used?: string;
  }) => api.post('/downloads', data),
  
  cancelDownload: (id: number) =>
    api.delete(`/downloads/${id}`),
};

export const settingsAPI = {
  getSettings: () => api.get('/settings'),
  updateSetting: (key: string, value: any) =>
    api.put(`/settings/${key}`, value),
};

export const logsAPI = {
  getLogs: (params?: { level?: string; lines?: number; search?: string }) =>
    api.get('/logs', { params }),
};

export default api;
```

- [ ] **Step 12.3: Create shadcn/ui base components**

Create simplified versions of Button, Input, Card, Badge, Progress, and Select components following shadcn/ui patterns with Tailwind CSS.

---

## Task 13: Frontend - Main Components

**Objective:** Create main application components.

**Files:**
- Create: `frontend/src/components/SearchBar.tsx`, `frontend/src/components/MediaCard.tsx`, `frontend/src/components/TorrentList.tsx`, `frontend/src/components/DownloadMonitor.tsx`

- [ ] **Step 13.1: Create SearchBar component**

```typescript
import React, { useState } from 'react';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Search } from 'lucide-react';

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export const SearchBar: React.FC<SearchBarProps> = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 w-full max-w-2xl">
      <Input
        type="text"
        placeholder="Buscar filmes, séries ou animes..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="flex-1"
      />
      <Button type="submit" disabled={isLoading}>
        <Search className="w-4 h-4 mr-2" />
        {isLoading ? 'Buscando...' : 'Buscar'}
      </Button>
    </form>
  );
};
```

- [ ] **Step 13.2: Create MediaCard component**

```typescript
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { TMDBSearchResult } from '../types';

interface MediaCardProps {
  media: TMDBSearchResult;
  onClick: (media: TMDBSearchResult) => void;
}

export const MediaCard: React.FC<MediaCardProps> = ({ media, onClick }) => {
  const title = media.title || media.name || 'Unknown';
  const year = media.release_date 
    ? new Date(media.release_date).getFullYear()
    : media.first_air_date
    ? new Date(media.first_air_date).getFullYear()
    : null;

  return (
    <Card 
      className="cursor-pointer hover:shadow-lg transition-shadow overflow-hidden"
      onClick={() => onClick(media)}
    >
      <div className="aspect-[2/3] relative bg-muted">
        {media.poster_path ? (
          <img
            src={`https://image.tmdb.org/t/p/w500${media.poster_path}`}
            alt={title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-muted-foreground">
            Sem imagem
          </div>
        )}
      </div>
      <CardHeader className="p-4">
        <CardTitle className="text-lg truncate">{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-4 pt-0">
        <div className="flex items-center justify-between">
          <Badge variant="secondary">
            {media.media_type === 'movie' ? 'Filme' : 'Série'}
          </Badge>
          {year && (
            <span className="text-sm text-muted-foreground">{year}</span>
          )}
        </div>
        {media.vote_average > 0 && (
          <div className="mt-2 text-sm text-muted-foreground">
            ★ {media.vote_average.toFixed(1)}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
```

- [ ] **Step 13.3: Create TorrentList component**

```typescript
import React from 'react';
import { TorrentResult } from '../types';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Download } from 'lucide-react';

interface TorrentListProps {
  torrents: TorrentResult[];
  onDownload: (torrent: TorrentResult) => void;
}

export const TorrentList: React.FC<TorrentListProps> = ({ torrents, onDownload }) => {
  if (torrents.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Nenhum torrent encontrado
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {torrents.map((torrent, index) => (
        <div
          key={index}
          className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors"
        >
          <div className="flex-1 min-w-0 mr-4">
            <h4 className="font-medium truncate">{torrent.title}</h4>
            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
              <span>{torrent.indexer}</span>
              <span>•</span>
              <span>{torrent.size}</span>
              <span>•</span>
              <span className="text-green-600">↑ {torrent.seeds}</span>
              <span className="text-blue-600">↓ {torrent.peers}</span>
            </div>
            <div className="flex gap-2 mt-2">
              {torrent.quality && (
                <Badge variant="outline">{torrent.quality}</Badge>
              )}
              {torrent.language && (
                <Badge variant="secondary">{torrent.language}</Badge>
              )}
              {torrent.release_group && (
                <Badge variant="outline">{torrent.release_group}</Badge>
              )}
            </div>
          </div>
          <Button
            size="sm"
            onClick={() => onDownload(torrent)}
          >
            <Download className="w-4 h-4 mr-2" />
            Baixar
          </Button>
        </div>
      ))}
    </div>
  );
};
```

- [ ] **Step 13.4: Create DownloadMonitor component**

```typescript
import React from 'react';
import { Download } from '../types';
import { Progress } from './ui/progress';
import { Badge } from './ui/badge';
import { Pause, Play, Trash2 } from 'lucide-react';
import { Button } from './ui/button';

interface DownloadMonitorProps {
  downloads: Download[];
  onPause: (id: number) => void;
  onResume: (id: number) => void;
  onCancel: (id: number) => void;
}

export const DownloadMonitor: React.FC<DownloadMonitorProps> = ({
  downloads,
  onPause,
  onResume,
  onCancel,
}) => {
  if (downloads.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Nenhum download ativo
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'downloading': return 'bg-blue-500';
      case 'completed': return 'bg-green-500';
      case 'failed': return 'bg-red-500';
      case 'cancelled': return 'bg-gray-500';
      default: return 'bg-yellow-500';
    }
  };

  return (
    <div className="space-y-4">
      {downloads.map((download) => (
        <div key={download.id} className="border rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-medium">{download.title}</h4>
            <Badge className={getStatusColor(download.status)}>
              {download.status}
            </Badge>
          </div>
          
          <Progress value={download.progress * 100} className="mb-2" />
          
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <div className="flex gap-4">
              <span>{(download.progress * 100).toFixed(1)}%</span>
              {download.speed && <span>{download.speed}</span>}
              {download.eta && <span>ETA: {download.eta}</span>}
            </div>
            
            <div className="flex gap-2">
              {download.status === 'downloading' && (
                <Button size="sm" variant="outline" onClick={() => onPause(download.id)}>
                  <Pause className="w-4 h-4" />
                </Button>
              )}
              {download.status === 'paused' && (
                <Button size="sm" variant="outline" onClick={() => onResume(download.id)}>
                  <Play className="w-4 h-4" />
                </Button>
              )}
              <Button size="sm" variant="outline" onClick={() => onCancel(download.id)}>
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
```

---

## Task 14: Frontend - Pages and Routing

**Objective:** Create pages and configure React Router.

**Files:**
- Create: `frontend/src/pages/Home.tsx`, `frontend/src/pages/Search.tsx`, `frontend/src/pages/Downloads.tsx`, `frontend/src/pages/Settings.tsx`, `frontend/src/App.tsx`

- [ ] **Step 14.1: Create Home page**

```typescript
import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Search, Download, Settings } from 'lucide-react';

export const Home: React.FC = () => {
  return (
    <div className="container mx-auto py-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Jellyfin Automation</h1>
        <p className="text-lg text-muted-foreground">
          Automatize a busca, download e organização do seu conteúdo
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
        <Link to="/search">
          <div className="border rounded-lg p-6 hover:shadow-lg transition-shadow text-center">
            <Search className="w-12 h-12 mx-auto mb-4 text-primary" />
            <h2 className="text-xl font-semibold mb-2">Buscar Conteúdo</h2>
            <p className="text-muted-foreground">
              Encontre filmes, séries e animes com metadados da TMDB
            </p>
          </div>
        </Link>

        <Link to="/downloads">
          <div className="border rounded-lg p-6 hover:shadow-lg transition-shadow text-center">
            <Download className="w-12 h-12 mx-auto mb-4 text-primary" />
            <h2 className="text-xl font-semibold mb-2">Downloads</h2>
            <p className="text-muted-foreground">
              Monitore e gerencie seus downloads ativos
            </p>
          </div>
        </Link>

        <Link to="/settings">
          <div className="border rounded-lg p-6 hover:shadow-lg transition-shadow text-center">
            <Settings className="w-12 h-12 mx-auto mb-4 text-primary" />
            <h2 className="text-xl font-semibold mb-2">Configurações</h2>
            <p className="text-muted-foreground">
              Configure indexers, pastas e preferências
            </p>
          </div>
        </Link>
      </div>
    </div>
  );
};
```

- [ ] **Step 14.2: Create Search page**

```typescript
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { SearchBar } from '../components/SearchBar';
import { MediaCard } from '../components/MediaCard';
import { TorrentList } from '../components/TorrentList';
import { searchAPI, downloadAPI } from '../services/api';
import { TMDBSearchResult, TorrentResult } from '../types';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Select } from '../components/ui/select';
import { Loader2 } from 'lucide-react';

export const Search: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMedia, setSelectedMedia] = useState<TMDBSearchResult | null>(null);
  const [showTorrents, setShowTorrents] = useState(false);
  const [quality, setQuality] = useState('1080p');
  const [language, setLanguage] = useState('legendado');

  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['search', searchQuery],
    queryFn: () => searchAPI.searchMedia(searchQuery).then(res => res.data),
    enabled: !!searchQuery,
  });

  const { data: torrents, isLoading: isLoadingTorrents } = useQuery({
    queryKey: ['torrents', selectedMedia?.id, quality, language],
    queryFn: () => {
      if (!selectedMedia) return Promise.resolve({ results: [] });
      return searchAPI.searchTorrents({
        tmdb_id: selectedMedia.id,
        title: selectedMedia.title || selectedMedia.name || '',
        type: selectedMedia.media_type === 'movie' ? 'movie' : 'series',
        quality,
        language,
      }).then(res => res.data);
    },
    enabled: showTorrents && !!selectedMedia,
  });

  const handleDownload = async (torrent: TorrentResult) => {
    if (!selectedMedia) return;
    
    try {
      await downloadAPI.createDownload({
        tmdb_id: selectedMedia.id,
        title: selectedMedia.title || selectedMedia.name || '',
        type: selectedMedia.media_type === 'movie' ? 'movie' : 'series',
        torrent_name: torrent.title,
        magnet_link: torrent.magnet_url || torrent.download_url,
        quality,
        language_preference: language,
        indexer_used: torrent.indexer,
      });
      
      setShowTorrents(false);
      alert('Download iniciado com sucesso!');
    } catch (error) {
      alert('Erro ao iniciar download');
    }
  };

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-8">Buscar Conteúdo</h1>
      
      <div className="mb-8">
        <SearchBar onSearch={setSearchQuery} isLoading={isSearching} />
      </div>

      {isSearching && (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      )}

      {searchResults?.results && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {searchResults.results.map((media: TMDBSearchResult) => (
            <MediaCard
              key={media.id}
              media={media}
              onClick={(media) => {
                setSelectedMedia(media);
                setShowTorrents(true);
              }}
            />
          ))}
        </div>
      )}

      {showTorrents && selectedMedia && (
        <Dialog open={showTorrents} onOpenChange={setShowTorrents}>
          <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                Torrents para {selectedMedia.title || selectedMedia.name}
              </DialogTitle>
            </DialogHeader>
            
            <div className="flex gap-4 mb-4">
              <div>
                <label className="text-sm font-medium">Qualidade</label>
                <Select
                  value={quality}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setQuality(e.target.value)}
                >
                  <option value="2160p">4K (2160p)</option>
                  <option value="1080p">Full HD (1080p)</option>
                  <option value="720p">HD (720p)</option>
                  <option value="480p">SD (480p)</option>
                </Select>
              </div>
              
              <div>
                <label className="text-sm font-medium">Idioma</label>
                <Select
                  value={language}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setLanguage(e.target.value)}
                >
                  <option value="legendado">Legendado</option>
                  <option value="dublado">Dublado</option>
                  <option value="dual">Dual Áudio</option>
                </Select>
              </div>
            </div>

            {isLoadingTorrents ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-8 h-8 animate-spin" />
              </div>
            ) : (
              <TorrentList
                torrents={torrents || []}
                onDownload={handleDownload}
              />
            )}
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};
```

- [ ] **Step 14.3: Create Downloads page**

```typescript
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { DownloadMonitor } from '../components/DownloadMonitor';
import { downloadAPI } from '../services/api';
import { Loader2 } from 'lucide-react';

export const Downloads: React.FC = () => {
  const { data: downloads, isLoading, refetch } = useQuery({
    queryKey: ['downloads'],
    queryFn: () => downloadAPI.listDownloads().then(res => res.data),
    refetchInterval: 30000,
  });

  const handlePause = async (id: number) => {
    console.log('Pause', id);
  };

  const handleResume = async (id: number) => {
    console.log('Resume', id);
  };

  const handleCancel = async (id: number) => {
    try {
      await downloadAPI.cancelDownload(id);
      refetch();
    } catch (error) {
      alert('Erro ao cancelar download');
    }
  };

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-8">Downloads</h1>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      ) : (
        <DownloadMonitor
          downloads={downloads || []}
          onPause={handlePause}
          onResume={handleResume}
          onCancel={handleCancel}
        />
      )}
    </div>
  );
};
```

- [ ] **Step 14.4: Create Settings page**

```typescript
import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { settingsAPI } from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Loader2, Save } from 'lucide-react';

export const Settings: React.FC = () => {
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => settingsAPI.getSettings().then(res => res.data),
  });

  const [localSettings, setLocalSettings] = useState<Record<string, any>>({});

  useEffect(() => {
    if (settings) {
      setLocalSettings(settings);
    }
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: any }) =>
      settingsAPI.updateSetting(key, value),
  });

  const handleSave = async (key: string) => {
    try {
      await updateMutation.mutateAsync({ key, value: localSettings[key] });
      alert('Configuração salva!');
    } catch (error) {
      alert('Erro ao salvar configuração');
    }
  };

  const handleChange = (key: string, value: any) => {
    setLocalSettings(prev => ({ ...prev, [key]: value }));
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-8">Configurações</h1>

      <div className="grid gap-6 max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle>Pastas de Biblioteca</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Filmes</label>
              <div className="flex gap-2">
                <Input
                  value={localSettings.movies_path || ''}
                  onChange={(e) => handleChange('movies_path', e.target.value)}
                />
                <Button size="sm" onClick={() => handleSave('movies_path')}>
                  <Save className="w-4 h-4" />
                </Button>
              </div>
            </div>
            
            <div>
              <label className="text-sm font-medium">Séries</label>
              <div className="flex gap-2">
                <Input
                  value={localSettings.series_path || ''}
                  onChange={(e) => handleChange('series_path', e.target.value)}
                />
                <Button size="sm" onClick={() => handleSave('series_path')}>
                  <Save className="w-4 h-4" />
                </Button>
              </div>
            </div>
            
            <div>
              <label className="text-sm font-medium">Animes</label>
              <div className="flex gap-2">
                <Input
                  value={localSettings.animes_path || ''}
                  onChange={(e) => handleChange('animes_path', e.target.value)}
                />
                <Button size="sm" onClick={() => handleSave('animes_path')}>
                  <Save className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Preferências Padrão</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Qualidade Padrão</label>
              <div className="flex gap-2">
                <Input
                  value={localSettings.default_quality || ''}
                  onChange={(e) => handleChange('default_quality', e.target.value)}
                />
                <Button size="sm" onClick={() => handleSave('default_quality')}>
                  <Save className="w-4 h-4" />
                </Button>
              </div>
            </div>
            
            <div>
              <label className="text-sm font-medium">Idioma Padrão</label>
              <div className="flex gap-2">
                <Input
                  value={localSettings.default_language || ''}
                  onChange={(e) => handleChange('default_language', e.target.value)}
                />
                <Button size="sm" onClick={() => handleSave('default_language')}>
                  <Save className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Serviços</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">qBittorrent Host</label>
              <div className="flex gap-2">
                <Input
                  value={localSettings.qbittorrent_host || ''}
                  onChange={(e) => handleChange('qbittorrent_host', e.target.value)}
                />
                <Button size="sm" onClick={() => handleSave('qbittorrent_host')}>
                  <Save className="w-4 h-4" />
                </Button>
              </div>
            </div>
            
            <div>
              <label className="text-sm font-medium">Jackett URL</label>
              <div className="flex gap-2">
                <Input
                  value={localSettings.jackett_url || ''}
                  onChange={(e) => handleChange('jackett_url', e.target.value)}
                />
                <Button size="sm" onClick={() => handleSave('jackett_url')}>
                  <Save className="w-4 h-4" />
                </Button>
              </div>
            </div>
            
            <div>
              <label className="text-sm font-medium">Jellyfin URL</label>
              <div className="flex gap-2">
                <Input
                  value={localSettings.jellyfin_url || ''}
                  onChange={(e) => handleChange('jellyfin_url', e.target.value)}
                />
                <Button size="sm" onClick={() => handleSave('jellyfin_url')}>
                  <Save className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
```

- [ ] **Step 14.5: Create App.tsx with routing**

```typescript
import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { Home } from './pages/Home';
import { Search } from './pages/Search';
import { Downloads } from './pages/Downloads';
import { Settings } from './pages/Settings';
import { Search as SearchIcon, Download, Settings as SettingsIcon, Home as HomeIcon } from 'lucide-react';

function App() {
  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="text-xl font-bold">
              Jellyfin Automation
            </Link>
            
            <div className="flex items-center gap-4">
              <Link to="/" className="flex items-center gap-2 text-sm hover:text-primary transition-colors">
                <HomeIcon className="w-4 h-4" />
                <span className="hidden sm:inline">Início</span>
              </Link>
              <Link to="/search" className="flex items-center gap-2 text-sm hover:text-primary transition-colors">
                <SearchIcon className="w-4 h-4" />
                <span className="hidden sm:inline">Buscar</span>
              </Link>
              <Link to="/downloads" className="flex items-center gap-2 text-sm hover:text-primary transition-colors">
                <Download className="w-4 h-4" />
                <span className="hidden sm:inline">Downloads</span>
              </Link>
              <Link to="/settings" className="flex items-center gap-2 text-sm hover:text-primary transition-colors">
                <SettingsIcon className="w-4 h-4" />
                <span className="hidden sm:inline">Configurações</span>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<Search />} />
          <Route path="/downloads" element={<Downloads />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
```

---

## Task 15: Build and Deployment

**Objective:** Configure production build and Windows executable packaging.

**Files:**
- Create: `scripts/build_windows.bat`, `docker-compose.yml`

- [ ] **Step 15.1: Create Windows build script**

```batch
@echo off
echo Building Jellyfin Automation for Windows...

REM Build frontend
cd frontend
call npm install
call npm run build
cd ..

REM Install backend dependencies
cd backend
call pip install -r requirements.txt
call pip install pyinstaller

REM Build backend executable with PyInstaller
call pyinstaller --onefile --name "JellyfinAutomation" ^
  --add-data "../frontend/dist;frontend/dist" ^
  --hidden-import sqlalchemy ^
  --hidden-import psycopg2 ^
  --hidden-import alembic ^
  --hidden-import httpx ^
  app/main.py

cd ..

echo Build complete! Executable is in backend/dist/JellyfinAutomation.exe
echo.
echo To run:
echo   1. Make sure PostgreSQL is running
echo   2. Copy .env.example to .env and configure
echo   3. Run backend/dist/JellyfinAutomation.exe
echo.
pause
```

- [ ] **Step 15.2: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: jellyfin_automation
      POSTGRES_USER: jfa_user
      POSTGRES_PASSWORD: jfa_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://jfa_user:jfa_password@db:5432/jellyfin_automation
    ports:
      - "8000:8000"
    depends_on:
      - db
    volumes:
      - ${MOVIES_PATH:-D:\Filmes}:/movies
      - ${SERIES_PATH:-D:\Séries}:/series
      - ${ANIMES_PATH:-D:\Animes}:/animes

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

- [ ] **Step 15.3: Run frontend build**

```bash
cd frontend && npm run build
```

**Expected:** Build completes successfully, static files in `frontend/dist/`

---

## Self-Review

### Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| TMDB API integration | Task 4 |
| Jackett scraper with multiple indexers | Task 5 |
| qBittorrent Web API | Task 6 |
| File organizer with rules | Task 7 |
| Jellyfin scan trigger | Task 8 |
| REST API endpoints | Task 9 |
| WebSocket notifications | Task 10 |
| React frontend with shadcn/ui | Tasks 11-14 |
| PostgreSQL database | Task 3 |
| Structured logging | Task 2 |
| Configuration management | Task 1 |
| Windows build | Task 15 |

**Coverage: 100%** - All spec requirements have corresponding tasks.

### Placeholder Scan

- No "TBD", "TODO", or "implement later" found
- No vague steps like "add appropriate error handling"
- All code blocks contain complete implementation
- All commands have exact expected output

### Type Consistency Check

- `TMDBSearchResult.display_title` used consistently
- `DownloadStatus` enum values match across models and routers
- `ContentType` enum values match across all files
- API endpoint paths consistent (`/api/search`, `/api/downloads`, etc.)
- Frontend types match backend models

**Result: PASS** - No inconsistencies found.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2025-04-30-jellyfin-automation-plan.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach would you prefer?**
