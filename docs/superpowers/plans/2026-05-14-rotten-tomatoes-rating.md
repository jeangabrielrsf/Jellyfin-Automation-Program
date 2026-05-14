# Rotten Tomatoes Rating — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-step. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display Rotten Tomatoes rating with conditional tomato icon and link on the media detail page hero section.

**Architecture:** Backend enriches TMDB detail with RT data by fetching `external_ids` from TMDB (to get `imdb_id`), then calling OMDB API with that IMDb ID to extract the RT rating from the `Ratings` array. An RT page URL is constructed from the title and validated with a HEAD request, falling back to a search URL if the slug page returns 404.

**Tech Stack:** Python/FastAPI/httpx (backend), TypeScript/React/Tailwind (frontend)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/config.py` | Modify | Add `omdb_api_key` setting |
| `backend/app/services/omdb_service.py` | **Create** | `OMDbService` — fetches RT rating from OMDB, builds RT URL |
| `backend/tests/services/test_omdb_service.py` | **Create** | Unit tests for `OMDbService` |
| `backend/app/models/tmdb.py` | Modify | Add `imdb_id`, `rt_rating`, `rt_url` to `TMDBDetail` |
| `backend/app/services/tmdb_service.py` | Modify | Add `external_ids` to `append_to_response` |
| `backend/app/routers/search.py` | Modify | Call OMDB in movie/TV detail endpoints, populate RT fields |
| `frontend/src/types/index.ts` | Modify | Add `rt_rating?` and `rt_url?` to `TMDBDetail` |
| `frontend/src/pages/Detail.tsx` | Modify | Render RT rating element in hero section |

---

### Task 1: Add OMDB API key to config

**Files:** Modify: `backend/app/config.py`

- [ ] **Step 1: Add `omdb_api_key` field to Settings**

In `backend/app/config.py`, after the `jackett_timeout` line (line 22), add:

```python
    # OMDB
    omdb_api_key: str = Field(default="")
```

- [ ] **Step 2: Verify the setting loads from `.env`**

Run:
```bash
cd backend && source venv/bin/activate && python -c "from app.config import get_settings; s = get_settings(); print('omdb_key set:', bool(s.omdb_api_key))"
```

Expected: `omdb_key set: True`

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py
git commit -m "feat: add omdb_api_key to settings"
```

---

### Task 2: Create OMDB service with tests

**Files:** Create `backend/app/services/omdb_service.py` and `backend/tests/services/test_omdb_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/services/test_omdb_service.py`:

```python
import httpx
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.omdb_service import OMDbService


@pytest.fixture
def omdb_service():
    return OMDbService(api_key="test-key")


@pytest.mark.asyncio
async def test_get_by_imdb_id_returns_rt_rating(omdb_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "Title": "Test Movie",
        "Year": "2023",
        "Rated": "PG",
        "Ratings": [
            {"Source": "Internet Movie Database", "Value": "8.5/10"},
            {"Source": "Rotten Tomatoes", "Value": "94%"},
            {"Source": "Metacritic", "Value": "82/100"},
        ],
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(omdb_service.client, "get", AsyncMock(return_value=mock_response)):
        result = await omdb_service.get_by_imdb_id("tt1234567")
        assert result is not None
        assert result["rt_rating"] == "94%"


@pytest.mark.asyncio
async def test_get_by_imdb_id_no_rt_rating_returns_none(omdb_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "Title": "Test Movie",
        "Ratings": [
            {"Source": "Internet Movie Database", "Value": "8.5/10"},
        ],
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(omdb_service.client, "get", AsyncMock(return_value=mock_response)):
        result = await omdb_service.get_by_imdb_id("tt1234567")
        assert result is None


@pytest.mark.asyncio
async def test_get_by_imdb_id_http_error_returns_none(omdb_service):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Error", request=MagicMock(), response=MagicMock(status_code=401)
    )

    with patch.object(omdb_service.client, "get", AsyncMock(return_value=mock_response)):
        result = await omdb_service.get_by_imdb_id("tt1234567")
        assert result is None


@pytest.mark.asyncio
async def test_get_by_imdb_id_empty_ratings_returns_none(omdb_service):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "Title": "Test Movie",
        "Ratings": [],
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(omdb_service.client, "get", AsyncMock(return_value=mock_response)):
        result = await omdb_service.get_by_imdb_id("tt1234567")
        assert result is None


@pytest.mark.asyncio
async def test_build_rt_url_movie_valid_returns_slug_url(omdb_service):
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(omdb_service.client, "head", AsyncMock(return_value=mock_response)):
        url = await omdb_service.build_rt_url("The Matrix", "movie")
        assert "rottentomatoes.com/m/the_matrix" in url


@pytest.mark.asyncio
async def test_build_rt_url_tv_valid_returns_slug_url(omdb_service):
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(omdb_service.client, "head", AsyncMock(return_value=mock_response)):
        url = await omdb_service.build_rt_url("Breaking Bad", "tv")
        assert "rottentomatoes.com/tv/breaking_bad" in url


@pytest.mark.asyncio
async def test_build_rt_url_404_falls_back_to_search(omdb_service):
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch.object(omdb_service.client, "head", AsyncMock(return_value=mock_response)):
        url = await omdb_service.build_rt_url("Some Obscure Title", "movie")
        assert "rottentomatoes.com/search" in url
        assert "Some+Obscure+Title" in url


@pytest.mark.asyncio
async def test_build_rt_url_head_error_falls_back_to_search(omdb_service):
    with patch.object(omdb_service.client, "head", AsyncMock(side_effect=Exception("timeout"))):
        url = await omdb_service.build_rt_url("Test Movie", "movie")
        assert "rottentomatoes.com/search" in url
        assert "Test+Movie" in url


@pytest.mark.asyncio
async def test_build_rt_url_removes_special_chars(omdb_service):
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(omdb_service.client, "head", AsyncMock(return_value=mock_response)):
        url = await omdb_service.build_rt_url("What's Up, Doc?", "movie")
        assert "whats_up_doc" in url
        assert "'" not in url
        assert "," not in url
        assert "?" not in url
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source venv/bin/activate && pytest tests/services/test_omdb_service.py -v
```

