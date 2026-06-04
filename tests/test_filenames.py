from pathlib import Path

from podload.filenames import episode_filename, podcast_directory_name


def test_podcast_directory_name_removes_unsafe_path_characters():
    assert (
        podcast_directory_name("Darknet Diaries: Plus / Premium?")
        == "Darknet Diaries Plus Premium"
    )


def test_episode_filename_uses_padded_episode_number_and_safe_title():
    assert episode_filename(7, "The Pirate Bay / Trial?", ".mp3") == Path(
        "007 - The Pirate Bay Trial.mp3"
    )


def test_episode_filename_accepts_extension_without_leading_dot():
    assert episode_filename(1, "Pilot", "m4a") == Path("001 - Pilot.m4a")
