"""Tests for sort_and_extract and sort_and_extract_irregular."""

from pathlib import Path
from unittest.mock import MagicMock

import metadata
from tests.conftest import make_jpeg_with_exif, make_jpeg_no_exif


def _capture_df(monkeypatch):
    """Install a create_sheet mock that captures DataFrame and counts."""
    captured = {}

    def fake_create_sheet(final_output, recursive, df, processed, skipped):
        captured["df"] = df
        captured["final_output"] = final_output
        captured["processed"] = processed
        captured["skipped"] = skipped

    monkeypatch.setattr(metadata, "create_sheet", fake_create_sheet)
    return captured


# ---------------------------------------------------------------------------
# sort_and_extract — the "regular mode" fallback
# ---------------------------------------------------------------------------

def test_sort_and_extract_all_photos(photos_only, monkeypatch):
    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract(
        photos_only, recursive=False,
        final_output=Path("out.xlsx"), modifier=0,
        output_series=True,
    )
    df = captured["df"]
    assert len(df) == 3
    assert list(df["Files"]) == ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]


def test_sort_and_extract_missing_exif_skips_file(folder_missing_exif, monkeypatch):
    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract(
        folder_missing_exif, recursive=False,
        final_output=Path("out.xlsx"), modifier=0,
        output_series=True,
    )
    df = captured["df"]
    assert len(df) == 2
    assert "IMG_002.jpg" not in list(df["Files"])
    assert captured["skipped"] == 1
    assert captured["processed"] == 2


def test_sort_and_extract_corrupt_file_does_not_hang(folder_with_corrupt_photo, monkeypatch):
    """Regression: the original code could infinite-loop on a bad file."""
    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract(
        folder_with_corrupt_photo, recursive=False,
        final_output=Path("out.xlsx"), modifier=0,
        output_series=True,
    )
    df = captured["df"]
    assert len(df) == 6
    assert captured["skipped"] == 1
    assert captured["processed"] == 6


def test_sort_and_extract_no_exif_gap_in_series(tmp_path, monkeypatch):
    """A skipped image should still consume a series slot."""
    folder = tmp_path / "gap"
    folder.mkdir()
    for name in ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]:
        make_jpeg_with_exif(folder / name, "2024:05:15 12:30:45")
    make_jpeg_no_exif(folder / "IMG_002.jpg")

    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract(
        folder, recursive=False,
        final_output=Path("out.xlsx"), modifier=0,
        output_series=True,
    )
    assert captured["processed"] == 2
    assert captured["skipped"] == 1


# ---------------------------------------------------------------------------
# sort_and_extract_irregular — pattern detection
# ---------------------------------------------------------------------------

def test_irregular_3_photos_1_video_pattern(photos_and_videos, monkeypatch):
    """P P P V ×3 → 3 rows, series 1-4, 5-8, 9-12."""
    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        photos_and_videos, recursive=False,
        final_output=Path("out.xlsx"), modifier=0,
    )
    df = captured["df"]
    assert len(df) == 3
    if "Image # Series" in df.columns:
        assert list(df["Image # Series"]) == ["1-4", "5-8", "9-12"]


def test_irregular_all_photos_falls_through_to_sort_and_extract(
    photos_only, monkeypatch
):
    """When there's no video, irregular mode delegates to sort_and_extract."""
    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        photos_only, recursive=False,
        final_output=Path("out.xlsx"), modifier=0,
    )
    df = captured["df"]
    assert len(df) == 3


def test_irregular_video_first_shows_warning_and_returns(tmp_path):
    """A folder starting with a video aborts with a warning, no output."""
    folder = tmp_path / "video_first"
    folder.mkdir()
    (folder / "A_video.mp4").write_bytes(b"fake")
    make_jpeg_with_exif(folder / "B_photo.jpg", "2024:05:15 12:30:45")

    metadata.collected_warnings.clear()
    metadata.sort_and_extract_irregular(
        folder, recursive=False,
        final_output=Path("out.xlsx"), modifier=0,
    )
    assert "Video First" in metadata.collected_warnings
    assert metadata.collected_warnings["Video First"]


def test_irregular_with_modifier(photos_and_videos, monkeypatch):
    """starting index 5 → series 5-8, 9-12, 13-16."""
    captured = _capture_df(monkeypatch)
    metadata.sort_and_extract_irregular(
        photos_and_videos, recursive=False,
        final_output=Path("out.xlsx"), modifier=4,
    )
    df = captured["df"]
    if "Image # Series" in df.columns:
        assert list(df["Image # Series"]) == ["5-8", "9-12", "13-16"]