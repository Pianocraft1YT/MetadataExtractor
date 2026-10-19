"""
Pattern detection edge cases for sort_and_extract_irregular.

These tests build folders with deliberately weird layouts and record what
the code currently does.
"""

from pathlib import Path

import pytest

import metadata
from tests.conftest import make_jpeg_with_exif


def _build_folder(folder: Path, layout: str):
    """Build a folder from a compact spec: P=photo, V=fake video."""
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

    def fake_create_sheet(final_output, recursive, df, processed, skipped):
        captured["df"] = df

    monkeypatch.setattr(metadata, "create_sheet", fake_create_sheet)
    return captured


def test_two_videos_in_a_row(tmp_path, monkeypatch):
    folder = tmp_path / "vv"
    folder.mkdir()
    _build_folder(folder, "PPVVPPVV")

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        folder, recursive=False, final_output=Path("out.xlsx"), modifier=0,
    )
    df = captured.get("df")
    assert df is not None


def test_pattern_breaks_midway(tmp_path, monkeypatch):
    folder = tmp_path / "break"
    folder.mkdir()
    _build_folder(folder, "PPPVPPPVPPPPP")

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        folder, recursive=False, final_output=Path("out.xlsx"), modifier=0,
    )
    assert captured.get("df") is not None


def test_exactly_five_photos_before_video(tmp_path, monkeypatch):
    folder = tmp_path / "five"
    folder.mkdir()
    _build_folder(folder, "PPPPPV")

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        folder, recursive=False, final_output=Path("out.xlsx"), modifier=0,
    )
    df = captured.get("df")
    assert df is not None
    assert len(df) == 1
    if "Image # Series" in df.columns:
        assert list(df["Image # Series"]) == ["1-6"]


def test_exactly_six_photos_before_video(tmp_path, monkeypatch):
    folder = tmp_path / "six"
    folder.mkdir()
    _build_folder(folder, "PPPPPPV")

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        folder, recursive=False, final_output=Path("out.xlsx"), modifier=0,
    )
    df = captured.get("df")
    assert df is not None
    assert len(df) == 6


def test_trailing_photos_with_no_video(tmp_path, monkeypatch):
    folder = tmp_path / "trailing"
    folder.mkdir()
    _build_folder(folder, "PPPVPPP")

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        folder, recursive=False, final_output=Path("out.xlsx"), modifier=0,
    )
    assert captured.get("df") is not None


def test_all_videos_no_photos(tmp_path, monkeypatch):
    folder = tmp_path / "all_videos"
    folder.mkdir()
    for i in range(3):
        (folder / f"{i:04d}_video.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        folder, recursive=False, final_output=Path("out.xlsx"), modifier=0,
    )
    # First file is a video → early return with warning.
    assert "Video First" in metadata.collected_warnings


def test_starting_index_zero(tmp_path, monkeypatch):
    folder = tmp_path / "idx0"
    folder.mkdir()
    _build_folder(folder, "PPPV")

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        folder, recursive=False, final_output=Path("out.xlsx"), modifier=-1,
    )
    df = captured.get("df")
    assert df is not None
    assert len(df) == 1