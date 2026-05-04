import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.download_worker import DownloadWorker

@pytest.fixture
def mock_db():
    db = MagicMock()
    return db

@pytest.fixture
def mock_qbit_service():
    service = AsyncMock()
    service.get_torrents = AsyncMock(return_value=[
        {
            "hash": "abc123",
            "progress": 0.5,
            "dlspeed": 1048576,
            "eta": 3600,
            "state": "downloading"
        }
    ])
    service.close = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_sync_progress_updates_download(mock_db, mock_qbit_service):
    worker = DownloadWorker()
    
    # Mock the database query
    mock_download = MagicMock()
    mock_download.torrent_hash = "abc123"
    mock_download.id = 1
    
    with patch("app.services.download_worker.SessionLocal") as mock_session:
        mock_session.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_download]
        
        with patch("app.services.download_worker.QBittorrentService", return_value=mock_qbit_service):
            await worker._sync_progress()
    
    # Verify the download was updated
    assert mock_download.progress == 0.5
    assert mock_download.speed == "1.0 MB/s"
    assert mock_download.eta == "01:00:00"
    assert mock_download.status.value == "downloading"
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_organize_completed_download_anime():
    """Test that anime downloads call organize_anime instead of organize_series."""
    worker = DownloadWorker()
    
    mock_download = MagicMock()
    mock_download.id = 1
    mock_download.type.value = "anime"
    mock_download.title = "Test Anime"
    mock_download.source_folder = "/downloads/test-anime"
    mock_download.season = 1
    mock_download.episode = 5
    mock_download.quality = "1080p"
    
    with patch("app.services.download_worker.OrganizerService") as mock_organizer_cls:
        mock_organizer = MagicMock()
        mock_organizer_cls.return_value = mock_organizer
        
        await worker._organize_completed_download(mock_download)
        
        mock_organizer.organize_anime.assert_called_once_with(
            source_path="/downloads/test-anime",
            title="Test Anime",
            season=1,
            episode=5,
            quality="1080p"
        )
        mock_organizer.organize_series.assert_not_called()

@pytest.mark.asyncio
async def test_organize_completed_download_series():
    """Test that series downloads call organize_series."""
    worker = DownloadWorker()
    
    mock_download = MagicMock()
    mock_download.id = 2
    mock_download.type.value = "series"
    mock_download.title = "Test Series"
    mock_download.source_folder = "/downloads/test-series"
    mock_download.season = 2
    mock_download.episode = 3
    mock_download.quality = None
    
    with patch("app.services.download_worker.OrganizerService") as mock_organizer_cls:
        mock_organizer = MagicMock()
        mock_organizer_cls.return_value = mock_organizer
        
        await worker._organize_completed_download(mock_download)
        
        mock_organizer.organize_series.assert_called_once_with(
            source_path="/downloads/test-series",
            title="Test Series",
            season=2,
            episode=3,
            quality="1080p"
        )
        mock_organizer.organize_anime.assert_not_called()
