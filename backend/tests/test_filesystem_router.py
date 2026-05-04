"""Tests for the filesystem router."""
import tempfile
import os
import pytest
from unittest.mock import patch


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
    with patch("app.routers.filesystem._is_wsl2", return_value=False):
        response = client.get("/api/filesystem/root")
    assert response.status_code == 200
    data = response.json()
    assert data["root"] == "/"


def test_get_root_wsl2(client):
    """Test /api/filesystem/root returns /mnt/ on WSL2."""
    with patch("app.routers.filesystem._is_wsl2", return_value=True):
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
