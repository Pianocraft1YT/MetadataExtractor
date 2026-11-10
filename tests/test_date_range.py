"""Tests for the date range filter."""

from tests.conftest import make_jpeg_with_exif


def test_find_directories_with_date_range(extractor, tmp_path):
    from tests.helpers import find_scan
    from datetime import date

    make_jpeg_with_exif(tmp_path / "may1.jpg", "2024:05:01 12:00:00")
    make_jpeg_with_exif(tmp_path / "may2.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(tmp_path / "may3.jpg", "2024:05:31 23:59:59")
    make_jpeg_with_exif(tmp_path / "jun1.jpg", "2024:06:01 00:00:00")
    make_jpeg_with_exif(tmp_path / "jun2.jpg", "2024:06:30 12:00:00")

    extractor.maxdepth = 0
    processed, skipped = find_scan(
        extractor,
        tmp_path,
        date_range=True,
        start_date=date(2024, 5, 1),
        end_date=date(2024, 5, 31),
        write=False,
    )

    assert processed == 3
    assert skipped == 0
    assert len(extractor.results) == 1
    df = extractor.results[0][0]
    assert len(df) == 3
    assert set(df["Files"]) == {"may1.jpg", "may2.jpg", "may3.jpg"}
