"""Tests for the settings service."""
import pytest
from app.services.settings_service import get_media_paths
from app.models.settings import Setting


def test_get_media_paths_from_db(db_session):
    """Test that paths are read from DB when present."""
    db_session.add(Setting(key="movies_path", value="/custom/movies"))
    db_session.add(Setting(key="animes_path", value="/custom/anime"))
    db_session.commit()

    paths = get_media_paths(db_session)
    assert paths["movies_path"] == "/custom/movies"
    assert paths["animes_path"] == "/custom/anime"
    assert paths["series_path"] == "D:\\Séries"  # falls back to .env default


def test_get_media_paths_empty_db(db_session):
    """Test that all paths fall back to .env when DB is empty."""
    paths = get_media_paths(db_session)
    assert paths["movies_path"] == "D:\\Filmes"
    assert paths["series_path"] == "D:\\Séries"
    assert paths["animes_path"] == "D:\\Animes"


def test_get_media_paths_partial_db(db_session):
    """Test partial DB settings still fall back for missing keys."""
    db_session.add(Setting(key="movies_path", value="/only/movies"))
    db_session.commit()

    paths = get_media_paths(db_session)
    assert paths["movies_path"] == "/only/movies"
    assert paths["series_path"] == "D:\\Séries"
    assert paths["animes_path"] == "D:\\Animes"
