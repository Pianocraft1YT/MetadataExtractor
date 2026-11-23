"""Tests for the selectable Date Format feature (v4.5.0)."""

import json

import pandas as pd
import pytest

import metadata
from tests.conftest import make_jpeg_with_exif
from tests.helpers import sort_scan

# ---------------------------------------------------------------------------
# fix_time date formats
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fmt,expected_date",
    [
        ("%m/%d/%Y", "05/15/2024"),
        ("%Y-%m-%d", "2024-05-15"),
        ("%d/%m/%Y", "15/05/2024"),
    ],
)
def test_fix_time_formats_date_and_time(extractor, tmp_path, fmt, expected_date):
    dates, times = extractor.fix_time(False, ["2024:05:15 12:30:45"], [None], ["a.jpg"], tmp_path, fmt)
    assert dates == [expected_date]
    assert times == ["12:30:45"]


@pytest.mark.parametrize(
    "fmt,expected_date",
    [
        ("%m/%d/%Y", "05/15/2024"),
        ("%Y-%m-%d", "2024-05-15"),
        ("%d/%m/%Y", "15/05/2024"),
    ],
)
def test_fix_time_formats_date_only_exif(extractor, tmp_path, fmt, expected_date):
    dates, times = extractor.fix_time(False, ["2024:05:15"], [None], ["a.jpg"], tmp_path, fmt)
    assert dates == [expected_date]
    assert times == [""]


def test_fix_time_utc_midnight_rollover_respects_custom_format(extractor_tz_on, tmp_path):
    dates, times = extractor_tz_on.fix_time(
        True,
        ["2024:01:31 22:00:00"],
        ["-05:00"],
        ["img.jpg"],
        tmp_path,
        "%Y-%m-%d",
    )
    assert dates == ["2024-02-01"]
    assert times == ["03:00:00"]


# ---------------------------------------------------------------------------
# extract + create_dataframe + _build_summary_dataframe
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fmt,expected",
    [
        ("%Y-%m-%d", "2024-05-15"),
        ("%d/%m/%Y", "15/05/2024"),
    ],
)
def test_sort_scan_with_custom_date_format(extractor, tmp_path, fmt, expected):
    make_jpeg_with_exif(tmp_path / "a.jpg", "2024:05:15 12:30:45")
    processed, skipped = sort_scan(extractor, tmp_path, date_format=fmt, write=False)

    assert (processed, skipped) == (1, 0)
    df = extractor.results[0][0]
    assert list(df["Dates"]) == [expected]


def test_create_dataframe_fallback_sort_parses_custom_date_format(extractor, tmp_path):
    data = extractor._empty_scan_data()
    data["Images"] = ["late.jpg", "early.jpg"]
    data["Dates"] = ["2025-01-05", "2024-12-31"]
    data["Times"] = ["08:00:00", "23:59:00"]
    extractor.sort_method = "Date (Oldest)"

    extractor.create_dataframe(
        ["1", "2"],
        data,
        tmp_path,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        date_format="%Y-%m-%d",
    )

    df = extractor.results[0][0]
    assert list(df["Files"]) == ["early.jpg", "late.jpg"]


def test_build_summary_dataframe_parses_and_formats_custom_date_format(extractor, tmp_path):
    df_a = pd.DataFrame(
        {
            "Files": ["a1.jpg", "a2.jpg"],
            "Dates": ["31/12/2024", "05/01/2025"],
            "Time": ["23:59:00", "08:00:00"],
            "Img # Series": ["1", "2"],
        }
    )
    df_b = pd.DataFrame(
        {
            "Files": ["b1.jpg"],
            "Dates": ["15/06/2024"],
            "Time": ["10:00:00"],
            "Img # Series": ["1"],
        }
    )

    summary_df, _, _ = extractor._build_summary_dataframe(
        [(df_a, "A", tmp_path.as_posix()), (df_b, "B", tmp_path.as_posix())],
        date_format="%d/%m/%Y",
    )

    assert summary_df.loc[0, "Dated"] == 2
    assert summary_df.loc[0, "Earliest Date"] == "31/12/2024"
    assert summary_df.loc[0, "Latest Date"] == "05/01/2025"
    assert summary_df.loc[2, "Earliest Date"] == "15/06/2024"
    assert summary_df.loc[2, "Latest Date"] == "05/01/2025"


# ---------------------------------------------------------------------------
# initialize() Basic vs Advanced + settings persistence
# ---------------------------------------------------------------------------


def test_initialize_passes_selected_date_format_in_advanced_and_defaults_in_basic(extractor, tmp_path):
    (tmp_path / "shot.jpg").write_bytes(b"fake")
    extractor.directory_path = tmp_path
    extractor.output_path = tmp_path
    captured = []
    extractor._start_scan = lambda cfg: captured.append(cfg.date_format)

    extractor.date_format_combobox.set("YYYY-MM-DD")

    extractor.user_mode_var.set("Basic")
    extractor.initialize()
    assert captured[-1] == "%m/%d/%Y"

    extractor.user_mode_var.set("Advanced")
    extractor.initialize()
    assert captured[-1] == "%Y-%m-%d"


def test_date_format_setting_round_trip_and_invalid_ignored(extractor):
    extractor.date_format_combobox.set("DD/MM/YYYY")
    extractor._save_settings()

    saved = json.loads(metadata.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert saved["Date Format"] == "DD/MM/YYYY"

    extractor.date_format_combobox.set("MM/DD/YYYY")
    extractor._load_settings()
    assert extractor.date_format_combobox.get() == "DD/MM/YYYY"

    saved["Date Format"] = "INVALID"
    metadata.SETTINGS_PATH.write_text(json.dumps(saved), encoding="utf-8")
    extractor._load_settings()
    assert extractor.date_format_combobox.get() == "DD/MM/YYYY"
