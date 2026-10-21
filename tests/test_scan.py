"""Tests for MetadataExtractor.scan_image.

Fixtures from conftest.py:
    extractor_tz_off  — timezone_var.get() returns False (GUI default)
    extractor_tz_on   — timezone_var.get() returns True
    make_jpeg         — EXIF-bearing JPEG factory
"""


def test_valid_image_with_exif_returns_true(extractor_tz_off, make_jpeg, tmp_path):
    make_jpeg("ok.jpg", datetime_original="2024:05:15 12:30:45")
    dates, images, offsets = [], [], []
    result = extractor_tz_off.scan_image(tmp_path, ["ok.jpg"], 0, dates, images, offsets)
    assert result is True
    assert dates == ["2024:05:15 12:30:45"]
    assert images == ["ok.jpg"]
    assert offsets == [None]


def test_image_missing_exif_returns_false(extractor_tz_off, make_jpeg, tmp_path):
    make_jpeg("no_exif.jpg")
    dates, images, offsets = [], [], []
    result = extractor_tz_off.scan_image(tmp_path, ["no_exif.jpg"], 0, dates, images, offsets)
    assert result is False
    assert "No Metadata" in extractor_tz_off.collected_warnings
    assert dates == [] and images == [] and offsets == []


def test_corrupt_file_returns_false(extractor_tz_off, tmp_path):
    (tmp_path / "bad.jpg").write_bytes(b"this is not a jpeg")
    dates, images, offsets = [], [], []
    result = extractor_tz_off.scan_image(tmp_path, ["bad.jpg"], 0, dates, images, offsets)
    assert result is False
    assert "Scan Error" in extractor_tz_off.collected_warnings


def test_prefers_datetime_original_over_others(extractor_tz_off, make_jpeg, tmp_path):
    make_jpeg("all_exif.jpg",
              datetime_original="2024:01:01 01:01:01",
              datetime_digitized="2024:02:02 02:02:02",
              datetime_general="2024:03:03 03:03:03")
    dates, images, offsets = [], [], []
    assert extractor_tz_off.scan_image(tmp_path, ["all_exif.jpg"], 0, dates, images, offsets)
    assert dates == ["2024:01:01 01:01:01"]


def test_falls_back_to_datetime_when_original_missing(extractor_tz_off, make_jpeg, tmp_path):
    make_jpeg("only_datetime.jpg", datetime_general="2024:03:03 03:03:03")
    dates, images, offsets = [], [], []
    assert extractor_tz_off.scan_image(tmp_path, ["only_datetime.jpg"], 0, dates, images, offsets)
    assert dates == ["2024:03:03 03:03:03"]


def test_falls_back_to_digitized_when_original_missing(extractor_tz_off, make_jpeg, tmp_path):
    make_jpeg("only_digitized.jpg", datetime_digitized="2024:02:02 02:02:02")
    dates, images, offsets = [], [], []
    assert extractor_tz_off.scan_image(tmp_path, ["only_digitized.jpg"], 0, dates, images, offsets)
    assert dates == ["2024:02:02 02:02:02"]


# ---------------------------------------------------------------------------
# Timezone-path regression coverage
# ---------------------------------------------------------------------------

def test_scan_image_timezone_off_does_not_crash(extractor_tz_off, make_jpeg, tmp_path):
    """Regression: `offset` was unbound when timezone_var.get() returned False.

    Requires .get.return_value = False (set by extractor_tz_off fixture) —
    with a truthy Mock this test would pass even with the bug present.
    """
    make_jpeg("t.jpg", datetime_original="2024:05:15 12:30:45")
    assert extractor_tz_off.timezone_var.get() is False
    dates, images, offsets = [], [], []
    result = extractor_tz_off.scan_image(tmp_path, ["t.jpg"], 0, dates, images, offsets)
    assert result is True
    assert offsets == [None]


def test_scan_image_captures_offset_when_timezone_on(extractor_tz_on, make_jpeg, tmp_path):
    make_jpeg("t.jpg",
              datetime_original="2024:05:15 12:30:45",
              offset_original="+05:30")
    dates, images, offsets = [], [], []
    assert extractor_tz_on.scan_image(tmp_path, ["t.jpg"], 0, dates, images, offsets)
    assert offsets == ["+05:30"]


def test_scan_image_missing_offset_when_timezone_on(extractor_tz_on, make_jpeg, tmp_path):
    make_jpeg("t.jpg", datetime_original="2024:05:15 12:30:45")
    dates, images, offsets = [], [], []
    assert extractor_tz_on.scan_image(tmp_path, ["t.jpg"], 0, dates, images, offsets)
    assert offsets == [None]