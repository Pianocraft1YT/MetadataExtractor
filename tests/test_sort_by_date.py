"""Tests for the date-based sort in create_dataframe."""

from tests.conftest import make_jpeg_with_exif
from tests.helpers import sort_scan


def test_sort_date_oldest(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "a.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(tmp_path / "b.jpg", "2024:04:01 12:00:00")
    make_jpeg_with_exif(tmp_path / "c.jpg", "2024:06:10 12:00:00")

    extractor.sort_method = "Date (Oldest)"
    sort_scan(extractor, tmp_path, write=False)

    df = extractor.results[0][0]
    assert list(df["Files"]) == ["b.jpg", "a.jpg", "c.jpg"]


def test_sort_date_newest(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "a.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(tmp_path / "b.jpg", "2024:04:01 12:00:00")
    make_jpeg_with_exif(tmp_path / "c.jpg", "2024:06:10 12:00:00")

    extractor.sort_method = "Date (Newest)"
    sort_scan(extractor, tmp_path, write=False)

    df = extractor.results[0][0]
    assert list(df["Files"]) == ["c.jpg", "a.jpg", "b.jpg"]


def test_sort_filename_no_reorder(extractor, tmp_path):
    # Dates out of filename order
    make_jpeg_with_exif(tmp_path / "a.jpg", "2024:06:10 12:00:00")
    make_jpeg_with_exif(tmp_path / "b.jpg", "2024:04:01 12:00:00")

    extractor.sort_method = "Filename"
    sort_scan(extractor, tmp_path, write=False)

    df = extractor.results[0][0]
    # Filename order preserved (natural sort: a before b)
    assert list(df["Files"]) == ["a.jpg", "b.jpg"]


def test_sort_unparseable_date_last(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "valid.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(tmp_path / "bad.jpg", "0000:00:00 00:00:00")

    extractor.sort_method = "Date (Oldest)"
    sort_scan(extractor, tmp_path, write=False)

    df = extractor.results[0][0]
    # NaT sorts to bottom regardless of direction
    assert list(df["Files"]) == ["valid.jpg", "bad.jpg"]


def test_sort_preserves_series_labels(extractor, tmp_path):
    """Series labels follow their rows through the sort."""
    make_jpeg_with_exif(tmp_path / "a_photo.jpg", "2024:04:01 12:00:00")
    (tmp_path / "a_video.mp4").write_bytes(b"fake")
    make_jpeg_with_exif(tmp_path / "b_photo.jpg", "2024:06:10 12:00:00")
    (tmp_path / "b_video.mp4").write_bytes(b"fake")

    extractor.sort_method = "Date (Newest)"
    sort_scan(extractor, tmp_path, write=False)

    df = extractor.results[0][0]
    # June photo (b) comes first after sort; April photo (a) second
    assert list(df["Files"]) == ["b_photo.jpg", "a_photo.jpg"]
    # Both rows have their series labels intact
    assert len(df["Img # Series"]) == 2


def test_sort_date_oldest_orders_within_day(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "a.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(tmp_path / "b.jpg", "2024:05:15 10:00:00")  # earlier time
    make_jpeg_with_exif(tmp_path / "c.jpg", "2024:05:15 14:00:00")  # later time

    extractor.sort_method = "Date (Oldest)"
    sort_scan(extractor, tmp_path, write=False)

    df = extractor.results[0][0]
    assert list(df["Time"]) == ["10:00:00", "12:00:00", "14:00:00"]


def test_sort_date_newest_orders_within_day(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "a.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(tmp_path / "b.jpg", "2024:05:15 10:00:00")
    make_jpeg_with_exif(tmp_path / "c.jpg", "2024:05:15 14:00:00")

    extractor.sort_method = "Date (Newest)"
    sort_scan(extractor, tmp_path, write=False)

    df = extractor.results[0][0]
    assert list(df["Time"]) == ["14:00:00", "12:00:00", "10:00:00"]
