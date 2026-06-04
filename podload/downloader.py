from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import httpx

from podload.feed import Podcast
from podload.filenames import episode_filename, podcast_directory_name


class DownloadStatus(StrEnum):
    DOWNLOADED = "downloaded"
    FAILED = "failed"
    SKIPPED = "skipped"
    WOULD_DOWNLOAD = "would-download"


@dataclass(frozen=True)
class DownloadOptions:
    limit: int | None = None
    overwrite: bool = False
    dry_run: bool = False


@dataclass(frozen=True)
class DownloadResult:
    status: DownloadStatus
    path: Path
    url: str
    error: str | None = None


@dataclass(frozen=True)
class DownloadPlan:
    path: Path
    url: str
    exists: bool


def download_podcast(
    podcast: Podcast,
    output_dir: Path,
    *,
    options: DownloadOptions | None = None,
    plans: list[DownloadPlan] | None = None,
    on_result: Callable[[int, int, DownloadResult], None] | None = None,
) -> list[DownloadResult]:
    options = options or DownloadOptions()
    plans = (
        plans
        if plans is not None
        else plan_downloads(podcast, output_dir, options=options)
    )
    results: list[DownloadResult] = []

    if not options.dry_run:
        podcast_dir = output_dir.expanduser() / podcast_directory_name(podcast.title)
        podcast_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client(follow_redirects=True, timeout=60.0) as client:
        total = len(plans)
        for index, plan in enumerate(plans, start=1):
            if plan.exists and not options.overwrite:
                result = DownloadResult(DownloadStatus.SKIPPED, plan.path, plan.url)
                results.append(result)
                if on_result:
                    on_result(index, total, result)
                continue

            if options.dry_run:
                result = DownloadResult(
                    DownloadStatus.WOULD_DOWNLOAD, plan.path, plan.url
                )
                results.append(result)
                if on_result:
                    on_result(index, total, result)
                continue

            try:
                _download_file(client, plan.url, plan.path)
            except (httpx.HTTPError, OSError) as error:
                result = DownloadResult(
                    DownloadStatus.FAILED, plan.path, plan.url, _error_message(error)
                )
            else:
                result = DownloadResult(DownloadStatus.DOWNLOADED, plan.path, plan.url)
            results.append(result)
            if on_result:
                on_result(index, total, result)

    return results


def plan_downloads(
    podcast: Podcast,
    output_dir: Path,
    *,
    options: DownloadOptions | None = None,
) -> list[DownloadPlan]:
    options = options or DownloadOptions()
    episodes = (
        podcast.episodes[: options.limit]
        if options.limit is not None
        else podcast.episodes
    )
    podcast_dir = output_dir.expanduser() / podcast_directory_name(podcast.title)
    plans: list[DownloadPlan] = []

    for index, episode in enumerate(episodes, start=1):
        number = episode.episode_number or index
        destination = podcast_dir / episode_filename(
            number, episode.title, episode.extension
        )
        plans.append(DownloadPlan(destination, episode.audio_url, destination.exists()))

    return plans


def _download_file(client: httpx.Client, url: str, destination: Path) -> None:
    partial = destination.with_name(f"{destination.name}.part")
    try:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with partial.open("wb") as file:
                for chunk in response.iter_bytes():
                    file.write(chunk)
        partial.replace(destination)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise


def _error_message(error: httpx.HTTPError | OSError) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        return f"{error.response.status_code} {error.response.reason_phrase}"
    if isinstance(error, httpx.HTTPError):
        return f"Request failed: {error}"
    return f"File error: {error}"
