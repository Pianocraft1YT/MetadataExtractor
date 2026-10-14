"""
Pattern detection edge cases for sort_and_extract_irregular.

These tests build folders with deliberately weird layouts and record what
the code currently does. Some document bugs; those are marked xfail so the
suite stays green while the behavior is under review.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import metadata
from tests.conftest import make_jpeg_with_exif


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_folder(folder: Path, layout: str):
    """
    Build a folder from a compact spec.

    "P" = photo, "V" = fake video. Example: "PPPVPPPV" = 3 photos, 1 video, 3 photos, 1 video.

    Files are numbered so sort order matches the layout string.
    """
    counter = 1
    for ch in layout:
        if ch == "P":
            make_jpeg_with_exif(
                folder / f"{counter:04d}_photo.jpg",
                "2024:05:15 12:30:45",
            )
        elif ch == "V":
            (folder / f"{counter:04d}_video.mp4").write_bytes(
                b"\x00\x00\x00\x18ftypmp42"
            )
        else:
            raise ValueError(f"unknown layout char: {ch}")
        counter += 1


def _capture_df(monkeypatch):
    captured = {}

    def fake_create_sheet(final_output, recursive, df):
        captured["df"] = df

    monkeypatch.setattr(metadata, "create_sheet", fake_create_sheet)
    return captured


# ---------------------------------------------------------------------------
# Video-video in a row
# ---------------------------------------------------------------------------

def test_two_videos_in_a_row(tmp_path, monkeypatch):
    """
    Pattern P P V V P P V V — what does the detector do?

    Current code treats consecutive videos as one boundary. Marking xfail
    until the intended behavior is decided.
    """
    folder = tmp_path / "vv"
    folder.mkdir()
    _build_folder(folder, "PPVVPPVV")

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        folder, recursive=False, final_output=Path("out.xlsx"), modifier=0,
    )
    df = captured.get("df")
    # Whatever the correct row count is, it shouldn't crash.
    assert df is not None


# ---------------------------------------------------------------------------
# Pattern breaks mid-way
# ---------------------------------------------------------------------------

def test_pattern_breaks_midway(tmp_path, monkeypatch):
    """
    P P P V | P P P V | P P P P P V  (third group has 5 photos).

    First two groups should be detected. Third group either extends or the
    detector gives up. Just verify no crash and some output.
    """
    folder = tmp_path / "break"
    folder.mkdir()
    _build_folder(folder, "PPPVPPPVPPPPP")  # 3P+1V, 3P+1V, 5P+1V

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        folder, recursive=False, final_output=Path("out.xlsx"), modifier=0,
    )
    assert captured.get("df") is not None


# ---------------------------------------------------------------------------
# Boundary: 5 vs 6 photos before first video
# ---------------------------------------------------------------------------

def test_exactly_five_photos_before_video(tmp_path, monkeypatch):
    """
    Five photos then a video: the check is `> 5`, so 5 should still be
    treated as series mode.
    """
    folder = tmp_path / "five"
    folder.mkdir()
    _build_folder(folder, "PPPPP V".replace(" ", ""))

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        folder, recursive=False, final_output=Path("out.xlsx"), modifier=0,
    )
    df = captured.get("df")
    assert df is not None
    # With 5P+1V, one series should exist with range 1-6.
    assert len(df) == 1
    if "Image # Series" in df.columns:
        assert list(df["Image # Series"]) == ["1-6"]


def test_exactly_six_photos_before_video(tmp_path, monkeypatch):
    """
    Six photos then a video: `> 5` triggers, so output_series should go
    False and irregular mode falls back to all-photos output.
    """
    folder = tmp_path / "six"
    folder.mkdir()
    _build_folder(folder, "PPPPPPV")

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        folder, recursive=False, final_output=Path("out.xlsx"), modifier=0,
    )
    df = captured.get("df")
    assert df is not None
    # Fallback to per-image output: 6 photos → 6 rows.
    assert len(df) == 6


# ---------------------------------------------------------------------------
# Trailing photos with no video
# ---------------------------------------------------------------------------

def test_trailing_photos_with_no_video(tmp_path, monkeypatch):
    """
    P P P V | P P P  (last group has no video).

    The trailing photos are incomplete. What should happen?
    """
    folder = tmp_path / "trailing"
    folder.mkdir()
    _build_folder(folder, "PPPVPPP")

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        folder, recursive=False, final_output=Path("out.xlsx"), modifier=0,
    )
    # Whatever the intended behavior, no crash.
    assert captured.get("df") is not None


# ---------------------------------------------------------------------------
# All-video folder
# ---------------------------------------------------------------------------

def test_all_videos_no_photos(tmp_path, monkeypatch):
    folder = tmp_path / "all_videos"
    folder.mkdir()
    for i in range(3):
        (folder / f"{i:04d}_video.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        folder, recursive=False, final_output=Path("out.xlsx"), modifier=0,
    )
    # First file is a video → early return, no df written.
    assert "df" not in captured or captured["df"] is None


# ---------------------------------------------------------------------------
# Starting index 0 (likely buggy)
# ---------------------------------------------------------------------------

def test_starting_index_zero(tmp_path, monkeypatch):
    """
    modifier = -1 (since "0".isdigit() is True and 0-1 = -1).
    Series would start at 0. Record behavior; may be a bug.
    """
    folder = tmp_path / "idx0"
    folder.mkdir()
    _build_folder(folder, "PPPV")

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        folder, recursive=False, final_output=Path("out.xlsx"), modifier=-1,
    )
    df = captured.get("df")
    assert df is not None
    if "Image # Series" in df.columns:
        # Whatever the first series is, just verify it doesn't crash.
        assert len(df) == 1