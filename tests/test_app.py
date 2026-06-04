import httpx
import respx

from podload.app import run_download
from podload.downloader import DownloadOptions


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


@respx.mock
def test_run_download_fetches_plans_and_downloads_episodes(tmp_path):
    respx.get("https://example.com/feed.rss").mock(
        return_value=httpx.Response(200, text=RSS_XML)
    )
    respx.get("https://cdn.example.com/001.mp3").mock(
        return_value=httpx.Response(200, content=b"one")
    )
    respx.get("https://cdn.example.com/002.mp3").mock(
        return_value=httpx.Response(200, content=b"two")
    )

    result = run_download("https://example.com/feed.rss", tmp_path, DownloadOptions())

    assert result.podcast.title == "Example Podcast"
    assert [plan.path.name for plan in result.plans] == [
        "001 - First Episode.mp3",
        "002 - Second Episode.mp3",
    ]
    assert [download.status for download in result.results] == [
        "downloaded",
        "downloaded",
    ]
    assert (
        tmp_path / "Example Podcast" / "001 - First Episode.mp3"
    ).read_bytes() == b"one"
    assert (
        tmp_path / "Example Podcast" / "002 - Second Episode.mp3"
    ).read_bytes() == b"two"


@respx.mock
def test_run_download_calls_plan_callback_before_result_callback(tmp_path):
    respx.get("https://example.com/feed.rss").mock(
        return_value=httpx.Response(200, text=RSS_XML)
    )
    respx.get("https://cdn.example.com/001.mp3").mock(
        return_value=httpx.Response(200, content=b"one")
    )
    respx.get("https://cdn.example.com/002.mp3").mock(
        return_value=httpx.Response(200, content=b"two")
    )
    events = []

    def on_plan(podcast, plans, options):
        events.append(("plan", podcast.title, len(plans), options.dry_run))

    def on_result(index, total, result):
        events.append(("result", index, total, result.status))

    run_download(
        "https://example.com/feed.rss",
        tmp_path,
        DownloadOptions(),
        on_plan=on_plan,
        on_result=on_result,
    )

    assert events[0] == ("plan", "Example Podcast", 2, False)
    assert events[1:] == [
        ("result", 1, 2, "downloaded"),
        ("result", 2, 2, "downloaded"),
    ]


@respx.mock
def test_run_download_does_not_create_directory_for_empty_feed(tmp_path):
    respx.get("https://example.com/feed.rss").mock(
        return_value=httpx.Response(
            200,
            text="""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Empty Podcast</title></channel></rss>
""",
        )
    )

    result = run_download("https://example.com/feed.rss", tmp_path, DownloadOptions())

    assert result.podcast.title == "Empty Podcast"
    assert result.plans == []
    assert result.results == []
    assert not (tmp_path / "Empty Podcast").exists()
