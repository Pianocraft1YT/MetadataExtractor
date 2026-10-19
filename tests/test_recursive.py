"""
Tests for recursive-mode scanning.

find_directories writes the real xlsx at the end, so we patch create_sheet
to capture calls and read the accumulated counts.
"""

from pathlib import Path

import metadata
from tests.conftest import make_jpeg_with_exif


def _make_photos(folder: Path, names):
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        make_jpeg_with_exif(folder / name, "2024:05:15 12:30:45")


def _capture_recursive_run(monkeypatch):
    """
    Patch create_sheet so find_directories doesn't write, and capture
    the sheet list and accumulated counts from `results` and the args.
    """
    calls = []

    def fake_create_sheet(final_output, recursive, df, total_processed, total_skipped):
        calls.append({
            "final_output": final_output,
            "recursive": recursive,
            "results": list(metadata.results),
            "total_processed": total_processed,
            "total_skipped": total_skipped,
        })

    monkeypatch.setattr(metadata, "create_sheet", fake_create_sheet)
    return calls


def test_two_clean_subfolders(tmp_path, monkeypatch):
    parent = tmp_path / "parent"
    _make_photos(parent / "Trip_A", ["IMG_001.jpg", "IMG_002.jpg"])
    _make_photos(parent / "Trip_B", ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"])

    calls = _capture_recursive_run(monkeypatch)
    metadata.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    assert len(calls) == 1
    call = calls[0]
    assert call["recursive"] is True
    assert len(call["results"]) == 2
    assert call["total_processed"] == 5
    assert call["total_skipped"] == 0


def test_subfolder_with_skips(tmp_path, monkeypatch):
    parent = tmp_path / "parent"
    _make_photos(parent / "Clean", ["IMG_001.jpg", "IMG_002.jpg"])
    _make_photos(parent / "Messy", ["IMG_001.jpg"])
    (parent / "Messy" / "IMG_002.jpg").write_text("not an image")

    calls = _capture_recursive_run(monkeypatch)
    metadata.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    assert calls[0]["total_processed"] == 3
    assert calls[0]["total_skipped"] == 1


def test_subfolder_with_no_photos_ignored(tmp_path, monkeypatch):
    parent = tmp_path / "parent"
    _make_photos(parent / "WithPhotos", ["IMG_001.jpg"])

    empty = parent / "NoPhotos"
    empty.mkdir()
    (empty / "readme.txt").write_text("nothing here")

    calls = _capture_recursive_run(monkeypatch)
    metadata.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    assert len(calls[0]["results"]) == 1


def test_subfolder_with_only_videos_ignored(tmp_path, monkeypatch):
    parent = tmp_path / "parent"
    _make_photos(parent / "WithPhotos", ["IMG_001.jpg"])

    only_video = parent / "OnlyVideo"
    only_video.mkdir()
    (only_video / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")

    calls = _capture_recursive_run(monkeypatch)
    metadata.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    assert len(calls[0]["results"]) == 1


def test_no_valid_subfolders(tmp_path, monkeypatch):
    parent = tmp_path / "empty_parent"
    parent.mkdir()
    (parent / "notes.txt").write_text("nothing")

    calls = _capture_recursive_run(monkeypatch)
    metadata.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    assert calls[0]["results"] == []
    assert calls[0]["total_processed"] == 0
    assert calls[0]["total_skipped"] == 0