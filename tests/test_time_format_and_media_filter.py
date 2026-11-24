"""Tests for configurable Time Format and Media Filter (v4.7.0)."""

import json
from unittest.mock import patch
import pytest
import metadata
from tests.conftest import make_jpeg_with_exif
from tests.helpers import sort_scan, find_scan

# ---------------------------------------------------------------------------
# Time Format Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "t_fmt,expected_time",
    [
        ("%H:%M:%S", "14:30:45"),
        ("%I:%M:%S %p", "02:30:45 PM"),
    ],
)
def test_fix_time_respects_time_format(extractor, tmp_path, t_fmt, expected_time):
    dates, times = extractor.fix_time(
        False,
        ["2024:05:15 14:30:45"],
        [None],
        ["a.jpg"],
        tmp_path,
        date_format="%m/%d/%Y",
        time_format=t_fmt,
    )
    assert dates == ["05/15/2024"]
    assert times == [expected_time]


def test_time_format_settings_round_trip(extractor):
    extractor.time_format_var.set("12-Hour (hh:mm:ss AM/PM)")
    extractor._save_settings()

    saved = json.loads(metadata.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert saved["Time Format"] == "12-Hour (hh:mm:ss AM/PM)"

    extractor.time_format_var.set("24-Hour (HH:MM:SS)")
    extractor._load_settings()
    assert extractor.time_format_combobox.get() == "12-Hour (hh:mm:ss AM/PM)"


# ---------------------------------------------------------------------------
# Media Filter Tests (walk_and_filter)
# ---------------------------------------------------------------------------


def test_walk_and_filter_all_media_keeps_photos_and_videos(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "photo.jpg", "2024:05:15 12:00:00")
    (tmp_path / "clip.mp4").write_bytes(b"video")
    (tmp_path / "raw.cr2").write_bytes(b"raw")

    results = list(extractor.walk_and_filter(str(tmp_path), 0, False, media_filter="All Media"))
    files = results[0][2]
    assert sorted(files) == ["clip.mp4", "photo.jpg", "raw.cr2"]


def test_walk_and_filter_photos_only(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "photo.jpg", "2024:05:15 12:00:00")
    (tmp_path / "clip.mp4").write_bytes(b"video")

    results = list(extractor.walk_and_filter(str(tmp_path), 0, False, media_filter="Photos Only"))
    files = results[0][2]
    assert files == ["photo.jpg"]


def test_walk_and_filter_videos_only(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "photo.jpg", "2024:05:15 12:00:00")
    (tmp_path / "clip.mp4").write_bytes(b"video")

    results = list(extractor.walk_and_filter(str(tmp_path), 0, False, media_filter="Videos Only"))
    files = results[0][2]
    assert files == ["clip.mp4"]


def test_walk_and_filter_raw_only(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "photo.jpg", "2024:05:15 12:00:00")
    (tmp_path / "clip.mp4").write_bytes(b"video")
    (tmp_path / "shot.dng").write_bytes(b"raw")

    results = list(extractor.walk_and_filter(str(tmp_path), 0, False, media_filter="RAW Only"))
    files = results[0][2]
    assert files == ["shot.dng"]


def test_initialize_passes_time_format_and_media_filter(extractor, tmp_path):
    (tmp_path / "photo.jpg").write_bytes(b"fake")
    extractor.directory_path = tmp_path
    extractor.output_path = tmp_path
    captured = []
    extractor._start_scan = lambda cfg: captured.append((cfg.time_format, cfg.media_filter))

    extractor.user_mode_var.set("Advanced")
    extractor.time_format_combobox.set("12-Hour (hh:mm:ss AM/PM)")
    extractor.media_filter_combobox.set("RAW Only")

    extractor.initialize()

    assert captured[-1] == ("%I:%M:%S %p", "RAW Only")
