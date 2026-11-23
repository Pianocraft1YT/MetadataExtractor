"""Tests for optional Camera RAW EXIF support via exifread."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

import metadata
from tests.conftest import make_jpeg_with_exif
from tests.helpers import find_scan, sort_scan

_ALL_FLAGS_OFF = (False,) * 12
_ALL_FLAGS_ON = (True,) * 12

_EXTRA_OFF = dict(
    output_utc=False,
    output_dimensions=False,
    output_filesize=False,
    output_make=False,
    output_model=False,
    output_software=False,
    output_lens_model=False,
    output_aperture=False,
    output_exposure_time=False,
    output_focal_length=False,
    output_iso=False,
    output_gps=False,
)


class _FakeRatio:
    def __init__(self, num, den):
        self.num = num
        self.den = den


class _FakeTag:
    def __init__(self, text, values=None):
        self._text = text
        self.values = values if values is not None else [text]

    @property
    def printable(self):
        return self._text

    def __str__(self):
        return self._text


def _mock_exifread_module(tags_or_side_effect):
    mod = MagicMock()
    if callable(tags_or_side_effect):
        mod.process_file.side_effect = tags_or_side_effect
    else:
        mod.process_file.return_value = tags_or_side_effect
    return mod


def test_raw_supported_flag_and_extensions_present():
    assert isinstance(metadata.RAW_SUPPORTED, bool)
    for ext in (".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".rw2"):
        assert ext in metadata.RAW_TYPES
    assert set(metadata.RAW_TYPES).issubset(set(metadata.PHOTO_TYPES))


# ---------------------------------------------------------------------------
# RAW_SUPPORTED = False
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", ["shot.dng", "shot.DNG", "shot.cr2", "shot.nef", "shot.arw"])
def test_read_photo_entry_without_exifread_returns_clear_error(extractor, tmp_path, monkeypatch, filename):
    monkeypatch.setattr(metadata, "RAW_SUPPORTED", False)
    path = tmp_path / filename
    path.write_bytes(b"fake-raw-bytes")

    with patch("metadata.Image.open") as mock_open:
        dt, has_time, offset, fields, err = extractor._read_photo_entry(path, _ALL_FLAGS_OFF)

    mock_open.assert_not_called()
    assert dt is None
    assert has_time is False
    assert offset is None
    assert fields is None
    assert err == "RAW files require exifread"


def test_scan_image_raw_unsupported_logs_scan_error_and_skips(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "RAW_SUPPORTED", False)
    (tmp_path / "shot.cr2").write_bytes(b"fake-raw-bytes")

    data = extractor._empty_scan_data()
    ok = extractor.scan_image(tmp_path, "shot.cr2", data, **_EXTRA_OFF)

    assert ok is False
    assert data["Images"] == []
    assert "Scan Error" in extractor.collected_warnings
    assert "RAW files require exifread" in extractor.collected_warnings["Scan Error"][0]


def test_non_raw_jpeg_unaffected_when_raw_unsupported(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "RAW_SUPPORTED", False)
    make_jpeg_with_exif(tmp_path / "normal.jpg", "2024:05:15 12:30:45")

    data = extractor._empty_scan_data()
    ok = extractor.scan_image(tmp_path, "normal.jpg", data, **_EXTRA_OFF)

    assert ok is True
    assert data["Images"] == ["normal.jpg"]


def test_mixed_folder_with_raw_does_not_abort_when_raw_unsupported(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "RAW_SUPPORTED", False)
    make_jpeg_with_exif(tmp_path / "a.jpg", "2024:05:15 12:30:45")
    (tmp_path / "b.nef").write_bytes(b"fake-raw-bytes")

    processed, skipped = sort_scan(extractor, tmp_path, write=False)

    assert (processed, skipped) == (1, 1)
    assert list(extractor.results[0][0]["Files"]) == ["a.jpg"]
    assert any("RAW files require exifread" in w for w in extractor.collected_warnings["Scan Error"])


def test_date_range_excluding_undateable_drops_unsupported_raw_without_warning(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "RAW_SUPPORTED", False)
    make_jpeg_with_exif(tmp_path / "a.jpg", "2024:05:15 12:30:45")
    (tmp_path / "b.dng").write_bytes(b"fake-raw-bytes")

    extractor.maxdepth = 0
    processed, skipped = find_scan(
        extractor,
        tmp_path,
        date_range=True,
        start_date=date(2024, 5, 1),
        end_date=date(2024, 5, 31),
        include_undateable=False,
        write=False,
    )

    assert (processed, skipped) == (1, 0)
    assert "Scan Error" not in extractor.collected_warnings


# ---------------------------------------------------------------------------
# RAW_SUPPORTED = True (mocked exifread.process_file)
# ---------------------------------------------------------------------------


def test_read_photo_entry_raw_extracts_all_tags_and_bypasses_pillow(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "RAW_SUPPORTED", True)
    path = tmp_path / "camera.DNG"
    path.write_bytes(b"fake-dng-bytes")

    fake_tags = {
        "EXIF DateTimeOriginal": _FakeTag("2024:05:15 12:30:45"),
        "EXIF OffsetTimeOriginal": _FakeTag("+02:00"),
        "EXIF ExifImageWidth": _FakeTag("6000", [6000]),
        "EXIF ExifImageLength": _FakeTag("4000", [4000]),
        "Image Make": _FakeTag("SONY\x00\x00"),
        "Image Model": _FakeTag("ILCE-7M4"),
        "Image Software": _FakeTag("ILCE-7M4 v2.00"),
        "EXIF LensModel": _FakeTag("FE 50mm F1.8"),
        "EXIF FNumber": _FakeTag("14/5", [_FakeRatio(28, 10)]),
        "EXIF ExposureTime": _FakeTag("1/500", [_FakeRatio(1, 500)]),
        "EXIF FocalLength": _FakeTag("50", [_FakeRatio(50, 1)]),
        "EXIF ISOSpeedRatings": _FakeTag("200", [200]),
        "GPS GPSLatitudeRef": _FakeTag("N"),
        "GPS GPSLatitude": _FakeTag("[48, 51, 24]", [_FakeRatio(48, 1), _FakeRatio(51, 1), _FakeRatio(24, 1)]),
        "GPS GPSLongitudeRef": _FakeTag("E"),
        "GPS GPSLongitude": _FakeTag("[2, 21, 7]", [_FakeRatio(2, 1), _FakeRatio(21, 1), _FakeRatio(7, 1)]),
    }
    fake_mod = _mock_exifread_module(fake_tags)

    with (
        patch("metadata.exifread", fake_mod, create=True),
        patch("metadata.Image.open") as mock_open,
    ):
        dt, has_time, offset, fields, err = extractor._read_photo_entry(path, _ALL_FLAGS_ON)

    mock_open.assert_not_called()
    fake_mod.process_file.assert_called_once()
    assert err is None
    assert dt == datetime(2024, 5, 15, 12, 30, 45)
    assert has_time is True
    assert offset == "+02:00"
    assert fields["Dimensions"] == "6000x4000"
    assert fields["Makes"] == "SONY"
    assert fields["Models"] == "ILCE-7M4"
    assert fields["Softwares"] == "ILCE-7M4 v2.00"
    assert fields["Lens_Models"] == "FE 50mm F1.8"
    assert fields["Apertures"] == "f/2.8"
    assert fields["Exposure_Times"] == "1/500"
    assert fields["Focal_Lengths"] == "50mm"
    assert fields["ISOs"] == 200
    assert fields["GPS_Latitudes"] == "48.856667"
    assert fields["GPS_Longitudes"] == "2.351944"


def test_raw_datetime_pairs_with_matching_offset_and_hex_fallback(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "RAW_SUPPORTED", True)
    path = tmp_path / "edited.cr2"
    path.write_bytes(b"fake-cr2")

    # DateTimeOriginal without OffsetTimeOriginal must not borrow Image DateTime's OffsetTime
    tags_no_pair = {
        "EXIF DateTimeOriginal": _FakeTag("2024:05:15 10:00:00"),
        "Image DateTime": _FakeTag("2024:05:20 18:00:00"),
        "EXIF OffsetTime": _FakeTag("-04:00"),
    }
    with patch("metadata.exifread", _mock_exifread_module(tags_no_pair), create=True):
        dt, _, offset, _, err = extractor._read_photo_entry(path, None)
    assert err is None
    assert dt == datetime(2024, 5, 15, 10, 0, 0)
    assert offset is None

    # Fallback hex tag 0x9011 works for OffsetTimeOriginal
    tags_hex_offset = {
        "EXIF DateTimeOriginal": _FakeTag("2024:05:15 10:00:00"),
        "EXIF Tag 0x9011": _FakeTag("+09:00"),
    }
    with patch("metadata.exifread", _mock_exifread_module(tags_hex_offset), create=True):
        dt2, _, offset2, _, err2 = extractor._read_photo_entry(path, None)
    assert err2 is None
    assert dt2 == datetime(2024, 5, 15, 10, 0, 0)
    assert offset2 == "+09:00"


def test_raw_empty_tags_zero_den_and_image_width_fallback(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "RAW_SUPPORTED", True)

    empty_path = tmp_path / "stripped.x3f"
    empty_path.write_bytes(b"fake")
    with patch("metadata.exifread", _mock_exifread_module({}), create=True):
        dt, has_time, offset, fields, err = extractor._read_photo_entry(empty_path, _ALL_FLAGS_ON)
    assert err is None
    assert dt is None
    assert has_time is False
    assert offset is None
    assert fields["ISOs"] == ""
    assert fields["Dimensions"] is None

    fallback_path = tmp_path / "shot.nef"
    fallback_path.write_bytes(b"fake")
    tags = {
        "EXIF DateTimeOriginal": _FakeTag("2024:05:15 12:00:00"),
        "Image ImageWidth": _FakeTag("4000", [4000]),
        "Image ImageLength": _FakeTag("3000", [3000]),
        "EXIF FNumber": _FakeTag("5/0", [_FakeRatio(5, 0)]),
    }
    with patch("metadata.exifread", _mock_exifread_module(tags), create=True):
        _, _, _, fields2, err2 = extractor._read_photo_entry(fallback_path, _ALL_FLAGS_ON)
    assert err2 is None
    assert fields2["Dimensions"] == "4000x3000"
    assert fields2["Apertures"] is None


def test_raw_reader_exception_logs_scan_error(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "RAW_SUPPORTED", True)
    (tmp_path / "broken.arw").write_bytes(b"corrupt")

    def boom(*args, **kwargs):
        raise OSError("corrupt header")

    data = extractor._empty_scan_data()
    with patch("metadata.exifread", _mock_exifread_module(boom), create=True):
        ok = extractor.scan_image(tmp_path, "broken.arw", data, **_EXTRA_OFF)

    assert ok is False
    assert "Scan Error" in extractor.collected_warnings
    assert "corrupt header" in extractor.collected_warnings["Scan Error"][0]


def test_end_to_end_sort_scan_with_raw_supported(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "RAW_SUPPORTED", True)
    (tmp_path / "RAW_001.cr2").write_bytes(b"raw-1")
    (tmp_path / "RAW_002.cr2").write_bytes(b"raw-2")

    tags_1 = {
        "EXIF DateTimeOriginal": _FakeTag("2024:05:15 12:30:45"),
        "EXIF ISOSpeedRatings": _FakeTag("400", [400]),
    }
    tags_2 = {
        "EXIF DateTimeOriginal": _FakeTag("2024:05:15 12:30:46"),
    }

    def fake_process(fh, details=False):
        return tags_1 if fh.name.endswith("RAW_001.cr2") else tags_2

    with patch("metadata.exifread", _mock_exifread_module(fake_process), create=True):
        processed, skipped = sort_scan(extractor, tmp_path, output_iso=True, write=False)

    assert (processed, skipped) == (2, 0)
    df = extractor.results[0][0]
    assert list(df["Files"]) == ["RAW_001.cr2", "RAW_002.cr2"]
    assert list(df["Dates"]) == ["05/15/2024", "05/15/2024"]
    assert list(df["Time"]) == ["12:30:45", "12:30:46"]
    assert list(df["Img # Series"]) == ["1-2", "1-2"]
    assert df.loc[0, "ISO"] == 400
    assert df.loc[1, "ISO"] == ""
