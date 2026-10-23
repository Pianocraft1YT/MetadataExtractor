"""End-to-end tests using the real Excel writer."""

import pandas as pd
import pytest

pytestmark = pytest.mark.real_create_sheet


def test_end_to_end_single_folder(extractor, photos_only, tmp_path):
    output = tmp_path / "output.xlsx"
    extractor.sort_and_extract(
        photos_only,
        recursive=False,
        final_output=output,
        modifier=0,
        output_series=True,
    )

    assert output.exists()
    df = pd.read_excel(output, sheet_name="Sheet")
    assert len(df) == 3
    assert "Files" in df.columns
    assert "Dates" in df.columns


def test_end_to_end_custom_starting_index(extractor, photos_and_videos, tmp_path):
    output = tmp_path / "series.xlsx"
    extractor.sort_and_extract_irregular(
        photos_and_videos,
        recursive=False,
        final_output=output,
        modifier=4,
    )

    assert output.exists()
    df = pd.read_excel(output, sheet_name="Sheet")
    if "Img # Series" in df.columns:
        assert all(str(s).startswith(("5", "9", "13")) for s in df["Img # Series"])
