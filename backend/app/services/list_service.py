"""CRUD and exclusion logic for the user_lists table."""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.download import Download, DownloadStatus
from app.models.user_list import ListKind, UserList


class ListService:
    """Single-user wrapper around the user_lists table."""

    def __init__(self, db: Session):
        self.db = db

    def get_status(self, media_type: str, tmdb_id: int) -> dict:
        rows = (
            self.db.query(UserList)
            .filter(
                UserList.media_type == media_type,
                UserList.tmdb_id == tmdb_id,
            )
            .all()
        )
        return {
            "watched": any(r.kind == ListKind.WATCHED for r in rows),
            "watchlist": any(r.kind == ListKind.WATCHLIST for r in rows),
        }

    def add(
        self,
        kind: ListKind,
        media_type: str,
        tmdb_id: int,
        *,
        title: str,
        poster_path: Optional[str],
        backdrop_path: Optional[str],
        year: Optional[int],
    ) -> UserList:
        existing = (
            self.db.query(UserList)
            .filter(
                UserList.kind == kind,
                UserList.media_type == media_type,
                UserList.tmdb_id == tmdb_id,
            )
            .first()
        )
        if existing:
            existing.title = title
            existing.poster_path = poster_path
            existing.backdrop_path = backdrop_path
            existing.year = year
            self.db.commit()
            self.db.refresh(existing)
            return existing

        row = UserList(
            kind=kind,
            media_type=media_type,
            tmdb_id=tmdb_id,
            title=title,
            poster_path=poster_path,
            backdrop_path=backdrop_path,
            year=year,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def remove(self, kind: ListKind, media_type: str, tmdb_id: int) -> bool:
        existing = (
            self.db.query(UserList)
            .filter(
                UserList.kind == kind,
                UserList.media_type == media_type,
                UserList.tmdb_id == tmdb_id,
            )
            .first()
        )
        if not existing:
            return False
        self.db.delete(existing)
        self.db.commit()
        return True

    def list_watchlist(self) -> list[UserList]:
        return (
            self.db.query(UserList)
            .filter(UserList.kind == ListKind.WATCHLIST)
            .order_by(UserList.created_at.desc())
            .all()
        )

    def list_watched(self) -> list[UserList]:
        return (
            self.db.query(UserList)
            .filter(UserList.kind == ListKind.WATCHED)
            .order_by(UserList.created_at.desc())
            .all()
        )

    def excluded_tmdb_ids(self, media_type: str) -> set[int]:
        list_ids = {
            row.tmdb_id
            for row in self.db.query(UserList.tmdb_id)
            .filter(UserList.media_type == media_type)
            .all()
        }
        download_ids = {
            row.tmdb_id
            for row in self.db.query(Download.tmdb_id)
            .filter(
                Download.type == media_type,
                Download.status == DownloadStatus.COMPLETED,
            )
            .all()
        }
        return list_ids | download_ids
