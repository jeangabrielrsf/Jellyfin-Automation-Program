"""Recommendations endpoint — TMDB similar + recommendations, exclusion-filtered."""
import inspect

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.recommendation_service import RecommendationService
from app.services.tmdb_service import TMDBService


router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

_VALID_MEDIA_TYPES = {"movie", "series", "anime"}


@router.get("/{media_type}/{tmdb_id}/")
async def get_recommendations(
    media_type: str,
    tmdb_id: int,
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[dict]:
    if media_type not in _VALID_MEDIA_TYPES:
        raise HTTPException(status_code=400, detail="invalid media_type")
    tmdb_media_type = "movie" if media_type == "movie" else "tv"
    tmdb = TMDBService(db=db)
    try:
        service = RecommendationService(db=db, tmdb=tmdb)
        return await service.get_recommendations(tmdb_media_type, tmdb_id, limit=limit)
    finally:
        close_result = tmdb.close()
        if inspect.iscoroutine(close_result):
            await close_result
