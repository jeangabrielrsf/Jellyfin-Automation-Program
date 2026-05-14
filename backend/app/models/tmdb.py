"""TMDB Pydantic models."""
from pydantic import BaseModel, computed_field
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
    
    @computed_field
    @property
    def display_title(self) -> str:
        return self.title or self.name or "Unknown"
    
    @computed_field
    @property
    def year(self) -> Optional[int]:
        date = self.release_date or self.first_air_date
        if date and len(date) >= 4 and date[:4].isdigit():
            return int(date[:4])
        return None


class TMDBSearchResponse(BaseModel):
    page: int
    results: List[TMDBSearchResult]
    total_pages: int
    total_results: int


class TMDBDetail(BaseModel):
    id: int
    title: Optional[str] = None
    original_title: Optional[str] = None
    name: Optional[str] = None
    original_name: Optional[str] = None
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
    external_ids: Optional[dict] = None
    imdb_id: Optional[str] = None
    rt_rating: Optional[str] = None
    rt_url: Optional[str] = None
    seasons: List[dict] = []
    
    @computed_field
    @property
    def display_title(self) -> str:
        return self.title or self.name or "Unknown"
    
    @computed_field
    @property
    def year(self) -> Optional[int]:
        date = self.release_date or self.first_air_date
        if date and len(date) >= 4 and date[:4].isdigit():
            return int(date[:4])
        return None
    
    @property
    def is_animation(self) -> bool:
        return any(g.get("name", "").lower() == "animation" for g in self.genres)
    
    @property
    def studios(self) -> List[str]:
        return []
