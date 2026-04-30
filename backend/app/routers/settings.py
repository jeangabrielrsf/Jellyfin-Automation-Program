"""Settings router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any
from app.database import get_db
from app.models.settings import Setting

router = APIRouter(prefix="/api/settings", tags=["settings"])

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
    value: Any,
    db: Session = Depends(get_db)
):
    """Update or create a setting."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)

    try:
        db.commit()
        db.refresh(setting)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update setting: {str(e)}")
    return {"key": setting.key, "value": setting.value}
