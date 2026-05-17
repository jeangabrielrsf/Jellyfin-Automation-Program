"""Filesystem browser router — list directories on the server."""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.services.path_converter import is_wsl2
from app.services.config_service import get_config
from app.database import get_db
from app.logging_config import get_logger

router = APIRouter(prefix="/api/filesystem", tags=["filesystem"])
logger = get_logger(__name__)


@router.get("/root")
def get_root():
    """Return the root directory for browsing."""
    if is_wsl2():
        return {"root": "/mnt/"}
    return {"root": "/"}


@router.get("/dirs")
def list_dirs(path: str = Query("/")):
    """List immediate subdirectories of the given path."""
    target = Path(path).resolve()

    if not target.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    dirs = []
    try:
        for entry in sorted(target.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                dirs.append(entry.name)
    except PermissionError as e:
        logger.warning("Permission error listing directory", path=str(target), error=str(e))
    except OSError as e:
        logger.warning("OS error listing directory", path=str(target), error=str(e))

    parent = str(target.parent)
    if parent == str(target):
        parent = None

    return {
        "path": str(target) + ("/" if str(target) != "/" else ""),
        "dirs": dirs,
        "parent": parent,
    }


@router.get("/disk-space/")
def get_disk_space(db: Session = Depends(get_db)):
    """Return aggregated disk space for all unique disks hosting media folders."""
    path_keys = ["movies_path", "series_path", "animes_path"]
    paths = []
    for key in path_keys:
        val = get_config(key, db=db)
        if val:
            paths.append(val)

    if not paths:
        return {"total_bytes": 0, "free_bytes": 0, "used_bytes": 0, "disks_count": 0}

    unique_disks: dict[tuple, dict] = {}

    for path in paths:
        try:
            stat = os.statvfs(path)
        except (OSError, FileNotFoundError) as e:
            logger.warning(f"Cannot statvfs path '{path}': {e}")
            continue

        device_id = stat.f_fsid
        if device_id not in unique_disks:
            unique_disks[device_id] = {
                "total": stat.f_frsize * stat.f_blocks,
                "free": stat.f_frsize * stat.f_bavail,
            }

    total_bytes = sum(d["total"] for d in unique_disks.values())
    free_bytes = sum(d["free"] for d in unique_disks.values())
    used_bytes = total_bytes - free_bytes

    return {
        "total_bytes": total_bytes,
        "free_bytes": free_bytes,
        "used_bytes": used_bytes,
        "disks_count": len(unique_disks),
    }
