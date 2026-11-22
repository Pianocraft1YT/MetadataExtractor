"""Tests for selected Source/Output path labels, _open_path, and View warnings.log."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

import metadata

# ---------------------------------------------------------------------------
# _format_path_label & _update_path_labels
# ---------------------------------------------------------------------------


def test_format_path_label_none(extractor):
    assert extractor._format_path_label("Source", None) == "Source: Not set"
    assert extractor._format_path_label("Output", None) == "Output: Not set"


def test_format_path_label_short_path_not_truncated(extractor):
    short = Path("photos/trip")
    assert extractor._format_path_label("Source", short) == "Source: photos/trip"


def test_format_path_label_long_path_truncated(extractor):
    long_path = Path("a" * 30) / ("b" * 30)
    formatted = extractor._format_path_label("Source", long_path)
    assert formatted == f"Source: ...{long_path.as_posix()[-47:]}"
    assert len(formatted) == len("Source: ") + 50


def test_init_defaults_path_labels_to_not_set(extractor):
    assert extractor.source_path_var.get() == "Source: Not set"
    assert extractor.output_path_var.get() == "Output: Not set"


def test_init_loads_saved_paths_into_labels(tmp_path):
    src = tmp_path / "src"
    out = tmp_path / "out"
    src.mkdir()
    out.mkdir()
    metadata.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    metadata.SETTINGS_PATH.write_text(
        json.dumps({"Directory Path": src.as_posix(), "Output Path": out.as_posix()}),
        encoding="utf-8",
    )

    fresh = metadata.MetadataExtractor()

    assert fresh.source_path_var.get() == fresh._format_path_label("Source", src)
    assert fresh.output_path_var.get() == fresh._format_path_label("Output", out)


def test_set_dir_updates_source_label_and_cancel_preserves_it(extractor, tmp_path):
    chosen = tmp_path / "pics"
    chosen.mkdir()

    with patch("metadata.filedialog.askdirectory", return_value=str(chosen)):
        extractor.set_dir()
    assert extractor.directory_path == chosen
    assert extractor.source_path_var.get() == extractor._format_path_label("Source", chosen)

    with patch("metadata.filedialog.askdirectory", return_value=""):
        extractor.set_dir()
    assert extractor.directory_path == chosen
    assert extractor.source_path_var.get() == extractor._format_path_label("Source", chosen)


def test_set_output_updates_output_label_and_cancel_preserves_it(extractor, tmp_path):
    chosen = tmp_path / "exports"
    chosen.mkdir()

    with patch("metadata.filedialog.askdirectory", return_value=str(chosen)):
        extractor.set_output()
    assert extractor.output_path == chosen
    assert extractor.output_path_var.get() == extractor._format_path_label("Output", chosen)

    with patch("metadata.filedialog.askdirectory", return_value=""):
        extractor.set_output()
    assert extractor.output_path == chosen
    assert extractor.output_path_var.get() == extractor._format_path_label("Output", chosen)


# ---------------------------------------------------------------------------
# _open_path (file vs parent directory)
# ---------------------------------------------------------------------------


def test_open_path_file_opens_file_not_parent_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    log_file = tmp_path / "warnings.log"
    log_file.write_text("warn", encoding="utf-8")

    with patch("metadata.os.startfile", create=True) as mock_start:
        metadata.MetadataExtractor._open_path(log_file, open_parent=False)
    mock_start.assert_called_once_with(log_file)


def test_open_path_open_parent_true_opens_directory_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    target = tmp_path / "out.xlsx"
    target.write_bytes(b"data")

    with patch("metadata.os.startfile", create=True) as mock_start:
        metadata.MetadataExtractor._open_path(target, open_parent=True)
    mock_start.assert_called_once_with(tmp_path)


def test_open_path_file_macos_and_linux(tmp_path, monkeypatch):
    log_file = tmp_path / "warnings.log"
    log_file.write_text("warn", encoding="utf-8")
    monkeypatch.setattr(os, "name", "posix")

    monkeypatch.setattr(sys, "platform", "darwin")
    with patch("subprocess.Popen") as mock_popen:
        metadata.MetadataExtractor._open_path(log_file, open_parent=False)
    mock_popen.assert_called_once_with(["open", str(log_file)])

    monkeypatch.setattr(sys, "platform", "linux")
    with patch("subprocess.Popen") as mock_popen:
        metadata.MetadataExtractor._open_path(log_file, open_parent=False)
    mock_popen.assert_called_once_with(["xdg-open", str(log_file)])


def test_open_path_missing_no_op_and_swallows_oserror(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    missing = tmp_path / "missing.log"
    with patch("metadata.os.startfile", create=True) as mock_start:
        metadata.MetadataExtractor._open_path(missing, open_parent=False)
    mock_start.assert_not_called()

    existing = tmp_path / "warnings.log"
    existing.write_text("warn", encoding="utf-8")
    with patch("metadata.os.startfile", side_effect=OSError("boom"), create=True):
        metadata.MetadataExtractor._open_path(existing, open_parent=False)


# ---------------------------------------------------------------------------
# View warnings.log button lifecycle & handler
# ---------------------------------------------------------------------------


def test_reset_clears_last_warnings_log_and_disables_button(extractor, tmp_path):
    extractor.last_warnings_log = tmp_path / "warnings.log"
    extractor.view_log_button.config.reset_mock()

    extractor.reset()

    assert extractor.last_warnings_log is None
    extractor.view_log_button.config.assert_called_once_with(state="disabled")


@pytest.mark.real_create_sheet
def test_create_sheet_enables_view_log_button_when_warnings_written(extractor, tmp_path):
    df = pd.DataFrame({"Files": ["a.jpg"], "Dates": ["01/01/2024"], "Time": ["12:00:00"], "Img # Series": ["1"]})
    extractor.results.append((df, "Sheet", tmp_path))
    extractor.collected_warnings["No Metadata"].append("a.jpg")
    extractor.hyperlink_var.set(False)
    extractor.keepopen_var.set(True)
    extractor.view_log_button.config.reset_mock()
    output = tmp_path / "out.xlsx"

    extractor.create_sheet(output, 1, 0)

    expected_log = tmp_path / "warnings.log"
    assert expected_log.is_file()
    assert extractor.last_warnings_log == expected_log
    extractor.view_log_button.config.assert_called_once_with(state="normal")


@pytest.mark.real_create_sheet
def test_create_sheet_no_warnings_keeps_view_log_button_disabled(extractor, tmp_path):
    df = pd.DataFrame({"Files": ["a.jpg"], "Dates": ["01/01/2024"], "Time": ["12:00:00"], "Img # Series": ["1"]})
    extractor.results.append((df, "Sheet", tmp_path))
    extractor.hyperlink_var.set(False)
    extractor.keepopen_var.set(True)
    extractor.view_log_button.config.reset_mock()

    extractor.create_sheet(tmp_path / "out.xlsx", 1, 0)

    assert not (tmp_path / "warnings.log").exists()
    assert extractor.last_warnings_log is None
    extractor.view_log_button.config.assert_not_called()


@pytest.mark.real_create_sheet
def test_create_sheet_log_write_oserror_does_not_enable_view_log_button(extractor, tmp_path):
    df = pd.DataFrame({"Files": ["a.jpg"], "Dates": ["01/01/2024"], "Time": ["12:00:00"], "Img # Series": ["1"]})
    extractor.results.append((df, "Sheet", tmp_path))
    extractor.collected_warnings["Scan Error"].append("bad.jpg")
    extractor.hyperlink_var.set(False)
    extractor.keepopen_var.set(True)
    extractor.view_log_button.config.reset_mock()

    with patch.object(Path, "write_text", side_effect=OSError("read-only")):
        extractor.create_sheet(tmp_path / "out.xlsx", 1, 0)

    assert extractor.last_warnings_log is None
    extractor.view_log_button.config.assert_not_called()


def test_view_warnings_log_opens_existing_file(extractor, tmp_path):
    log_file = tmp_path / "warnings.log"
    log_file.write_text("Scan Error\nbad.jpg\n", encoding="utf-8")
    extractor.last_warnings_log = log_file

    with patch.object(extractor, "_open_path") as mock_open:
        extractor._view_warnings_log()

    mock_open.assert_called_once_with(log_file, False)


def test_view_warnings_log_missing_shows_info_dialog(extractor, tmp_path, monkeypatch):
    infos = []
    monkeypatch.setattr(metadata.messagebox, "showinfo", lambda title, **kw: infos.append(title))
    extractor.last_warnings_log = tmp_path / "deleted_warnings.log"

    with patch.object(extractor, "_open_path") as mock_open:
        extractor._view_warnings_log()

    mock_open.assert_not_called()
    assert infos == ["Log file not found."]
