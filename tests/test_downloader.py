import httpx
import respx

from podload.downloader import DownloadOptions, download_podcast
from podload.feed import Episode, Podcast


def make_podcast() -> Podcast:
    return Podcast(
        title="Example Podcast",
        episodes=(
            Episode(
                "First Episode", "https://cdn.example.com/001.mp3", 1, None, ".mp3"
            ),
            Episode(
                "Second Episode", "https://cdn.example.com/002.mp3", 2, None, ".mp3"
            ),
        ),
    )


@respx.mock
def test_download_podcast_writes_audio_files_to_podcast_directory(tmp_path):
    respx.get("https://cdn.example.com/001.mp3").mock(
        return_value=httpx.Response(200, content=b"one")
    )
    respx.get("https://cdn.example.com/002.mp3").mock(
        return_value=httpx.Response(200, content=b"two")
    )

    results = download_podcast(make_podcast(), tmp_path)

    assert (
        tmp_path / "Example Podcast" / "001 - First Episode.mp3"
    ).read_bytes() == b"one"
    assert (
        tmp_path / "Example Podcast" / "002 - Second Episode.mp3"
    ).read_bytes() == b"two"
    assert [result.status for result in results] == ["downloaded", "downloaded"]


@respx.mock
def test_download_podcast_skips_existing_files_by_default(tmp_path):
    podcast_dir = tmp_path / "Example Podcast"
    podcast_dir.mkdir()
    existing = podcast_dir / "001 - First Episode.mp3"
    existing.write_bytes(b"existing")
    respx.get("https://cdn.example.com/002.mp3").mock(
        return_value=httpx.Response(200, content=b"two")
    )

    results = download_podcast(make_podcast(), tmp_path)

    assert existing.read_bytes() == b"existing"
    assert (podcast_dir / "002 - Second Episode.mp3").read_bytes() == b"two"
    assert [result.status for result in results] == ["skipped", "downloaded"]


@respx.mock
def test_download_podcast_overwrites_existing_files_when_requested(tmp_path):
    podcast_dir = tmp_path / "Example Podcast"
    podcast_dir.mkdir()
    existing = podcast_dir / "001 - First Episode.mp3"
    existing.write_bytes(b"existing")
    respx.get("https://cdn.example.com/001.mp3").mock(
        return_value=httpx.Response(200, content=b"new")
    )
    respx.get("https://cdn.example.com/002.mp3").mock(
        return_value=httpx.Response(200, content=b"two")
    )

    download_podcast(make_podcast(), tmp_path, options=DownloadOptions(overwrite=True))

    assert existing.read_bytes() == b"new"


@respx.mock
def test_download_podcast_dry_run_writes_no_audio_files(tmp_path):
    results = download_podcast(
        make_podcast(), tmp_path, options=DownloadOptions(dry_run=True)
    )

    assert not (tmp_path / "Example Podcast").exists()
    assert [result.status for result in results] == ["would-download", "would-download"]


@respx.mock
def test_download_podcast_continues_when_episode_download_fails(tmp_path):
    respx.get("https://cdn.example.com/001.mp3").mock(return_value=httpx.Response(404))
    respx.get("https://cdn.example.com/002.mp3").mock(
        return_value=httpx.Response(200, content=b"two")
    )

    results = download_podcast(make_podcast(), tmp_path)

    podcast_dir = tmp_path / "Example Podcast"
    assert [result.status for result in results] == ["failed", "downloaded"]
    assert results[0].error == "404 Not Found"
    assert not (podcast_dir / "001 - First Episode.mp3").exists()
    assert not (podcast_dir / "001 - First Episode.mp3.part").exists()
    assert (podcast_dir / "002 - Second Episode.mp3").read_bytes() == b"two"
