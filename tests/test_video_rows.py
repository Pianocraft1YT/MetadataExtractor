"""Tests for Create Video Rows (output_video_rows=True)."""

import json
import os
from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd

import metadata
from tests.conftest import make_jpeg_with_exif
from tests.helpers import find_scan, sort_scan


def _write_minimal_mp4(path, utc: datetime) -> None:
    mp4_time = int(utc.timestamp()) + 2_082_844_800
    mvhd_payload = b"\x00\x00\x00\x00" + mp4_time.to_bytes(4, "big")
    mvhd = (8 + len(mvhd_payload)).to_bytes(4, "big") + b"mvhd" + mvhd_payload
    moov = (8 + len(mvhd)).to_bytes(4, "big") + b"moov" + mvhd
    ftyp_payload = b"isom\x00\x00\x02\x00isomiso2"
    ftyp = (8 + len(ftyp_payload)).to_bytes(4, "big") + b"ftyp" + ftyp_payload
    path.write_bytes(ftyp + moov)


class _FakeMeta:
    def __init__(self, width=None, height=None):
        self._data = {}
        if width is not None:
            self._data["width"] = width
        if height is not None:
            self._data["height"] = height

    def has(self, key):
        return key in self._data

    def get(self, key):
        if key not in self._data:
            raise ValueError(f"Missing {key}")
        return self._data[key]


class _FakeParser:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_mixed_burst_includes_video_row_and_keeps_columns_aligned(extractor, make_jpeg_with_tags, tmp_path):
    make_jpeg_with_tags(
        "IMG_001.jpg",
        {36867: "2024:05:15 12:30:45", 34855: 400, 271: "Canon"},
    )
    clip = tmp_path / "clip.mp4"
    _write_minimal_mp4(clip, datetime(2024, 5, 15, 12, 30, 46, tzinfo=timezone.utc))
    make_jpeg_with_tags(
        "IMG_002.jpg",
        {36867: "2024:05:15 12:30:47", 34855: 800, 271: "Canon"},
    )
    expected_video_size = extractor._convert_filesize(os.path.getsize(clip))

    with (
        patch("metadata.createParser", return_value=_FakeParser()),
        patch("metadata.extractMetadata", return_value=_FakeMeta(1920, 1080)),
    ):
        processed, skipped = sort_scan(
            extractor,
            tmp_path,
            output_video_rows=True,
            output_dimensions=True,
            output_filesize=True,
            output_make=True,
            output_iso=True,
            write=False,
        )

    assert (processed, skipped) == (3, 0)
    df = extractor.results[0][0]
    assert list(df["Files"]) == ["IMG_001.jpg", "clip.mp4", "IMG_002.jpg"]
    assert list(df["Dates"]) == ["05/15/2024", "05/15/2024", "05/15/2024"]
    assert list(df["Time"]) == ["12:30:45", "12:30:46", "12:30:47"]
    assert list(df["Img # Series"]) == ["1-3", "1-3", "1-3"]
    assert df.loc[1, "File Size"] == expected_video_size
    assert df.loc[1, "Dimensions"] == "1920x1080"
    assert pd.isna(df.loc[1, "Camera Make"])
    assert df.loc[0, "ISO"] == 400
    assert df.loc[1, "ISO"] == ""
    assert df.loc[2, "ISO"] == 800


def test_video_only_group_before_photo_consumes_series_slot(extractor, tmp_path):
    _write_minimal_mp4(tmp_path / "clip1.mp4", datetime(2024, 5, 15, 12, 0, 0, tzinfo=timezone.utc))
    _write_minimal_mp4(tmp_path / "clip2.mp4", datetime(2024, 5, 15, 12, 0, 1, tzinfo=timezone.utc))
    make_jpeg_with_exif(tmp_path / "IMG_001.jpg", "2024:05:15 12:05:00")

    processed, skipped = sort_scan(extractor, tmp_path, output_video_rows=True, write=False)

    assert (processed, skipped) == (3, 0)
    df = extractor.results[0][0]
    assert list(df["Files"]) == ["clip1.mp4", "clip2.mp4", "IMG_001.jpg"]
    assert list(df["Img # Series"]) == ["1-2", "1-2", "3"]


def test_video_only_folder_is_scanned_when_video_rows_enabled(extractor, tmp_path):
    folder = tmp_path / "OnlyVideo"
    folder.mkdir()
    _write_minimal_mp4(folder / "clip.mp4", datetime(2024, 5, 15, 12, 0, 0, tzinfo=timezone.utc))

    extractor.maxdepth = 1
    processed, skipped = find_scan(extractor, tmp_path, output_video_rows=True, write=False)

    assert (processed, skipped) == (1, 0)
    assert "Only Video(s)" not in extractor.collected_warnings
    assert len(extractor.results) == 1
    assert list(extractor.results[0][0]["Files"]) == ["clip.mp4"]


def test_video_dimensions_missing_meta_or_keys_stores_none_without_crash(extractor, tmp_path):
    _write_minimal_mp4(tmp_path / "v1.mp4", datetime(2024, 5, 15, 12, 0, 0, tzinfo=timezone.utc))
    _write_minimal_mp4(tmp_path / "v2.mp4", datetime(2024, 5, 15, 12, 0, 10, tzinfo=timezone.utc))
    _write_minimal_mp4(tmp_path / "v3.mp4", datetime(2024, 5, 15, 12, 0, 20, tzinfo=timezone.utc))

    with (
        patch("metadata.createParser", side_effect=[None, _FakeParser(), _FakeParser()]),
        patch("metadata.extractMetadata", side_effect=[None, _FakeMeta()]),
    ):
        processed, skipped = sort_scan(
            extractor,
            tmp_path,
            output_video_rows=True,
            output_dimensions=True,
            write=False,
        )

    assert (processed, skipped) == (3, 0)
    df = extractor.results[0][0]
    assert list(df["Files"]) == ["v1.mp4", "v2.mp4", "v3.mp4"]
    assert all(pd.isna(v) for v in df["Dimensions"])


def test_utc_mode_does_not_suppress_photo_bad_timestamp_when_video_rows_on(extractor_tz_on, tmp_path):
    make_jpeg_with_exif(tmp_path / "no_offset.jpg", "2024:05:15 12:30:45")
    _write_minimal_mp4(tmp_path / "clip.mp4", datetime(2024, 5, 15, 12, 30, 46, tzinfo=timezone.utc))

    processed, skipped = sort_scan(
        extractor_tz_on,
        tmp_path,
        output_utc=True,
        output_video_rows=True,
        write=False,
    )

    assert (processed, skipped) == (2, 0)
    bad = extractor_tz_on.collected_warnings.get("Bad Timestamp", [])
    assert len(bad) == 1
    assert "no_offset.jpg" in bad[0]


def test_video_rows_setting_round_trip(extractor):
    extractor.video_rows_var.set(True)
    extractor._save_settings()

    saved = json.loads(metadata.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert saved["Video Rows"] is True

    extractor.video_rows_var.set(False)
    extractor._load_settings()

    assert extractor.video_rows_var.get() is True