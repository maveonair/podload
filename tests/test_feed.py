from podload.feed import parse_feed


RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Example Podcast</title>
    <item>
      <title>Newest Episode</title>
      <pubDate>Wed, 03 Jan 2024 00:00:00 GMT</pubDate>
      <itunes:episode>3</itunes:episode>
      <enclosure url="https://cdn.example.com/003.mp3" type="audio/mpeg" length="3" />
    </item>
    <item>
      <title>Oldest Episode</title>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
      <itunes:episode>1</itunes:episode>
      <enclosure url="https://cdn.example.com/001.mp3" type="audio/mpeg" length="1" />
    </item>
    <item>
      <title>Middle Episode</title>
      <pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate>
      <itunes:episode>2</itunes:episode>
      <enclosure url="https://cdn.example.com/002.m4a" type="audio/mp4" length="2" />
    </item>
  </channel>
</rss>
"""


def test_parse_feed_extracts_podcast_and_orders_episodes_oldest_first():
    podcast = parse_feed(RSS_XML)

    assert podcast.title == "Example Podcast"
    assert [episode.title for episode in podcast.episodes] == [
        "Oldest Episode",
        "Middle Episode",
        "Newest Episode",
    ]
    assert [episode.episode_number for episode in podcast.episodes] == [1, 2, 3]
    assert [episode.audio_url for episode in podcast.episodes] == [
        "https://cdn.example.com/001.mp3",
        "https://cdn.example.com/002.m4a",
        "https://cdn.example.com/003.mp3",
    ]
    assert [episode.extension for episode in podcast.episodes] == [
        ".mp3",
        ".m4a",
        ".mp3",
    ]


def test_parse_feed_skips_items_without_audio_enclosures():
    podcast = parse_feed(
        """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example Podcast</title>
    <item><title>No Audio</title></item>
    <item><title>Has Audio</title><enclosure url="https://cdn.example.com/audio.mp3" type="audio/mpeg" /></item>
  </channel>
</rss>
"""
    )

    assert [episode.title for episode in podcast.episodes] == ["Has Audio"]
