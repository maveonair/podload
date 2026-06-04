from __future__ import annotations

import argparse
from pathlib import Path
import sys

import httpx

from podload.app import run_download
from podload.downloader import (
    DownloadOptions,
    DownloadPlan,
    DownloadResult,
    DownloadStatus,
)
from podload.feed import Podcast


DEFAULT_OUTPUT = Path("~/Music/Podcasts")


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except KeyboardInterrupt:
        print("Interrupted.")
        return 130


def _main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    options = DownloadOptions(
        limit=args.limit, overwrite=args.overwrite, dry_run=args.dry_run
    )

    try:
        result = run_download(
            args.rss_url,
            args.output,
            options,
            on_plan=_print_plan,
            on_result=_print_progress,
        )
    except httpx.HTTPError as error:
        print(f"Feed error: {_http_error_message(error)}", file=sys.stderr)
        return 1

    if result.plans:
        _print_complete(result.results, dry_run=options.dry_run)

    return 0


def _print_plan(
    podcast: Podcast, plans: list[DownloadPlan], options: DownloadOptions
) -> None:
    skipped = sum(plan.exists and not options.overwrite for plan in plans)
    pending = len(plans) - skipped

    print(f"Podcast: {podcast.title}")
    if not plans:
        print("No downloadable episodes found.")
        return

    if options.dry_run:
        print(
            f"Episodes: {len(plans)} total, {pending} would download, {skipped} already downloaded"
        )
    else:
        print(
            f"Episodes: {len(plans)} total, {pending} to download, {skipped} already downloaded"
        )


def _print_progress(index: int, total: int, result: DownloadResult) -> None:
    if result.error:
        print(f"[{index}/{total}] {result.status}: {result.path.name} ({result.error})")
        return
    print(f"[{index}/{total}] {result.status}: {result.path.name}")


def _print_complete(results: list[DownloadResult], *, dry_run: bool) -> None:
    skipped = sum(result.status == DownloadStatus.SKIPPED for result in results)
    if dry_run:
        would_download = sum(
            result.status == DownloadStatus.WOULD_DOWNLOAD for result in results
        )
        print(f"Complete: {would_download} would download, {skipped} skipped")
        return

    downloaded = sum(result.status == DownloadStatus.DOWNLOADED for result in results)
    failed = sum(result.status == DownloadStatus.FAILED for result in results)
    print(f"Complete: {downloaded} downloaded, {skipped} skipped, {failed} failed")


def _http_error_message(error: httpx.HTTPError) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        return f"{error.response.status_code} {error.response.reason_phrase}"
    return f"Request failed: {error}"


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "--limit must be a positive integer"
        ) from error
    if number < 1:
        raise argparse.ArgumentTypeError("--limit must be a positive integer")
    return number


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download podcast episodes from an RSS feed."
    )
    parser.add_argument("rss_url", help="Podcast RSS feed URL")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Base directory for podcast downloads (default: ~/Music/Podcasts)",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        help="Maximum number of oldest episodes to download",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Replace existing episode files"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show downloads without writing files"
    )
    return parser
