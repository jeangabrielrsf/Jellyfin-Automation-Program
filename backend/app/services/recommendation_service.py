"""Combines TMDB similar + recommendations, dedupes, applies exclusion set, caches."""
import asyncio
import time

from app.services.list_service import ListService


class RecommendationService:
    CACHE_TTL_SECONDS = 3600

    def __init__(self, db, tmdb):
        self.db = db
        self.tmdb = tmdb
        self._cache: dict[tuple[str, int], tuple[float, list[dict]]] = {}

    async def get_recommendations(
        self, media_type: str, tmdb_id: int, *, limit: int = 10
    ) -> list[dict]:
        key = (media_type, tmdb_id)
        now = time.time()

        cached = self._cache.get(key)
        if cached is not None and now - cached[0] < self.CACHE_TTL_SECONDS:
            raw = cached[1]
        else:
            raw = await self._fetch_union(media_type, tmdb_id)
            self._cache[key] = (now, raw)

        excluded = ListService(self.db).excluded_tmdb_ids(media_type)

        seen: set[tuple[int, str]] = set()
        result: list[dict] = []
        for item in raw:
            item_id = item.get("id")
            if item_id is None or item_id == tmdb_id:
                continue
            if item_id in excluded:
                continue
            dedupe_key = (item_id, item.get("media_type", media_type))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            result.append(item)
            if len(result) >= limit:
                break
        return result

    async def _fetch_union(self, media_type: str, tmdb_id: int) -> list[dict]:
        if media_type == "movie":
            similar_task = self.tmdb.get_similar_movies(tmdb_id)
            recs_task = self.tmdb.get_recommendations_movies(tmdb_id)
        else:
            similar_task = self.tmdb.get_similar_tv(tmdb_id)
            recs_task = self.tmdb.get_recommendations_tv(tmdb_id)

        similar, recs = await asyncio.gather(similar_task, recs_task)
        return list(similar) + list(recs)
