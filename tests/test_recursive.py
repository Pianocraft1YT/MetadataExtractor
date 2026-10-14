"""
Tests for recursive-mode scanning.

find_directories writes the real xlsx at the end, so we patch create_sheet
to capture calls and count how many sheets it received.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import metadata
from tests.conftest import make_jpeg_with_exif


def _make_photos(folder: Path, names):
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        make_jpeg_with_exif(folder / name, "2024:05:15 12:30:45")


def _capture_recursive_run(monkeypatch):
    """
    Patch create_sheet so find_directories doesn't write, and capture the
    final sheet list from `metadata.results`.
    """
    calls = []

    def fake_create_sheet(final_output, recursive, df):
        calls.append((final_output, recursive, list(metadata.results)))

    monkeypatch.setattr(metadata, "create_sheet", fake_create_sheet)
    return calls


# ---------------------------------------------------------------------------
# Multiple subfolders, all clean
# ---------------------------------------------------------------------------

def test_two_clean_subfolders(tmp_path, monkeypatch):
    parent = tmp_path / "parent"
    _make_photos(parent / "Trip_A", ["IMG_001.jpg", "IMG_002.jpg"])
    _make_photos(parent / "Trip_B", ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"])

    calls = _capture_recursive_run(monkeypatch)
    metadata.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    assert len(calls) == 1
    final_output, recursive, results = calls[0]
    assert recursive is True
    assert len(results) == 2
    assert metadata.total_processed == 5
    assert metadata.total_skipped == 0


# ---------------------------------------------------------------------------
# One subfolder has skips
# ---------------------------------------------------------------------------

def test_subfolder_with_skips(tmp_path, monkeypatch):
    parent = tmp_path / "parent"
    _make_photos(parent / "Clean", ["IMG_001.jpg", "IMG_002.jpg"])
    _make_photos(parent / "Messy", ["IMG_001.jpg"])
    # Add a corrupt file to Messy.
    (parent / "Messy" / "IMG_002.jpg").write_text("not an image")

    calls = _capture_recursive_run(monkeypatch)
    metadata.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    assert metadata.total_processed == 3
    assert metadata.total_skipped == 1


# ---------------------------------------------------------------------------
# Subfolder with no photos is ignored
# ---------------------------------------------------------------------------

def test_subfolder_with_no_photos_ignored(tmp_path, monkeypatch):
    parent = tmp_path / "parent"
    _make_photos(parent / "WithPhotos", ["IMG_001.jpg"])

    empty = parent / "NoPhotos"
    empty.mkdir()
    (empty / "readme.txt").write_text("nothing here")

    calls = _capture_recursive_run(monkeypatch)
    metadata.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    _, _, results = calls[0]
    # Only the folder with photos becomes a sheet.
    assert len(results) == 1


# ---------------------------------------------------------------------------
# Subfolder containing only videos is ignored (no photos → not in list)
# ---------------------------------------------------------------------------

def test_subfolder_with_only_videos_ignored(tmp_path, monkeypatch):
    parent = tmp_path / "parent"
    _make_photos(parent / "WithPhotos", ["IMG_001.jpg"])

    only_video = parent / "OnlyVideo"
    only_video.mkdir()
    (only_video / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")

    calls = _capture_recursive_run(monkeypatch)
    metadata.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    _, _, results = calls[0]
    assert len(results) == 1


# ---------------------------------------------------------------------------
# No valid subfolders at all
# ---------------------------------------------------------------------------

def test_no_valid_subfolders(tmp_path, monkeypatch):
    parent = tmp_path / "empty_parent"
    parent.mkdir()
    (parent / "notes.txt").write_text("nothing")

    calls = _capture_recursive_run(monkeypatch)
    metadata.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    # create_sheet is still called (with empty results) so it can show
    # the "no data" popup. Verify results is empty.
    _, _, results = calls[0]
    assert results == []
    assert metadata.total_processed == 0
    assert metadata.total_skipped == 0