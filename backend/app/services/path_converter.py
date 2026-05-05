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


def wsl_to_windows(path: str) -> str:
    r"""Convert a WSL2 Linux path to Windows format.

    /mnt/d/Filmes/Ted Lasso/Season 01 -> D:\Filmes\Ted Lasso\Season 01
    /mnt/c/Users/foo          -> C:\Users\foo
    /home/user/Downloads       -> /home/user/Downloads  (unchanged, not under /mnt/)
    """
    path = Path(path)
    parts = path.parts

    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "mnt":
        drive = parts[2]
        if re.match(r"^[a-zA-Z]$", drive):
            windows_path = f"{drive.upper()}:\\" + "\\".join(parts[3:])
            logger.debug("Converted WSL path to Windows", wsl=str(path), windows=windows_path)
            return windows_path

    return str(path)


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
