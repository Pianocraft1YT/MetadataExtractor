"""Tests for Tier 3 (rational) EXIF formatting."""

import pytest

from PIL import Image

# ---------------------------------------------------------------------------
# _format_aperture
# ---------------------------------------------------------------------------


def test_format_aperture_standard(extractor):
    assert extractor._format_aperture(5.6) == "f/5.6"
    assert extractor._format_aperture(2.8) == "f/2.8"


def test_format_aperture_whole_number_trims_decimal(extractor):
    assert extractor._format_aperture(8.0) == "f/8"
    assert extractor._format_aperture(11.0) == "f/11"


def test_format_aperture_none_and_zero(extractor):
    assert extractor._format_aperture(None) is None
    assert extractor._format_aperture(0) is None


# ---------------------------------------------------------------------------
# _format_exposure_time
# ---------------------------------------------------------------------------


def test_format_exposure_time_fraction(extractor):
    assert extractor._format_exposure_time(0.004) == "1/250"
    assert extractor._format_exposure_time(0.00025) == "1/4000"
    assert extractor._format_exposure_time(0.5) == "1/2"


def test_format_exposure_time_above_one_second(extractor):
    assert extractor._format_exposure_time(1.0) == "1s"
    assert extractor._format_exposure_time(2.5) == "2.5s"
    assert extractor._format_exposure_time(30.0) == "30s"


def test_format_exposure_time_non_repeating_fraction(extractor):
    """0.3s is 0.3s, not 1/3."""
    assert extractor._format_exposure_time(0.3) == "0.3s"
    assert extractor._format_exposure_time(0.7) == "0.7s"


def test_format_exposure_time_none_and_zero(extractor):
    assert extractor._format_exposure_time(None) is None
    assert extractor._format_exposure_time(0) is None


# ---------------------------------------------------------------------------
# _format_focal_length
# ---------------------------------------------------------------------------


def test_format_focal_length_integer(extractor):
    assert extractor._format_focal_length(23.0) == "23mm"
    assert extractor._format_focal_length(50.0) == "50mm"


def test_format_focal_length_decimal(extractor):
    assert extractor._format_focal_length(18.5) == "18.5mm"


def test_format_focal_length_none_and_zero(extractor):
    assert extractor._format_focal_length(None) is None
    assert extractor._format_focal_length(0) is None


# ---------------------------------------------------------------------------
# _format_iso
# ---------------------------------------------------------------------------


def test_format_iso_int(extractor):
    assert extractor._format_iso(400) == 400


def test_format_iso_tuple_takes_first(extractor):
    """Multi-ISO capture: some cameras write a tuple."""
    assert extractor._format_iso((400, 800)) == 400


def test_format_iso_none(extractor):
    assert extractor._format_iso(None) is None


def test_format_iso_string_coerced(extractor):
    """Defensive: some malformed EXIF writes ISO as a string."""
    assert extractor._format_iso("400") == 400


# ---------------------------------------------------------------------------
# End-to-end: scan_image populates the formatted values
# ---------------------------------------------------------------------------


def test_scan_image_extracts_and_formats_tier3(extractor, make_jpeg_with_tags, tmp_path):
    make_jpeg_with_tags(
        "photo.jpg",
        {
            36867: "2024:05:15 12:30:45",  # DateTimeOriginal
            33437: (56, 10),  # FNumber -> 5.6
            33434: (1, 250),  # ExposureTime -> 1/250
            37386: (23, 1),  # FocalLength -> 23mm
            34855: 400,  # ISO -> 400
        },
    )
    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        0,
        data,
        ["photo.jpg"],
        output_utc=False,
        output_dimensions=False,
        output_make=False,
        output_model=False,
        output_software=False,
        output_lens_model=False,
        output_aperture=True,
        output_exposure_time=True,
        output_focal_length=True,
        output_iso=True,
    )
    assert ok is True
    assert data["Apertures"] == ["f/5.6"]
    assert data["Exposure_Times"] == ["1/250"]
    assert data["Focal_Lengths"] == ["23mm"]
    assert data["ISOs"] == [400]


def test_scan_image_tier3_disabled_stores_none(extractor, make_jpeg_with_tags, tmp_path):
    make_jpeg_with_tags(
        "photo.jpg",
        {36867: "2024:05:15 12:30:45", 33437: (56, 10)},
    )
    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        0,
        data,
        ["photo.jpg"],
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
    assert ok is True
    assert data["Apertures"] == [None]
    assert data["Exposure_Times"] == [None]


def test_scan_image_missing_tier3_tags_stores_none(extractor, make_jpeg_with_tags, tmp_path):
    """A photo with only DateTimeOriginal and no lens data is not an error."""
    make_jpeg_with_tags("photo.jpg", {36867: "2024:05:15 12:30:45"})
    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        0,
        data,
        ["photo.jpg"],
        output_utc=False,
        output_dimensions=False,
        output_make=False,
        output_model=False,
        output_software=False,
        output_lens_model=False,
        output_aperture=True,
        output_exposure_time=True,
        output_focal_length=True,
        output_iso=True,
    )
    assert ok is True
    assert data["Apertures"] == [None]
    assert data["Exposure_Times"] == [None]
    assert data["Focal_Lengths"] == [None]
    assert data["ISOs"] == [None]
