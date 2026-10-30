"""Tests for make_series — series range construction."""


def test_all_photos_mode_produces_per_image_series(extractor):
    data = extractor._empty_scan_data()
    data["Images"] = ["a.jpg", "b.jpg", "c.jpg"]
    img_series = extractor.make_series(data, modifier=0, output_series=True)
    assert img_series == ["1", "2", "3"]


def test_all_photos_with_modifier(extractor):
    data = extractor._empty_scan_data()
    data["Images"] = ["a.jpg", "b.jpg"]
    img_series = extractor.make_series(data, modifier=4, output_series=True)
    assert img_series == ["5", "6"]


def test_output_series_false_skips_column(extractor):
    data = extractor._empty_scan_data()
    data["Images"] = ["a.jpg", "b.jpg"]
    assert extractor.make_series(data, modifier=0, output_series=False) is None
