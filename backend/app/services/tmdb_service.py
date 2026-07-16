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

    async def discover(
        self,
        media_type: str = "all",
        genre_ids: list[int] | None = None,
        watch_provider_ids: list[int] | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        min_rating: float | None = None,
        sort_by: str = "popularity.desc",
        page: int = 1,
    ) -> TMDBSearchResponse:
        """Discover movies/TV with filters via TMDB /discover endpoints."""
        import asyncio
        logger.info(
            "Discover",
            media_type=media_type,
            genre_ids=genre_ids,
            watch_provider_ids=watch_provider_ids,
            year_from=year_from,
            year_to=year_to,
            min_rating=min_rating,
            sort_by=sort_by,
            page=page,
        )

        if media_type == "all":
            movie_resp, tv_resp = await asyncio.gather(
                self._discover_single("movie", genre_ids, watch_provider_ids, year_from, year_to, min_rating, sort_by, page),
                self._discover_single("tv", genre_ids, watch_provider_ids, year_from, year_to, min_rating, sort_by, page),
            )
            combined = movie_resp.results + tv_resp.results
            combined.sort(key=lambda r: self._sort_key(r, sort_by), reverse=self._sort_reverse(sort_by))
            combined = combined[:20]
            total_results = movie_resp.total_results + tv_resp.total_results
            total_pages = max(movie_resp.total_pages, tv_resp.total_pages)
            return TMDBSearchResponse(
                page=page,
                results=combined,
                total_results=total_results,
                total_pages=total_pages,
            )

        tmdb_type = "tv" if media_type in ("series", "anime") else "movie"
        return await self._discover_single(tmdb_type, genre_ids, watch_provider_ids, year_from, year_to, min_rating, sort_by, page, is_anime=(media_type == "anime"))

    async def _discover_single(
        self,
        tmdb_type: str,
        genre_ids: list[int] | None,
        watch_provider_ids: list[int] | None,
        year_from: int | None,
        year_to: int | None,
        min_rating: float | None,
        sort_by: str,
        page: int,
        is_anime: bool = False,
    ) -> TMDBSearchResponse:
        url = f"{self.BASE_URL}/discover/{tmdb_type}"
        params: dict = {
            "api_key": self.api_key,
            "language": "pt-BR",
            "include_adult": "false",
            "sort_by": sort_by,
            "page": page,
        }

        if is_anime:
            params["with_origin_country"] = "JP"
            all_genres = [16] + [g for g in (genre_ids or []) if g != 16]
            params["with_genres"] = "|".join(str(g) for g in all_genres)
        elif genre_ids:
            params["with_genres"] = "|".join(str(g) for g in genre_ids)

        if watch_provider_ids:
            params["with_watch_providers"] = ",".join(str(p) for p in watch_provider_ids)
            params["watch_region"] = "BR"

        date_prefix = "primary_release_date" if tmdb_type == "movie" else "first_air_date"
        if year_from is not None:
            params[f"{date_prefix}.gte"] = f"{year_from}-01-01"
        if year_to is not None:
            params[f"{date_prefix}.lte"] = f"{year_to}-12-31"

        if min_rating is not None:
            params["vote_average.gte"] = min_rating

        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        results = [
            TMDBSearchResult(**{**item, "media_type": item.get("media_type", tmdb_type)})
            for item in data.get("results", [])
        ]

        return TMDBSearchResponse(
            page=data.get("page", page),
            results=results,
            total_pages=data.get("total_pages", 0),
            total_results=data.get("total_results", 0),
        )

    @staticmethod
    def _sort_key(result: TMDBSearchResult, sort_by: str):
        if sort_by == "popularity.desc":
            return result.popularity or 0.0
        if sort_by == "vote_average.desc":
            return result.vote_average
        if sort_by == "vote_count.desc":
            return result.vote_count or 0
        if sort_by == "release_date.desc":
            date = result.release_date or result.first_air_date or ""
            return float(date.replace("-", "")) if date else 0.0
        if sort_by == "original_title.asc":
            return (result.original_title or result.title or result.original_name or result.name or "").lower()
        return result.popularity or 0.0

    @staticmethod
    def _sort_reverse(sort_by: str) -> bool:
        return sort_by != "original_title.asc"

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
