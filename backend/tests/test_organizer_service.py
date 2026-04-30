"""Tests for organizer service."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
from app.services.organizer_service import OrganizerService

@pytest.fixture
def organizer_service():
    return OrganizerService()

@pytest.fixture
def temp_media_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        movies_dir = Path(tmpdir) / "movies"
        series_dir = Path(tmpdir) / "series"
        animes_dir = Path(tmpdir) / "animes"
        
        movies_dir.mkdir()
        series_dir.mkdir()
        animes_dir.mkdir()
        
        with patch('app.services.organizer_service.get_settings') as mock_settings:
            mock_settings.return_value.movies_path = str(movies_dir)
            mock_settings.return_value.series_path = str(series_dir)
            mock_settings.return_value.animes_path = str(animes_dir)
            yield {
                "movies": movies_dir,
                "series": series_dir,
                "animes": animes_dir
            }

def test_sanitize_filename(organizer_service):
    """Test filename sanitization."""
    assert organizer_service._sanitize_filename("Test: Movie") == "Test_ Movie"
    assert organizer_service._sanitize_filename("Test/Movie") == "Test_Movie"
    assert organizer_service._sanitize_filename("Test<Movie>") == "Test_Movie_"

def test_get_video_files(organizer_service, tmp_path):
    """Test getting video files."""
    video_file = tmp_path / "movie.mp4"
    video_file.write_text("fake video")
    
    txt_file = tmp_path / "readme.txt"
    txt_file.write_text("readme")
    
    video_files = organizer_service._get_video_files(tmp_path)
    assert len(video_files) == 1
    assert video_files[0].name == "movie.mp4"

def test_organize_movie(organizer_service, temp_media_dirs):
    """Test movie organization."""
    service = OrganizerService()
    
    source_dir = Path(tempfile.mkdtemp())
    source_file = source_dir / "movie.mkv"
    source_file.write_text("fake video content")
    
    result = service.organize_movie(
        source_path=str(source_file),
        title="Test Movie",
        year=2023,
        quality="1080p"
    )
    
    assert Path(result).exists()
    assert "Test Movie (2023)" in result
    assert "1080p" in result
