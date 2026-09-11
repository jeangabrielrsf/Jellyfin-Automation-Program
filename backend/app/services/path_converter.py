"""Utility to convert between WSL2 Linux paths and Windows paths."""

from pathlib import Path
import re
from app.logging_config import get_logger

logger = get_logger(__name__)

# /mnt/<letter>/... -> <LETTER>:\...
_WSL_PATTERN = re.compile(r"^/mnt/([a-zA-Z])(/.*)?$")


def is_wsl2() -> bool:
    """Detect if running under WSL2 by checking if /mnt/ contains any drive mounts."""
    mnt = Path("/mnt")
    if not mnt.exists() or not mnt.is_dir():
        return False
    try:
        for entry in mnt.iterdir():
            if entry.is_dir() and re.match(r"^[a-zA-Z]$", entry.name):
                return True
    except (PermissionError, OSError):
        pass
    return False


def windows_to_wsl(path: str) -> str:
    r"""Convert a Windows path to WSL2 Linux format.

    D:\Filmes\Ted Lasso  -> /mnt/d/Filmes/Ted Lasso
    C:\Users\foo          -> /mnt/c/Users/foo
    """
    match = re.match(r"^([a-zA-Z]):[\\/]?(.*)$", path)
    if match:
        drive = match.group(1).lower()
        rest = match.group(2).replace("\\", "/")
        wsl_path = f"/mnt/{drive}/{rest}"
        logger.debug("Converted Windows path to WSL", windows=path, wsl=wsl_path)
        return wsl_path

    return path
