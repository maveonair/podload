from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from podload.downloader import (
    DownloadOptions,
    DownloadPlan,
    DownloadResult,
    download_podcast,
    plan_downloads,
)
from podload.feed import Podcast, parse_feed


@dataclass(frozen=True)
class RunResult:
    podcast: Podcast
    plans: list[DownloadPlan]
    results: list[DownloadResult]


def fetch_feed(url: str) -> str:
    with httpx.Client(follow_redirects=True, timeout=60.0) as client:
        response = client.get(url)
        response.raise_for_status()
    return response.text


def run_download(
    rss_url: str,
    output_dir: Path,
    options: DownloadOptions,
    *,
    on_plan: Callable[[Podcast, list[DownloadPlan], DownloadOptions], None]
    | None = None,
    on_result: Callable[[int, int, DownloadResult], None] | None = None,
) -> RunResult:
    podcast = parse_feed(fetch_feed(rss_url))
    plans = plan_downloads(podcast, output_dir, options=options)

    if on_plan:
        on_plan(podcast, plans, options)

    if not plans:
        return RunResult(podcast, plans, [])

    results = download_podcast(
        podcast,
        output_dir,
        options=options,
        plans=plans,
        on_result=on_result,
    )
    return RunResult(podcast, plans, results)
