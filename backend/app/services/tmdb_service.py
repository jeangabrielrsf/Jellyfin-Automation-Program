"""TMDB API service."""
import httpx
from typing import List, Optional
from app.config import get_settings
from app.models.tmdb import TMDBSearchResult, TMDBSearchResponse, TMDBDetail
from app.logging_config import get_logger

logger = get_logger(__name__)


class TMDBService:
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.tmdb_api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def search(self, query: str, page: int = 1) -> TMDBSearchResponse:
        """Search for movies and TV shows."""
        logger.info("Searching TMDB", query=query, page=page)
        
        url = f"{self.BASE_URL}/search/multi"
        params = {
            "api_key": self.api_key,
            "query": query,
            "page": page,
            "include_adult": "false",
            "language": "pt-BR"
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        results = [
            TMDBSearchResult(**item)
            for item in data.get("results", [])
            if item.get("media_type") in ["movie", "tv"]
        ]

        filtered_total = len(results)
        total_pages = max(1, (filtered_total + 19) // 20) if filtered_total > 0 else 0

        return TMDBSearchResponse(
            page=data.get("page", 1),
            results=results,
            total_pages=total_pages,
            total_results=filtered_total
        )
    
    async def get_movie_detail(self, movie_id: int) -> TMDBDetail:
        """Get movie details by ID."""
        logger.info("Getting movie details", movie_id=movie_id)
        
        url = f"{self.BASE_URL}/movie/{movie_id}"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR",
            "append_to_response": "credits"
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return TMDBDetail(**response.json())
    
    async def get_tv_detail(self, tv_id: int) -> TMDBDetail:
        """Get TV show details by ID."""
        logger.info("Getting TV details", tv_id=tv_id)
        
        url = f"{self.BASE_URL}/tv/{tv_id}"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR",
            "append_to_response": "credits"
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return TMDBDetail(**response.json())