Expected: all tests FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create the OMDB service**

Create `backend/app/services/omdb_service.py`:

```python
"""OMDB API service for Rotten Tomatoes ratings."""
import re
from urllib.parse import quote_plus
import httpx
from app.logging_config import get_logger

logger = get_logger(__name__)


class OMDbService:
    BASE_URL = "https://www.omdbapi.com"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=15.0)

    async def close(self):
        await self.client.aclose()

    async def get_by_imdb_id(self, imdb_id: str) -> dict | None:
        """Fetch OMDB data by IMDb ID. Returns {rt_rating: '94%'} or None."""
        try:
            url = self.BASE_URL
            params = {
                "apikey": self.api_key,
                "i": imdb_id,
            }
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("Response") == "False":
                logger.warning("OMDB returned False response", imdb_id=imdb_id)
                return None

            ratings = data.get("Ratings") or []
            for rating in ratings:
                if rating.get("Source") == "Rotten Tomatoes":
                    return {"rt_rating": rating["Value"]}

            logger.info("No Rotten Tomatoes rating in OMDB response", imdb_id=imdb_id)
            return None
        except Exception as e:
            logger.warning("OMDB request failed", imdb_id=imdb_id, error=str(e))
            return None

    async def build_rt_url(self, title: str, media_type: str) -> str:
        """Build a validated Rotten Tomatoes URL for the given title.

        Tries slug URL first (HEAD check), falls back to search URL.
        """
        slug = self._slugify(title)
        if media_type == "tv":
            slug_url = f"https://www.rottentomatoes.com/tv/{slug}"
        else:
            slug_url = f"https://www.rottentomatoes.com/m/{slug}"

        try:
            head_response = await self.client.head(slug_url, follow_redirects=True)
            if head_response.status_code == 200:
                return slug_url
        except Exception:
            pass

        search_url = f"https://www.rottentomatoes.com/search?search={quote_plus(title)}"
        return search_url

    @staticmethod
    def _slugify(title: str) -> str:
        """Convert a title to a Rotten Tomatoes-compatible slug."""
        slug = title.lower()
        slug = slug.replace(" ", "_")
        slug = re.sub(r"[^a-z0-9_]", "", slug)
        slug = re.sub(r"_+", "_", slug)
        slug = slug.strip("_")
        return slug
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && source venv/bin/activate && pytest tests/services/test_omdb_service.py -v
```

Expected: all 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/omdb_service.py backend/tests/services/test_omdb_service.py
git commit -m "feat: add OMDbService for Rotten Tomatoes ratings and URL building"
```

---

### Task 3: Add external_ids to TMDB service and RT fields to TMDBDetail model

**Files:** Modify `backend/app/services/tmdb_service.py` and `backend/app/models/tmdb.py`

- [ ] **Step 1: Add `external_ids` to TMDB detail calls**

In `backend/app/services/tmdb_service.py`, change `"credits"` to `"credits,external_ids"` on both line 65 (`get_movie_detail`) and line 80 (`get_tv_detail`).

```python
# Line 65: change from "credits" to "credits,external_ids"
            "append_to_response": "credits,external_ids"

# Line 80: change from "credits" to "credits,external_ids"
            "append_to_response": "credits,external_ids"
```

- [ ] **Step 2: Add `external_ids`, `imdb_id`, `rt_rating`, `rt_url` to TMDBDetail model**

In `backend/app/models/tmdb.py`, after the `tagline` field (line 57), add:

```python
    external_ids: Optional[dict] = None
    imdb_id: Optional[str] = None
    rt_rating: Optional[str] = None
    rt_url: Optional[str] = None
