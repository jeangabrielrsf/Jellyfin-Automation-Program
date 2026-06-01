"""UserList model — single-user watched and watchlist tracking."""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint, Column, DateTime, Enum, Integer, String, UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ListKind(str, enum.Enum):
    WATCHED = "watched"
    WATCHLIST = "watchlist"


class UserList(Base):
    __tablename__ = "user_lists"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(Enum(ListKind), nullable=False)
    media_type = Column(String(16), nullable=False)
    tmdb_id = Column(Integer, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    poster_path = Column(String(255))
    backdrop_path = Column(String(255))
    year = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=_utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tmdb_id", "media_type", "kind", name="uq_user_lists_tmdb_type_kind"),
        CheckConstraint(
            "media_type IN ('movie','series','anime')",
            name="ck_user_lists_media_type",
        ),
    )
