"""Tests for Excel worksheet formatting (_format_excel_sheet + create_sheet)."""

import openpyxl
import pandas as pd
import pytest

from metadata import MetadataExtractor


def _make_ws(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    return ws


def test_format_excel_sheet_freezes_bolds_and_autofilters():
    ws = _make_ws(
        [
            ["Files", "Dates", "ISO"],
            ["a.jpg", "05/15/2024", 400],
        ]
    )

    MetadataExtractor._format_excel_sheet(ws)

    assert ws.freeze_panes == "A2"
    assert all(cell.font.bold is True for cell in ws[1])
    assert ws["A2"].font.bold is not True
    assert ws.auto_filter.ref == "A1:C2"


def test_format_excel_sheet_autofits_and_caps_widths():
    ws = _make_ws(
        [
            ["A", "LongVal", "Multi", "Blank"],
            ["x", "y" * 100, "line1\nwidestline\nend", None],
        ]
    )

    MetadataExtractor._format_excel_sheet(ws)

    # "A" -> len 1 + 4 = 5
    assert ws.column_dimensions["A"].width == 5
    # 100 chars capped at 50
    assert ws.column_dimensions["B"].width == 50
    # Longest line in "line1\nwidestline\nend" is "widestline" (10) -> 10 + 4 = 14
    assert ws.column_dimensions["C"].width == 14
    # None cell shouldn't widen past header "Blank" (5 + 4 = 9)
    assert ws.column_dimensions["D"].width == 9


def test_format_excel_sheet_handles_none_and_empty_worksheet():
    MetadataExtractor._format_excel_sheet(None)
    wb = openpyxl.Workbook()
    ws = wb.active
    # Fresh openpyxl sheet has max_row == 1, max_column == 1 with value None;
    # confirm no crash on either blank sheet or 0-row sheet.
    MetadataExtractor._format_excel_sheet(ws)
    ws.delete_rows(1, 1)
    MetadataExtractor._format_excel_sheet(ws)


@pytest.mark.real_create_sheet
def test_create_sheet_preserves_formatting_with_hyperlinks(extractor, tmp_path):
    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    df = pd.DataFrame(
        {
            "Files": ["vacation_photo_001.jpg"],
            "Dates": ["05/15/2024"],
            "Time": ["12:30:45"],
            "Img # Series": ["1"],
        }
    )
    extractor.results.append((df, "Sheet", photo_dir))
    extractor.filetype_var.set("Excel")
    extractor.hyperlink_var.set(True)
    extractor.keepopen_var.set(True)
    output = tmp_path / "formatted.xlsx"

    extractor.create_sheet(output, 1, 0)

    wb = openpyxl.load_workbook(output)
    ws = wb["Sheet"]
    assert ws.freeze_panes == "A2"
    assert all(cell.font.bold is True for cell in ws[1])
    assert ws.auto_filter.ref == "A1:D2"
    assert ws.column_dimensions["A"].width == len("vacation_photo_001.jpg") + 4
    assert ws["A2"].hyperlink.target == (photo_dir / "vacation_photo_001.jpg").as_uri()
