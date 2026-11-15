"""Direct tests for MetadataExtractor._filter_by_date.

This is the internal filter walk_and_filter applies when date_range=True.
Existing coverage exercises it via find_scan; these tests probe the helper
directly to lock in include_undateable and boundary behavior.
"""

import os
from datetime import date

from tests.conftest import make_jpeg_with_exif, make_jpeg_no_exif


def _filter(extractor, folder, start=None, end=None, include_undateable=True):
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png", ".mp4", ".mov")))
    return extractor._filter_by_date(str(folder), files, start, end, include_undateable)


def test_keeps_only_dated_photos_in_range(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "may1.jpg", "2024:05:01 12:00:00")
    make_jpeg_with_exif(tmp_path / "may15.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(tmp_path / "may31.jpg", "2024:05:31 23:59:59")
    make_jpeg_with_exif(tmp_path / "jun1.jpg", "2024:06:01 00:00:00")

    result = _filter(extractor, tmp_path, start=date(2024, 5, 1), end=date(2024, 5, 31))
    assert sorted(result) == ["may1.jpg", "may15.jpg", "may31.jpg"]


def test_start_date_only(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "april.jpg", "2024:04:15 12:00:00")
    make_jpeg_with_exif(tmp_path / "may.jpg", "2024:05:15 12:00:00")
    assert _filter(extractor, tmp_path, start=date(2024, 5, 1)) == ["may.jpg"]


def test_end_date_only(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "may.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(tmp_path / "june.jpg", "2024:06:15 12:00:00")
    assert _filter(extractor, tmp_path, end=date(2024, 5, 31)) == ["may.jpg"]


def test_start_date_boundary_inclusive(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "boundary.jpg", "2024:05:01 00:00:00")
    assert _filter(extractor, tmp_path, start=date(2024, 5, 1)) == ["boundary.jpg"]


def test_end_date_boundary_inclusive(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "boundary.jpg", "2024:05:31 23:59:59")
    assert _filter(extractor, tmp_path, end=date(2024, 5, 31)) == ["boundary.jpg"]


def test_include_undateable_false_drops_no_exif(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "dated.jpg", "2024:05:15 12:00:00")
    make_jpeg_no_exif(tmp_path / "undated.jpg")
    assert _filter(extractor, tmp_path, include_undateable=False) == ["dated.jpg"]


def test_include_undateable_true_keeps_no_exif(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "dated.jpg", "2024:05:15 12:00:00")
    make_jpeg_no_exif(tmp_path / "undated.jpg")
    assert sorted(_filter(extractor, tmp_path, include_undateable=True)) == ["dated.jpg", "undated.jpg"]


def test_corrupt_file_treated_as_undateable(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "good.jpg", "2024:05:15 12:00:00")
    (tmp_path / "broken.jpg").write_bytes(b"not an image")

    assert _filter(extractor, tmp_path, include_undateable=False) == ["good.jpg"]
    assert sorted(_filter(extractor, tmp_path, include_undateable=True)) == ["broken.jpg", "good.jpg"]
