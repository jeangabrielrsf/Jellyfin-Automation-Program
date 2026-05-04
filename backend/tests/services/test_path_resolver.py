import pytest
from unittest.mock import patch
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


def test_extract_season_episode_8x17_format(resolver):
    result = resolver.extract_season_episode("Show 8x17 1080p WEB-DL")
    assert result == {"season": 8, "episode": 17}


def test_extract_season_episode_season_x_episode_y_format(resolver):
    result = resolver.extract_season_episode("Show Season 8 Episode 17 1080p")
    assert result == {"season": 8, "episode": 17}


def test_resolve_series_path(resolver):
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


def test_resolve_anime_path(resolver):
    with patch("app.services.path_resolver.get_settings") as mock_settings, \
         patch("pathlib.Path.mkdir"):
        mock_settings.return_value.animes_path = "/animes"
        result = resolver.resolve_path(
            title="Attack on Titan",
            media_type="anime",
            torrent_name="Attack on Titan S04E01 1080p",
            season=4,
            episode=1
        )
        assert result == "/animes/Attack on Titan/Season 04"


def test_resolve_invalid_media_type_raises_value_error(resolver):
    with patch("app.services.path_resolver.get_settings") as mock_settings, \
         patch("pathlib.Path.mkdir"):
        mock_settings.return_value.movies_path = "/movies"
        with pytest.raises(ValueError, match="Unknown media type: invalid"):
            resolver.resolve_path(
                title="Some Title",
                media_type="invalid"
            )


def test_resolve_path_with_special_characters_in_title(resolver):
    with patch("app.services.path_resolver.get_settings") as mock_settings, \
         patch("pathlib.Path.mkdir"):
        mock_settings.return_value.movies_path = "/movies"
        result = resolver.resolve_path(
            title="Movie: The Special <Edition> \"Remastered\"",
            media_type="movie",
            year=2023
        )
        assert result == "/movies/Movie_ The Special _Edition_ _Remastered_ (2023)"
