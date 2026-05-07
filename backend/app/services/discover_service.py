"""Discover service — TMDB section data with in-memory TTL cache."""
import time
from typing import Optional, List, Dict, Tuple
from app.config import get_settings
from app.models.discover import (
    DiscoverParams,
    SectionInfo,
    SectionCatalog,
    DiscoverSection,
    Genre,
)
from app.models.tmdb import TMDBSearchResult
from app.logging_config import get_logger

logger = get_logger(__name__)

SECTION_DEFS: List[SectionInfo] = [
    SectionInfo(id="popular-movies", title="Filmes Populares", media_type="movie"),
    SectionInfo(id="popular-series", title="Séries Populares", media_type="series"),
    SectionInfo(id="popular-animes", title="Animes Populares", media_type="anime"),
    SectionInfo(id="trending", title="Tendências da Semana", media_type="mixed"),
    SectionInfo(id="top-rated-movies", title="Filmes Melhor Avaliados", media_type="movie"),
    SectionInfo(id="top-rated-series", title="Séries Melhor Avaliadas", media_type="series"),
    SectionInfo(id="now-playing", title="Nos Cinemas", media_type="movie"),
    SectionInfo(id="upcoming", title="Em Breve", media_type="movie"),
    SectionInfo(id="genre-action", title="Ação", media_type="mixed"),
    SectionInfo(id="genre-comedy", title="Comédia", media_type="mixed"),
    SectionInfo(id="genre-drama", title="Drama", media_type="mixed"),
    SectionInfo(id="genre-horror", title="Terror", media_type="mixed"),
    SectionInfo(id="genre-scifi", title="Ficção Científica", media_type="mixed"),
]

GENRE_SECTION_IDS = {
    "genre-action": 28,
    "genre-comedy": 35,
    "genre-drama": 18,
    "genre-horror": 27,
    "genre-scifi": 878,
}

ANIME_GENRE_ID = 16


