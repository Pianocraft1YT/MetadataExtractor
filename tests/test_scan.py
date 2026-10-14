"""Tests for scan_image — the EXIF extractor."""

from pathlib import Path
from unittest.mock import MagicMock

import metadata
from tests.conftest import make_jpeg_with_exif, make_jpeg_no_exif, make_corrupt_file


def test_valid_image_with_exif_returns_true(tmp_path):
    path = make_jpeg_with_exif(tmp_path / "ok.jpg", "2024:05:15 12:30:45")
    dates, images = [], []

    result = metadata.scan_image(tmp_path, ["ok.jpg"], 0, dates, images)

    assert result is True
    assert dates == ["2024:05:15 12:30:45"]
    assert images == ["ok.jpg"]


def test_image_missing_exif_returns_false(tmp_path):
    make_jpeg_no_exif(tmp_path / "no_exif.jpg")
    dates, images = [], []

    result = metadata.scan_image(tmp_path, ["no_exif.jpg"], 0, dates, images)

    assert result is False
    assert dates == []
    assert images == []


def test_corrupt_file_returns_false(tmp_path):
    make_corrupt_file(tmp_path / "bad.jpg")
    dates, images = [], []

    result = metadata.scan_image(tmp_path, ["bad.jpg"], 0, dates, images)

    assert result is False
    assert dates == []
    assert images == []


def test_prefers_datetime_original_over_others(tmp_path):
    # Write all three fields — Original should win.
    img_path = tmp_path / "all_exif.jpg"
    from PIL import Image
    img = Image.new("RGB", (10, 10), color="green")
    exif = Image.Exif()
    exif[metadata.EXIF_DATETIME_ORIGINAL] = "2024:05:15 12:00:00"
    exif[metadata.EXIF_DATETIME_DIGITIZED] = "2024:06:15 12:00:00"
    exif[metadata.EXIF_DATETIME] = "2024:07:15 12:00:00"
    img.save(img_path, format="JPEG", exif=exif)

    dates, images = [], []
    result = metadata.scan_image(tmp_path, ["all_exif.jpg"], 0, dates, images)

    assert result is True
    assert dates[0] == "2024:05:15 12:00:00"


def test_falls_back_to_datetime_when_original_missing(tmp_path):
    img_path = tmp_path / "only_datetime.jpg"
    from PIL import Image
    img = Image.new("RGB", (10, 10))
    exif = Image.Exif()
    exif[metadata.EXIF_DATETIME] = "2024:05:15 12:00:00"
    img.save(img_path, format="JPEG", exif=exif)

    dates, images = [], []
    result = metadata.scan_image(tmp_path, ["only_datetime.jpg"], 0, dates, images)

    assert result is True
    assert dates[0] == "2024:05:15 12:00:00"