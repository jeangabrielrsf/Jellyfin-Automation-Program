"""Filesystem browser router — list directories on the server."""
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from app.services.path_converter import is_wsl2
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
