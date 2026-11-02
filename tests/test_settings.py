"""Tests for settings persistence (_save_settings / _load_settings)."""

import json
from datetime import date

import pytest

import metadata

_EXTRA_OFF = dict(
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
    output_gps=False,
    date_range=False,
    start_date=None,
    end_date=None,
)


# ---------------------------------------------------------------------------
# Save side
# ---------------------------------------------------------------------------


def test_save_creates_file_and_parent_dir(extractor):
    assert not metadata.SETTINGS_PATH.exists()
    extractor._save_settings()
    assert metadata.SETTINGS_PATH.exists()
    assert metadata.SETTINGS_PATH.parent.exists()


def test_save_produces_valid_json(extractor):
    extractor._save_settings()
    data = json.loads(metadata.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    # All 15 booleans are present as keys
    for key in (
        "Keep Open",
        "Recursive",
        "UTC",
        "Hyperlinks",
        "Date Range",
        "Extra EXIF",
        "Dimensions",
        "Make",
        "Model",
        "Software",
        "Lens Model",
        "Aperture",
        "Exposure Time",
        "Focal Length",
        "ISO",
    ):
        assert key in data
        assert isinstance(data[key], bool)


def test_save_does_not_include_debug_var(extractor):
    """Debug mode must never be persisted — it redirects output to
    ~/Downloads and disables the irregular-pattern check. Persisting it
    would trap the user in debug mode forever."""
    extractor.debug_var.set(True)
    extractor._save_settings()
    data = json.loads(metadata.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert "Debug" not in data
    assert "Debug Mode" not in data
    assert "debug" not in data


# ---------------------------------------------------------------------------
# Round-trip: booleans
# ---------------------------------------------------------------------------


def test_boolean_round_trip_restores_truthy(extractor):
    extractor.keepopen_var.set(True)
    extractor.recursive_var.set(True)
    extractor.hyperlink_var.set(False)  # default True — set to False to prove override
    extractor.dimensions_var.set(True)
    extractor.iso_var.set(True)

    extractor._save_settings()

    # Reset to opposite of what was saved
    extractor.keepopen_var.set(False)
    extractor.recursive_var.set(False)
    extractor.hyperlink_var.set(True)
    extractor.dimensions_var.set(False)
    extractor.iso_var.set(False)

    extractor._load_settings()

    assert extractor.keepopen_var.get() is True
    assert extractor.recursive_var.get() is True
    assert extractor.hyperlink_var.get() is False
    assert extractor.dimensions_var.get() is True
    assert extractor.iso_var.get() is True


def test_saved_false_overrides_true_default(extractor, monkeypatch):
    """Regression: if someone changes an __init__ default to True, a saved
    False must still override it. The `if value:` guard in _load_settings
    would skip False and leave the default intact — this test catches that.
    """
    # Simulate a future where the default flips to True
    extractor.keepopen_var.set(True)
    extractor._save_settings()  # saves True
    extractor.keepopen_var.set(False)
    extractor._save_settings()  # saves False
    extractor.keepopen_var.set(True)  # pretend the new default is True
    extractor._load_settings()
    assert extractor.keepopen_var.get() is False


# ---------------------------------------------------------------------------
# Round-trip: filetype
# ---------------------------------------------------------------------------


def test_filetype_round_trip(extractor):
    extractor.filetype_var.set("JSON")
    extractor._save_settings()
    extractor.filetype_var.set("Excel")
    extractor._load_settings()
    assert extractor.filetype_var.get() == "JSON"


def test_filetype_invalid_value_ignored(extractor):
    """If the settings file was hand-edited to an unsupported format,
    loading should not crash and should leave the current value alone."""
    extractor.filetype_var.set("CSV")
    extractor._save_settings()

    data = json.loads(metadata.SETTINGS_PATH.read_text(encoding="utf-8"))
    data["Filetype"] = "XML"  # not in self.filetypes
    metadata.SETTINGS_PATH.write_text(json.dumps(data), encoding="utf-8")

    extractor._load_settings()
    assert extractor.filetype_var.get() == "CSV"  # unchanged


# ---------------------------------------------------------------------------
# Round-trip: paths
# ---------------------------------------------------------------------------


def test_directory_and_output_path_round_trip(extractor, tmp_path):
    d = tmp_path / "photos"
    o = tmp_path / "exports"
    d.mkdir()
    o.mkdir()

    extractor.directory_path = d
    extractor.output_path = o
    extractor._save_settings()

    extractor.directory_path = None
    extractor.output_path = None
    extractor._load_settings()

    assert extractor.directory_path == d
    assert extractor.output_path == o


def test_nonexistent_path_not_restored(extractor, tmp_path):
    """Moved/deleted folders must not be restored — silent fallback to None."""
    d = tmp_path / "will_be_deleted"
    d.mkdir()
    extractor.directory_path = d
    extractor._save_settings()

    # Delete the folder after saving
    # Delete the folder after saving
    d.rmdir()
    extractor.directory_path = None  # ← simulate fresh app launch

    extractor._load_settings()
    assert extractor.directory_path is None


# ---------------------------------------------------------------------------
# Round-trip: dates
# ---------------------------------------------------------------------------


def test_start_and_end_date_round_trip(extractor):
    extractor.start_date_entry.set_date(date(2024, 5, 15))
    extractor.end_date_entry.set_date(date(2024, 6, 30))
    extractor._save_settings()

    extractor.start_date_entry.set_date(None)
    extractor.end_date_entry.set_date(None)
    extractor._load_settings()

    assert extractor.start_date_entry.get_date() == date(2024, 5, 15)
    assert extractor.end_date_entry.get_date() == date(2024, 6, 30)


def test_none_dates_round_trip(extractor):
    extractor.start_date_entry.set_date(None)
    extractor.end_date_entry.set_date(None)
    extractor._save_settings()
    extractor.start_date_entry.set_date(date(2024, 5, 15))
    extractor._load_settings()
    assert extractor.start_date_entry.get_date() is None


# ---------------------------------------------------------------------------
# Round-trip: maxdepth
# ---------------------------------------------------------------------------


def test_maxdepth_round_trip(extractor):
    extractor.maxdepth_entry.delete(0, "end")
    extractor.maxdepth_entry.insert(0, "5")
    extractor._save_settings()

    extractor.maxdepth_entry.delete(0, "end")
    extractor.maxdepth_entry.insert(0, "1")
    extractor.maxdepth = 1
    extractor._load_settings()

    assert extractor.maxdepth_entry.get() == "5"
    assert extractor.maxdepth == 5


def test_maxdepth_invalid_saved_value_ignored(extractor):
    extractor._save_settings()
    data = json.loads(metadata.SETTINGS_PATH.read_text(encoding="utf-8"))
    data["Max Depth"] = "not-a-number"
    metadata.SETTINGS_PATH.write_text(json.dumps(data), encoding="utf-8")

    extractor._load_settings()  # must not crash
    # whatever the entry currently holds, it should still be valid text
    assert extractor.maxdepth_entry.get() != ""


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


def test_missing_file_silent_fallback(extractor):
    """First run — no settings file exists. Load must not crash."""
    assert not metadata.SETTINGS_PATH.exists()
    extractor._load_settings()  # no exception
    assert extractor.directory_path is None
    assert extractor.filetype_var.get() == "Excel"


def test_corrupt_json_silent_fallback(extractor):
    metadata.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    metadata.SETTINGS_PATH.write_text("{not valid json", encoding="utf-8")

    extractor._load_settings()  # no exception
    assert extractor.filetype_var.get() == "Excel"


def test_save_never_raises_on_permission_error(extractor, monkeypatch):
    """_save_settings must never block close on an I/O failure."""

    def boom(*a, **k):
        raise PermissionError("read-only filesystem")

    monkeypatch.setattr("pathlib.Path.write_text", boom)
    extractor._save_settings()  # no exception


# ---------------------------------------------------------------------------
# Integration: full round-trip through both methods
# ---------------------------------------------------------------------------


def test_full_round_trip_preserves_multiple_fields(extractor, tmp_path):
    d = tmp_path / "photos"
    d.mkdir()

    extractor.directory_path = d
    extractor.filetype_var.set("JSON")
    extractor.keepopen_var.set(True)
    extractor.recursive_var.set(True)
    extractor.hyperlink_var.set(False)
    extractor.dimensions_var.set(True)
    extractor.aperture_var.set(True)
    extractor.iso_var.set(True)
    extractor.start_date_entry.set_date(date(2024, 5, 1))
    extractor.end_date_entry.set_date(date(2024, 5, 31))
    extractor.maxdepth_entry.delete(0, "end")
    extractor.maxdepth_entry.insert(0, "3")

    extractor._save_settings()

    # Wipe everything
    extractor.directory_path = None
    extractor.filetype_var.set("Excel")
    extractor.keepopen_var.set(False)
    extractor.recursive_var.set(False)
    extractor.hyperlink_var.set(True)
    extractor.dimensions_var.set(False)
    extractor.aperture_var.set(False)
    extractor.iso_var.set(False)
    extractor.start_date_entry.set_date(None)
    extractor.end_date_entry.set_date(None)
    extractor.maxdepth_entry.delete(0, "end")
    extractor.maxdepth_entry.insert(0, "1")
    extractor.maxdepth = 1

    extractor._load_settings()

    assert extractor.directory_path == d
    assert extractor.filetype_var.get() == "JSON"
    assert extractor.keepopen_var.get() is True
    assert extractor.recursive_var.get() is True
    assert extractor.hyperlink_var.get() is False
    assert extractor.dimensions_var.get() is True
    assert extractor.aperture_var.get() is True
    assert extractor.iso_var.get() is True
    assert extractor.start_date_entry.get_date() == date(2024, 5, 1)
    assert extractor.end_date_entry.get_date() == date(2024, 5, 31)
    assert extractor.maxdepth_entry.get() == "3"
    assert extractor.maxdepth == 3


def test_markdown_filetype_round_trips(extractor, tmp_path):
    extractor.filetype_var.set("Markdown")
    extractor.directory_path = tmp_path
    extractor.output_path = tmp_path
    extractor._save_settings()

    fresh = metadata.MetadataExtractor()
    fresh._load_settings()
    assert fresh.filetype_var.get() == "Markdown"
