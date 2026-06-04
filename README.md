# podload

Download podcast episodes from an RSS feed.

## Usage

```bash
uv run podload "https://example.com/feed.rss"
```

By default, episodes are downloaded oldest-to-newest into:

```text
~/Music/Podcasts/<PodcastName>/
```

Episode files are named with padded episode numbers when available:

```text
001 - First Episode.mp3
002 - Second Episode.mp3
```

## Options

```bash
uv run podload "https://example.com/feed.rss" --dry-run
uv run podload "https://example.com/feed.rss" --limit 5
uv run podload "https://example.com/feed.rss" --output ~/Music/Podcasts
uv run podload "https://example.com/feed.rss" --overwrite
```

Existing files are skipped by default. Use `--overwrite` to replace them.

## Development

```bash
uv sync
uv run pytest
```
