"""Discover service — TMDB section data."""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict

import httpx
from sqlalchemy.orm import Session

from app.services.config_service import get_config
from app.models.discover import (
    SectionInfo,
    SectionCatalog,
    DiscoverSection,
    Genre,
    BannerMedia,
)
from app.models.tmdb import TMDBSearchResult
from app.logging_config import get_logger

logger = get_logger(__name__)

SECTION_DEFS: List[SectionInfo] = [
    SectionInfo(id="trending", title="Tendências da Semana", media_type="mixed"),
    SectionInfo(id="recently-added", title="Recém Adicionados", media_type="mixed"),
    SectionInfo(id="streaming-hot", title="Em Alta no Streaming", media_type="mixed"),
    SectionInfo(id="seasonal-anime", title="Animes da Temporada", media_type="anime"),
    SectionInfo(id="classics", title="Clássicos Imperdíveis", media_type="movie"),
]

STREAMING_PROVIDERS = [
    {"id": 8, "name": "Netflix", "logo_path": None},
    {"id": 119, "name": "Amazon Prime Video", "logo_path": None},
    {"id": 337, "name": "Disney+", "logo_path": None},
    {"id": 384, "name": "HBO Max", "logo_path": None},
    {"id": 350, "name": "Apple TV+", "logo_path": None},
    {"id": 307, "name": "Globoplay", "logo_path": None},
    {"id": 531, "name": "Paramount+", "logo_path": None},
]

STREAMING_PROVIDER_IDS = "|".join(str(p["id"]) for p in STREAMING_PROVIDERS)


class DiscoverService:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, db: Session | None = None):
        self.db = db
        self.api_key = get_config("tmdb_api_key", db, required=True)
        self.client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        await self.client.aclose()

    @staticmethod
    def _pick_banner_index(now: datetime) -> int:
        return (now.timetuple().tm_yday - 1) % 5

    async def _fetch_banner(self) -> Optional[TMDBSearchResult]:
        try:
            common = {"api_key": self.api_key, "language": "pt-BR", "include_adult": "false"}
            response = await self.client.get(
                f"{self.BASE_URL}/trending/all/week", params=common
            )
            response.raise_for_status()
            data = response.json()
            raw = data.get("results", [])[:5]

            if not raw:
                return None

            index = self._pick_banner_index(datetime.now())
            index = min(index, len(raw) - 1)
            item = raw[index]

            mt = item.get("media_type", "")
            if not mt:
                mt = "movie" if "title" in item else "tv"

            tmdb_type = "movie" if mt == "movie" else "tv"
            detail_url = f"{self.BASE_URL}/{tmdb_type}/{item['id']}"
            providers_url = f"{self.BASE_URL}/{tmdb_type}/{item['id']}/watch/providers"

            detail_resp, providers_resp = await asyncio.gather(
                self.client.get(detail_url, params={"api_key": self.api_key, "language": "pt-BR"}),
                self.client.get(providers_url, params={"api_key": self.api_key}),
                return_exceptions=True,
            )

            genres: List[str] = []
            runtime: Optional[int] = None
            if not isinstance(detail_resp, Exception):
                detail_resp.raise_for_status()
                detail = detail_resp.json()
                genres = [g["name"] for g in detail.get("genres", [])]
                runtime = detail.get("runtime")
                if mt == "tv":
                    eps = detail.get("episode_run_time", [])
                    if eps and isinstance(eps, list):
                        runtime = eps[0]

            providers: List[str] = []
            if not isinstance(providers_resp, Exception):
                providers_resp.raise_for_status()
                pdata = providers_resp.json()
                br = pdata.get("results", {}).get("BR", {})
                providers = [p["provider_name"] for p in br.get("flatrate", [])]

            title = item.get("title") or item.get("name")
            date = item.get("release_date") or item.get("first_air_date")
            year = int(date[:4]) if date and len(date) >= 4 and date[:4].isdigit() else None

            banner = BannerMedia(
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
                genres=genres,
                providers=providers,
                runtime=runtime,
                display_title=title,
                year=year,
            )
            return banner
        except Exception:
            logger.exception("Failed to fetch banner")
            return None

    async def get_sections_catalog(self) -> SectionCatalog:
        banner = await self._fetch_banner()
        sections = list(SECTION_DEFS)
        return SectionCatalog(banner=banner, sections=sections)

    async def get_section(self, section_id: str) -> DiscoverSection:
        section_def = next((s for s in SECTION_DEFS if s.id == section_id), None)
        if not section_def:
            return DiscoverSection(id=section_id, title="", media_type="", results=[], total_results=0)

        try:
            results = await self._fetch_tmdb(section_id, section_def)
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
        return section

    async def _fetch_tmdb(self, section_id: str, section_def: SectionInfo) -> List[TMDBSearchResult]:
        common = {"api_key": self.api_key, "language": "pt-BR", "include_adult": "false"}

        url: str
        query: dict

        if section_id == "trending":
            url = f"{self.BASE_URL}/trending/all/week"
            query = {**common}
        elif section_id == "recently-added":
            url = f"{self.BASE_URL}/discover/movie"
            date_30_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            query = {
                **common,
                "sort_by": "primary_release_date.desc",
                "with_watch_providers": STREAMING_PROVIDER_IDS,
                "watch_region": "BR",
                "primary_release_date.gte": date_30_days_ago,
            }
        elif section_id == "streaming-hot":
            url = f"{self.BASE_URL}/discover/movie"
            query = {
                **common,
                "sort_by": "popularity.desc",
                "with_watch_providers": STREAMING_PROVIDER_IDS,
                "watch_region": "BR",
            }
        elif section_id == "seasonal-anime":
            url = f"{self.BASE_URL}/discover/tv"
            query = {
                **common,
                "sort_by": "popularity.desc",
                "with_genres": "16",
                "with_origin_country": "JP",
            }
        elif section_id == "classics":
            url = f"{self.BASE_URL}/discover/movie"
            query = {
                **common,
                "sort_by": "vote_average.desc",
                "vote_count.gte": "1000",
            }
        else:
            url = f"{self.BASE_URL}/movie/popular"
            query = {**common}

        response = await self.client.get(url, params=query)
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
        common = {"api_key": self.api_key, "language": "pt-BR", "include_adult": "false"}
        try:
            movie_resp = await self.client.get(f"{self.BASE_URL}/genre/movie/list", params=common)
            movie_resp.raise_for_status()
            movie_genres = movie_resp.json().get("genres", [])

            tv_resp = await self.client.get(f"{self.BASE_URL}/genre/tv/list", params=common)
            tv_resp.raise_for_status()
            tv_genres = tv_resp.json().get("genres", [])

            seen: Dict[int, str] = {}
            for g in movie_genres + tv_genres:
                gid = g["id"]
                if gid not in seen:
                    seen[gid] = g["name"]

            genres = [Genre(id=gid, name=name) for gid, name in sorted(seen.items())]
            return genres
        except Exception:
            logger.exception("Failed to fetch genres")
            return []
