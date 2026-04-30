# Fix Torrent Search — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the 500 error on `/api/search/torrents`, make the backend fetch both Portuguese and original titles from TMDB, support season/episode refinement, and expose a TV seasons endpoint.

**Architecture:** The torrent search endpoint will no longer receive `title` from the frontend. Instead, it receives `tmdb_id` and `media_type`, fetches the TMDB record to get both Portuguese and original titles, optionally appends season/episode suffixes, runs two Jackett searches, merges and deduplicates results by magnet URL, and re-sorts by score. A new endpoint returns season metadata for TV shows.

**Tech Stack:** FastAPI, httpx, pytest, Loguru

---

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/app/routers/search.py` | Torrent search endpoint refactor + new TV seasons endpoint |
| `backend/app/services/tmdb_service.py` | No changes needed — existing `get_movie_detail` / `get_tv_detail` already return the required fields |
| `backend/app/scrapers/jackett_scraper.py` | No changes needed — `search()` already accepts arbitrary query strings |
| `backend/tests/test_routers.py` | Update torrent search test + add TV seasons test |

---

## Task 1: Fix 500 Error + Refactor Torrent Search Endpoint

**Files:**
- Modify: `backend/app/routers/search.py:58-74`
- Test: `backend/tests/test_routers.py:86-108`

- [ ] **Step 1: Write the updated router test**

Add the new test to `backend/tests/test_routers.py`, replacing the old `test_search_torrents`:

```python
    def test_search_torrents(self, client):
        """Test torrent search endpoint with TMDB lookup."""
        mock_detail = {
            "id": 1,
            "title": "Filme Teste",
            "original_title": "Test Movie",
            "overview": "A test",
            "release_date": "2023-01-01",
            "vote_average": 8.0,
            "genres": [],
            "runtime": 120
        }
        mock_torrents = [
            {
                "title": "Test",
                "indexer": "1337x",
                "size": "1 GB",
                "seeds": 100,
                "peers": 50,
                "download_url": "http://example.com",
                "magnet_url": "magnet:?xt=urn:btih:test",
                "score": 100.0
            }
        ]

        with patch('app.routers.search.TMDBService.get_movie_detail') as mock_detail_fn:
            mock_detail_fn.return_value = mock_detail
            with patch('app.routers.search.JackettScraper.search') as mock_search:
                mock_search.return_value = mock_torrents
                response = client.get(
                    "/api/search/torrents?tmdb_id=1&media_type=movie"
                )
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["title"] == "Test"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation/backend && pytest tests/test_routers.py::TestSearchRouter::test_search_torrents -v
```

Expected: FAIL — 422 validation error because `title` is no longer accepted.

- [ ] **Step 3: Refactor the torrent search endpoint**

Replace lines 58-74 in `backend/app/routers/search.py` with:

```python
@router.get("/torrents")
async def search_torrents(
    tmdb_id: int = Query(...),
    media_type: str = Query(..., pattern="^(movie|series|anime)$"),
    season: Optional[int] = Query(None, ge=1),
    episode: Optional[int] = Query(None, ge=1),
    quality: Optional[str] = Query("1080p"),
    language: Optional[str] = Query("legendado")
):
    """Search for torrents for a specific media using TMDB titles."""
    service = TMDBService()
    scraper = JackettScraper()
    try:
        # Fetch detail to get both Portuguese and original titles
        if media_type == "movie":
            detail = await service.get_movie_detail(tmdb_id)
            pt_title = detail.title or detail.original_title or ""
            original_title = detail.original_title or detail.title or ""
        else:
            detail = await service.get_tv_detail(tmdb_id)
            pt_title = detail.name or detail.original_name or ""
            original_title = detail.original_name or detail.name or ""

        # Build suffix for season/episode refinement
        suffix = ""
        if season is not None and episode is not None:
            suffix = f" S{season:02d}E{episode:02d}"
        elif season is not None:
            suffix = f" S{season:02d}"

        queries = []
        if pt_title:
            queries.append(pt_title + suffix)
        if original_title and original_title != pt_title:
            queries.append(original_title + suffix)

        if not queries:
            return []

        # Run Jackett searches and merge results
        all_results = []
        for query in queries:
            results = await scraper.search(query, media_type, quality, language)
            all_results.extend(results)

        # Deduplicate by magnet URL (fallback to title match)
        seen = set()
        deduped = []
        for torrent in all_results:
            key = torrent.magnet_url or torrent.download_url or torrent.title
            if key not in seen:
                seen.add(key)
                deduped.append(torrent)

        deduped.sort(key=lambda x: x.score, reverse=True)
        return deduped

    except HTTPException:
        raise
    except Exception as e:
        logger = get_logger(__name__)
        logger.exception("Torrent search failed unexpectedly")
        raise HTTPException(status_code=500, detail=f"Torrent search failed: {str(e)}")
    finally:
        await service.close()
        await scraper.close()
