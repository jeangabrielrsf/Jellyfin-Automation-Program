"""Settings model."""
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base

class Setting(Base):
    __tablename__ = "settings"
    
    key = Column(String(100), primary_key=True)
    value = Column(JSON)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
