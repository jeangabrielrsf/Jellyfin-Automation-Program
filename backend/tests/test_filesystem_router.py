"""Tests for the filesystem router."""
import tempfile
import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def temp_dir():
    """Create a temporary directory structure for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "Movies"), exist_ok=True)
        os.makedirs(os.path.join(tmp, "Series"), exist_ok=True)
        os.makedirs(os.path.join(tmp, ".hidden"), exist_ok=True)
        with open(os.path.join(tmp, "file.txt"), "w") as f:
            f.write("test")
        yield tmp


def test_get_root_not_wsl2(client):
    """Test /api/filesystem/root returns / when not in WSL2."""
    with patch("app.routers.filesystem.is_wsl2", return_value=False):
        response = client.get("/api/filesystem/root")
    assert response.status_code == 200
    data = response.json()
    assert data["root"] == "/"


def test_get_root_wsl2(client):
    """Test /api/filesystem/root returns /mnt/ on WSL2."""
    with patch("app.routers.filesystem.is_wsl2", return_value=True):
        response = client.get("/api/filesystem/root")
    assert response.status_code == 200
    data = response.json()
    assert data["root"] == "/mnt/"


def test_list_dirs_success(client, temp_dir):
    """Test listing directories returns expected subdirectories."""
    response = client.get("/api/filesystem/dirs", params={"path": temp_dir})
    assert response.status_code == 200
    data = response.json()
    assert "Movies" in data["dirs"]
    assert "Series" in data["dirs"]
    assert ".hidden" not in data["dirs"]  # dot-prefixed directories excluded
    assert "file.txt" not in data["dirs"]        # files excluded
    assert "parent" in data


def test_list_dirs_nonexistent(client):
    """Test listing a nonexistent directory returns 404."""
    response = client.get("/api/filesystem/dirs", params={"path": "/nonexistent/path/xyz"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Directory not found"


def test_list_dirs_not_a_directory(client, temp_dir):
    """Test listing a file returns 400."""
    file_path = os.path.join(temp_dir, "file.txt")
    response = client.get("/api/filesystem/dirs", params={"path": file_path})
    assert response.status_code == 400
    assert response.json()["detail"] == "Path is not a directory"


def test_list_dirs_root(client):
    """Test listing root directory works (may have no dirs in test container but shouldn't 500)."""
    response = client.get("/api/filesystem/dirs", params={"path": "/"})
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "/"
    assert "dirs" in data


def test_disk_space_no_paths(client, db_session):
    """Test disk space returns zeros when no paths are configured."""
    with patch("app.routers.filesystem.get_config", return_value=""):
        response = client.get("/api/filesystem/disk-space/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_bytes"] == 0
    assert data["free_bytes"] == 0
    assert data["used_bytes"] == 0
    assert data["disks_count"] == 0


def test_disk_space_single_disk(client, db_session):
    """Test disk space returns correct values for a single disk."""
    mock_statvfs = MagicMock()
    mock_statvfs.f_frsize = 4096
    mock_statvfs.f_blocks = 1000000
    mock_statvfs.f_bavail = 600000
    mock_statvfs.f_fsid = (1, 2)

    with patch("app.routers.filesystem.get_config") as mock_config:
        mock_config.side_effect = lambda key, db, required=False: {
            "movies_path": "/media/movies",
            "series_path": "/media/series",
            "animes_path": "/media/animes",
        }.get(key, "")
        with patch("os.statvfs", return_value=mock_statvfs):
            response = client.get("/api/filesystem/disk-space/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_bytes"] == 4096 * 1000000
    assert data["free_bytes"] == 4096 * 600000
    assert data["used_bytes"] == data["total_bytes"] - data["free_bytes"]
    assert data["disks_count"] == 1


def test_disk_space_multiple_disks(client, db_session):
    """Test disk space correctly sums multiple unique disks."""
    mock_statvfs_1 = MagicMock()
    mock_statvfs_1.f_frsize = 4096
    mock_statvfs_1.f_blocks = 1000000
    mock_statvfs_1.f_bavail = 500000
    mock_statvfs_1.f_fsid = (1, 1)

    mock_statvfs_2 = MagicMock()
    mock_statvfs_2.f_frsize = 4096
    mock_statvfs_2.f_blocks = 2000000
    mock_statvfs_2.f_bavail = 1500000
    mock_statvfs_2.f_fsid = (2, 2)

    with patch("app.routers.filesystem.get_config") as mock_config:
        mock_config.side_effect = lambda key, db, required=False: {
            "movies_path": "/media/movies",
            "series_path": "/media/series",
            "animes_path": "/media/animes",
        }.get(key, "")
        with patch("os.statvfs", side_effect=[
            mock_statvfs_1,
            mock_statvfs_1,
            mock_statvfs_2,
        ]):
            response = client.get("/api/filesystem/disk-space/")
    assert response.status_code == 200
    data = response.json()
    expected_total = 4096 * 1000000 + 4096 * 2000000
    expected_free = 4096 * 500000 + 4096 * 1500000
    assert data["total_bytes"] == expected_total
    assert data["free_bytes"] == expected_free
    assert data["used_bytes"] == expected_total - expected_free
    assert data["disks_count"] == 2


def test_disk_space_path_does_not_exist(client, db_session):
    """Test disk space skips paths that don't exist."""
    with patch("app.routers.filesystem.get_config") as mock_config:
        mock_config.side_effect = lambda key, db, required=False: {
            "movies_path": "/nonexistent/path",
            "series_path": "",
            "animes_path": "",
        }.get(key, "")
        response = client.get("/api/filesystem/disk-space/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_bytes"] == 0
    assert data["free_bytes"] == 0
    assert data["disks_count"] == 0
