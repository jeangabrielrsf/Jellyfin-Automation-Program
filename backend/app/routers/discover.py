"""Discover routes — browse sections with optional filters."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.discover import SectionCatalog, DiscoverSection, Genre, StreamingProvider
from app.services.discover_service import DiscoverService, STREAMING_PROVIDERS

router = APIRouter(prefix="/api/discover", tags=["discover"])


@router.get("/sections/", response_model=SectionCatalog)
async def get_sections_catalog(db: Session = Depends(get_db)):
    """Return the catalog of available sections with daily banner."""
    service = DiscoverService(db=db)
    try:
        catalog = await service.get_sections_catalog()
        return catalog
    finally:
        await service.close()


@router.get("/sections/{section_id}/", response_model=DiscoverSection)
async def get_section(section_id: str, db: Session = Depends(get_db)):
    """Return data for a specific section."""
    service = DiscoverService(db=db)
    try:
        section = await service.get_section(section_id)
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
    return [StreamingProvider(**p) for p in STREAMING_PROVIDERS]
