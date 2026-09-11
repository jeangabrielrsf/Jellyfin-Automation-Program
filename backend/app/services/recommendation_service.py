"""Combines TMDB similar + recommendations, dedupes, applies exclusion set."""
import asyncio

from app.services.list_service import ListService


class RecommendationService:
    def __init__(self, db, tmdb):
        self.db = db
        self.tmdb = tmdb

    async def get_recommendations(
        self, media_type: str, tmdb_id: int, *, limit: int = 10
    ) -> list[dict]:
        raw = await self._fetch_union(media_type, tmdb_id)

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
        similar, recs = await asyncio.gather(
            self.tmdb.get_similar(media_type, tmdb_id),
            self.tmdb.get_recommendations(media_type, tmdb_id),
            return_exceptions=True,
        )
        for result in (similar, recs):
            if isinstance(result, BaseException):
                raise result
        return list(similar) + list(recs)