```

- [ ] **Step 3: Run existing tests to verify nothing broke**

```bash
cd backend && source venv/bin/activate && pytest tests/test_tmdb_service.py tests/test_routers.py::TestSearchRouter -v
```

Expected: all existing tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/tmdb_service.py backend/app/models/tmdb.py
git commit -m "feat: add external_ids to TMDB detail calls and RT fields to TMDBDetail"
```

---

### Task 4: Enrich search router endpoints with RT data

**Files:** Modify `backend/app/routers/search.py`

- [ ] **Step 1: Add import**

In `backend/app/routers/search.py`, after line 8 (the existing imports), add:

```python
from app.services.omdb_service import OMDbService
```

- [ ] **Step 2: Add enrichment helper function**

Before the `search_media` function (before line 12), add:

```python
async def _enrich_with_rt_data(detail: TMDBDetail, media_type: str) -> TMDBDetail:
    """Enrich a TMDBDetail with Rotten Tomatoes rating and URL from OMDB."""
    external_ids = getattr(detail, "external_ids", None) or {}
    imdb_id = external_ids.get("imdb_id")
    if not imdb_id:
        return detail

    from app.config import get_settings
    settings = get_settings()
    if not settings.omdb_api_key:
        return detail

    omdb = OMDbService(api_key=settings.omdb_api_key)
    try:
        omdb_data = await omdb.get_by_imdb_id(imdb_id)
        if omdb_data:
            detail.rt_rating = omdb_data.get("rt_rating")

        display_title = detail.title or detail.name or ""
        detail.rt_url = await omdb.build_rt_url(display_title, media_type)
    except Exception:
        pass
    finally:
        await omdb.close()

    return detail
```

- [ ] **Step 3: Call enrichment in movie detail endpoint**

In the `get_movie_detail` function, after `result = await service.get_movie_detail(movie_id)` (line 32), add:

```python
        result = await _enrich_with_rt_data(result, "movie")
```

The full function should be:

```python
@router.get("/movie/{movie_id}", response_model=TMDBDetail)
async def get_movie_detail(movie_id: int):
    """Get movie details by TMDB ID."""
    service = TMDBService()
    try:
        result = await service.get_movie_detail(movie_id)
        if not result:
            raise HTTPException(status_code=404, detail="Movie not found")
        result = await _enrich_with_rt_data(result, "movie")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get movie details: {str(e)}")
    finally:
        await service.close()
```

- [ ] **Step 4: Call enrichment in TV detail endpoint**

In the `get_tv_detail` function, same pattern: after `result = await service.get_tv_detail(tv_id)`, add:

```python
        result = await _enrich_with_rt_data(result, "tv")
```

- [ ] **Step 5: Run tests to verify**

```bash
cd backend && source venv/bin/activate && pytest tests/test_routers.py::TestSearchRouter -v
```

Expected: all existing tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/search.py
git commit -m "feat: enrich movie/TV detail endpoints with Rotten Tomatoes data from OMDB"
```

---

### Task 5: Add RT fields to frontend TypeScript types

**Files:** Modify `frontend/src/types/index.ts`

- [ ] **Step 1: Add `rt_rating` and `rt_url` to TMDBDetail interface**

In `frontend/src/types/index.ts`, after the `year?` line (line 34), add:

```typescript
  rt_rating?: string;
  rt_url?: string;
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add rt_rating and rt_url to TMDBDetail TypeScript interface"
```

---

### Task 6: Render RT rating in Detail page hero

**Files:** Modify `frontend/src/pages/Detail.tsx`

- [ ] **Step 1: Add RT element to the hero section**

In the hero text block (lines 186-196), after the overview paragraph (line 195) and before the closing `</div>`, insert the RT rating element. The hero section should look like:

```tsx
          <div className="flex-1">
            <h1 className="font-display text-3xl md:text-4xl font-bold text-foreground">
              {media.display_title}
            </h1>
            <p className="text-muted-foreground mt-1">
              {media.year} • {media.genres?.map((g: any) => g.name).join(', ')}
            </p>
            <p className="text-sm text-muted-foreground mt-2 line-clamp-3">
              {media.overview}
            </p>
            {media.rt_rating && (
              <div className="flex items-center gap-2 mt-3">
                <span className="text-lg">
                  {parseInt(media.rt_rating) >= 60 ? '🍅' : '💀'}
                </span>
                <a
                  href={media.rt_url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-white/80 hover:text-white underline underline-offset-2 transition-colors"
                >
                  {media.rt_rating} no Rotten Tomatoes
                </a>
              </div>
            )}
          </div>
```

Fresh tomato emoji: `🍅` for score >= 60%, `💀` for score < 60%.

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Detail.tsx
git commit -m "feat: render Rotten Tomatoes rating with conditional tomato icon in detail page hero"
```

---

### Task 7: End-to-end verification

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && source venv/bin/activate && pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 2: Run frontend build**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 3: Manual verification (optional)**

Start backend and frontend, navigate to a movie or TV show detail page, confirm RT rating renders in hero section.

```bash
cd backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
