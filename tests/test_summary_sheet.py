"""Tests for the opt-in Summary Sheet feature."""

import json

import openpyxl
import pandas as pd
import pytest

import metadata


def _sample_results(tmp_path):
    dir_a = tmp_path / "Trip_A"
    dir_b = tmp_path / "Trip_B"
    dir_a.mkdir()
    dir_b.mkdir()
    df_a = pd.DataFrame(
        {
            "Files": ["a1.jpg", "a2.jpg", "a3.jpg"],
            "Dates": ["12/31/2024", "01/05/2025", ""],
            "Time": ["23:59:00", "08:00:00", ""],
            "Img # Series": ["1", "2", ""],
        }
    )
    df_b = pd.DataFrame(
        {
            "Files": ["b1.jpg", "b2.jpg"],
            "Dates": ["06/15/2024", "06/15/2024"],
            "Time": ["10:00:00", "10:00:01"],
            "Img # Series": ["1-2", "1-2"],
        }
    )
    return [
        (df_a, "Trip_A", dir_a.as_posix()),
        (df_b, "Trip_B", dir_b.as_posix()),
    ]


# ---------------------------------------------------------------------------
# _build_summary_dataframe unit tests
# ---------------------------------------------------------------------------


def test_build_summary_dataframe_computes_metrics_and_total_row(extractor, tmp_path):
    results = _sample_results(tmp_path)
    summary_df, sheet_name, directory = extractor._build_summary_dataframe(results)

    assert sheet_name == "Summary"
    assert directory is None
    assert list(summary_df["Sheet"]) == ["Trip_A", "Trip_B", "Total"]
    assert list(summary_df["Items"]) == [3, 2, 5]
    assert list(summary_df["Dated"]) == [2, 2, 4]
    assert list(summary_df["Undated"]) == [1, 0, 1]
    assert list(summary_df["Series Groups"]) == [2, 1, 3]
    # Cross-year check: 12/31/2024 < 01/05/2025 (catches string min/max bug)
    assert summary_df.loc[0, "Earliest Date"] == "12/31/2024"
    assert summary_df.loc[0, "Latest Date"] == "01/05/2025"
    assert summary_df.loc[2, "Earliest Date"] == "06/15/2024"
    assert summary_df.loc[2, "Latest Date"] == "01/05/2025"
    assert list(summary_df["File Size"]) == ["0 B", "0 B", "0 B"]


def test_build_summary_dataframe_sums_file_sizes_per_folder_and_total(extractor, tmp_path):
    results = _sample_results(tmp_path)
    (tmp_path / "Trip_A" / "a1.jpg").write_bytes(b"x" * 1500)
    (tmp_path / "Trip_A" / "a2.jpg").write_bytes(b"x" * 500)
    # a3.jpg missing on disk -> safely ignored
    (tmp_path / "Trip_B" / "b1.jpg").write_bytes(b"x" * 3000)

    summary_df, _, _ = extractor._build_summary_dataframe(results)

    assert list(summary_df["File Size"]) == ["2.0 KB", "3.0 KB", "5.0 KB"]


def test_build_summary_dataframe_handles_missing_columns_and_undated_rows(extractor, tmp_path):
    df_minimal = pd.DataFrame({"Files": ["only.jpg"]})
    df_undated = pd.DataFrame({"Files": [None], "Dates": [""], "Img # Series": [""]})
    results = [
        (df_minimal, "Minimal", None),
        (df_undated, "Undated", tmp_path.as_posix()),
    ]

    summary_df, _, _ = extractor._build_summary_dataframe(results)

    assert list(summary_df["Items"]) == [1, 1, 2]
    assert list(summary_df["Dated"]) == [0, 0, 0]
    assert list(summary_df["Undated"]) == [1, 1, 2]
    assert list(summary_df["Series Groups"]) == [0, 0, 0]
    assert summary_df.loc[2, "Earliest Date"] == ""
    assert summary_df.loc[2, "Latest Date"] == ""
    assert list(summary_df["File Size"]) == ["0 B", "0 B", "0 B"]


# ---------------------------------------------------------------------------
# create_sheet integration across formats
# ---------------------------------------------------------------------------


@pytest.mark.real_create_sheet
def test_create_sheet_excel_prepends_formatted_summary_and_keeps_hyperlinks(extractor, tmp_path):
    extractor.results = _sample_results(tmp_path)
    extractor.filetype_var.set("Excel")
    extractor.hyperlink_var.set(True)
    extractor.keepopen_var.set(True)
    output = tmp_path / "with_summary.xlsx"

    extractor.create_sheet(output, 5, 0, output_summary=True)

    wb = openpyxl.load_workbook(output)
    assert wb.sheetnames == ["Summary", "Trip_A", "Trip_B"]
    ws_summary = wb["Summary"]
    assert ws_summary.freeze_panes == "A2"
    assert all(cell.font.bold is True for cell in ws_summary[1])
    assert ws_summary["B2"].hyperlink is not None
    assert ws_summary["B2"].hyperlink.target == (tmp_path / "Trip_A").as_uri()
    assert ws_summary["B2"].font.underline == "single"
    assert ws_summary["B3"].hyperlink is not None
    assert ws_summary["B3"].hyperlink.target == (tmp_path / "Trip_B").as_uri()
    assert ws_summary["B4"].hyperlink is None  # Total row has no Source Path
    assert wb["Trip_A"]["A2"].hyperlink is not None
    assert [name for _, name, _ in extractor.results] == ["Summary", "Trip_A", "Trip_B"]


