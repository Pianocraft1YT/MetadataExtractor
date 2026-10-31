"""Tests for the date range filter."""

from datetime import date
from pathlib import Path

from tests.conftest import make_jpeg_with_exif

_EXTRA_OFF = dict(
    output_utc=False,
    output_dimensions=False,
    output_make=False,
    output_model=False,
    output_software=False,
    output_lens_model=False,
    output_aperture=False,
    output_exposure_time=False,
    output_focal_length=False,
    output_iso=False,
)


def test_scan_image_within_range_returns_true(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "in.jpg", "2024:05:15 12:30:45")
    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        0,
        data,
        ["in.jpg"],
        **_EXTRA_OFF,
        date_range=True,
        start_date=date(2024, 5, 1),
        end_date=date(2024, 5, 31),
    )
    assert ok is True
    assert data["Images"] == ["in.jpg"]


def test_scan_image_before_start_returns_false(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "out.jpg", "2024:04:30 12:30:45")
    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        0,
        data,
        ["out.jpg"],
        **_EXTRA_OFF,
        date_range=True,
        start_date=date(2024, 5, 1),
        end_date=None,
    )
    assert ok is False
    assert data["Images"] == []


def test_scan_image_after_end_returns_false(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "out.jpg", "2024:06:01 12:30:45")
    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        0,
        data,
        ["out.jpg"],
        **_EXTRA_OFF,
        date_range=True,
        start_date=None,
        end_date=date(2024, 5, 31),
    )
    assert ok is False


def test_scan_image_only_start(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "in.jpg", "2024:12:31 23:59:59")
    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        0,
        data,
        ["in.jpg"],
        **_EXTRA_OFF,
        date_range=True,
        start_date=date(2024, 1, 1),
        end_date=None,
    )
    assert ok is True


def test_scan_image_only_end(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "in.jpg", "2020:01:01 00:00:00")
    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        0,
        data,
        ["in.jpg"],
        **_EXTRA_OFF,
        date_range=True,
        start_date=None,
        end_date=date(2024, 12, 31),
    )
    assert ok is True


def test_scan_image_date_only_no_time(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "in.jpg", "2024:05:15")
    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        0,
        data,
        ["in.jpg"],
        **_EXTRA_OFF,
        date_range=True,
        start_date=date(2024, 5, 1),
        end_date=date(2024, 5, 31),
    )
    assert ok is True


def test_scan_image_unparseable_date_excluded_when_filter_active(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "bad.jpg", "0000:00:00 00:00:00")
    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        0,
        data,
        ["bad.jpg"],
        **_EXTRA_OFF,
        date_range=True,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )
    assert ok is False


def test_scan_image_no_filter_keeps_everything(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "in.jpg", "1990:01:01 00:00:00")
    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        0,
        data,
        ["in.jpg"],
        **_EXTRA_OFF,
        date_range=False,
        start_date=None,
        end_date=None,
    )
    assert ok is True


def test_sort_and_extract_with_date_range(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "may1.jpg", "2024:05:01 12:00:00")
    make_jpeg_with_exif(tmp_path / "may2.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(tmp_path / "may3.jpg", "2024:05:31 23:59:59")
    make_jpeg_with_exif(tmp_path / "jun1.jpg", "2024:06:01 00:00:00")
    make_jpeg_with_exif(tmp_path / "jun2.jpg", "2024:06:30 12:00:00")

    processed, skipped = extractor.sort_and_extract(
        tmp_path,
        recursive=False,
        final_output=Path("out.xlsx"),
        modifier=0,
        output_series=True,
        output_utc=False,
        output_dimensions=False,
        output_make=False,
        output_model=False,
        output_software=False,
        output_lens_model=False,
        output_aperture=False,
        output_exposure_time=False,
        output_focal_length=False,
        output_iso=False,
        date_range=True,
        start_date=date(2024, 5, 1),
        end_date=date(2024, 5, 31),
    )
    assert processed == 3
    assert skipped == 2
    assert len(extractor.results) == 1
    df = extractor.results[0][0]
    assert len(df) == 3
    assert set(df["Files"]) == {"may1.jpg", "may2.jpg", "may3.jpg"}
