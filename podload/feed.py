from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from mimetypes import guess_extension
from urllib.parse import urlparse

import feedparser


@dataclass(frozen=True)
class Episode:
    title: str
    audio_url: str
    episode_number: int | None
    published: datetime | None
    extension: str


@dataclass(frozen=True)
class Podcast:
    title: str
    episodes: tuple[Episode, ...]


def parse_feed(xml: str) -> Podcast:
    parsed = feedparser.parse(xml)
    title = parsed.feed.get("title", "Podcast")
    episodes = [
        episode for entry in parsed.entries if (episode := _episode_from_entry(entry))
    ]
    return Podcast(title=title, episodes=tuple(sorted(episodes, key=_episode_sort_key)))


def _episode_from_entry(entry) -> Episode | None:
    enclosure = _audio_enclosure(entry)
    if enclosure is None:
        return None

    audio_url = enclosure.get("href") or enclosure.get("url")
    if not audio_url:
        return None

    return Episode(
        title=entry.get("title", "Episode"),
        audio_url=audio_url,
        episode_number=_episode_number(entry),
        published=_published_datetime(entry),
        extension=_extension(audio_url, enclosure.get("type")),
    )


def _audio_enclosure(entry):
    for enclosure in entry.get("enclosures", []):
        media_type = enclosure.get("type", "")
        href = enclosure.get("href") or enclosure.get("url")
        if href and (not media_type or media_type.startswith("audio/")):
            return enclosure
    return None


def _episode_number(entry) -> int | None:
    value = entry.get("itunes_episode")
    if value is None:
        return None
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def _published_datetime(entry) -> datetime | None:
    if entry.get("published_parsed"):
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if entry.get("published"):
        try:
            published = parsedate_to_datetime(entry.published)
        except TypeError, ValueError:
            return None
        if published.tzinfo is None:
            return published.replace(tzinfo=timezone.utc)
        return published
    return None


def _extension(audio_url: str, media_type: str | None) -> str:
    path_suffix = _url_suffix(audio_url)
    if path_suffix:
        return path_suffix

    if media_type:
        guessed = guess_extension(media_type.split(";", 1)[0].strip())
        if guessed == ".mpga":
            return ".mp3"
        if guessed:
            return guessed

    return ".mp3"


def _episode_sort_key(episode: Episode):
    return (
        episode.published or datetime.max.replace(tzinfo=timezone.utc),
        episode.episode_number or 0,
        episode.title,
    )


def _url_suffix(url: str) -> str:
    suffix = urlparse(url).path.rsplit("/", 1)[-1].rsplit(".", 1)
    if len(suffix) != 2 or not suffix[1]:
        return ""
    return f".{suffix[1].lower()}"
