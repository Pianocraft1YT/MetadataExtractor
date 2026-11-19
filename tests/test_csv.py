"""Tests for CSV output mode and filetype-dependent filename cleaning."""

import pandas as pd
import pytest

from tests.conftest import make_jpeg_with_exif
from tests.helpers import find_scan, sort_scan


@pytest.mark.real_create_sheet
def test_excel_mode_writes_xlsx(extractor, photos_only, tmp_path):
    output = tmp_path / "output.xlsx"
    sort_scan(extractor, photos_only, final_output=output)
    assert output.exists()
    df = pd.read_excel(output, sheet_name="Sheet")
    assert len(df) == 3
    assert "Files" in df.columns


@pytest.mark.real_create_sheet
def test_csv_mode_writes_csv_for_single_sheet(extractor_csv, photos_only, tmp_path):
    output = tmp_path / "output.csv"
    sort_scan(extractor_csv, photos_only, final_output=output)
    assert output.exists()
    df = pd.read_csv(output)
    assert len(df) == 3
    assert "Files" in df.columns
    assert "Img # Series" in df.columns


@pytest.mark.real_create_sheet
def test_csv_mode_writes_csv_per_sheet_when_multiple(extractor_csv, tmp_path):
    parent = tmp_path / "parent"
    for sub in ("Trip_A", "Trip_B"):
        folder = parent / sub
        folder.mkdir(parents=True)
        make_jpeg_with_exif(folder / "IMG_001.jpg", "2024:05:15 12:30:45")
    extractor_csv.maxdepth = 1
    output = tmp_path / "output.csv"
    find_scan(extractor_csv, parent, final_output=output)
    assert (tmp_path / "output_Trip_A.csv").exists()
    assert (tmp_path / "output_Trip_B.csv").exists()


@pytest.mark.real_create_sheet
def test_csv_mode_includes_series_column(extractor_csv, photos_only, tmp_path):
    output = tmp_path / "output.csv"
    sort_scan(extractor_csv, photos_only, final_output=output)
    df = pd.read_csv(output)
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
