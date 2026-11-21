"""Tests for nested Exif sub-IFD extraction, paired offsets, UTC clustering,
date-only EXIF routing, and Python-datetime DataFrame sorting.
"""

from datetime import datetime, timedelta

import pytest
from PIL import Image

from tests.conftest import make_jpeg_with_nested_exif
from tests.helpers import sort_scan


def _save_mixed_ifd_jpeg(path, ifd0_tags=None, exif_subifd=None, gps_subifd=None):
    img = Image.new("RGB", (10, 10), color="red")
    exif = Image.Exif()
    if ifd0_tags:
        for tag, val in ifd0_tags.items():
            exif[tag] = val
    if exif_subifd:
        exif[0x8769] = exif_subifd
    if gps_subifd:
        exif[0x8825] = gps_subifd
    img.save(path, format="JPEG", exif=exif)
    return path


# ---------------------------------------------------------------------------
# Sub-IFD extraction (reviewer feedback: tags live in 0x8769 / 0x8825)
# ---------------------------------------------------------------------------


def test_all_camera_tags_extracted_from_sub_ifds_only(extractor, tmp_path):
    """Real cameras write capture tags in 0x8769 and GPS in 0x8825, not IFD0."""
    path = tmp_path / "camera.jpg"
    make_jpeg_with_nested_exif(
        path,
        exif_tags={
            36867: "2024:05:15 12:30:45",  # DateTimeOriginal
            36881: "+02:00",  # OffsetTimeOriginal
            33437: (28, 10),  # FNumber -> f/2.8
            33434: (1, 500),  # ExposureTime -> 1/500
            37386: (50, 1),  # FocalLength -> 50mm
            34855: 200,  # ISO -> 200
            42036: "FE 50mm F1.8",  # LensModel
        },
        gps_tags={
            1: "N",
            2: (48.0, 51.0, 24.0),
            3: "E",
            4: (2.0, 21.0, 7.0),
        },
    )

    dt, has_time, offset = extractor._get_photo_date_and_offset(path)
    assert dt == datetime(2024, 5, 15, 12, 30, 45)
    assert has_time is True
    assert offset == "+02:00"

    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        "camera.jpg",
        data,
        output_utc=True,
        output_dimensions=True,
        output_filesize=False,
        output_make=False,
        output_model=False,
        output_software=False,
        output_lens_model=True,
        output_aperture=True,
        output_exposure_time=True,
        output_focal_length=True,
        output_iso=True,
        output_gps=True,
    )
    assert ok is True
    assert data["Offsets"] == ["+02:00"]
    assert data["Lens_Models"] == ["FE 50mm F1.8"]
    assert data["Apertures"] == ["f/2.8"]
    assert data["Exposure_Times"] == ["1/500"]
    assert data["Focal_Lengths"] == ["50mm"]
    assert data["ISOs"] == [200]
    assert data["GPS_Latitudes"] == ["48.856667"]
    assert data["GPS_Longitudes"] == ["2.351944"]


# ---------------------------------------------------------------------------
# Paired datetime <-> offset selection
# ---------------------------------------------------------------------------


def test_offset_pairs_with_winning_datetime_tag(extractor, tmp_path):
    """DateTimeOriginal without OffsetTimeOriginal must NOT borrow DateTime's OffsetTime."""
    path = tmp_path / "edited.jpg"
    _save_mixed_ifd_jpeg(
        path,
        ifd0_tags={306: "2024:05:20 18:00:00"},  # DateTime (IFD0)
        exif_subifd={
            36867: "2024:05:15 10:00:00",  # DateTimeOriginal (no 36881)
            36880: "-04:00",  # OffsetTime (editor's offset)
        },
    )
    dt, _, offset = extractor._get_photo_date_and_offset(path)
    assert dt == datetime(2024, 5, 15, 10, 0, 0)
    assert offset is None


def test_blank_datetime_original_falls_back_to_datetime_and_its_offset(extractor, tmp_path):
    """Blank DateTimeOriginal skips to DateTime and reads OffsetTime (ignoring stale 36881)."""
    path = tmp_path / "fallback.jpg"
    _save_mixed_ifd_jpeg(
        path,
        ifd0_tags={306: "2024:05:20 18:00:00"},  # DateTime (IFD0)
        exif_subifd={
            36867: "0000:00:00 00:00:00",  # invalid
            36881: "+09:00",  # stale OffsetTimeOriginal
            36880: "-04:00",  # OffsetTime
        },
    )
    dt, _, offset = extractor._get_photo_date_and_offset(path)
    assert dt == datetime(2024, 5, 20, 18, 0, 0)
    assert offset == "-04:00"


