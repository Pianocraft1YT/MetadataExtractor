"""Tests for Exposure Bias and Focal Length (35mm) extraction and formatting (v5.1.0)."""

import json
from unittest.mock import patch

import pandas as pd
import pytest
from PIL.TiffImagePlugin import IFDRational

import metadata
from tests.conftest import make_jpeg_with_nested_exif
from tests.helpers import sort_scan


class _FakeRatio:
    def __init__(self, num, den):
        self.num = num
        self.den = den


class _FakeTag:
    def __init__(self, text, values=None):
        self._text = text
        self.values = values if values is not None else [text]

    def __str__(self):
        return self._text


# ---------------------------------------------------------------------------
# _format_exposure_bias unit tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ((7, 10), "+0.7 EV"),
        ((-3, 10), "-0.3 EV"),
        ((0, 1), "0 EV"),
        (0.0, "0 EV"),
        (-0.001, "0 EV"),
        ((33, 16), "+2.06 EV"),
        ((-10, 3), "-3.33 EV"),
        (None, None),
        ((5, 0), None),
        (float("nan"), None),
        (float("inf"), None),
        ("not-a-number", None),
    ],
)
def test_format_exposure_bias_values(extractor, raw, expected):
    assert extractor._format_exposure_bias(raw) == expected


# ---------------------------------------------------------------------------
# JPEG + RAW extraction
# ---------------------------------------------------------------------------


def test_jpeg_extracts_exposure_bias_and_35mm_focal_length(extractor, tmp_path):
    make_jpeg_with_nested_exif(
        tmp_path / "shot.jpg",
        exif_tags={
            36867: "2024:05:15 12:30:45",
            37380: IFDRational(-7, 10),
            41989: 26,
        },
    )

    processed, skipped = sort_scan(
        extractor,
        tmp_path,
        output_exposure_bias=True,
        output_focal_length_35mm=True,
        write=False,
    )

    assert (processed, skipped) == (1, 0)
    df = extractor.results[0][0]
    assert df["Exposure Bias"].iloc[0] == "-0.7 EV"
    assert df["Focal Length (35mm)"].iloc[0] == "26mm"


def test_raw_extracts_exposure_bias_and_35mm_focal_length(extractor, tmp_path, monkeypatch):
    monkeypatch.setattr(metadata, "RAW_SUPPORTED", True)
    (tmp_path / "shot.dng").write_bytes(b"fake-dng")

    fake_tags = {
        "EXIF DateTimeOriginal": _FakeTag("2024:05:15 12:30:45"),
        "EXIF ExposureBiasValue": _FakeTag("1/3", [_FakeRatio(1, 3)]),
        "EXIF FocalLengthIn35mmFilm": _FakeTag("35", [35]),
    }
    fake_mod = type("Mod", (), {"process_file": staticmethod(lambda f, details=False: fake_tags)})

    with patch("metadata.exifread", fake_mod, create=True):
        processed, skipped = sort_scan(
            extractor,
            tmp_path,
            output_exposure_bias=True,
            output_focal_length_35mm=True,
            write=False,
        )

    assert (processed, skipped) == (1, 0)
    df = extractor.results[0][0]
    assert df["Exposure Bias"].iloc[0] == "+0.33 EV"
    assert df["Focal Length (35mm)"].iloc[0] == "35mm"


def test_disabled_flags_omit_columns_and_store_none(extractor, tmp_path):
    make_jpeg_with_nested_exif(
        tmp_path / "shot.jpg",
        exif_tags={36867: "2024:05:15 12:30:45", 37380: IFDRational(1, 2), 41989: 50},
    )

    data = extractor._empty_scan_data()
    ok = extractor.scan_image(tmp_path, "shot.jpg", data)
    assert ok is True
    assert data["Exposure_Biases"] == [None]
    assert data["Focal_Lengths_35mm"] == [None]

    sort_scan(extractor, tmp_path, write=False)
    df = extractor.results[0][0]
    assert "Exposure Bias" not in df.columns
    assert "Focal Length (35mm)" not in df.columns


# ---------------------------------------------------------------------------
# Settings round-trip, initialize(), and CLI flags
# ---------------------------------------------------------------------------


def test_exposure_bias_and_35mm_settings_round_trip(extractor):
    extractor.exposure_bias_var.set(True)
    extractor.focal_length_35mm_var.set(True)
    extractor._save_settings()

    saved = json.loads(metadata.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert saved["Exposure Bias"] is True
    assert saved["Focal Length (35mm)"] is True

    extractor.exposure_bias_var.set(False)
    extractor.focal_length_35mm_var.set(False)
    extractor._load_settings()

    assert extractor.exposure_bias_var.get() is True
    assert extractor.focal_length_35mm_var.get() is True


def test_initialize_gates_exposure_bias_and_35mm_on_extra_exif(extractor, tmp_path):
    (tmp_path / "shot.jpg").write_bytes(b"fake")
    extractor.directory_path = tmp_path
    extractor.output_path = tmp_path
    captured = []
    extractor._start_scan = lambda cfg: captured.append((cfg.output_exposure_bias, cfg.output_focal_length_35mm))

    extractor.user_mode_var.set("Advanced")
    extractor.exposure_bias_var.set(True)
    extractor.focal_length_35mm_var.set(True)

    extractor.extra_exif_var.set(False)
    extractor.initialize()
    assert captured[-1] == (False, False)

    extractor.extra_exif_var.set(True)
    extractor.initialize()
    assert captured[-1] == (True, True)


def test_cli_flags_exposure_bias_and_35mm_and_all(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    make_jpeg_with_nested_exif(
        src / "shot.jpg",
        exif_tags={36867: "2024:05:15 12:30:45", 37380: IFDRational(-3, 10), 41989: 85},
    )

    out_ind = tmp_path / "ind.json"
    assert metadata.run_cli(["-i", str(src), "-o", str(out_ind), "-eb", "-fl35mm", "-q"]) == 0
    row_ind = json.loads(out_ind.read_text(encoding="utf-8"))["sheets"]["Sheet"][0]
    assert row_ind["Exposure Bias"] == "-0.3 EV"
    assert row_ind["Focal Length (35mm)"] == "85mm"
    assert "Camera Make" not in row_ind

    out_all = tmp_path / "all.json"
    assert metadata.run_cli(["-i", str(src), "-o", str(out_all), "-a", "-q"]) == 0
    row_all = json.loads(out_all.read_text(encoding="utf-8"))["sheets"]["Sheet"][0]
    assert row_all["Exposure Bias"] == "-0.3 EV"
    assert row_all["Focal Length (35mm)"] == "85mm"
