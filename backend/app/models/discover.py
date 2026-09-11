"""Discover Pydantic models."""
from typing import Optional, List

from pydantic import BaseModel

from app.models.tmdb import TMDBSearchResult


class BannerMedia(BaseModel):
    id: int
    title: Optional[str] = None
    name: Optional[str] = None
    overview: str
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    release_date: Optional[str] = None
    first_air_date: Optional[str] = None
    vote_average: float
    media_type: str
    genres: List[str] = []
    providers: List[str] = []
    runtime: Optional[int] = None
    display_title: Optional[str] = None
    year: Optional[int] = None


class SectionInfo(BaseModel):
    id: str
    title: str
    media_type: str


class SectionCatalog(BaseModel):
    banner: Optional[BannerMedia] = None
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


class StreamingProvider(BaseModel):
    id: int
    name: str
    logo_path: Optional[str] = None
