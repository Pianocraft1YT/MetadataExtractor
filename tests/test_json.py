"""Tests for JSON output mode."""

import json
import pytest

from tests.conftest import make_jpeg_with_exif

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
    date_range=False,
    start_date=None,
    end_date=None,
)


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
# End-to-end output (fail until create_sheet has the JSON branch)
# ---------------------------------------------------------------------------


@pytest.mark.real_create_sheet
def test_json_mode_writes_json_file(extractor_json, photos_only, tmp_path):
    output = tmp_path / "output.json"
    extractor_json.sort_and_extract(
        photos_only,
        recursive=False,
        final_output=output,
        modifier=0,
        output_series=True,
        **_EXTRA_OFF,
    )
    assert output.exists()


@pytest.mark.real_create_sheet
def test_json_mode_is_parseable_with_expected_top_level_keys(extractor_json, photos_only, tmp_path):
    output = tmp_path / "output.json"
    extractor_json.sort_and_extract(
        photos_only,
        recursive=False,
        final_output=output,
        modifier=0,
        output_series=True,
        **_EXTRA_OFF,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "exported_at" in payload
    assert "sheets" in payload
    assert isinstance(payload["sheets"], dict)


@pytest.mark.real_create_sheet
def test_json_mode_sheet_structure(extractor_json, photos_only, tmp_path):
    output = tmp_path / "output.json"
    extractor_json.sort_and_extract(
        photos_only,
        recursive=False,
        final_output=output,
        modifier=0,
        output_series=True,
        **_EXTRA_OFF,
    )
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

    output = tmp_path / "output.json"
    extractor_json.maxdepth = 1
    extractor_json.find_directories(
        parent,
        output,
        modifier=0,
        debug=False,
        **_EXTRA_OFF,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert set(payload["sheets"].keys()) == {"Trip_A", "Trip_B"}
    assert len(payload["sheets"]["Trip_A"]) == 1
    assert len(payload["sheets"]["Trip_B"]) == 1
