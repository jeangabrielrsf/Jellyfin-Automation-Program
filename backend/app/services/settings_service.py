"""Settings service — DEPRECATED: use config_service.get_config() instead."""
from sqlalchemy.orm import Session
from app.services.config_service import get_config


def get_media_paths(db: Session) -> dict:
    """DEPRECATED: Use get_config() for individual path keys instead."""
    return {
        "movies_path": get_config("movies_path", db, required=True),
        "series_path": get_config("series_path", db, required=True),
        "animes_path": get_config("animes_path", db, required=True),
    }
