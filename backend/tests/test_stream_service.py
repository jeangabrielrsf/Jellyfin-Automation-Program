"""Tests for StreamService file resolution."""
from unittest.mock import patch

import pytest
from app.exceptions import StreamTranscodeError
from app.models.download import ContentType, Download, DownloadStatus
from app.services.stream_service import StreamService


def make_download(**overrides):
    """Build a Download with sensible defaults (no DB session needed)."""
    defaults = {
        "id": 1,
        "tmdb_id": 100,
        "title": "Test Movie",
        "type": ContentType.MOVIE,
        "status": DownloadStatus.ORGANIZED,
        "source_folder": None,
        "destination_folder": None,
    }
    defaults.update(overrides)
    return Download(**defaults)


@pytest.fixture
def service():
    return StreamService()


def test_movie_folder_skips_samples_and_extras(service, tmp_path):
    """Movie resolution picks the largest video excluding sample/trailer/extra."""
    folder = tmp_path / "movie"
    folder.mkdir()
    (folder / "sample.mkv").write_bytes(b"x" * 9000)
    (folder / "trailer.mp4").write_bytes(b"x" * 7000)
    (folder / "behind the scenes extra.mkv").write_bytes(b"x" * 6000)
    main = folder / "Test Movie (2023) - 1080p.mp4"
    main.write_bytes(b"x" * 5000)

    files = service.resolve_files(make_download(destination_folder=str(folder)))

    assert len(files) == 1
    assert files[0]["path"] == main
    assert files[0]["episode"] is None
    assert files[0]["season"] is None


def test_movie_folder_no_video_raises(service, tmp_path):
    """Movie resolution raises FileNotFoundError when no video files exist."""
    folder = tmp_path / "movie"
    folder.mkdir()
    (folder / "readme.txt").write_text("hi")

    with pytest.raises(FileNotFoundError, match="Nenhum arquivo de vídeo"):
        service.resolve_files(make_download(destination_folder=str(folder)))


def test_missing_folder_raises(service, tmp_path):
    """Resolution raises a clear FileNotFoundError when the folder is gone."""
    missing = tmp_path / "gone"

    with pytest.raises(FileNotFoundError, match="não encontrado"):
        service.resolve_files(make_download(destination_folder=str(missing)))


def test_no_folder_registered_raises(service):
    """Resolution raises when neither source nor destination folder is set."""
    with pytest.raises(FileNotFoundError, match="folder"):
        service.resolve_files(make_download())


def test_destination_folder_takes_priority(service, tmp_path):
    """destination_folder wins over source_folder when both exist."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "Old Movie.mp4").write_bytes(b"x" * 9000)
    dst = tmp_path / "dst"
    dst.mkdir()
    main = dst / "New Movie.mp4"
    main.write_bytes(b"x" * 1000)

    files = service.resolve_files(
        make_download(source_folder=str(src), destination_folder=str(dst))
    )

    assert files[0]["path"] == main


def test_source_folder_fallback_when_destination_missing(service, tmp_path):
    """A stale destination falls back to the source folder."""
    src = tmp_path / "src"
    src.mkdir()
    main = src / "Movie.mp4"
    main.write_bytes(b"x" * 1000)

    files = service.resolve_files(
        make_download(
            source_folder=str(src), destination_folder=str(tmp_path / "gone")
        )
    )

    assert files[0]["path"] == main


def test_series_pack_enumerates_episodes_sorted(service, tmp_path):
    """Season pack returns all SxxExx episodes, sorted, excluding samples."""
    folder = tmp_path / "season"
    folder.mkdir()
    names = {
        "Show - S01E02 - 1080p.mkv": b"e2",
        "Show - S01E10 - 1080p.mkv": b"e10",
        "Show - S01E01 - 720p.mkv": b"e1",
        "Show - S01E01 - sample.mkv": b"sample",
        "Show - Special.mkv": b"special",
    }
    for name, content in names.items():
        (folder / name).write_bytes(content)

    files = service.resolve_files(
        make_download(type=ContentType.SERIES, title="Show", destination_folder=str(folder))
    )

    assert [f["episode"] for f in files] == [1, 2, 10]
    assert [f["season"] for f in files] == [1, 1, 1]
    assert all("sample" not in f["title"] for f in files)
    assert all("Special" not in f["title"] for f in files)


def test_excludes_videos_inside_sample_subfolder(service, tmp_path):
    """Files inside sample/extras subfolders are excluded from movie picks."""
    folder = tmp_path / "movie"
    folder.mkdir()
    extras = folder / "Extras"
    extras.mkdir()
    (extras / "Making Of.mp4").write_bytes(b"x" * 9000)
    main = folder / "Test Movie.mp4"
    main.write_bytes(b"x" * 1000)

    files = service.resolve_files(make_download(destination_folder=str(folder)))

    assert len(files) == 1
    assert files[0]["path"] == main


def test_pack_limited_to_download_season(service, tmp_path):
    """Season packs only enumerate episodes of the download's season."""
    folder = tmp_path / "season"
    folder.mkdir()
    (folder / "Show - S01E02 - 1080p.mkv").write_bytes(b"e2")
    (folder / "Show - S02E01 - 1080p.mkv").write_bytes(b"e1")

    files = service.resolve_files(
        make_download(type=ContentType.SERIES, season=1, destination_folder=str(folder))
    )

    assert [f["episode"] for f in files] == [2]
    assert files[0]["season"] == 1


