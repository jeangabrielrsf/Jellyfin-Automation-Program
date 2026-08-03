"""Tests for StreamService file resolution."""
import pytest
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
