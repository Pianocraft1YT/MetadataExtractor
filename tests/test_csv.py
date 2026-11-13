"""Tests for CSV output mode and filetype-dependent filename cleaning."""

import pandas as pd
import pytest

from tests.conftest import make_jpeg_with_exif
from tests.helpers import sort_scan


@pytest.mark.real_create_sheet
def test_excel_mode_writes_xlsx(extractor, photos_only, tmp_path):
    output = tmp_path / "output.xlsx"
    sort_scan(extractor, photos_only, final_output=output)
    assert output.exists()
    df = pd.read_excel(output, sheet_name="Sheet")
    assert len(df) == 3
    assert "Files" in df.columns


@pytest.mark.real_create_sheet
def test_csv_mode_writes_csv_per_sheet(extractor_csv, photos_only, tmp_path):
    output = tmp_path / "output.csv"
    sort_scan(extractor_csv, photos_only, final_output=output)
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
    sort_scan(extractor_csv, photos_only, final_output=output)
    df = pd.read_csv(tmp_path / "output_Sheet.csv")
    assert list(df.columns) == ["Files", "Dates", "Time", "Img # Series"]
    assert list(df["Img # Series"]) == [1, 2, 3]


@pytest.mark.real_create_sheet
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
    sort_scan(extractor, photos_only, final_output=output)
    xl = pd.ExcelFile(output)
    assert xl.sheet_names == ["Sheet"]
