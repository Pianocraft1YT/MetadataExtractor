"""Tests for make_series — series range construction."""


def test_all_photos_mode_produces_per_image_series(extractor):
    img_series, imgs, dates, times = extractor.make_series(
        list_of_images=["a.jpg", "b.jpg", "c.jpg"],
        photos_before_video_updated=False,
        photos_before_video=0,
        fixed_date=["01/01/2024"] * 3,
        fixed_time=["12:00:00"] * 3,
        modifier=0,
        output_series=True,
    )
    assert img_series == ["1", "2", "3"]
    assert imgs == ["a.jpg", "b.jpg", "c.jpg"]


def test_all_photos_with_modifier(extractor):
    img_series, _, _, _ = extractor.make_series(
        list_of_images=["a.jpg", "b.jpg"],
        photos_before_video_updated=False,
        photos_before_video=0,
        fixed_date=["01/01/2024"] * 2,
        fixed_time=["12:00:00"] * 2,
        modifier=4,
        output_series=True,
    )
    assert img_series == ["5", "6"]


def test_series_mode_only_keeps_last_image_per_group(extractor):
    img_series, imgs, dates, times = extractor.make_series(
        list_of_images=[f"p{i}.jpg" for i in range(1, 10)],
        photos_before_video_updated=True,
        photos_before_video=3,
        fixed_date=["01/01/2024"] * 9,
        fixed_time=["12:00:00"] * 9,
        modifier=0,
        output_series=True,
    )
    assert img_series == ["1-4", "5-8", "9-12"]
    assert imgs == ["p3.jpg", "p6.jpg", "p9.jpg"]


def test_output_series_false_skips_column(extractor):
    img_series, imgs, _, _ = extractor.make_series(
        list_of_images=["a.jpg", "b.jpg"],
        photos_before_video_updated=False,
        photos_before_video=0,
        fixed_date=["01/01/2024"] * 2,
        fixed_time=["12:00:00"] * 2,
        modifier=0,
        output_series=False,
    )
    assert img_series is None
    assert imgs == ["a.jpg", "b.jpg"]
