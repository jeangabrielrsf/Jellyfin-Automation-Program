"""Settings model."""
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base

class Setting(Base):
    __tablename__ = "settings"
    
    key = Column(String(100), primary_key=True)
    value = Column(JSONB)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
