import pytest
from app.services.path_resolver import PathResolver


@pytest.fixture
def resolver():
    return PathResolver()


def test_extract_season_episode_standard_format(resolver):
    result = resolver.extract_season_episode("The Rookie S08E17 1080p x265 ELiTE")
    assert result == {"season": 8, "episode": 17}


def test_extract_season_episode_lowercase_format(resolver):
    result = resolver.extract_season_episode("Show s01e05 WEB-DL")
    assert result == {"season": 1, "episode": 5}


def test_extract_season_episode_no_match(resolver):
    result = resolver.extract_season_episode("Movie.2024.1080p.BluRay")
    assert result == {"season": None, "episode": None}


def test_resolve_series_path(resolver):
    from unittest.mock import patch
    with patch("app.services.path_resolver.get_settings") as mock_settings, \
         patch("pathlib.Path.mkdir"):
        mock_settings.return_value.series_path = "/series"
        result = resolver.resolve_path(
            title="Breaking Bad",
            media_type="series",
            torrent_name="Breaking Bad S05E14 1080p",
            season=5,
            episode=14
        )
        assert result == "/series/Breaking Bad/Season 05"


def test_resolve_movie_path(resolver):
    from unittest.mock import patch
    with patch("app.services.path_resolver.get_settings") as mock_settings, \
         patch("pathlib.Path.mkdir"):
        mock_settings.return_value.movies_path = "/movies"
        result = resolver.resolve_path(
            title="Inception",
            media_type="movie",
            year=2010,
            quality="1080p"
        )
        assert result == "/movies/Inception (2010)"
