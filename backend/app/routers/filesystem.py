"""Filesystem browser router — list directories on the server."""
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/filesystem", tags=["filesystem"])


def _is_wsl2() -> bool:
    """Check if running under WSL2 by looking for /mnt/ mounted drives."""
    mnt = Path("/mnt")
    if not mnt.exists() or not mnt.is_dir():
        return False
    try:
        for entry in mnt.iterdir():
            if entry.is_dir():
                return True
    except PermissionError:
        pass
    return False


@router.get("/root")
def get_root():
    """Return the root directory for browsing."""
    if _is_wsl2():
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
    except PermissionError:
        pass

    parent = str(target.parent)
    if parent == str(target):
        parent = None

    return {
        "path": str(target) + ("/" if str(target) != "/" else ""),
        "dirs": dirs,
        "parent": parent,
    }
