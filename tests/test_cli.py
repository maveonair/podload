import httpx
import pytest
import respx

from podload.cli import main


RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Example Podcast</title>
    <item>
      <title>Second Episode</title>
      <pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate>
      <itunes:episode>2</itunes:episode>
      <enclosure url="https://cdn.example.com/002.mp3" type="audio/mpeg" />
    </item>
    <item>
      <title>First Episode</title>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
      <itunes:episode>1</itunes:episode>
      <enclosure url="https://cdn.example.com/001.mp3" type="audio/mpeg" />
    </item>
  </channel>
</rss>
"""


def test_cli_help_shows_supported_options(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--help"])

    output = capsys.readouterr().out
    assert error.value.code == 0
    assert "rss_url" in output
    assert "--output" in output
    assert "--limit" in output
    assert "--overwrite" in output
    assert "--dry-run" in output


@respx.mock
def test_cli_downloads_feed_episodes_to_output_directory(tmp_path):
    respx.get("https://example.com/feed.rss").mock(
        return_value=httpx.Response(200, text=RSS_XML)
    )
    respx.get("https://cdn.example.com/001.mp3").mock(
        return_value=httpx.Response(200, content=b"one")
    )
    respx.get("https://cdn.example.com/002.mp3").mock(
        return_value=httpx.Response(200, content=b"two")
    )

    exit_code = main(["https://example.com/feed.rss", "--output", str(tmp_path)])

    assert exit_code == 0
    assert (
        tmp_path / "Example Podcast" / "001 - First Episode.mp3"
    ).read_bytes() == b"one"
    assert (
        tmp_path / "Example Podcast" / "002 - Second Episode.mp3"
    ).read_bytes() == b"two"


@respx.mock
def test_cli_prints_progress_and_skips_existing_files(tmp_path, capsys):
    podcast_dir = tmp_path / "Example Podcast"
    podcast_dir.mkdir()
    existing = podcast_dir / "001 - First Episode.mp3"
    existing.write_bytes(b"existing")
    respx.get("https://example.com/feed.rss").mock(
        return_value=httpx.Response(200, text=RSS_XML)
    )
    respx.get("https://cdn.example.com/002.mp3").mock(
        return_value=httpx.Response(200, content=b"two")
    )

    exit_code = main(["https://example.com/feed.rss", "--output", str(tmp_path)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Podcast: Example Podcast" in output
    assert "Episodes: 2 total, 1 to download, 1 already downloaded" in output
    assert "[1/2] skipped: 001 - First Episode.mp3" in output
    assert "[2/2] downloaded: 002 - Second Episode.mp3" in output
    assert "Complete: 1 downloaded, 1 skipped" in output
    assert existing.read_bytes() == b"existing"
    assert (podcast_dir / "002 - Second Episode.mp3").read_bytes() == b"two"


@respx.mock
def test_cli_dry_run_prints_planned_downloads_without_audio_requests(tmp_path, capsys):
    feed_route = respx.get("https://example.com/feed.rss").mock(
        return_value=httpx.Response(200, text=RSS_XML)
    )

    exit_code = main(
        ["https://example.com/feed.rss", "--output", str(tmp_path), "--dry-run"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert feed_route.called
    assert "Episodes: 2 total, 2 would download, 0 already downloaded" in output
    assert "[1/2] would-download: 001 - First Episode.mp3" in output
    assert "[2/2] would-download: 002 - Second Episode.mp3" in output
    assert "Complete: 2 would download, 0 skipped" in output
    assert "would-download" in output
    assert "001 - First Episode.mp3" in output
    assert not (tmp_path / "Example Podcast").exists()


@respx.mock
def test_cli_limit_downloads_only_oldest_requested_episode(tmp_path):
    respx.get("https://example.com/feed.rss").mock(
        return_value=httpx.Response(200, text=RSS_XML)
    )
    respx.get("https://cdn.example.com/001.mp3").mock(
        return_value=httpx.Response(200, content=b"one")
    )

    exit_code = main(
        ["https://example.com/feed.rss", "--output", str(tmp_path), "--limit", "1"]
    )

    assert exit_code == 0
    assert (tmp_path / "Example Podcast" / "001 - First Episode.mp3").exists()
    assert not (tmp_path / "Example Podcast" / "002 - Second Episode.mp3").exists()


@respx.mock
def test_cli_reports_failed_episode_and_continues_downloading(tmp_path, capsys):
    respx.get("https://example.com/feed.rss").mock(
        return_value=httpx.Response(200, text=RSS_XML)
    )
    respx.get("https://cdn.example.com/001.mp3").mock(return_value=httpx.Response(404))
    respx.get("https://cdn.example.com/002.mp3").mock(
        return_value=httpx.Response(200, content=b"two")
    )

    exit_code = main(["https://example.com/feed.rss", "--output", str(tmp_path)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "[1/2] failed: 001 - First Episode.mp3 (404 Not Found)" in output
    assert "[2/2] downloaded: 002 - Second Episode.mp3" in output
    assert "Complete: 1 downloaded, 0 skipped, 1 failed" in output
    assert not (tmp_path / "Example Podcast" / "001 - First Episode.mp3").exists()
    assert (
        tmp_path / "Example Podcast" / "002 - Second Episode.mp3"
    ).read_bytes() == b"two"


@respx.mock
def test_cli_exits_cleanly_when_interrupted(tmp_path, capsys, monkeypatch):
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("podload.cli.run_download", interrupt)

    exit_code = main(["https://example.com/feed.rss", "--output", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 130
    assert "Interrupted." in captured.out
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err


@respx.mock
def test_cli_reports_feed_http_error_without_traceback(capsys):
    respx.get("https://example.com/feed.rss").mock(return_value=httpx.Response(404))

    exit_code = main(["https://example.com/feed.rss"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Feed error: 404 Not Found" in captured.err
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err


def test_cli_rejects_negative_limit(capsys):
    with pytest.raises(SystemExit) as error:
        main(["https://example.com/feed.rss", "--limit", "-1"])

    captured = capsys.readouterr()
    assert error.value.code == 2
    assert "--limit must be a positive integer" in captured.err


@respx.mock
def test_cli_reports_when_feed_has_no_downloadable_episodes(tmp_path, capsys):
    respx.get("https://example.com/feed.rss").mock(
        return_value=httpx.Response(
            200,
            text="""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Empty Podcast</title></channel></rss>
""",
        )
    )

    exit_code = main(["https://example.com/feed.rss", "--output", str(tmp_path)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Podcast: Empty Podcast" in output
    assert "No downloadable episodes found." in output
    assert not (tmp_path / "Empty Podcast").exists()
