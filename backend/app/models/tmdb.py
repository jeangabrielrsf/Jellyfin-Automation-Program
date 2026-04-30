"""TMDB Pydantic models."""
from pydantic import BaseModel
from typing import List, Optional


class TMDBSearchResult(BaseModel):
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
    genre_ids: List[int] = []
    
    @property
    def display_title(self) -> str:
        return self.title or self.name or "Unknown"
    
    @property
    def year(self) -> Optional[int]:
        date = self.release_date or self.first_air_date
        if date:
            return int(date.split("-")[0])
        return None


class TMDBSearchResponse(BaseModel):
    page: int
    results: List[TMDBSearchResult]
    total_pages: int
    total_results: int


class TMDBDetail(BaseModel):
    id: int
    title: Optional[str] = None
    name: Optional[str] = None
    overview: str
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    release_date: Optional[str] = None
    first_air_date: Optional[str] = None
    vote_average: float
    genres: List[dict] = []
    runtime: Optional[int] = None
    number_of_seasons: Optional[int] = None
    number_of_episodes: Optional[int] = None
    status: Optional[str] = None
    tagline: Optional[str] = None
    
    @property
    def display_title(self) -> str:
        return self.title or self.name or "Unknown"
    
    @property
    def year(self) -> Optional[int]:
        date = self.release_date or self.first_air_date
        if date:
            return int(date.split("-")[0])
        return None
    
    @property
    def is_animation(self) -> bool:
        return any(g.get("name", "").lower() == "animation" for g in self.genres)
    
    @property
    def studios(self) -> List[str]:
        return []