def test_series_single_episode_matches(service, tmp_path):
    """Single-episode download matches its SxxExx file in a directory."""
    folder = tmp_path / "season"
    folder.mkdir()
    (folder / "Show - S01E02 - 1080p.mkv").write_bytes(b"e2")
    (folder / "Show - S01E03 - 1080p.mkv").write_bytes(b"e3")
    (folder / "Show - S01E04 - 1080p.mkv").write_bytes(b"e4")

    files = service.resolve_files(
        make_download(
            type=ContentType.SERIES, season=1, episode=3, destination_folder=str(folder)
        )
    )

    assert len(files) == 1
    assert files[0]["episode"] == 3
    assert files[0]["title"] == "Show - S01E03 - 1080p"


def test_series_single_episode_no_match_raises(service, tmp_path):
    """Single-episode download with no matching file raises FileNotFoundError."""
    folder = tmp_path / "season"
    folder.mkdir()
    (folder / "Show - S01E02 - 1080p.mkv").write_bytes(b"e2")

    with pytest.raises(FileNotFoundError, match="S01E07"):
        service.resolve_files(
            make_download(
                type=ContentType.SERIES, season=1, episode=7, destination_folder=str(folder)
            )
        )


def test_series_single_episode_falls_back_to_lone_file(service, tmp_path):
    """Single-episode download falls back to the only video file when no SxxExx match."""
    folder = tmp_path / "season"
    folder.mkdir()
    video = folder / "[Group] Show - 05 [1080p].mkv"
    video.write_bytes(b"content")

    files = service.resolve_files(
        make_download(
            type=ContentType.SERIES, season=1, episode=5, destination_folder=str(folder)
        )
    )

    assert len(files) == 1
    assert files[0]["path"] == video


def test_series_single_file_folder(service, tmp_path):
    """Organized episode where destination_folder is a file works."""
    video = tmp_path / "Show - S01E05 - 1080p.mkv"
    video.write_bytes(b"content")

    files = service.resolve_files(
        make_download(
            type=ContentType.SERIES,
            season=1,
            episode=5,
            destination_folder=str(video),
        )
    )

    assert len(files) == 1
    assert files[0]["path"] == video
    assert files[0]["episode"] == 5


def test_anime_single_file_parses_episode(service, tmp_path):
    """Anime organized files follow the same SxxExx matching."""
    video = tmp_path / "Anime - S01E03 - 1080p.mkv"
    video.write_bytes(b"x")

    files = service.resolve_files(
        make_download(
            type=ContentType.ANIME, season=1, episode=3, destination_folder=str(video)
        )
    )

    assert files[0]["episode"] == 3


def test_resolve_file_movie(service, tmp_path):
    """resolve_file returns the picked movie file."""
    folder = tmp_path / "movie"
    folder.mkdir()
    (folder / "sample.mkv").write_bytes(b"x" * 9000)
    main = folder / "Test Movie.mp4"
    main.write_bytes(b"x" * 1000)

    assert service.resolve_file(make_download(destination_folder=str(folder))) == main


