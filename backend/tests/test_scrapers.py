"""Tests for scrapers."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.scrapers.jackett_scraper import JackettScraper
from app.clients.jackett_client import JackettClient
from app.models.torrent import TorrentResult
from app.models.settings import Setting


@pytest.fixture
def mock_jackett_client():
    """Create a mock JackettClient."""
    client = AsyncMock(spec=JackettClient)
    client.search = AsyncMock(return_value=[])
    return client


@pytest.fixture
def jackett_scraper(mock_jackett_client):
    """Create JackettScraper with injected mock JackettClient."""
    return JackettScraper(jackett_client=mock_jackett_client)


@pytest.fixture
def jackett_scraper_with_db(db_session):
    """Create JackettScraper with db (uses default JackettClient)."""
    db_session.add(Setting(key="jackett_api_key", value="test_key"))
    db_session.add(Setting(key="jackett_url", value="http://localhost:9117"))
    db_session.commit()
    mock_client = AsyncMock(spec=JackettClient)
    mock_client.search = AsyncMock(return_value=[])
    return JackettScraper(db=db_session, jackett_client=mock_client)


@pytest.mark.asyncio
async def test_jackett_search(jackett_scraper, mock_jackett_client):
    """Test Jackett search delegates to JackettClient and parses results."""
    mock_jackett_client.search.return_value = [
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

    results = await jackett_scraper.search("test movie", media_type="movie")

    assert len(results) == 1
    assert results[0].title == "Test Movie 1080p Legendado -GROUP"
    assert results[0].quality == "1080p"
    assert results[0].language == "Legendado"
    mock_jackett_client.search.assert_called_once_with("test movie", category=[2000])


@pytest.mark.asyncio
async def test_jackett_search_passes_correct_category(jackett_scraper, mock_jackett_client):
    """Test that search passes correct category for each media type."""
    mock_jackett_client.search.return_value = []

    await jackett_scraper.search("test", media_type="movie")
    mock_jackett_client.search.assert_called_with("test", category=[2000])

    await jackett_scraper.search("test", media_type="series")
    mock_jackett_client.search.assert_called_with("test", category=[5000])

    await jackett_scraper.search("test", media_type="anime")
    mock_jackett_client.search.assert_called_with("test", category=[5070])


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


@pytest.mark.asyncio
async def test_jackett_search_new_fields(jackett_scraper, mock_jackett_client):
    """Test that new Jackett fields are captured correctly."""
    mock_jackett_client.search.return_value = [
        {
            "Title": "Test Anime 1080p Dual -GROUP",
            "Tracker": "Nyaa",
            "Size": 1073741824,
            "Seeders": 50,
            "Peers": 10,
            "Link": "https://example.com/torrent",
            "MagnetUri": "magnet:?xt=urn:btih:test",
            "PublishDate": "2025-01-15T10:30:00Z",
            "Grabs": 500,
            "DownloadVolumeFactor": 0.0,
            "Files": 12
        }
    ]

    results = await jackett_scraper.search("test anime", media_type="anime")

    assert len(results) == 1
    assert results[0].grabs == 500
    assert results[0].download_volume_factor == 0.0
    assert results[0].files == 12
    assert results[0].publish_date is not None
    assert results[0].publish_date.year == 2025


def test_parse_date(jackett_scraper):
    """Test date parsing from Jackett ISO format."""
    assert jackett_scraper._parse_date("2025-01-15T10:30:00Z") is not None
    assert jackett_scraper._parse_date("2025-01-15T10:30:00+00:00") is not None
    assert jackett_scraper._parse_date(None) is None
    assert jackett_scraper._parse_date("invalid") is None


@pytest.mark.asyncio
async def test_jackett_search_empty_results(jackett_scraper, mock_jackett_client):
    """Test search returns empty list when JackettClient returns no results."""
    mock_jackett_client.search.return_value = []

    results = await jackett_scraper.search("nonexistent", media_type="movie")

    assert results == []


@pytest.mark.asyncio
async def test_jackett_search_handles_client_exception(jackett_scraper, mock_jackett_client):
    """Test search handles exceptions from JackettClient gracefully."""
    mock_jackett_client.search.side_effect = Exception("Client error")

    results = await jackett_scraper.search("test", media_type="movie")

    assert results == []


@pytest.mark.asyncio
async def test_jackett_search_sorts_by_score(jackett_scraper, mock_jackett_client):
    """Test that results are sorted by score descending."""
    mock_jackett_client.search.return_value = [
        {
            "Title": "Low Score 720p",
            "Tracker": "Test",
            "Size": 1073741824,
            "Seeders": 5,
            "Peers": 2,
            "Link": "https://example.com/1",
            "MagnetUri": None,
        },
        {
            "Title": "High Score 1080p Legendado",
            "Tracker": "Test",
            "Size": 2147483648,
            "Seeders": 100,
            "Peers": 50,
            "Link": "https://example.com/2",
            "MagnetUri": None,
        },
    ]

    results = await jackett_scraper.search("test", media_type="movie", quality="1080p", language="legendado")

    assert len(results) == 2
    assert results[0].title == "High Score 1080p Legendado"
    assert results[0].score > results[1].score


@pytest.mark.asyncio
async def test_jackett_scraper_uses_injected_client():
    """Test that JackettScraper uses the injected JackettClient, not a default one."""
    mock_client = AsyncMock(spec=JackettClient)
    mock_client.search = AsyncMock(return_value=[])

    scraper = JackettScraper(jackett_client=mock_client)
    await scraper.search("test", media_type="movie")

    mock_client.search.assert_called_once()


def test_jackett_scraper_default_client_creation():
    """Test that JackettScraper creates a default JackettClient if none provided."""
    with patch('app.scrapers.jackett_scraper.JackettClient') as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance

        scraper = JackettScraper()

        MockClient.assert_called_once_with(db=None)
        assert scraper.jackett_client == mock_instance


def test_jackett_scraper_default_client_with_db(db_session):
    """Test that default JackettClient receives db parameter."""
    db_session.add(Setting(key="jackett_api_key", value="test_key"))
    db_session.add(Setting(key="jackett_url", value="http://localhost:9117"))
    db_session.commit()

    with patch('app.scrapers.jackett_scraper.JackettClient') as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance

        scraper = JackettScraper(db=db_session)

        MockClient.assert_called_once_with(db=db_session)
        assert scraper.jackett_client == mock_instance
