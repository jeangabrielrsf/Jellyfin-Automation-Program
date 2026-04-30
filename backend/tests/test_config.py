"""Tests for configuration."""
import os
import pytest
from app.config import Settings, get_settings

def test_settings_defaults():
    """Test that settings have correct defaults."""
    settings = Settings()
    assert settings.app_port == 8000
    assert settings.log_level == "INFO"
    assert settings.default_quality == "1080p"
    assert settings.default_language == "legendado"

def test_settings_from_env():
    """Test that settings can be loaded from environment variables."""
    os.environ["APP_PORT"] = "9000"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    settings = Settings()
    assert settings.app_port == 9000
    assert settings.log_level == "DEBUG"
    
    # Cleanup
    del os.environ["APP_PORT"]
    del os.environ["LOG_LEVEL"]

def test_get_settings_cached():
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2
