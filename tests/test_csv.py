"""Tests for CSV output mode and filetype-dependent filename cleaning."""

import pandas as pd
import pytest

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


@pytest.mark.real_create_sheet
def test_excel_mode_writes_xlsx(extractor, photos_only, tmp_path):
    output = tmp_path / "output.xlsx"
    extractor.sort_and_extract(
        photos_only,
        recursive=False,
        final_output=output,
        modifier=0,
        output_series=True,
        **_EXTRA_OFF,
    )
    assert output.exists()
    df = pd.read_excel(output, sheet_name="Sheet")
    assert len(df) == 3
    assert "Files" in df.columns


@pytest.mark.real_create_sheet
def test_csv_mode_writes_csv_per_sheet(extractor_csv, photos_only, tmp_path):
    output = tmp_path / "output.csv"
    extractor_csv.sort_and_extract(
        photos_only,
        recursive=False,
        final_output=output,
        modifier=0,
        output_series=True,
        **_EXTRA_OFF,
    )
    assert not output.exists()
    csv_path = tmp_path / "output_Sheet.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert len(df) == 3
    assert "Files" in df.columns
    assert "Img # Series" in df.columns


@pytest.mark.real_create_sheet
def test_csv_mode_includes_series_column(extractor_csv, photos_only, tmp_path):
    output = tmp_path / "output.csv"
    extractor_csv.sort_and_extract(
        photos_only,
        recursive=False,
        final_output=output,
        modifier=0,
        output_series=True,
        **_EXTRA_OFF,
    )
    df = pd.read_csv(tmp_path / "output_Sheet.csv")
    assert list(df.columns) == ["Files", "Dates", "Time", "Img # Series"]
    assert list(df["Img # Series"]) == [1, 2, 3]


@pytest.mark.real_create_sheet
def test_csv_mode_without_series_column(extractor_csv, photos_only, tmp_path):
    output = tmp_path / "output.csv"
    extractor_csv.sort_and_extract(
        photos_only,
        recursive=False,
        final_output=output,
        modifier=0,
        output_series=False,
        **_EXTRA_OFF,
    )
    df = pd.read_csv(tmp_path / "output_Sheet.csv")
    assert "Img # Series" not in df.columns


def test_clean_name_excel_mode_appends_xlsx(extractor):
    assert extractor.clean_name("myname") == "myname.xlsx"


def test_clean_name_csv_mode_appends_csv(extractor_csv):
    assert extractor_csv.clean_name("myname") == "myname.csv"


def test_clean_name_typed_xlsx_in_csv_mode_forced_to_csv(extractor_csv):
    assert extractor_csv.clean_name("myname.xlsx") == "myname.csv"


def test_clean_name_preserves_typed_xlsx_case(extractor):
    assert extractor.clean_name("myname.XLSX") == "myname.XLSX"


def test_clean_name_reserved_word_excel_mode(extractor):
    assert extractor.clean_name("CON") == "_CON.xlsx"


def test_clean_name_reserved_word_csv_mode(extractor_csv):
    assert extractor_csv.clean_name("CON") == "_CON.csv"


@pytest.mark.real_create_sheet
def test_default_sheet_name_used(extractor, photos_only, tmp_path):
    output = tmp_path / "output.xlsx"
    extractor.sort_and_extract(
        photos_only,
        recursive=False,
        final_output=output,
        modifier=0,
        output_series=True,
        **_EXTRA_OFF,
    )
    xl = pd.ExcelFile(output)
    assert xl.sheet_names == ["Sheet"]