class DiscoverService:
    BASE_URL = "https://api.themoviedb.org/3"
    SECTION_TTL = 300   # 5 minutes
    GENRE_TTL = 3600    # 1 hour

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.tmdb_api_key
        self._section_cache: Dict[str, Tuple[float, DiscoverSection]] = {}
        self._genre_cache: Optional[Tuple[float, List[Genre]]] = None

    def _filters_active(self, params: DiscoverParams) -> bool:
        return params.genre_id is not None or params.media_type is not None

    def _cache_key(self, section_id: str, params: DiscoverParams) -> str:
        return f"{section_id}:{params.genre_id}:{params.media_type}:{params.sort_by}"

    def get_sections_catalog(self, params: DiscoverParams) -> SectionCatalog:
        sections = list(SECTION_DEFS)
        if self._filters_active(params):
            sections = [s for s in sections if s.id != "trending"]
        return SectionCatalog(sections=sections)

    async def get_section(self, section_id: str, params: DiscoverParams) -> DiscoverSection:
        import httpx

        # Return cached if still valid
        key = self._cache_key(section_id, params)
        cached = self._section_cache.get(key)
        if cached:
            ts, data = cached
            if time.time() - ts < self.SECTION_TTL:
                return data

        # Find section definition
        section_def = next((s for s in SECTION_DEFS if s.id == section_id), None)
        if not section_def:
            return DiscoverSection(id=section_id, title="", media_type="", results=[], total_results=0)

        # Trending + filters = empty
        if section_id == "trending" and self._filters_active(params):
            return DiscoverSection(
                id=section_id,
                title=section_def.title,
                media_type=section_def.media_type,
                results=[],
                total_results=0,
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                results = await self._fetch_tmdb(client, section_id, section_def, params)
        except Exception:
            logger.exception("Failed to fetch section data", section_id=section_id)
            results = []

        section = DiscoverSection(
            id=section_id,
            title=section_def.title,
            media_type=section_def.media_type,
            results=results,
            total_results=len(results),
        )
        self._section_cache[key] = (time.time(), section)
        return section

    async def _fetch_tmdb(self, client, section_id: str, section_def: SectionInfo, params: DiscoverParams) -> List[TMDBSearchResult]:
        common = {"api_key": self.api_key, "language": "pt-BR"}

        use_discover = self._filters_active(params) or section_id.startswith("genre-") or section_def.media_type == "anime"

        if use_discover:
            media = "tv" if section_def.media_type in ("series", "anime", "mixed") else "movie"
            if section_def.media_type == "movie":
                media = "movie"
            elif section_def.media_type in ("series", "anime"):
                media = "tv"
            else:
                media = "tv" if params.media_type == "series" else "movie"

            url = f"{self.BASE_URL}/discover/{media}"
            query: dict = {**common, "sort_by": params.sort_by}

            # Genre
            if section_id.startswith("genre-"):
                genre_id = GENRE_SECTION_IDS.get(section_id)
                if genre_id:
                    query["with_genres"] = str(genre_id)
            elif params.genre_id:
                query["with_genres"] = str(params.genre_id)

            # Anime
            if section_def.media_type == "anime":
                query["with_genres"] = str(ANIME_GENRE_ID)
                query["with_origin_country"] = "JP"
                if params.genre_id and params.genre_id != ANIME_GENRE_ID:
                    query["with_genres"] = f"{ANIME_GENRE_ID},{params.genre_id}"

        else:
            # Native endpoints (no filters)
            path: str
            param_extra: dict = {}
            if section_id == "popular-movies":
                path = "/movie/popular"
            elif section_id == "popular-series":
                path = "/tv/popular"
            elif section_id == "trending":
                path = "/trending/all/week"
            elif section_id == "top-rated-movies":
                path = "/movie/top_rated"
            elif section_id == "top-rated-series":
                path = "/tv/top_rated"
            elif section_id == "now-playing":
                path = "/movie/now_playing"
            elif section_id == "upcoming":
                path = "/movie/upcoming"
            else:
                path = "/movie/popular"

            url = f"{self.BASE_URL}{path}"
            query = {**common, **param_extra}

        response = await client.get(url, params=query)
        response.raise_for_status()
        data = response.json()

        raw = data.get("results", [])[:20]
        results: List[TMDBSearchResult] = []
        for item in raw:
            mt = item.get("media_type", "")
            if not mt:
                mt = "movie" if "title" in item else "tv"
            results.append(TMDBSearchResult(
                id=item["id"],
                title=item.get("title"),
                name=item.get("name"),
                overview=item.get("overview", ""),
                poster_path=item.get("poster_path"),
                backdrop_path=item.get("backdrop_path"),
                release_date=item.get("release_date"),
                first_air_date=item.get("first_air_date"),
                vote_average=item.get("vote_average", 0.0),
                media_type=mt,
                genre_ids=item.get("genre_ids", []),
            ))
        return results

    async def get_genres(self) -> List[Genre]:
        import httpx

        # Check cache
        if self._genre_cache:
            ts, data = self._genre_cache
            if time.time() - ts < self.GENRE_TTL:
                return data

        common = {"api_key": self.api_key, "language": "pt-BR"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                movie_resp = await client.get(f"{self.BASE_URL}/genre/movie/list", params=common)
                movie_resp.raise_for_status()
                movie_genres = movie_resp.json().get("genres", [])

                tv_resp = await client.get(f"{self.BASE_URL}/genre/tv/list", params=common)
                tv_resp.raise_for_status()
                tv_genres = tv_resp.json().get("genres", [])

            seen: Dict[int, str] = {}
            for g in movie_genres + tv_genres:
                gid = g["id"]
                if gid not in seen:
                    seen[gid] = g["name"]

            genres = [Genre(id=gid, name=name) for gid, name in sorted(seen.items())]
            self._genre_cache = (time.time(), genres)
            return genres
        except Exception:
            logger.exception("Failed to fetch genres")
            return []
