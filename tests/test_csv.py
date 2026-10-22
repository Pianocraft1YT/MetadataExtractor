"""Tests for CSV output mode and filetype-dependent filename cleaning."""

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# End-to-end output
# ---------------------------------------------------------------------------

@pytest.mark.real_create_sheet
def test_excel_mode_writes_xlsx(extractor, photos_only, tmp_path):
    """Default Excel mode writes a single xlsx with one 'Sheet' sheet."""
    output = tmp_path / "output.xlsx"
    extractor.sort_and_extract(
        photos_only, recursive=False,
        final_output=output, modifier=0, output_series=True,
    )
    assert output.exists()
    df = pd.read_excel(output, sheet_name="Sheet")
    assert len(df) == 3
    assert "Files" in df.columns


@pytest.mark.real_create_sheet
def test_csv_mode_writes_csv_per_sheet(extractor_csv, photos_only, tmp_path):
    """CSV mode writes <stem>_<sheet>.csv instead of xlsx."""
    output = tmp_path / "output.csv"
    extractor_csv.sort_and_extract(
        photos_only, recursive=False,
        final_output=output, modifier=0, output_series=True,
    )
    # No xlsx written
    assert not output.exists()
    # CSV at expected path
    csv_path = tmp_path / "output_Sheet.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert len(df) == 3
    assert "Files" in df.columns
    assert "Img # Series" in df.columns


@pytest.mark.real_create_sheet
def test_csv_mode_includes_series_column(extractor_csv, photos_only, tmp_path):
    """CSV output preserves the Img # Series column when enabled."""
    output = tmp_path / "output.csv"
    extractor_csv.sort_and_extract(
        photos_only, recursive=False,
        final_output=output, modifier=0, output_series=True,
    )
    df = pd.read_csv(tmp_path / "output_Sheet.csv")
    assert list(df.columns) == ["Files", "Dates", "Time", "Img # Series"]
    assert list(df["Img # Series"]) == [1, 2, 3]

@pytest.mark.real_create_sheet
def test_csv_mode_without_series_column(extractor_csv, photos_only, tmp_path):
    """CSV output omits Img # Series when output_series is False."""
    output = tmp_path / "output.csv"
    extractor_csv.sort_and_extract(
        photos_only, recursive=False,
        final_output=output, modifier=0, output_series=False,
    )
    df = pd.read_csv(tmp_path / "output_Sheet.csv")
    assert "Img # Series" not in df.columns


# ---------------------------------------------------------------------------
# clean_name filetype behavior
# ---------------------------------------------------------------------------

def test_clean_name_excel_mode_appends_xlsx(extractor):
    """Excel mode: no extension typed, .xlsx appended."""
    assert extractor.clean_name("myname") == "myname.xlsx"


def test_clean_name_csv_mode_appends_csv(extractor_csv):
    """CSV mode: no extension typed, .csv appended."""
    assert extractor_csv.clean_name("myname") == "myname.csv"


def test_clean_name_preserves_typed_xlsx_in_csv_mode(extractor_csv):
    """Typed .xlsx extension is preserved even in CSV mode.

    User explicitly typed .xlsx, so respect it (they might be
    intentionally writing an xlsx-shaped file with a custom name,
    though the CSV writer will still produce CSV content — a known
    limitation of relying on typed extensions).
    """
    assert extractor_csv.clean_name("myname.xlsx") == "myname.xlsx"


def test_clean_name_preserves_typed_xlsx_case(extractor):
    """Typed .XLSX case is preserved."""
    assert extractor.clean_name("myname.XLSX") == "myname.XLSX"


def test_clean_name_reserved_word_excel_mode(extractor):
    """Reserved Windows names get prefixed in Excel mode."""
    assert extractor.clean_name("CON") == "_CON.xlsx"


def test_clean_name_reserved_word_csv_mode(extractor_csv):
    """Reserved Windows names get prefixed in CSV mode."""
    assert extractor_csv.clean_name("CON") == "_CON.csv"


# ---------------------------------------------------------------------------
# Sheet naming in output
# ---------------------------------------------------------------------------

@pytest.mark.real_create_sheet
def test_default_sheet_name_used(extractor, photos_only, tmp_path):
    """Single-folder scans use the default 'Sheet' name."""
    output = tmp_path / "output.xlsx"
    extractor.sort_and_extract(
        photos_only, recursive=False,
        final_output=output, modifier=0, output_series=True,
    )
    # Verify only "Sheet" exists as a sheet name
    xl = pd.ExcelFile(output)
    assert xl.sheet_names == ["Sheet"]