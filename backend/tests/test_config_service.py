"""Tests for the unified config service."""
import os
import pytest
from app.services.config_service import get_config
from app.exceptions import ConfigurationError
from app.models.settings import Setting
from app.config import get_settings


def _clear_settings_cache():
    """Clear lru_cache on get_settings so os.environ changes take effect."""
    get_settings.cache_clear()


class TestGetConfig:
    """Tests for get_config() priority chain."""

    def test_returns_db_value_when_present(self, db_session):
        """DB value takes priority over .env."""
        db_session.add(Setting(key="tmdb_api_key", value="db-value"))
        db_session.commit()

        result = get_config("tmdb_api_key", db=db_session)
        assert result == "db-value"

    def test_falls_back_to_env_when_db_empty(self, db_session):
        """When key not in DB, falls back to .env."""
        os.environ["TMDB_API_KEY"] = "env-value"
        _clear_settings_cache()
        try:
            result = get_config("tmdb_api_key", db=db_session)
            assert result == "env-value"
        finally:
            del os.environ["TMDB_API_KEY"]
            _clear_settings_cache()

    def test_falls_back_to_env_when_db_has_none_value(self, db_session):
        """When DB has key but value is None, falls back to .env."""
        db_session.add(Setting(key="tmdb_api_key", value=None))
        db_session.commit()

        os.environ["TMDB_API_KEY"] = "env-value"
        _clear_settings_cache()
        try:
            result = get_config("tmdb_api_key", db=db_session)
            assert result == "env-value"
        finally:
            del os.environ["TMDB_API_KEY"]
            _clear_settings_cache()

    def test_raises_error_when_required_and_not_found(self, db_session):
        """Raises ConfigurationError when required=True and value missing."""
        with pytest.raises(ConfigurationError) as exc_info:
            get_config("tmdb_api_key", db=db_session, required=True)
        assert "tmdb_api_key" in str(exc_info.value)

    def test_returns_empty_string_when_not_required(self, db_session):
        """Returns empty string when not required and value missing."""
        result = get_config("tmdb_api_key", db=db_session, required=False)
        assert result == ""

    def test_returns_int_as_string_from_db(self, db_session):
        """Integer values from DB are returned as strings."""
        db_session.add(Setting(key="jackett_timeout", value=120))
        db_session.commit()

        result = get_config("jackett_timeout", db=db_session)
        assert result == "120"
        assert isinstance(result, str)

    def test_db_priority_over_env(self, db_session):
        """DB value is returned even when .env also has a value."""
        db_session.add(Setting(key="jackett_url", value="http://db-jackett:9117"))
        db_session.commit()

        os.environ["JACKETT_URL"] = "http://env-jackett:9117"
        _clear_settings_cache()
        try:
            result = get_config("jackett_url", db=db_session)
            assert result == "http://db-jackett:9117"
        finally:
            del os.environ["JACKETT_URL"]
            _clear_settings_cache()

    def test_without_db_falls_back_to_env(self):
        """When db=None, skips DB lookup and goes straight to .env."""
        os.environ["OMDB_API_KEY"] = "test-key"
        _clear_settings_cache()
        try:
            result = get_config("omdb_api_key", db=None)
            assert result == "test-key"
        finally:
            del os.environ["OMDB_API_KEY"]
            _clear_settings_cache()

    def test_without_db_raises_when_required_and_missing(self):
        """When db=None and required=True, raises if .env has no value."""
        with pytest.raises(ConfigurationError):
            get_config("tmdb_api_key", db=None, required=True)
