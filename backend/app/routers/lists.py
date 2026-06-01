"""User list endpoints — watched and watchlist."""
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_list import ListKind, UserList
from app.services.list_service import ListService
from app.services.tmdb_service import TMDBService


router = APIRouter(prefix="/api/lists", tags=["lists"])

_VALID_MEDIA_TYPES = {"movie", "series", "anime"}


class ListItemPayload(BaseModel):
    title: str
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    year: Optional[int] = None


def _check_media_type(media_type: str) -> None:
    if media_type not in _VALID_MEDIA_TYPES:
        raise HTTPException(status_code=400, detail="invalid media_type")


@router.get("/status/{media_type}/{tmdb_id}/")
def get_status(media_type: str, tmdb_id: int, db: Session = Depends(get_db)) -> dict:
    _check_media_type(media_type)
    return ListService(db).get_status(media_type, tmdb_id)


@router.post("/{kind}/{media_type}/{tmdb_id}/", status_code=204)
async def add_item(
    kind: ListKind,
    media_type: str,
    tmdb_id: int,
    payload: Optional[ListItemPayload] = Body(default=None),
    db: Session = Depends(get_db),
):
    _check_media_type(media_type)
    if payload is None:
        # Hydrate from TMDB.
        tmdb = TMDBService(db=db)
        try:
            detail = (
                await tmdb.get_movie_detail(tmdb_id)
                if media_type == "movie"
                else await tmdb.get_tv_detail(tmdb_id)
            )
            payload = ListItemPayload(
                title=detail.display_title,
                poster_path=detail.poster_path,
                backdrop_path=detail.backdrop_path,
                year=detail.year,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"TMDB hydration failed: {exc}"
            ) from exc
        finally:
            await tmdb.close()

    ListService(db).add(
        kind,
        media_type,
        tmdb_id,
        title=payload.title,
        poster_path=payload.poster_path,
        backdrop_path=payload.backdrop_path,
        year=payload.year,
    )
    return Response(status_code=204)


@router.delete("/{kind}/{media_type}/{tmdb_id}/", status_code=204)
def remove_item(
    kind: ListKind,
    media_type: str,
    tmdb_id: int,
    db: Session = Depends(get_db),
):
    _check_media_type(media_type)
    deleted = ListService(db).remove(kind, media_type, tmdb_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="not in list")
    return Response(status_code=204)


@router.get("/watchlist/", response_model=None)
def get_watchlist(db: Session = Depends(get_db)):
    return ListService(db).list_watchlist()


@router.get("/watched/", response_model=None)
def get_watched(db: Session = Depends(get_db)):
    return ListService(db).list_watched()
