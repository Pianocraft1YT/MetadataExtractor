"""Tests for JSON output mode."""

import json

import pytest

from tests.conftest import make_jpeg_with_exif
from tests.helpers import find_scan, sort_scan

# ---------------------------------------------------------------------------
# clean_name extension handling (no file I/O — should pass immediately)
# ---------------------------------------------------------------------------


def test_clean_name_json_mode_appends_json(extractor_json):
    assert extractor_json.clean_name("myname") == "myname.json"


def test_clean_name_preserves_typed_json_in_json_mode(extractor_json):
    assert extractor_json.clean_name("myname.json") == "myname.json"


def test_clean_name_typed_xlsx_in_json_mode_forced_to_json(extractor_json):
    """User typed .xlsx but JSON is selected → extension forced to .json."""
    assert extractor_json.clean_name("myname.xlsx") == "myname.json"


def test_clean_name_typed_json_case_preserved(extractor_json):
    """Typed .JSON uppercase: matching suffix, case preserved in output."""
    assert extractor_json.clean_name("myname.JSON") == "myname.JSON"


# ---------------------------------------------------------------------------
# End-to-end output
# ---------------------------------------------------------------------------


@pytest.mark.real_create_sheet
def test_json_mode_writes_json_file(extractor_json, photos_only, tmp_path):
    output = tmp_path / "output.json"
    sort_scan(extractor_json, photos_only, final_output=output)
    assert output.exists()


@pytest.mark.real_create_sheet
def test_json_mode_is_parseable_with_expected_top_level_keys(extractor_json, photos_only, tmp_path):
    output = tmp_path / "output.json"
    sort_scan(extractor_json, photos_only, final_output=output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "exported_at" in payload
    assert "sheets" in payload
    assert isinstance(payload["sheets"], dict)


@pytest.mark.real_create_sheet
def test_json_mode_sheet_structure(extractor_json, photos_only, tmp_path):
    output = tmp_path / "output.json"
    sort_scan(extractor_json, photos_only, final_output=output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "Sheet" in payload["sheets"]
    records = payload["sheets"]["Sheet"]
    assert isinstance(records, list)
    assert len(records) == 3
    assert records[0]["Files"] == "IMG_001.jpg"
    assert "Dates" in records[0]
    assert "Time" in records[0]
    assert "Img # Series" in records[0]


@pytest.mark.real_create_sheet
def test_json_mode_recursive_produces_multiple_sheets(extractor_json, tmp_path):
    parent = tmp_path / "parent"
    for sub in ["Trip_A", "Trip_B"]:
        folder = parent / sub
        folder.mkdir(parents=True)
        make_jpeg_with_exif(folder / "IMG_001.jpg", "2024:05:15 12:30:45")

    extractor_json.maxdepth = 1
    output = tmp_path / "output.json"
    find_scan(extractor_json, parent, final_output=output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert set(payload["sheets"].keys()) == {"Trip_A", "Trip_B"}
    assert len(payload["sheets"]["Trip_A"]) == 1
    assert len(payload["sheets"]["Trip_B"]) == 1
