"""End-to-end tests for real-camera JPEG sub-IFD extraction and full-EXIF fixture."""

import shutil
from pathlib import Path

import pandas as pd
import pytest

from tests.helpers import sort_scan

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_ALL_EXTRAS_ON = dict(
    output_dimensions=True,
    output_filesize=True,
    output_make=True,
    output_model=True,
    output_software=True,
    output_lens_model=True,
    output_aperture=True,
    output_exposure_time=True,
    output_focal_length=True,
    output_iso=True,
    output_orientation=True,
    output_gps=True,
    output_gps_altitude=True,
)


def test_kitchen_sink_full_exif_end_to_end(extractor, tmp_path):
    fixture = FIXTURES_DIR / "kitchen_sink_exif.jpg"
    assert fixture.is_file(), f"Missing fixture: {fixture}"
    shutil.copy2(fixture, tmp_path / fixture.name)

    processed, skipped = sort_scan(
        extractor,
        tmp_path,
        output_utc=True,
        **_ALL_EXTRAS_ON,
        write=False,
    )

    assert (processed, skipped) == (1, 0)
    df = extractor.results[0][0]
    row = df.iloc[0]

    assert row["Files"] == "kitchen_sink_exif.jpg"
    # 2024-12-01 01:01:01 with +02:00 offset -> 2024-11-30 23:01:01 UTC
    assert row["Dates"] == "11/30/2024"
    assert row["Time"] == "23:01:01"
    assert row["Img # Series"] == "1"
    assert row["Dimensions"] == "148x196"
    assert isinstance(row["File Size"], str) and row["File Size"].endswith(("B", "KB", "MB"))
    assert row["Camera Make"] == "Canon"
    assert row["Camera Model"] == "Canon EOS R5"
    assert row["Software"] == "Extractor of Metadata"
    assert row["Lens Model"] == "RF 50mm F1.2L USM"
    assert row["Aperture / FNumber"] == "f/2.8"
    assert row["Exposure Time"] == "1/500"
    assert row["Focal Length"] == "50mm"
    assert row["ISO"] == 400
    assert row["Orientation"] == "Rotated 90° CW"
    assert row["GPS Latitude"] == "48.856667"
    assert row["GPS Longitude"] == "2.351944"
    assert row["GPS Altitude"] == "124.5 m"


def test_real_camera_iphone_jpeg_subifds_end_to_end(extractor, tmp_path):
    fixture = FIXTURES_DIR / "real_camera.jpg"
    assert fixture.is_file(), f"Missing fixture: {fixture}"
    shutil.copy2(fixture, tmp_path / fixture.name)

    processed, skipped = sort_scan(
        extractor,
        tmp_path,
        output_utc=False,
        **_ALL_EXTRAS_ON,
        write=False,
    )

    assert (processed, skipped) == (1, 0)
    df = extractor.results[0][0]
    row = df.iloc[0]

    assert row["Files"] == "real_camera.jpg"
    assert row["Dates"] == "11/24/2026"
    assert row["Time"] == "07:58:24"
    assert row["Img # Series"] == "1"
    assert isinstance(row["Dimensions"], str) and "x" in row["Dimensions"]
    assert isinstance(row["File Size"], str) and row["File Size"].endswith(("B", "KB", "MB"))
    assert row["Camera Make"] == "Apple"
    assert row["Camera Model"] == "iPhone 12 Pro"
    assert row["Software"] == "26.6"
    assert row["Lens Model"] == "iPhone 12 Pro back triple camera 4.2mm f/1.6"
    assert row["Orientation"] == "Rotated 90° CW"
    assert row["GPS Latitude"] == "49.234000"
    assert row["GPS Longitude"] == "-104.123000"
    assert pd.notna(row["Aperture / FNumber"])
    assert pd.notna(row["Exposure Time"])
    assert pd.notna(row["Focal Length"])