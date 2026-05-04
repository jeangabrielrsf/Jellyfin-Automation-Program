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
