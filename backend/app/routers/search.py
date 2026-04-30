"""Search router."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.tmdb_service import TMDBService
from app.scrapers.jackett_scraper import JackettScraper
from app.models.tmdb import TMDBSearchResponse, TMDBDetail
from app.models.torrent import TorrentResult
from app.logging_config import get_logger

router = APIRouter(prefix="/api/search", tags=["search"])

@router.get("/", response_model=TMDBSearchResponse)
async def search_media(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1)
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
