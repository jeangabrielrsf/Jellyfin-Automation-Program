"""Settings router."""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any
from app.database import get_db
from app.models.settings import Setting
from app.services.path_converter import is_wsl2, windows_to_wsl
from app.logging_config import get_logger

router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = get_logger(__name__)

_PATH_SETTINGS = {"movies_path", "series_path", "animes_path"}


def _validate_path_setting(key: str, value: str) -> str:
    """Validate and optionally convert path setting values.

    On WSL2, auto-convert Windows paths (D:\\Foo) to WSL paths (/mnt/d/Foo)
    and warn about backslash usage.
    """
    if key not in _PATH_SETTINGS:
        return value

    if not isinstance(value, str):
        return value

    value = value.strip()

    # If running in WSL2 and user enters a Windows-style path, auto-convert
    if is_wsl2() and value and len(value) >= 2 and value[1] == ":":
        converted = windows_to_wsl(value)
        logger.info("Auto-converted Windows path to WSL", key=key, original=value, converted=converted)
        return converted

    # Reject paths with backslashes (Windows-style on Linux)
    if "\\" in value:
        raise HTTPException(
            status_code=400,
            detail=f"Path for '{key}' contains backslashes. Use forward slashes (e.g. /mnt/d/Filmes) instead."
        )

    return value

@router.get("/")
def get_settings(db: Session = Depends(get_db)):
    """Get all settings."""
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}

@router.get("/{key}")
def get_setting(key: str, db: Session = Depends(get_db)):
    """Get specific setting."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return {"key": setting.key, "value": setting.value}

@router.put("/{key}")
def update_setting(
    key: str,
    value: Any = Body(...),
    db: Session = Depends(get_db)
):
    """Update or create a setting."""
    validated_value = _validate_path_setting(key, value)

    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = validated_value
    else:
        setting = Setting(key=key, value=validated_value)
        db.add(setting)

    try:
        db.commit()
        db.refresh(setting)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update setting: {str(e)}")
    return {"key": setting.key, "value": setting.value}
