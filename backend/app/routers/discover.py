"""Discover routes — browse sections with optional filters."""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.discover import SectionCatalog, DiscoverSection, Genre, DiscoverParams
from app.services.discover_service import DiscoverService

router = APIRouter(prefix="/api/discover", tags=["discover"])


def get_discover_service() -> DiscoverService:
    return DiscoverService()


@router.get("/sections", response_model=SectionCatalog)
async def get_sections_catalog(
    genre_id: int | None = Query(None),
    media_type: str | None = Query(None, regex="^(movie|series|anime)$"),
    sort_by: str = Query("popularity.desc"),
    service: DiscoverService = Depends(get_discover_service),
):
    """Return the catalog of available sections."""
    params = DiscoverParams(genre_id=genre_id, media_type=media_type, sort_by=sort_by)
    return service.get_sections_catalog(params)


@router.get("/sections/{section_id}", response_model=DiscoverSection)
async def get_section(
    section_id: str,
    genre_id: int | None = Query(None),
    media_type: str | None = Query(None, regex="^(movie|series|anime)$"),
    sort_by: str = Query("popularity.desc"),
    service: DiscoverService = Depends(get_discover_service),
):
    """Return data for a specific section."""
    params = DiscoverParams(genre_id=genre_id, media_type=media_type, sort_by=sort_by)
    section = await service.get_section(section_id, params)
    if not section.title:
        raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found")
    return section


@router.get("/genres", response_model=list[Genre])
async def get_genres(
    service: DiscoverService = Depends(get_discover_service),
):
    """Return the merged list of movie and TV genres."""
    genres = await service.get_genres()
    return genres
