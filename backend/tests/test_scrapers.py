"""Tests for scrapers."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.scrapers.jackett_scraper import JackettScraper
from app.models.torrent import TorrentResult

@pytest.fixture
def jackett_scraper():
    return JackettScraper()

@pytest.mark.asyncio
async def test_jackett_search(jackett_scraper):
    """Test Jackett search."""
    mock_response = {
        "Results": [
            {
                "Title": "Test Movie 1080p Legendado -GROUP",
                "Tracker": "1337x",
                "Size": 2147483648,
                "Seeders": 100,
                "Peers": 50,
                "Link": "https://example.com/torrent",
                "MagnetUri": "magnet:?xt=urn:btih:test"
            }
        ]
    }
    
    with patch.object(jackett_scraper, 'settings') as mock_settings:
        mock_settings.jackett_api_key = "test_key"
        mock_settings.jackett_url = "http://localhost:9117"
        
        with patch.object(jackett_scraper.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_get.return_value = mock_response_obj
            
            results = await jackett_scraper.search("test movie", media_type="movie")
            
            assert len(results) == 1
            assert results[0].title == "Test Movie 1080p Legendado -GROUP"
            assert results[0].quality == "1080p"
            assert results[0].language == "Legendado"

def test_calculate_score(jackett_scraper):
    """Test score calculation."""
    torrent = TorrentResult(
        title="Test",
        indexer="Test",
        size="1 GB",
        seeds=100,
        peers=50,
        download_url="test",
        quality="1080p",
        language="Legendado"
    )
    
    score = jackett_scraper.calculate_score(torrent, "1080p", "legendado")
    assert score > 0
    assert score == 100.0