def test_whitespace_only_offset_normalized_to_none(extractor, tmp_path):
    path = tmp_path / "blank_offset.jpg"
    make_jpeg_with_nested_exif(path, exif_tags={36867: "2024:05:15 12:00:00", 36881: "   "})
    _, _, offset = extractor._get_photo_date_and_offset(path)
    assert offset is None


# ---------------------------------------------------------------------------
# _parse_utc_offset & UTC burst clustering
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Z", timedelta(0)),
        ("z", timedelta(0)),
        ("+05:30", timedelta(hours=5, minutes=30)),
        ("-04:00", timedelta(hours=-4)),
        ("-00:30", timedelta(minutes=-30)),
        ("+0530", timedelta(hours=5, minutes=30)),
        ("-0400", timedelta(hours=-4)),
        ("+05", timedelta(hours=5)),
        ("-4", timedelta(hours=-4)),
    ],
)
def test_parse_utc_offset_valid(extractor, raw, expected):
    assert extractor._parse_utc_offset(raw) == expected


@pytest.mark.parametrize("raw", ["05:00", "+-5:00", "+25:00", "+05:60", "+5:0", "+530", "", "   ", None])
def test_parse_utc_offset_invalid(extractor, raw):
    assert extractor._parse_utc_offset(raw) is None


def test_utc_burst_clustering_across_timezones_without_double_shift(extractor_tz_on, make_jpeg, tmp_path):
    """12:00:00-04:00 (16:00:00 UTC) and 11:00:01-05:00 (16:00:01 UTC) are 1s apart in UTC."""
    make_jpeg("ny.jpg", datetime_original="2024:05:15 12:00:00", offset_original="-04:00")
    make_jpeg("chi.jpg", datetime_original="2024:05:15 11:00:01", offset_original="-05:00")

    processed, skipped = sort_scan(extractor_tz_on, tmp_path, output_utc=True, write=False)
    assert (processed, skipped) == (2, 0)
    df = extractor_tz_on.results[0][0]
    assert list(df["Img # Series"]) == ["1-2", "1-2"]
    assert list(df["Time"]) == ["16:00:00", "16:00:01"]


# ---------------------------------------------------------------------------
# Date-only EXIF & sorting edge cases
# ---------------------------------------------------------------------------


def test_date_only_exif_not_grouped_and_not_shifted_in_utc(extractor_tz_on, make_jpeg, tmp_path):
    make_jpeg("d1.jpg", datetime_original="2024:05:15", offset_original="+12:00")
    make_jpeg("d2.jpg", datetime_original="2024:05:15", offset_original="-12:00")

    sort_scan(extractor_tz_on, tmp_path, output_utc=True, write=False)
    df = extractor_tz_on.results[0][0]
    assert list(df["Dates"]) == ["05/15/2024", "05/15/2024"]
    assert list(df["Time"]) == ["", ""]
    assert list(df["Img # Series"]) == ["", ""]


def test_sort_subsecond_tie_breaking_and_date_newest_keeps_burst_forward(extractor, make_jpeg, tmp_path):
    make_jpeg("b1.jpg", datetime_original="2024:05:15 12:00:00.800000")
    make_jpeg("b2.jpg", datetime_original="2024:05:15 12:00:00.200000")
    make_jpeg("later.jpg", datetime_original="2024:05:16 09:00:00")

    extractor.sort_method = "Date (Oldest)"
    sort_scan(extractor, tmp_path, write=False)
    assert list(extractor.results[0][0]["Files"]) == ["b2.jpg", "b1.jpg", "later.jpg"]

    extractor.reset()
    extractor.sort_method = "Date (Newest)"
    sort_scan(extractor, tmp_path, write=False)
    df_new = extractor.results[0][0]
    assert list(df_new["Files"]) == ["later.jpg", "b2.jpg", "b1.jpg"]
    assert list(df_new["Img # Series"]) == ["3", "1-2", "1-2"]


def test_sort_handles_years_before_1677_without_nat(extractor, make_jpeg, tmp_path):
    make_jpeg("old.jpg", datetime_original="1500:01:01 12:00:00")
    make_jpeg("modern.jpg", datetime_original="2024:01:01 12:00:00")

    extractor.sort_method = "Date (Oldest)"
    sort_scan(extractor, tmp_path, write=False)
    assert list(extractor.results[0][0]["Files"]) == ["old.jpg", "modern.jpg"]
