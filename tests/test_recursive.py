"""Tests for recursive-mode scanning via find_directories."""

from pathlib import Path
from unittest.mock import MagicMock
import metadata
from tests.conftest import make_jpeg_with_exif


def _make_photos(folder, names):
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        make_jpeg_with_exif(folder / name, "2024:05:15 12:30:45")


def _capture(extractor):
    calls = []

    def fake(output_path, recursive, total_processed, total_skipped):
        calls.append({
            "output_path": output_path,
            "recursive": recursive,
            "results": list(extractor.results),
            "total_processed": total_processed,
            "total_skipped": total_skipped,
        })

    extractor.create_sheet = fake
    return calls


def test_two_clean_subfolders(extractor, tmp_path):
    parent = tmp_path / "parent"
    _make_photos(parent / "Trip_A", ["IMG_001.jpg", "IMG_002.jpg"])
    _make_photos(parent / "Trip_B", ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"])

    calls = _capture(extractor)
    extractor.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    assert len(calls) == 1
    assert calls[0]["recursive"] is True
    assert len(calls[0]["results"]) == 2
    assert calls[0]["total_processed"] == 5
    assert calls[0]["total_skipped"] == 0


def test_subfolder_with_skips(extractor, tmp_path):
    parent = tmp_path / "parent"
    _make_photos(parent / "Clean", ["IMG_001.jpg", "IMG_002.jpg"])
    _make_photos(parent / "Messy", ["IMG_001.jpg"])
    (parent / "Messy" / "IMG_002.jpg").write_text("not an image")

    calls = _capture(extractor)
    extractor.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    assert calls[0]["total_processed"] == 3
    assert calls[0]["total_skipped"] == 1


def test_subfolder_with_no_photos_ignored(extractor, tmp_path):
    parent = tmp_path / "parent"
    _make_photos(parent / "WithPhotos", ["IMG_001.jpg"])
    empty = parent / "NoPhotos"
    empty.mkdir()
    (empty / "readme.txt").write_text("nothing")

    calls = _capture(extractor)
    extractor.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    assert len(calls[0]["results"]) == 1


def test_subfolder_with_only_videos_ignored(extractor, tmp_path):
    parent = tmp_path / "parent"
    _make_photos(parent / "WithPhotos", ["IMG_001.jpg"])
    only_video = parent / "OnlyVideo"
    only_video.mkdir()
    (only_video / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")

    calls = _capture(extractor)
    extractor.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    assert len(calls[0]["results"]) == 1


def test_no_valid_subfolders(extractor, tmp_path):
    parent = tmp_path / "empty_parent"
    parent.mkdir()
    (parent / "notes.txt").write_text("nothing")

    calls = _capture(extractor)
    extractor.find_directories(parent, tmp_path / "out.xlsx", modifier=0)

    assert calls[0]["results"] == []
    assert calls[0]["total_processed"] == 0
    assert calls[0]["total_skipped"] == 0