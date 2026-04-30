"""Settings router."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.database import get_db
from app.models.settings import Setting
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    key: str
    value: Any

@router.get("/")
def get_settings(db: Session = Depends(get_db)):
    """Get all settings."""
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}

@router.get("/{key}")
def get_setting(key: str, db: Session = Depends(get_db)):
    """Get specific setting."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        return {"key": setting.key, "value": setting.value}
    return {"key": key, "value": None}

@router.put("/{key}")
def update_setting(
    key: str,
    value: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update or create a setting."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    return {"key": setting.key, "value": setting.value}
