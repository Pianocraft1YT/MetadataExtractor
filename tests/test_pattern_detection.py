"""Pattern detection tests for sort_and_extract."""

import pytest

from tests.conftest import make_jpeg_with_exif
from tests.helpers import sort_scan


def _make_pattern(tmp_path, specs):
    """specs: list of ("p"|"v", count, date_str_for_photos)."""
    folder = tmp_path / "pattern"
    folder.mkdir()
    counter = 1
    for kind, count, date in specs:
        for _ in range(count):
            if kind == "p":
                make_jpeg_with_exif(folder / f"{counter:04d}.jpg", date)
            else:
                (folder / f"{counter:04d}.mp4").write_bytes(b"fake")
            counter += 1
    return folder


def _scan(extractor, folder, modifier=0):
    extractor.create_sheet = lambda *a, **k: None
    return sort_scan(extractor, folder, modifier=modifier)


def test_exactly_five_photos_before_video(extractor, tmp_path):
    folder = _make_pattern(
        tmp_path,
        [
            ("p", 5, "2024:05:15 12:00:00"),
            ("v", 1, None),
            ("p", 5, "2024:05:16 12:00:00"),
            ("v", 1, None),
        ],
    )
    _scan(extractor, folder)
    df, _, _ = extractor.results[0]
    assert len(df) == 2
    assert "Img # Series" in df.columns


def test_exactly_six_photos_before_video(extractor, tmp_path):
    """6 > MAX_PHOTOS_BEFORE_VIDEO -> series disabled, one-off each."""
    folder = _make_pattern(
        tmp_path,
        [
            ("p", 6, "2024:05:15 12:00:00"),
            ("v", 1, None),
        ],
    )
    _scan(extractor, folder)
    df, _, _ = extractor.results[0]
    assert len(df) == 6
    # Series column dropped
    assert "Img # Series" not in df.columns


def test_two_videos_in_a_row(extractor, tmp_path):
    folder = _make_pattern(
        tmp_path,
        [
            ("p", 2, "2024:05:15 12:00:00"),
            ("v", 2, None),
            ("p", 2, "2024:05:16 12:00:00"),
            ("v", 1, None),
        ],
    )
    _scan(extractor, folder)
    # Should produce some rows without crashing
    assert len(extractor.results) == 1


def test_pattern_breaks_midway(extractor, tmp_path):
    """First group regular, second group irregular -> one-offs for stragglers."""
    folder = _make_pattern(
        tmp_path,
        [
            ("p", 3, "2024:05:15 12:00:00"),
            ("v", 1, None),
            ("p", 2, "2024:05:16 12:00:00"),  # short group
            ("v", 1, None),
        ],
    )
    _scan(extractor, folder)
    df, _, _ = extractor.results[0]
    assert len(df) > 0


def test_trailing_photos_with_no_video(extractor, tmp_path):
    """Pattern + trailing photos with no closing video -> tail scan.

    Folder: p p v p p p
    Group 1 = (photo, photo, video) -> 1 series row
    Trailing = photo, photo, photo -> 3 one-off rows
    Total = 4 rows (not 5; the series row represents the whole group)
    """
    folder = _make_pattern(
        tmp_path,
        [
            ("p", 2, "2024:05:15 12:00:00"),
            ("v", 1, None),
            ("p", 3, "2024:05:16 12:00:00"),
        ],
    )
    _scan(extractor, folder)
    df, _, _ = extractor.results[0]
    assert len(df) == 4


def test_all_videos_no_photos(extractor, tmp_path):
    folder = tmp_path / "videos_only"
    folder.mkdir()
    for name in ["a.mp4", "b.mp4", "c.mp4"]:
        (folder / name).write_bytes(b"fake")
    _scan(extractor, folder)
    assert len(extractor.results) == 0


def test_all_photos(extractor, tmp_path):
    folder = _make_pattern(tmp_path, [("p", 5, "2024:05:15 12:00:00")])
    _scan(extractor, folder)
    df, _, _ = extractor.results[0]
    assert len(df) == 5
    assert "Img # Series" in df.columns


def test_starting_index_zero(extractor, tmp_path):
    """Modifier -1 shifts series index to 0-based."""
    folder = _make_pattern(
        tmp_path,
        [
            ("p", 2, "2024:05:15 12:00:00"),
            ("v", 1, None),
            ("p", 2, "2024:05:16 12:00:00"),
            ("v", 1, None),
        ],
    )
    _scan(extractor, folder, modifier=-1)
    df, _, _ = extractor.results[0]
    if "Img # Series" in df.columns:
        # First label should start below 1
        first = df["Img # Series"].iloc[0]
        start = int(first.split("-")[0])
        assert start <= 0
