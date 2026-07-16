"""TMDB API service."""
import httpx
from typing import List, Optional
from sqlalchemy.orm import Session
from app.services.config_service import get_config
from app.models.tmdb import TMDBSearchResult, TMDBSearchResponse, TMDBDetail
from app.logging_config import get_logger

logger = get_logger(__name__)


class TMDBService:
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
    
    def __init__(self, db: Session | None = None):
        self.db = db
        self.api_key = get_config("tmdb_api_key", db, required=True)
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
            "append_to_response": "credits,external_ids,videos"
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
            "append_to_response": "credits,external_ids,videos"
        }

        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return TMDBDetail(**response.json())

    async def get_tv_season_detail(self, tv_id: int, season_number: int) -> dict:
        """Get season detail with episodes by TV ID and season number."""
        logger.info("Getting TV season details", tv_id=tv_id, season_number=season_number)

        url = f"{self.BASE_URL}/tv/{tv_id}/season/{season_number}"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR"
        }

        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_similar_movies(self, movie_id: int) -> list[dict]:
        """Fetch movies similar to the given movie id."""
        logger.info("Fetching similar movies", movie_id=movie_id)
        url = f"{self.BASE_URL}/movie/{movie_id}/similar"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR",
        }
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("results", [])

    async def get_similar_tv(self, tv_id: int) -> list[dict]:
        """Fetch TV shows similar to the given tv id."""
        logger.info("Fetching similar TV", tv_id=tv_id)
        url = f"{self.BASE_URL}/tv/{tv_id}/similar"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR",
        }
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("results", [])

    async def get_recommendations_movies(self, movie_id: int) -> list[dict]:
        """Fetch TMDB-curated movie recommendations for the given movie id."""
        logger.info("Fetching movie recommendations", movie_id=movie_id)
        url = f"{self.BASE_URL}/movie/{movie_id}/recommendations"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR",
        }
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("results", [])

    async def get_recommendations_tv(self, tv_id: int) -> list[dict]:
        """Fetch TMDB-curated TV recommendations for the given tv id."""
        logger.info("Fetching TV recommendations", tv_id=tv_id)
        url = f"{self.BASE_URL}/tv/{tv_id}/recommendations"
        params = {
            "api_key": self.api_key,
            "language": "pt-BR",
        }
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("results", [])

    async def get_movie_alternative_titles(self, movie_id: int) -> list[dict]:
        """Fetch alternative titles for a movie."""
        logger.info("Fetching movie alternative titles", movie_id=movie_id)
        url = f"{self.BASE_URL}/movie/{movie_id}/alternative_titles"
        params = {"api_key": self.api_key}
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        titles = []
        for country_data in data.get("titles", []):
            titles.append({
                "country": country_data.get("iso_3166_1"),
                "title": country_data.get("title")
            })
        return titles

    async def get_tv_alternative_titles(self, tv_id: int) -> list[dict]:
        """Fetch alternative titles for a TV show."""
        logger.info("Fetching TV alternative titles", tv_id=tv_id)
        url = f"{self.BASE_URL}/tv/{tv_id}/alternative_titles"
        params = {"api_key": self.api_key}
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        titles = []
        for country_data in data.get("results", []):
            titles.append({
                "country": country_data.get("iso_3166_1"),
                "title": country_data.get("title")
            })
        return titles
