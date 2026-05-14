"""Discover routes — browse sections with optional filters."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.discover import SectionCatalog, DiscoverSection, Genre, DiscoverParams, StreamingProvider
from app.services.discover_service import DiscoverService

router = APIRouter(prefix="/api/discover", tags=["discover"])


@router.get("/sections/", response_model=SectionCatalog)
async def get_sections_catalog(
    genre_id: Optional[int] = Query(None),
    media_type: Optional[str] = Query(None, pattern="^(movie|series|anime)$"),
    sort_by: str = Query("popularity.desc"),
    watch_provider_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Return the catalog of available sections."""
    service = DiscoverService(db=db)
    try:
        params = DiscoverParams(genre_id=genre_id, media_type=media_type, sort_by=sort_by, watch_provider_id=watch_provider_id)
        return service.get_sections_catalog(params)
    finally:
        await service.close()


@router.get("/sections/{section_id}/", response_model=DiscoverSection)
async def get_section(
    section_id: str,
    genre_id: Optional[int] = Query(None),
    media_type: Optional[str] = Query(None, pattern="^(movie|series|anime)$"),
    sort_by: str = Query("popularity.desc"),
    watch_provider_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Return data for a specific section."""
    service = DiscoverService(db=db)
    try:
        params = DiscoverParams(genre_id=genre_id, media_type=media_type, sort_by=sort_by, watch_provider_id=watch_provider_id)
        section = await service.get_section(section_id, params)
        if not section.title:
            raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found")
        return section
    finally:
        await service.close()


@router.get("/genres/", response_model=List[Genre])
async def get_genres(db: Session = Depends(get_db)):
    """Return the merged list of movie and TV genres."""
    service = DiscoverService(db=db)
    try:
        genres = await service.get_genres()
        return genres
    finally:
        await service.close()


@router.get("/providers/", response_model=List[StreamingProvider])
async def get_providers():
    """Return the list of supported streaming providers."""
    from app.services.discover_service import STREAMING_PROVIDERS
    return [StreamingProvider(**p) for p in STREAMING_PROVIDERS]
