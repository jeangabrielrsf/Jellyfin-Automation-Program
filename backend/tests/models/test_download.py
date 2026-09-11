"""Tests for Download model."""
import pytest
from datetime import datetime, timezone
from app.models.download import Download, ContentType, DownloadStatus


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


class TestValidTransitions:
    def test_valid_transitions_exists_as_class_constant(self):
        assert hasattr(Download, "VALID_TRANSITIONS")
        assert isinstance(Download.VALID_TRANSITIONS, dict)

    def test_pending_can_transition_to_downloading(self):
        assert DownloadStatus.DOWNLOADING in Download.VALID_TRANSITIONS[DownloadStatus.PENDING]

    def test_pending_can_transition_to_failed(self):
        assert DownloadStatus.FAILED in Download.VALID_TRANSITIONS[DownloadStatus.PENDING]

    def test_pending_can_transition_to_cancelled(self):
        assert DownloadStatus.CANCELLED in Download.VALID_TRANSITIONS[DownloadStatus.PENDING]

    def test_downloading_can_transition_to_completed(self):
        assert DownloadStatus.COMPLETED in Download.VALID_TRANSITIONS[DownloadStatus.DOWNLOADING]

    def test_downloading_can_transition_to_failed(self):
        assert DownloadStatus.FAILED in Download.VALID_TRANSITIONS[DownloadStatus.DOWNLOADING]

    def test_downloading_can_transition_to_cancelled(self):
        assert DownloadStatus.CANCELLED in Download.VALID_TRANSITIONS[DownloadStatus.DOWNLOADING]

    def test_completed_can_transition_to_organized(self):
        assert DownloadStatus.ORGANIZED in Download.VALID_TRANSITIONS[DownloadStatus.COMPLETED]

    def test_completed_can_transition_to_failed(self):
        assert DownloadStatus.FAILED in Download.VALID_TRANSITIONS[DownloadStatus.COMPLETED]


class TestTransitionTo:
    def test_transition_to_valid_status_updates_status(self, db_session):
        download = Download(
            tmdb_id=12345,
            title="Test Movie",
            type=ContentType.MOVIE,
            status=DownloadStatus.PENDING,
        )
        db_session.add(download)
        db_session.commit()

        download.transition_to(DownloadStatus.DOWNLOADING)
        assert download.status == DownloadStatus.DOWNLOADING

    def test_transition_to_invalid_status_raises_value_error(self, db_session):
        download = Download(
            tmdb_id=12345,
            title="Test Movie",
            type=ContentType.MOVIE,
            status=DownloadStatus.PENDING,
        )
        db_session.add(download)
        db_session.commit()

        with pytest.raises(ValueError, match="Cannot transition"):
            download.transition_to(DownloadStatus.COMPLETED)

    def test_transition_to_same_status_is_allowed(self, db_session):
        download = Download(
            tmdb_id=12345,
            title="Test Movie",
            type=ContentType.MOVIE,
            status=DownloadStatus.PENDING,
        )
        db_session.add(download)
        db_session.commit()

        download.transition_to(DownloadStatus.PENDING)
        assert download.status == DownloadStatus.PENDING

    def test_transition_from_cancelled_raises_value_error(self, db_session):
        download = Download(
            tmdb_id=12345,
            title="Test Movie",
            type=ContentType.MOVIE,
            status=DownloadStatus.CANCELLED,
        )
        db_session.add(download)
        db_session.commit()

        with pytest.raises(ValueError, match="Cannot transition"):
            download.transition_to(DownloadStatus.PENDING)

    def test_transition_from_organized_raises_value_error(self, db_session):
        download = Download(
            tmdb_id=12345,
            title="Test Movie",
            type=ContentType.MOVIE,
            status=DownloadStatus.ORGANIZED,
        )
        db_session.add(download)
        db_session.commit()

        with pytest.raises(ValueError, match="Cannot transition"):
            download.transition_to(DownloadStatus.PENDING)


