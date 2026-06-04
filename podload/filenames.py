from pathlib import Path
import re


UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')
WHITESPACE = re.compile(r"\s+")


def podcast_directory_name(title: str) -> str:
    return _safe_name(title, fallback="Podcast")


def episode_filename(number: int, title: str, extension: str) -> Path:
    suffix = extension if extension.startswith(".") else f".{extension}"
    return Path(f"{number:03d} - {_safe_name(title, fallback='Episode')}{suffix}")


def _safe_name(value: str, fallback: str) -> str:
    name = UNSAFE_FILENAME_CHARS.sub(" ", value)
    name = WHITESPACE.sub(" ", name).strip().rstrip(".")
    return name or fallback