@pytest.mark.real_create_sheet
def test_create_sheet_excel_summary_name_collision_still_hyperlinks_summary_tab(extractor, tmp_path):
    dir_summary = tmp_path / "Summary"
    dir_other = tmp_path / "Other"
    dir_summary.mkdir()
    dir_other.mkdir()
    df1 = pd.DataFrame({"Files": ["a.jpg"], "Dates": ["05/15/2024"], "Time": ["12:00:00"], "Img # Series": ["1"]})
    df2 = pd.DataFrame({"Files": ["b.jpg"], "Dates": ["05/16/2024"], "Time": ["12:00:00"], "Img # Series": ["1"]})

    extractor.results = [
        (df1, "Summary", dir_summary.as_posix()),
        (df2, "Other", dir_other.as_posix()),
    ]
    extractor.filetype_var.set("Excel")
    extractor.hyperlink_var.set(True)
    extractor.keepopen_var.set(True)
    output = tmp_path / "collision.xlsx"

    extractor.create_sheet(output, 2, 0, output_summary=True)

    wb = openpyxl.load_workbook(output)
    assert wb.sheetnames == ["Summary_2", "Summary", "Other"]
    ws_sum = wb["Summary_2"]
    assert ws_sum["B2"].hyperlink.target == dir_summary.as_uri()
    assert ws_sum["B3"].hyperlink.target == dir_other.as_uri()
    assert ws_sum["B4"].hyperlink is None


@pytest.mark.real_create_sheet
def test_create_sheet_json_includes_summary_sheet(extractor, tmp_path):
    extractor.results = _sample_results(tmp_path)
    extractor.filetype_var.set("JSON")
    extractor.keepopen_var.set(True)
    output = tmp_path / "with_summary.json"

    extractor.create_sheet(output, 5, 0, output_summary=True)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert list(payload["sheets"].keys()) == ["Summary", "Trip_A", "Trip_B"]
    assert payload["sheets"]["Summary"][-1]["Sheet"] == "Total"
    assert payload["sheets"]["Summary"][-1]["Items"] == 5


@pytest.mark.real_create_sheet
@pytest.mark.parametrize("filetype,ext", [("CSV", ".csv"), ("Markdown", ".md")])
def test_create_sheet_csv_and_markdown_write_summary_file(extractor, tmp_path, filetype, ext):
    extractor.results = _sample_results(tmp_path)
    extractor.filetype_var.set(filetype)
    extractor.hyperlink_var.set(False)
    extractor.keepopen_var.set(True)
    output = tmp_path / f"report{ext}"

    extractor.create_sheet(output, 5, 0, output_summary=True)

    assert (tmp_path / f"report_Summary{ext}").exists()
    assert (tmp_path / f"report_Trip_A{ext}").exists()
    assert (tmp_path / f"report_Trip_B{ext}").exists()


@pytest.mark.real_create_sheet
def test_create_sheet_skips_summary_for_single_sheet_or_disabled(extractor, tmp_path):
    results = _sample_results(tmp_path)
    extractor.filetype_var.set("Excel")
    extractor.hyperlink_var.set(False)
    extractor.keepopen_var.set(True)

    # Disabled on multi-sheet -> no Summary
    extractor.results = list(results)
    out_disabled = tmp_path / "disabled.xlsx"
    extractor.create_sheet(out_disabled, 5, 0, output_summary=False)
    assert openpyxl.load_workbook(out_disabled).sheetnames == ["Trip_A", "Trip_B"]

    # Enabled on single-sheet -> no Summary
    extractor.results = [results[0]]
    out_single = tmp_path / "single.xlsx"
    extractor.create_sheet(out_single, 3, 0, output_summary=True)
    assert openpyxl.load_workbook(out_single).sheetnames == ["Trip_A"]


# ---------------------------------------------------------------------------
# Settings persistence
# ---------------------------------------------------------------------------


def test_summary_setting_round_trip(extractor):
    extractor.summary_var.set(True)
    extractor._save_settings()

    saved = json.loads(metadata.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert saved["Summary"] is True

    extractor.summary_var.set(False)
    extractor._load_settings()

    assert extractor.summary_var.get() is True
