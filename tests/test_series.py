"""Tests for make_series — series range construction."""

import metadata


def test_all_photos_mode_produces_per_image_series():
    img_series, imgs, dates, times = metadata.make_series(
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


def test_all_photos_with_modifier():
    img_series, _, _, _ = metadata.make_series(
        list_of_images=["a.jpg", "b.jpg"],
        photos_before_video_updated=False,
        photos_before_video=0,
        fixed_date=["01/01/2024"] * 2,
        fixed_time=["12:00:00"] * 2,
        modifier=4,  # starting index 5
        output_series=True,
    )
    assert img_series == ["5", "6"]


def test_series_mode_only_keeps_last_image_per_group():
    # 3 photos per video, 3 groups → 3 rows, series 1-4, 5-8, 9-12
    img_series, imgs, dates, times = metadata.make_series(
        list_of_images=[f"p{i}.jpg" for i in range(1, 10)],
        photos_before_video_updated=True,
        photos_before_video=3,
        fixed_date=["01/01/2024"] * 9,
        fixed_time=["12:00:00"] * 9,
        modifier=0,
        output_series=True,
    )
    assert img_series == ["1-4", "5-8", "9-12"]
    # Only the last photo of each group is kept
    assert imgs == ["p3.jpg", "p6.jpg", "p9.jpg"]


def test_output_series_false_skips_column():
    img_series, imgs, _, _ = metadata.make_series(
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