def test_resolve_file_single_file(service, tmp_path):
    """resolve_file returns the single-file folder as-is."""
    video = tmp_path / "Show - S01E05 - 1080p.mkv"
    video.write_bytes(b"x")

    assert service.resolve_file(
        make_download(
            type=ContentType.SERIES,
            season=1,
            episode=5,
            destination_folder=str(video),
        )
    ) == video


def test_resolve_file_episode_param(service, tmp_path):
    """resolve_file with an episode param selects that episode."""
    folder = tmp_path / "season"
    folder.mkdir()
    (folder / "Show - S01E01 - 1080p.mkv").write_bytes(b"e1")
    e2 = folder / "Show - S01E02 - 1080p.mkv"
    e2.write_bytes(b"e2")

    download = make_download(type=ContentType.SERIES, season=1, destination_folder=str(folder))

    assert service.resolve_file(download, episode=2) == e2


def test_resolve_file_uses_download_episode(service, tmp_path):
    """resolve_file without a param uses download.episode when set."""
    folder = tmp_path / "season"
    folder.mkdir()
    (folder / "Show - S01E01 - 1080p.mkv").write_bytes(b"e1")
    e2 = folder / "Show - S01E02 - 1080p.mkv"
    e2.write_bytes(b"e2")

    download = make_download(
        type=ContentType.SERIES, season=1, episode=2, destination_folder=str(folder)
    )

    assert service.resolve_file(download) == e2


def test_resolve_file_pack_defaults_to_first_episode(service, tmp_path):
    """resolve_file without episode on a pack serves the first sorted episode."""
    folder = tmp_path / "season"
    folder.mkdir()
    (folder / "Show - S01E02 - 1080p.mkv").write_bytes(b"e2")
    e1 = folder / "Show - S01E01 - 1080p.mkv"
    e1.write_bytes(b"e1")

    download = make_download(type=ContentType.SERIES, season=1, destination_folder=str(folder))

    assert service.resolve_file(download) == e1


def test_resolve_file_missing_episode_raises(service, tmp_path):
    """resolve_file raises a clear error for a nonexistent episode."""
    folder = tmp_path / "season"
    folder.mkdir()
    (folder / "Show - S01E02 - 1080p.mkv").write_bytes(b"e2")

    download = make_download(
        type=ContentType.SERIES, season=1, episode=9, destination_folder=str(folder)
    )

    with pytest.raises(FileNotFoundError, match="S01E09"):
        service.resolve_file(download)