```

Also add this import near the top of `backend/app/routers/search.py`:

```python
from app.logging_config import get_logger
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation/backend && pytest tests/test_routers.py::TestSearchRouter::test_search_torrents -v
```

Expected: PASS

- [ ] **Step 5: Run all router tests to ensure no regressions**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation/backend && pytest tests/test_routers.py -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation && git add backend/app/routers/search.py backend/tests/test_routers.py && git commit -m "fix(backend): refactor torrent search to use TMDB titles, add season/episode params, fix 500 handling"
```

---

## Task 2: Add TV Seasons Endpoint

**Files:**
- Modify: `backend/app/routers/search.py`
- Test: `backend/tests/test_routers.py`

- [ ] **Step 1: Write the test for the new endpoint**

Add to `backend/tests/test_routers.py` inside `TestSearchRouter`:

```python
    def test_get_tv_seasons(self, client):
        """Test TV seasons endpoint."""
        mock_detail = {
            "id": 2,
            "name": "Test Show",
            "overview": "A test",
            "first_air_date": "2022-06-15",
            "vote_average": 7.5,
            "genres": [],
            "number_of_seasons": 2,
            "number_of_episodes": 20,
            "seasons": [
                {"season_number": 0, "name": "Specials", "episode_count": 2},
                {"season_number": 1, "name": "Season 1", "episode_count": 10},
                {"season_number": 2, "name": "Season 2", "episode_count": 10},
            ]
        }

        with patch('app.routers.search.TMDBService.get_tv_detail') as mock_get:
            mock_get.return_value = mock_detail
            response = client.get("/api/search/tv/2/seasons")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["season_number"] == 1
            assert data[0]["episode_count"] == 10
            assert data[1]["season_number"] == 2
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation/backend && pytest tests/test_routers.py::TestSearchRouter::test_get_tv_seasons -v
```

Expected: FAIL — 404 because the route does not exist.

- [ ] **Step 3: Add the seasons endpoint**

Add this endpoint to `backend/app/routers/search.py`, after the `get_tv_detail` endpoint (around line 56):

```python
@router.get("/tv/{tv_id}/seasons")
async def get_tv_seasons(tv_id: int):
    """Get season list with episode counts for a TV show."""
    service = TMDBService()
    try:
        result = await service.get_tv_detail(tv_id)
        if not result:
            raise HTTPException(status_code=404, detail="TV show not found")
        
        seasons = [
            {"season_number": s["season_number"], "name": s["name"], "episode_count": s["episode_count"]}
            for s in result.seasons or []
            if s.get("season_number", 0) > 0
        ]
        return seasons
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get seasons: {str(e)}")
    finally:
        await service.close()
```

**Important:** The `TMDBDetail` model currently does not have a `seasons` field. You need to add it.

- [ ] **Step 4: Add `seasons` field to `TMDBDetail` model**

In `backend/app/models/tmdb.py`, add inside `TMDBDetail`:

```python
    seasons: List[dict] = []
```

Add the `List` import if not already present:

```python
from typing import List, Optional
```

- [ ] **Step 5: Run the test again**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation/backend && pytest tests/test_routers.py::TestSearchRouter::test_get_tv_seasons -v
```

Expected: PASS

- [ ] **Step 6: Run all backend tests**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation/backend && pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
cd /home/jeanfrusca/Projetos/jellyfin_automation && git add backend/app/routers/search.py backend/app/models/tmdb.py backend/tests/test_routers.py && git commit -m "feat(backend): add /api/search/tv/{id}/seasons endpoint"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - Fix 500 error → Task 1, Steps 1-3 (try/except + logging)
   - Remove `title` param, fetch from TMDB → Task 1, Step 3
   - Dual title search (PT + original) → Task 1, Step 3
   - Season/episode suffix → Task 1, Step 3
   - Merge + deduplicate → Task 1, Step 3
   - TV seasons endpoint → Task 2

2. **Placeholder scan:** No TBD, TODO, or vague steps found.

3. **Type consistency:** `season` and `episode` are `Optional[int]` everywhere. `TMDBDetail.seasons` is `List[dict]`.
