"""Boundary-value tests for pure helper methods."""

import pytest


# make_series

def test_make_series_zero_images(extractor):
    img_series, imgs, dates, times = extractor.make_series(
        list_of_images=[],
        photos_before_video_updated=False,
        photos_before_video=0,
        fixed_date=[],
        fixed_time=[],
        modifier=0,
        output_series=True,
    )
    assert img_series == []
    assert imgs == []


def test_make_series_one_image_all_photos_mode(extractor):
    img_series, imgs, _, _ = extractor.make_series(
        list_of_images=["a.jpg"],
        photos_before_video_updated=False,
        photos_before_video=0,
        fixed_date=["01/01/2024"],
        fixed_time=["12:00:00"],
        modifier=0,
        output_series=True,
    )
    assert img_series == ["1"]
    assert imgs == ["a.jpg"]


def test_make_series_one_image_series_mode_incomplete_group(extractor):
    img_series, imgs, _, _ = extractor.make_series(
        list_of_images=["a.jpg"],
        photos_before_video_updated=True,
        photos_before_video=3,
        fixed_date=["01/01/2024"],
        fixed_time=["12:00:00"],
        modifier=0,
        output_series=True,
    )
    assert img_series == []
    assert imgs == []


def test_make_series_one_photo_per_video(extractor):
    img_series, imgs, _, _ = extractor.make_series(
        list_of_images=["a.jpg", "b.jpg", "c.jpg"],
        photos_before_video_updated=True,
        photos_before_video=1,
        fixed_date=["01/01/2024"] * 3,
        fixed_time=["12:00:00"] * 3,
        modifier=0,
        output_series=True,
    )
    assert img_series == ["1-2", "3-4", "5-6"]
    assert imgs == ["a.jpg", "b.jpg", "c.jpg"]


def test_make_series_exact_group(extractor):
    img_series, imgs, _, _ = extractor.make_series(
        list_of_images=["a.jpg", "b.jpg", "c.jpg"],
        photos_before_video_updated=True,
        photos_before_video=3,
        fixed_date=["01/01/2024"] * 3,
        fixed_time=["12:00:00"] * 3,
        modifier=0,
        output_series=True,
    )
    assert img_series == ["1-4"]
    assert imgs == ["c.jpg"]


# fix_time

def test_fix_time_empty_list(extractor):
    dates, times = extractor.fix_time([])
    assert dates == []
    assert times == []


def test_fix_time_invalid_date_raises(extractor):
    with pytest.raises(ValueError):
        extractor.fix_time(["not-a-date"])


def test_fix_time_invalid_calendar_date_raises(extractor):
    with pytest.raises(ValueError):
        extractor.fix_time(["2024:13:45"])


def test_fix_time_with_timezone_suffix(extractor):
    dates, times = extractor.fix_time(["2024:05:15 12:30:45+00:00"])
    assert dates == ["05/15/2024"]
    assert times == ["12:30:45+00:00"]


# clean_name

def test_clean_name_very_long(extractor):
    result = extractor.clean_name("a" * 300)
    assert result.endswith(".xlsx")
    assert len(result) == 205


def test_clean_name_reserved_with_extension(extractor):
    assert extractor.clean_name("CON.xlsx") == "_CON.xlsx"
    assert extractor.clean_name("nul.xlsx") == "_nul.xlsx"
    assert extractor.clean_name("com1.XLSX") == "_com1.XLSX"


def test_clean_name_unicode_preserved(extractor):
    assert extractor.clean_name("café_résumé") == "café_résumé.xlsx"


def test_clean_name_emoji_preserved(extractor):
    assert extractor.clean_name("📸_shoot") == "📸_shoot.xlsx"


# verify_name

def test_verify_name_31_char_collision(extractor):
    name = "a" * 31
    first = extractor.verify_name(name)
    second = extractor.verify_name(name)
    assert len(second) <= 31
    assert first != second


def test_verify_name_only_apostrophes(extractor):
    assert extractor.verify_name("'''") == "Sheet"


def test_verify_name_history_lowercase(extractor):
    assert extractor.verify_name("history") == "History_"


def test_verify_name_history_uppercase(extractor):
    assert extractor.verify_name("HISTORY") == "History_"