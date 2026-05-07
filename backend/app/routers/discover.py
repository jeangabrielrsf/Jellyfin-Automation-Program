"""Discover routes — browse sections with optional filters."""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.discover import SectionCatalog, DiscoverSection, Genre, DiscoverParams
from app.services.discover_service import DiscoverService

router = APIRouter(prefix="/api/discover", tags=["discover"])


@router.get("/sections/", response_model=SectionCatalog)
async def get_sections_catalog(
    genre_id: Optional[int] = Query(None),
    media_type: Optional[str] = Query(None, pattern="^(movie|series|anime)$"),
    sort_by: str = Query("popularity.desc"),
):
    """Return the catalog of available sections."""
    service = DiscoverService()
    try:
        params = DiscoverParams(genre_id=genre_id, media_type=media_type, sort_by=sort_by)
        return service.get_sections_catalog(params)
    finally:
        await service.close()


@router.get("/sections/{section_id}/", response_model=DiscoverSection)
async def get_section(
    section_id: str,
    genre_id: Optional[int] = Query(None),
    media_type: Optional[str] = Query(None, pattern="^(movie|series|anime)$"),
    sort_by: str = Query("popularity.desc"),
):
    """Return data for a specific section."""
    service = DiscoverService()
    try:
        params = DiscoverParams(genre_id=genre_id, media_type=media_type, sort_by=sort_by)
        section = await service.get_section(section_id, params)
        if not section.title:
            raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found")
        return section
    finally:
        await service.close()


@router.get("/genres/", response_model=List[Genre])
async def get_genres():
    """Return the merged list of movie and TV genres."""
    service = DiscoverService()
    try:
        genres = await service.get_genres()
        return genres
    finally:
        await service.close()