class TestExtractHash:
    def test_extract_hash_from_valid_magnet_link(self):
        magnet = "magnet:?xt=urn:btih:AABBCCDD11223344556677889900AABBCCDDEEFF&dn=test"
        result = Download.extract_hash(magnet)
        assert result == "aabbccdd11223344556677889900aabbccddeeff"

    def test_extract_hash_returns_lowercase(self):
        magnet = "magnet:?xt=urn:btih:AABBCCDD11223344556677889900AABBCCDDEEFF"
        result = Download.extract_hash(magnet)
        assert result == result.lower()

    def test_extract_hash_from_magnet_without_btih_returns_none(self):
        magnet = "magnet:?xt=urn:sha1:ABCDEF1234567890"
        result = Download.extract_hash(magnet)
        assert result is None

    def test_extract_hash_from_invalid_string_returns_none(self):
        result = Download.extract_hash("not a magnet link")
        assert result is None

    def test_extract_hash_from_empty_string_returns_none(self):
        result = Download.extract_hash("")
        assert result is None

    def test_extract_hash_from_none_returns_none(self):
        result = Download.extract_hash(None)
        assert result is None

    def test_extract_hash_is_static_method(self):
        assert isinstance(Download.__dict__["extract_hash"], staticmethod)

    def test_extract_hash_with_short_hash_returns_none(self):
        magnet = "magnet:?xt=urn:btih:AABBCCDD11223344"
        result = Download.extract_hash(magnet)
        assert result is None

    def test_extract_hash_with_long_hash_returns_none(self):
        magnet = "magnet:?xt=urn:btih:AABBCCDD11223344556677889900AABBCCDDEEFF0011"
        result = Download.extract_hash(magnet)
        assert result is None


class TestToDict:
    def test_to_dict_returns_all_fields(self, db_session):
        now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        download = Download(
            id=1,
            tmdb_id=12345,
            title="Test Movie",
            type=ContentType.MOVIE,
            season=None,
            episode=None,
            torrent_name="Test.Movie.2024.1080p.BluRay",
            torrent_hash="aabbccdd11223344556677889900aabbccddeeff",
            magnet_link="magnet:?xt=urn:btih:AABBCCDD11223344556677889900AABBCCDDEEFF",
            quality="1080p",
            language_preference="legendado",
            status=DownloadStatus.DOWNLOADING,
            progress=0.5,
            speed="5.0 MB/s",
            eta="00:05:00",
            source_folder="/downloads",
            destination_folder="/movies",
            indexer_used="1337x",
            size="2.5 GB",
            seeds=100,
            peers=50,
            error_message=None,
            created_at=now,
            updated_at=now,
            completed_at=None,
        )
        db_session.add(download)
        db_session.commit()

        result = download.to_dict()

        assert result["id"] == 1
        assert result["tmdb_id"] == 12345
        assert result["title"] == "Test Movie"
        assert result["type"] == "movie"
        assert result["season"] is None
        assert result["episode"] is None
        assert result["torrent_name"] == "Test.Movie.2024.1080p.BluRay"
        assert result["torrent_hash"] == "aabbccdd11223344556677889900aabbccddeeff"
        assert result["magnet_link"] == "magnet:?xt=urn:btih:AABBCCDD11223344556677889900AABBCCDDEEFF"
        assert result["quality"] == "1080p"
        assert result["language_preference"] == "legendado"
        assert result["status"] == "downloading"
        assert result["progress"] == 0.5
        assert result["speed"] == "5.0 MB/s"
        assert result["eta"] == "00:05:00"
        assert result["source_folder"] == "/downloads"
        assert result["destination_folder"] == "/movies"
        assert result["indexer_used"] == "1337x"
        assert result["size"] == "2.5 GB"
        assert result["seeds"] == 100
        assert result["peers"] == 50
        assert result["error_message"] is None
        assert "2024-01-15T12:00:00" in result["created_at"]
        assert "2024-01-15T12:00:00" in result["updated_at"]
        assert result["completed_at"] is None

    def test_to_dict_with_series_content_type(self, db_session):
        download = Download(
            tmdb_id=12345,
            title="Test Show",
            type=ContentType.SERIES,
            season=2,
            episode=5,
            status=DownloadStatus.PENDING,
        )
        db_session.add(download)
        db_session.commit()

        result = download.to_dict()

        assert result["type"] == "series"
        assert result["season"] == 2
        assert result["episode"] == 5

    def test_to_dict_with_anime_content_type(self, db_session):
        download = Download(
            tmdb_id=12345,
            title="Test Anime",
            type=ContentType.ANIME,
            status=DownloadStatus.COMPLETED,
        )
        db_session.add(download)
        db_session.commit()

        result = download.to_dict()

        assert result["type"] == "anime"
        assert result["status"] == "completed"

    def test_to_dict_with_null_enum_values(self, db_session):
        download = Download(
            tmdb_id=12345,
            title="Test Movie",
            type=ContentType.MOVIE,
        )
        db_session.add(download)
        db_session.commit()

        result = download.to_dict()

        assert result["status"] == "pending"
        assert result["type"] == "movie"
