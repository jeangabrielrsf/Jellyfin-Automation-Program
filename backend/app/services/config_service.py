"""Unified configuration service — DB > .env > error priority chain."""
from typing import Any, Optional
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.settings import Setting
from app.exceptions import ConfigurationError


def get_config(key: str, db: Optional[Session] = None, required: bool = False) -> str:
    """Get configuration value with priority: DB > .env > error.

    Args:
        key: Configuration key (e.g., 'tmdb_api_key', 'jackett_url').
        db: Optional SQLAlchemy session for DB lookup.
        required: If True, raises ConfigurationError when value not found.

    Returns:
        Configuration value as string, or empty string if not required and not found.
    """
    # 1. Try DB first
    if db is not None:
        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting is not None and setting.value is not None:
            val: Any = setting.value
            # Setting.value is JSON — can be str, int, bool, etc.
            return str(val) if not isinstance(val, str) else val

    # 2. Fallback to .env
    env_settings = get_settings()
    env_value = getattr(env_settings, key, None)
    if env_value:
        return str(env_value)

    # 3. Error if required
    if required:
        raise ConfigurationError(key)

    return ""
