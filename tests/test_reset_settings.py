"""Tests for Reset Settings / Restore Defaults (v4.11.0)."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import metadata
from metadata import ScanConfig


def test_reset_settings_deletes_file_and_restores_all_defaults(extractor, tmp_path):
    src = tmp_path / "src"
    out = tmp_path / "out"
    src.mkdir()
    out.mkdir()

    extractor.directory_path = src
    extractor.output_path = out
    extractor.maxdepth = 3
    extractor.sort_method = "Date (Newest)"
    extractor._update_path_labels()

    extractor.hyperlink_var.set(False)
    extractor.include_undateable_var.set(False)
    for var in (
        extractor.keepopen_var,
        extractor.open_folder_var,
        extractor.recursive_var,
        extractor.summary_var,
        extractor.video_rows_var,
        extractor.hidden_var,
        extractor.utc_var,
        extractor.gps_var,
        extractor.gps_altitude_var,
        extractor.date_range_var,
        extractor.extra_exif_var,
        extractor.dimensions_var,
        extractor.filesize_var,
        extractor.make_var,
        extractor.model_var,
        extractor.software_var,
        extractor.lens_model_var,
        extractor.aperture_var,
        extractor.exposure_time_var,
        extractor.focal_length_var,
        extractor.iso_var,
        extractor.orientation_var,
        extractor.debug_var,
    ):
        var.set(True)

    extractor.filetype_var.set("JSON")
    extractor.user_mode_var.set("Advanced")
    extractor.sort_methods_var.set("Date (Newest)")
    extractor.media_filter_combobox.set("RAW Only")
    extractor.date_format_combobox.set("YYYY-MM-DD")
    extractor.time_format_combobox.set("12-Hour (hh:mm:ss AM/PM)")
    extractor.start_date_entry.set_date(date(2024, 1, 1))
    extractor.end_date_entry.set_date(date(2024, 12, 31))

    for entry, text in (
        (extractor.name_entry, "custom"),
        (extractor.modifier_entry, "5"),
        (extractor.maxdepth_entry, "3"),
        (extractor.burst_cutoff_entry, "10"),
    ):
        entry.delete(0, "end")
        entry.insert(0, text)

    extractor._save_settings()
    assert metadata.SETTINGS_PATH.exists()

    extractor.reset_settings()

    assert not metadata.SETTINGS_PATH.exists()
    assert extractor.directory_path is None
    assert extractor.output_path is None
    assert extractor.maxdepth == 0
    assert extractor.sort_method == "Timestamp"
    assert extractor.source_path_var.get() == "Source: Not set"
    assert extractor.output_path_var.get() == "Output: Not set"

    assert extractor.hyperlink_var.get() is True
    assert extractor.include_undateable_var.get() is True
    for var in (
        extractor.keepopen_var,
        extractor.open_folder_var,
        extractor.recursive_var,
        extractor.summary_var,
        extractor.video_rows_var,
        extractor.hidden_var,
        extractor.utc_var,
        extractor.gps_var,
        extractor.gps_altitude_var,
        extractor.date_range_var,
        extractor.extra_exif_var,
        extractor.dimensions_var,
        extractor.filesize_var,
        extractor.make_var,
        extractor.model_var,
        extractor.software_var,
        extractor.lens_model_var,
        extractor.aperture_var,
        extractor.exposure_time_var,
        extractor.focal_length_var,
        extractor.iso_var,
        extractor.orientation_var,
        extractor.debug_var,
    ):
        assert var.get() is False

    assert extractor.filetype_var.get() == "Excel"
    assert extractor.user_mode_var.get() == "Basic"
    assert extractor.sort_methods_var.get() == "Timestamp"
    assert extractor.media_filter_combobox.get() == "All Media"
    assert extractor.date_format_combobox.get() == "MM/DD/YYYY"
    assert extractor.time_format_combobox.get() == "24-Hour (HH:MM:SS)"
    assert extractor.start_date_entry.get_date() is None
    assert extractor.end_date_entry.get_date() is None

    assert extractor.name_entry.get() == "Filename (default output.filetype)"
    assert extractor.modifier_entry.get() == "Starting index (Img # Series)"
    assert extractor.maxdepth_entry.get() == "Recursion Depth (#)"
    assert extractor.burst_cutoff_entry.get() == "Photo grouping cutoff (default 2 seconds)"


def test_reset_settings_still_resets_ui_when_settings_file_missing(extractor, tmp_path):
    assert not metadata.SETTINGS_PATH.exists()

    extractor.directory_path = tmp_path
    extractor.user_mode_var.set("Advanced")
    extractor.filetype_var.set("CSV")
    extractor.utc_var.set(True)
    extractor.name_entry.delete(0, "end")
    extractor.name_entry.insert(0, "custom")

    extractor.reset_settings()

    assert extractor.directory_path is None
    assert extractor.user_mode_var.get() == "Basic"
    assert extractor.filetype_var.get() == "Excel"
    assert extractor.utc_var.get() is False
    assert extractor.name_entry.get() == "Filename (default output.filetype)"


def test_reset_settings_cancelled_by_user_keeps_file_and_state(extractor, monkeypatch):
    extractor.filetype_var.set("Markdown")
    extractor.utc_var.set(True)
    extractor._save_settings()
    assert metadata.SETTINGS_PATH.exists()

    monkeypatch.setattr(metadata.messagebox, "askyesno", lambda *a, **k: False)
    extractor.reset_settings()

    assert metadata.SETTINGS_PATH.exists()
    assert extractor.filetype_var.get() == "Markdown"
    assert extractor.utc_var.get() is True


def test_reset_settings_unlink_oserror_shows_error_and_leaves_state(extractor, monkeypatch, silence_messageboxes):
    extractor.utc_var.set(True)
    extractor._save_settings()

    def boom(self, missing_ok=False):
        raise OSError("locked")

    monkeypatch.setattr(Path, "unlink", boom)
    extractor.reset_settings()

    silence_messageboxes.showerror.assert_called_once()
    assert extractor.utc_var.get() is True


def test_start_scan_disables_and_clean_up_reenables_reset_settings_button(extractor, tmp_path):
    extractor.execute_button = MagicMock()
    extractor.cancel_button = MagicMock()
    extractor.set_directory_button = MagicMock()
    extractor.set_output_button = MagicMock()
    extractor.reset_settings_button = MagicMock()
    extractor.keepopen_var.set(True)

    cfg = ScanConfig(
        final_output=tmp_path / "out.xlsx",
        modifier=0,
        cutoff=2.0,
        date_range=False,
        date_format="%m/%d/%Y",
        time_format="%H:%M:%S",
        start_date=None,
        end_date=None,
        include_hiddens=False,
        include_undateable=True,
        media_filter="All Media",
        directory_path=tmp_path,
    )

    with patch("metadata.threading.Thread"):
        extractor._start_scan(cfg)

    extractor.reset_settings_button.config.assert_called_once_with(state="disabled")

    extractor._clean_up(cfg.final_output, 0, 0)
    extractor.reset_settings_button.config.assert_called_with(state="normal")