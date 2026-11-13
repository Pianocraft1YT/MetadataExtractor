"""End-to-end tests using the real Excel writer."""

import pandas as pd
import pytest

from tests.helpers import sort_scan

pytestmark = pytest.mark.real_create_sheet


def test_end_to_end_single_folder(extractor, photos_only, tmp_path):
    output = tmp_path / "output.xlsx"
    sort_scan(extractor, photos_only, final_output=output)

    assert output.exists()
    df = pd.read_excel(output, sheet_name="Sheet")
    assert len(df) == 3
    assert "Files" in df.columns
    assert "Dates" in df.columns


def test_end_to_end_custom_starting_index(extractor, photos_and_videos, tmp_path):
    output = tmp_path / "series.xlsx"
    sort_scan(extractor, photos_and_videos, modifier=4, final_output=output)

    assert output.exists()
    df = pd.read_excel(output, sheet_name="Sheet")
    assert list(df["Img # Series"]) == [
        "5-7",
        "5-7",
        "5-7",
        "8-10",
        "8-10",
        "8-10",
        "11-13",
        "11-13",
        "11-13",
    ]
