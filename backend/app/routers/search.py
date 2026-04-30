"""Search router."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.tmdb_service import TMDBService
from app.scrapers.jackett_scraper import JackettScraper
from app.models.tmdb import TMDBSearchResponse, TMDBDetail
from app.models.torrent import TorrentResult

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
    title: str = Query(...),
    media_type: str = Query(..., pattern="^(movie|series|anime)$"),
    quality: Optional[str] = Query("1080p"),
    language: Optional[str] = Query("legendado")
):
    """Search for torrents for a specific media."""
    scraper = JackettScraper()
    try:
        results = await scraper.search(title, media_type, quality, language)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Torrent search failed: {str(e)}")
    finally:
        await scraper.close()
