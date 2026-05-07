"""Discover Pydantic models."""
from pydantic import BaseModel
from app.models.tmdb import TMDBSearchResult


class DiscoverParams(BaseModel):
    genre_id: int | None = None
    media_type: str | None = None  # "movie" | "series" | "anime"
    sort_by: str = "popularity.desc"


class SectionInfo(BaseModel):
    id: str
    title: str
    media_type: str


class SectionCatalog(BaseModel):
    sections: list[SectionInfo]


class DiscoverSection(BaseModel):
    id: str
    title: str
    media_type: str
    results: list[TMDBSearchResult]
    total_results: int


class Genre(BaseModel):
    id: int
    name: str
