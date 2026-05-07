"""Discover Pydantic models."""
from typing import Optional, List

from pydantic import BaseModel

from app.models.tmdb import TMDBSearchResult


class DiscoverParams(BaseModel):
    genre_id: Optional[int] = None
    media_type: Optional[str] = None  # "movie" | "series" | "anime"
    sort_by: str = "popularity.desc"


class SectionInfo(BaseModel):
    id: str
    title: str
    media_type: str


class SectionCatalog(BaseModel):
    sections: List[SectionInfo]


class DiscoverSection(BaseModel):
    id: str
    title: str
    media_type: str
    results: List[TMDBSearchResult]
    total_results: int


class Genre(BaseModel):
    id: int
    name: str
