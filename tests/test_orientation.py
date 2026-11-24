"""Tests for Image Orientation metadata extraction and formatting (v5.0.0)."""

import pytest
from tests.helpers import sort_scan


def test_format_orientation_mapping(extractor):
    assert extractor._format_orientation(1) == "Normal"
    assert extractor._format_orientation(6) == "Rotated 90° CW"
    assert extractor._format_orientation(3) == "Rotated 180°"
    assert extractor._format_orientation(8) == "Rotated 270° CW"
    assert extractor._format_orientation(99) == "99"
    assert extractor._format_orientation(None) is None


def test_end_to_end_orientation_column_written(extractor, make_jpeg_with_tags, tmp_path):
    make_jpeg_with_tags(
        "shot.jpg",
        {36867: "2024:05:15 12:30:45", 274: 6},
    )
    sort_scan(extractor, tmp_path, output_orientation=True, write=False)
    df = extractor.results[0][0]
    assert "Orientation" in df.columns
    assert df["Orientation"].iloc[0] == "Rotated 90° CW"
