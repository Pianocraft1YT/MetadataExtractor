"""Cancel behaviour tests."""

from pathlib import Path

from tests.conftest import make_jpeg_with_exif
from tests.helpers import find_scan, media_files, sort_scan


def test_sort_and_extract_stops_on_cancel(extractor, tmp_path):
    for name in ["a.jpg", "b.jpg", "c.jpg"]:
        make_jpeg_with_exif(tmp_path / name, "2024:05:15 12:30:45")

    extractor.cancel_event.set()
    processed, skipped = sort_scan(extractor, tmp_path)

    assert processed == 0
    assert skipped == 0


def test_find_directories_breaks_on_cancel(extractor, tmp_path):
    extractor.cancel_event.set()
    p, s = find_scan(extractor, tmp_path)
    assert p == 0
    assert s == 0
