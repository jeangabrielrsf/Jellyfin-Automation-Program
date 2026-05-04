"""Tests for Download model."""
from app.models.download import Download, ContentType


def test_download_can_be_created_with_season_and_episode(db_session):
    """Test that Download model accepts season and episode fields."""
    download = Download(
        tmdb_id=12345,
        title="Test Show",
        type=ContentType.SERIES,
        season=2,
        episode=5,
    )
    db_session.add(download)
    db_session.commit()

    assert download.id is not None
    assert download.season == 2
    assert download.episode == 5


def test_download_with_null_season_and_episode(db_session):
    """Test that season and episode can be null."""
    download = Download(
        tmdb_id=12345,
        title="Test Movie",
        type=ContentType.MOVIE,
    )
    db_session.add(download)
    db_session.commit()

    assert download.season is None
    assert download.episode is None
