"""OMDB API service for Rotten Tomatoes ratings."""
import re
from urllib.parse import quote_plus
import httpx
from app.logging_config import get_logger

logger = get_logger(__name__)


class OMDbService:
    BASE_URL = "https://www.omdbapi.com"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=15.0)

    async def close(self):
        await self.client.aclose()

    async def get_by_imdb_id(self, imdb_id: str) -> dict | None:
        """Fetch OMDB data by IMDb ID. Returns {rt_rating: '94%'} or None."""
        try:
            url = self.BASE_URL
            params = {
                "apikey": self.api_key,
                "i": imdb_id,
            }
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("Response") == "False":
                logger.warning("OMDB returned False response", imdb_id=imdb_id)
                return None

            ratings = data.get("Ratings") or []
            for rating in ratings:
                if rating.get("Source") == "Rotten Tomatoes":
                    return {"rt_rating": rating["Value"]}

            logger.info("No Rotten Tomatoes rating in OMDB response", imdb_id=imdb_id)
            return None
        except Exception as e:
            logger.warning("OMDB request failed", imdb_id=imdb_id, error=str(e))
            return None

    async def build_rt_url(self, title: str, media_type: str) -> str:
        """Build a validated Rotten Tomatoes URL for the given title.

        Tries slug URL first (HEAD check), falls back to search URL.
        """
        slug = self._slugify(title)
        if media_type == "tv":
            slug_url = f"https://www.rottentomatoes.com/tv/{slug}"
        else:
            slug_url = f"https://www.rottentomatoes.com/m/{slug}"

        try:
            head_response = await self.client.head(slug_url, follow_redirects=True)
            if head_response.status_code == 200:
                return slug_url
        except Exception:
            pass

        search_url = f"https://www.rottentomatoes.com/search?search={quote_plus(title)}"
        return search_url

    @staticmethod
    def _slugify(title: str) -> str:
        """Convert a title to a Rotten Tomatoes-compatible slug."""
        slug = title.lower()
        slug = slug.replace(" ", "_")
        slug = re.sub(r"[^a-z0-9_]", "", slug)
        slug = re.sub(r"_+", "_", slug)
        slug = slug.strip("_")
        return slug