class TestResolveSubtitle:
    def test_exact_basename_match(self, service, tmp_path):
        """The .srt sharing the video's basename wins."""
        folder = tmp_path / "movie"
        folder.mkdir()
        video = folder / "Test Movie (2023) - 1080p.mp4"
        video.write_bytes(b"v")
        srt = folder / "Test Movie (2023) - 1080p.srt"
        srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nOi\n")

        result = service.resolve_subtitle(
            make_download(destination_folder=str(folder))
        )

        assert result == srt

    def test_basename_match_is_case_insensitive(self, service, tmp_path):
        """A .SRT extension or case difference still matches."""
        folder = tmp_path / "movie"
        folder.mkdir()
        video = folder / "Test Movie.mp4"
        video.write_bytes(b"v")
        srt = folder / "Test Movie.SRT"
        srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nOi\n")

        result = service.resolve_subtitle(
            make_download(destination_folder=str(folder))
        )

        assert result == srt

    def test_unique_srt_fallback(self, service, tmp_path):
        """A single .srt is used when the folder has a single playable video."""
        folder = tmp_path / "movie"
        folder.mkdir()
        (folder / "sample.mkv").write_bytes(b"sample")
        (folder / "Test Movie.mkv").write_bytes(b"v")
        srt = folder / "subs.srt"
        srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nOi\n")

        result = service.resolve_subtitle(
            make_download(destination_folder=str(folder))
        )

        assert result == srt

    def test_unique_srt_fallback_skipped_for_packs(self, service, tmp_path):
        """A pack never attaches one episode's .srt to another episode."""
        folder = tmp_path / "season"
        folder.mkdir()
        (folder / "Show - S01E01 - 1080p.mkv").write_bytes(b"e1")
        (folder / "Show - S01E02 - 1080p.mkv").write_bytes(b"e2")
        (folder / "Show - S01E02 - 1080p.srt").write_text("srt2")

        download = make_download(
            type=ContentType.SERIES, season=1, destination_folder=str(folder)
        )

        assert service.resolve_subtitle(download, episode=1) is None

    def test_ambiguous_multiple_srts_return_none(self, service, tmp_path):
        """Multiple non-matching .srt files are ambiguous: no subtitle."""
        folder = tmp_path / "movie"
        folder.mkdir()
        (folder / "Test Movie.mkv").write_bytes(b"v")
        (folder / "legendas-en.srt").write_text("en")
        (folder / "legendas-pt.srt").write_text("pt")

        result = service.resolve_subtitle(
            make_download(destination_folder=str(folder))
        )

        assert result is None

    def test_no_srt_returns_none(self, service, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()
        (folder / "Test Movie.mkv").write_bytes(b"v")

        result = service.resolve_subtitle(
            make_download(destination_folder=str(folder))
        )

        assert result is None

    def test_episode_selects_its_own_srt(self, service, tmp_path):
        """A pack resolves the .srt of the requested episode."""
        folder = tmp_path / "season"
        folder.mkdir()
        (folder / "Show - S01E01 - 1080p.mkv").write_bytes(b"e1")
        (folder / "Show - S01E02 - 1080p.mkv").write_bytes(b"e2")
        (folder / "Show - S01E01 - 1080p.srt").write_text("srt1")
        srt2 = folder / "Show - S01E02 - 1080p.srt"
        srt2.write_text("srt2")

        download = make_download(
            type=ContentType.SERIES, season=1, destination_folder=str(folder)
        )

        assert service.resolve_subtitle(download, episode=2) == srt2

    def test_pack_without_episode_resolves_first_episode(self, service, tmp_path):
        """No episode param on a pack resolves the first sorted episode's srt."""
        folder = tmp_path / "season"
        folder.mkdir()
        (folder / "Show - S01E02 - 1080p.mkv").write_bytes(b"e2")
        (folder / "Show - S01E01 - 1080p.mkv").write_bytes(b"e1")
        srt1 = folder / "Show - S01E01 - 1080p.srt"
        srt1.write_text("srt1")
        (folder / "Show - S01E02 - 1080p.srt").write_text("srt2")

        download = make_download(
            type=ContentType.SERIES, season=1, destination_folder=str(folder)
        )

        assert service.resolve_subtitle(download) == srt1

    def test_missing_video_propagates_file_not_found(self, service, tmp_path):
        folder = tmp_path / "movie"
        folder.mkdir()

        with pytest.raises(FileNotFoundError, match="Nenhum arquivo de vídeo"):
            service.resolve_subtitle(make_download(destination_folder=str(folder)))


class TestToWebVtt:
    def test_converts_srt_via_ffmpeg(self, service, tmp_path):
        """Runs ffmpeg -f webvtt and returns its stdout."""
        srt = tmp_path / "movie.srt"
        srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nOi\n")

        with patch("app.services.stream_service.subprocess.run") as run:
            run.return_value.stdout = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nOi\n"
            run.return_value.returncode = 0
            result = service.to_webvtt(srt)

        cmd = run.call_args.args[0]
        assert "ffmpeg" in cmd
        assert cmd[cmd.index("-f") + 1] == "webvtt"
        assert str(srt) in cmd
        assert result == "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nOi\n"

    def test_ffmpeg_failure_raises(self, service, tmp_path):
        srt = tmp_path / "movie.srt"
        srt.write_text("broken")

        with patch("app.services.stream_service.subprocess.run") as run:
            run.return_value.returncode = 1
            run.return_value.stdout = ""

            with pytest.raises(StreamTranscodeError, match="legenda"):
                service.to_webvtt(srt)

    def test_missing_binary_raises(self, service, tmp_path):
        srt = tmp_path / "movie.srt"
        srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nOi\n")

        with patch(
            "app.services.stream_service.subprocess.run",
            side_effect=FileNotFoundError("ffmpeg"),
        ):
            with pytest.raises(StreamTranscodeError, match="legenda"):
                service.to_webvtt(srt)
