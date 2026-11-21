"""Tests for optional HEIC/HEIF support via pillow-heif."""

from datetime import date, datetime
from unittest.mock import patch

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


class _FakeExif:
    def __init__(self, ifd0=None, exif_subifd=None, gps_subifd=None):
        self._ifd0 = ifd0 or {}
        self._subifds = {
            0x8769: exif_subifd or {},
            0x8825: gps_subifd or {},
        }

    def get(self, tag, default=None):
        return self._ifd0.get(tag, default)

    def get_ifd(self, tag):
        return self._subifds.get(tag, {})


class _FakeHeifImage:
    def __init__(self, size=(4000, 3000), ifd0=None, exif_subifd=None, gps_subifd=None):
        self.size = size
        self._exif = _FakeExif(ifd0=ifd0, exif_subifd=exif_subifd, gps_subifd=gps_subifd)

    def getexif(self):
        return self._exif

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_heif_supported_flag_and_extensions_present():
    assert isinstance(metadata.HEIF_SUPPORTED, bool)
    assert ".heic" in metadata.PHOTO_TYPES
    assert ".heif" in metadata.PHOTO_TYPES


# ---------------------------------------------------------------------------
# HEIF_SUPPORTED = False
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", ["shot.heic", "shot.HEIC", "shot.heif", "shot.HEIF"])
def test_read_photo_entry_without_pillow_heif_returns_clear_error(extractor, tmp_path, monkeypatch, filename):
    monkeypatch.setattr(metadata, "HEIF_SUPPORTED", False)
    path = tmp_path / filename
    path.write_bytes(b"fake-heic-bytes")

    with patch("metadata.Image.open") as mock_open:
        dt, has_time, offset, fields, err = extractor._read_photo_entry(path, _ALL_FLAGS_OFF)

    mock_open.assert_not_called()
    assert dt is None
    assert has_time is False
    assert offset is None
    assert fields is None
    assert err == "HEIC/HEIF requires pillow-heif"


def test_scan_image_heif_unsupported_logs_scan_error_and_skips(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "HEIF_SUPPORTED", False)
    (tmp_path / "iphone.heic").write_bytes(b"fake-heic-bytes")

    data = extractor._empty_scan_data()
    ok = extractor.scan_image(tmp_path, "iphone.heic", data, **_EXTRA_OFF)

    assert ok is False
    assert data["Images"] == []
    assert "Scan Error" in extractor.collected_warnings
    assert len(extractor.collected_warnings["Scan Error"]) == 1
    assert "HEIC/HEIF requires pillow-heif" in extractor.collected_warnings["Scan Error"][0]


def test_non_heif_jpeg_unaffected_when_heif_unsupported(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "HEIF_SUPPORTED", False)
    make_jpeg_with_exif(tmp_path / "normal.jpg", "2024:05:15 12:30:45")

    data = extractor._empty_scan_data()
    ok = extractor.scan_image(tmp_path, "normal.jpg", data, **_EXTRA_OFF)

    assert ok is True
    assert data["Images"] == ["normal.jpg"]


def test_mixed_folder_with_heic_does_not_abort_when_heif_unsupported(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "HEIF_SUPPORTED", False)
    make_jpeg_with_exif(tmp_path / "a.jpg", "2024:05:15 12:30:45")
    (tmp_path / "b.heic").write_bytes(b"fake-heic-bytes")

    processed, skipped = sort_scan(extractor, tmp_path, write=False)

    assert (processed, skipped) == (1, 1)
    assert len(extractor.results) == 1
    assert list(extractor.results[0][0]["Files"]) == ["a.jpg"]
    assert any("HEIC/HEIF requires pillow-heif" in w for w in extractor.collected_warnings["Scan Error"])


def test_date_range_excluding_undateable_drops_unsupported_heic_without_warning(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "HEIF_SUPPORTED", False)
    make_jpeg_with_exif(tmp_path / "a.jpg", "2024:05:15 12:30:45")
    (tmp_path / "b.heic").write_bytes(b"fake-heic-bytes")

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
# HEIF_SUPPORTED = True (mocked Pillow Image.open)
# ---------------------------------------------------------------------------


def test_read_photo_entry_with_heif_supported_extracts_subifd_and_gps(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "HEIF_SUPPORTED", True)
    path = tmp_path / "iphone.HEIC"
    path.write_bytes(b"fake-heic-bytes")

    fake_img = _FakeHeifImage(
        size=(4032, 3024),
        ifd0={271: "Apple", 272: "iPhone 15 Pro", 305: "17.4"},
        exif_subifd={
            36867: "2024:05:15 12:30:45",
            36881: "-07:00",
            33437: (178, 100),
            33434: (1, 500),
            37386: (24, 1),
            34855: 100,
            42036: "iPhone 15 Pro back triple camera 6.765mm f/1.78",
        },
        gps_subifd={
            1: "N",
            2: (37.0, 46.0, 30.0),
            3: "W",
            4: (122.0, 25.0, 0.0),
        },
    )

    with patch("metadata.Image.open", return_value=fake_img) as mock_open:
        dt, has_time, offset, fields, err = extractor._read_photo_entry(path, _ALL_FLAGS_ON)

    mock_open.assert_called_once_with(path)
    assert err is None
    assert dt == datetime(2024, 5, 15, 12, 30, 45)
    assert has_time is True
    assert offset == "-07:00"
    assert fields["Dimensions"] == "4032x3024"
    assert fields["Makes"] == "Apple"
    assert fields["Models"] == "iPhone 15 Pro"
    assert fields["Softwares"] == "17.4"
    assert fields["Apertures"] == "f/1.78"
    assert fields["Exposure_Times"] == "1/500"
    assert fields["Focal_Lengths"] == "24mm"
    assert fields["ISOs"] == 100
    assert fields["GPS_Latitudes"] == "37.775000"
    assert fields["GPS_Longitudes"] == "-122.416667"


def test_end_to_end_sort_scan_with_heif_supported(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "HEIF_SUPPORTED", True)
    (tmp_path / "IMG_001.heic").write_bytes(b"fake-heic-1")
    (tmp_path / "IMG_002.heif").write_bytes(b"fake-heif-2")

    fake_1 = _FakeHeifImage(exif_subifd={36867: "2024:05:15 12:30:45"})
    fake_2 = _FakeHeifImage(exif_subifd={36867: "2024:05:15 12:30:46"})

    def fake_open(fp, *args, **kwargs):
        return fake_1 if fp.name == "IMG_001.heic" else fake_2

    with patch("metadata.Image.open", side_effect=fake_open):
        processed, skipped = sort_scan(extractor, tmp_path, write=False)

    assert (processed, skipped) == (2, 0)
    assert len(extractor.results) == 1
    df = extractor.results[0][0]
    assert list(df["Files"]) == ["IMG_001.heic", "IMG_002.heif"]
    assert list(df["Dates"]) == ["05/15/2024", "05/15/2024"]
    assert list(df["Time"]) == ["12:30:45", "12:30:46"]
    assert list(df["Img # Series"]) == ["1-2", "1-2"]
