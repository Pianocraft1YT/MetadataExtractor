"""Tests for sort_and_extract (the merged scan function)."""

import os
from pathlib import Path

from tests.conftest import make_jpeg_with_exif, make_jpeg_no_exif
from tests.helpers import sort_scan


def _capture_create_sheet(extractor):
    captured = {}

    def fake(output_path, recursive, processed, skipped):
        captured["output_path"] = output_path
        captured["processed"] = processed
        captured["skipped"] = skipped

    extractor.create_sheet = fake
    return captured


def test_sort_and_extract_all_photos(extractor, photos_only):
    _capture_create_sheet(extractor)
    sort_scan(extractor, photos_only)
    assert len(extractor.results) == 1
    df, _, _ = extractor.results[0]
    assert len(df) == 3
    assert list(df["Files"]) == ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]


def test_sort_and_extract_missing_exif_skips_file(extractor, folder_missing_exif):
    captured = _capture_create_sheet(extractor)
    sort_scan(extractor, folder_missing_exif)
    df, _, _ = extractor.results[0]
    assert len(df) == 2
    assert "IMG_002.jpg" not in list(df["Files"])
    assert captured["skipped"] == 1
    assert captured["processed"] == 2


def test_sort_and_extract_corrupt_file_does_not_hang(extractor, folder_with_corrupt_photo):
    captured = _capture_create_sheet(extractor)
    sort_scan(extractor, folder_with_corrupt_photo)
    df, _, _ = extractor.results[0]
    assert len(df) == 6
    assert captured["skipped"] == 1
    assert captured["processed"] == 6


def test_sort_and_extract_no_exif_gap_in_series(extractor, tmp_path):
    folder = tmp_path / "gap"
    folder.mkdir()
    for name in ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]:
        make_jpeg_with_exif(folder / name, "2024:05:15 12:30:45")
    make_jpeg_no_exif(folder / "IMG_002.jpg")

    captured = _capture_create_sheet(extractor)
    sort_scan(extractor, folder)
    assert captured["processed"] == 2
    assert captured["skipped"] == 1


def test_3_photos_1_video_pattern(extractor, photos_and_videos):
    """Pattern (3 photos, 1 video) × 3 groups -> one row per group."""
    _capture_create_sheet(extractor)
    sort_scan(extractor, photos_and_videos)
    df, _, _ = extractor.results[0]
    assert len(df) == 3
    if "Img # Series" in df.columns:
        assert list(df["Img # Series"]) == ["1-4", "5-8", "9-12"]


def test_pattern_with_modifier(extractor, photos_and_videos):
    _capture_create_sheet(extractor)
    sort_scan(extractor, photos_and_videos, modifier=4)
    df, _, _ = extractor.results[0]
    if "Img # Series" in df.columns:
        assert list(df["Img # Series"]) == ["5-8", "9-12", "13-16"]


def test_video_first_orphan_returns_correctly(extractor, tmp_path, monkeypatch):
    """Single leading video, user says 'orphan' -> strip, scan photos."""
    folder = tmp_path / "video_first"
    folder.mkdir()
    (folder / "A_video.mp4").write_bytes(b"fake")
    make_jpeg_with_exif(folder / "B_photo.jpg", "2024:05:15 12:30:45")

    monkeypatch.setattr("metadata.messagebox.askyesno", lambda *args, **kwargs: True)

    sort_scan(extractor, folder)

    assert "Video First" not in extractor.collected_warnings
    assert extractor.results[0][0].shape[0] == 1


def test_video_first_not_orphan_falls_to_one_offs(extractor, tmp_path, monkeypatch):
    """Single leading video, user says 'not orphan' -> one-off photos."""
    folder = tmp_path / "video_first_pattern"
    folder.mkdir()
    (folder / "A_video.mp4").write_bytes(b"fake")
    make_jpeg_with_exif(folder / "B_photo.jpg", "2024:05:15 12:30:45")
    make_jpeg_with_exif(folder / "C_photo.jpg", "2024:05:16 12:30:45")

    monkeypatch.setattr("metadata.messagebox.askyesno", lambda *args, **kwargs: False)

    sort_scan(extractor, folder)

    # Photos are one-off'd since no closing video confirms a pattern
    assert len(extractor.results) == 1
    assert extractor.results[0][0].shape[0] == 2


def test_multiple_leading_videos_stripped(extractor, tmp_path):
    """Multiple leading videos -> all stripped without prompting, photos scan."""
    folder = tmp_path / "multi_video_first"
    folder.mkdir()
    (folder / "A1.mp4").write_bytes(b"fake")
    (folder / "A2.mp4").write_bytes(b"fake")
    (folder / "A3.mp4").write_bytes(b"fake")
    make_jpeg_with_exif(folder / "B.jpg", "2024:05:15 12:30:45")
    make_jpeg_with_exif(folder / "C.jpg", "2024:05:16 12:30:45")

    _capture_create_sheet(extractor)
    sort_scan(extractor, folder)

    df, _, _ = extractor.results[0]
    assert sorted(list(df["Files"])) == ["B.jpg", "C.jpg"]
