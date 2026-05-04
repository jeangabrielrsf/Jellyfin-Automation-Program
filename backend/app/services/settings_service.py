"""Settings service for reading runtime settings from DB with .env fallback."""
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.settings import Setting


def get_media_paths(db: Session) -> dict:
    """Get media paths from DB settings, falling back to .env values."""
    db_settings = {s.key: s.value for s in db.query(Setting).all()}
    env = get_settings()
    return {
        "movies_path": db_settings.get("movies_path") or env.movies_path,
        "series_path": db_settings.get("series_path") or env.series_path,
        "animes_path": db_settings.get("animes_path") or env.animes_path,
    }
