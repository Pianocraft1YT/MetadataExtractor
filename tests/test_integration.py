"""End-to-end tests using the real Excel writer."""

import pandas as pd
import pytest

pytestmark = pytest.mark.real_create_sheet


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
)


def test_end_to_end_single_folder(extractor, photos_only, tmp_path):
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
    assert "Dates" in df.columns


def test_end_to_end_custom_starting_index(extractor, photos_and_videos, tmp_path):
    output = tmp_path / "series.xlsx"
    extractor.sort_and_extract_irregular(
        photos_and_videos,
        recursive=False,
        final_output=output,
        modifier=4,
        debug=False,
        **_EXTRA_OFF,
    )

    assert output.exists()
    df = pd.read_excel(output, sheet_name="Sheet")
    if "Img # Series" in df.columns:
        assert all(str(s).startswith(("5", "9", "13")) for s in df["Img # Series"])
