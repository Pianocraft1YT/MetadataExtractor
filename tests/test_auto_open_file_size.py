"""Tests for v4.1.0 features: File Size metadata and Auto-Open Output Folder."""

import json
import os
import subprocess
import sys
from unittest.mock import patch

import pandas as pd
import pytest

import metadata
from tests.conftest import make_jpeg_with_exif
from tests.helpers import sort_scan

# ---------------------------------------------------------------------------
# _convert_filesize
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "num_bytes,expected",
    [
        (-5, "0 B"),
        (0, "0 B"),
        (512, "512 B"),
        (999, "999 B"),
        (1000, "1.0 KB"),
        (1500, "1.5 KB"),
        (4_500_000, "4.5 MB"),
        (1_200_000_000, "1.2 GB"),
        (2_500_000_000_000, "2.5 TB"),
        (1_000_000_000_000_000, "1.0 PB"),
    ],
)
def test_convert_filesize_units(extractor, num_bytes, expected):
    assert extractor._convert_filesize(num_bytes) == expected


def test_scan_image_filesize_enabled_and_disabled(extractor, tmp_path):
    path = tmp_path / "shot.jpg"
    make_jpeg_with_exif(path, "2024:05:15 12:30:45")
    expected_size = extractor._convert_filesize(os.path.getsize(path))

    data_on = extractor._empty_scan_data()
    ok_on = extractor.scan_image(
        tmp_path,
        "shot.jpg",
        data_on,
        False,
        False,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    )
    assert ok_on is True
    assert data_on["Filesizes"] == [expected_size]

    data_off = extractor._empty_scan_data()
    ok_off = extractor.scan_image(
        tmp_path,
        "shot.jpg",
        data_off,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    )
    assert ok_off is True
    assert data_off["Filesizes"] == [None]


def test_end_to_end_filesize_column_written(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "shot.jpg", "2024:05:15 12:30:45")
    sort_scan(extractor, tmp_path, output_filesize=True, write=False)
    df = extractor.results[0][0]
    assert "File Size" in df.columns
    assert df["File Size"].iloc[0].endswith(" B") or df["File Size"].iloc[0].endswith(" KB")


# ---------------------------------------------------------------------------
# _open_path & create_sheet integration
# _open_path & create_sheet integration
# ---------------------------------------------------------------------------


def test_open_path_windows_uses_startfile(tmp_path, monkeypatch):
def test_open_path_windows_uses_startfile(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    target = tmp_path / "out.xlsx"
    target.write_bytes(b"data")
    with patch("metadata.os.startfile", create=True) as mock_start:
        metadata.MetadataExtractor._open_path(target, True)
    mock_start.assert_called_once_with(tmp_path)


def test_open_path_macos_uses_open(tmp_path, monkeypatch):
def test_open_path_macos_uses_open(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(sys, "platform", "darwin")
    with patch("subprocess.Popen") as mock_popen:
        metadata.MetadataExtractor._open_path(tmp_path, True)
    mock_popen.assert_called_once_with(["open", str(tmp_path)])


def test_open_path_linux_uses_xdg_open(tmp_path, monkeypatch):
def test_open_path_linux_uses_xdg_open(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(sys, "platform", "linux")
    with patch("subprocess.Popen") as mock_popen:
        metadata.MetadataExtractor._open_path(tmp_path, True)
    mock_popen.assert_called_once_with(["xdg-open", str(tmp_path)])


def test_open_path_missing_path_no_op(tmp_path, monkeypatch):
def test_open_path_missing_path_no_op(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    missing = tmp_path / "does_not_exist" / "out.xlsx"
    with patch("metadata.os.startfile", create=True) as mock_start:
        metadata.MetadataExtractor._open_path(missing, True)
    mock_start.assert_not_called()


def test_open_path_swallows_oserror(tmp_path, monkeypatch):
def test_open_path_swallows_oserror(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    with patch("metadata.os.startfile", side_effect=OSError("boom"), create=True):
        metadata.MetadataExtractor._open_path(tmp_path, True)  # must not raise


@pytest.mark.real_create_sheet
def test_create_sheet_opens_folder_only_when_enabled(extractor, tmp_path):
    df = pd.DataFrame({"Files": ["a.jpg"], "Dates": ["01/01/2024"], "Time": ["12:00:00"], "Img # Series": ["1"]})
    extractor.hyperlink_var.set(False)
    extractor.keepopen_var.set(True)
    extractor.results.append((df, "Sheet", tmp_path))
    output = tmp_path / "out.xlsx"

    extractor.open_folder_var.set(False)
    with patch.object(extractor, "_open_path") as mock_open:
    with patch.object(extractor, "_open_path") as mock_open:
        extractor.create_sheet(output, 1, 0)
    mock_open.assert_not_called()

    extractor.open_folder_var.set(True)
    with patch.object(extractor, "_open_path") as mock_open:
    with patch.object(extractor, "_open_path") as mock_open:
        extractor.create_sheet(output, 1, 0)
    mock_open.assert_called_once_with(output, True)


# ---------------------------------------------------------------------------
# Settings persistence for v4.1.0 keys
# ---------------------------------------------------------------------------


def test_v4_1_0_settings_round_trip(extractor):
    extractor.open_folder_var.set(True)
    extractor.filesize_var.set(True)
    extractor._save_settings()

    saved = json.loads(metadata.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert saved["Auto-Open Output"] is True
    assert saved["Filesize"] is True

    extractor.open_folder_var.set(False)
    extractor.filesize_var.set(False)
    extractor._load_settings()

    assert extractor.open_folder_var.get() is True
    assert extractor.filesize_var.get() is True
