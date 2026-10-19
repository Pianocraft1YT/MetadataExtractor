"""
Boundary-value tests for the pure helper functions.
"""

import pytest

import metadata


# ---------------------------------------------------------------------------
# make_series boundaries
# ---------------------------------------------------------------------------

def test_make_series_zero_images():
    img_series, imgs, dates, times = metadata.make_series(
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


def test_make_series_one_image_all_photos_mode():
    img_series, imgs, _, _ = metadata.make_series(
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


def test_make_series_one_image_series_mode_incomplete_group():
    """photos_before_video=3, only 1 image → no complete group."""
    img_series, imgs, _, _ = metadata.make_series(
        list_of_images=["a.jpg"],
        photos_before_video_updated=True,
        photos_before_video=3,
        fixed_date=["01/01/2024"],
        fixed_time=["12:00:00"],
        modifier=0,
        output_series=True,
    )
    # i=1 only; 1 % 3 != 0 → no append. So empty.
    assert img_series == []
    assert imgs == []


def test_make_series_one_photo_per_video():
    """photos_before_video=1 → each image + its video forms a 2-file group."""
    img_series, imgs, _, _ = metadata.make_series(
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


def test_make_series_exact_group():
    """3 images, N=3 → exactly one group."""
    img_series, imgs, _, _ = metadata.make_series(
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


# ---------------------------------------------------------------------------
# fix_time boundaries
# ---------------------------------------------------------------------------

def test_fix_time_empty_list():
    dates, times = metadata.fix_time([])
    assert dates == []
    assert times == []


def test_fix_time_invalid_date_raises():
    """Malformed date → pandas raises. Record that behavior."""
    with pytest.raises(ValueError):
        metadata.fix_time(["not-a-date"])


def test_fix_time_invalid_calendar_date_raises():
    with pytest.raises(ValueError):
        metadata.fix_time(["2024:13:45"])


def test_fix_time_with_timezone_suffix():
    """
    '2024:05:15 12:30:45+00:00' — the date part still parses as %Y:%m:%d,
    but the time part lands in fixed_time as-is.
    """
    dates, times = metadata.fix_time(["2024:05:15 12:30:45+00:00"])
    assert dates == ["05/15/2024"]
    assert times == ["12:30:45+00:00"]


# ---------------------------------------------------------------------------
# clean_name boundaries
# ---------------------------------------------------------------------------

def test_clean_name_very_long():
    """Long names get their stem truncated to 200 chars."""
    long_name = "a" * 300
    result = metadata.clean_name(long_name)
    assert result.endswith(".xlsx")
    assert len(result) == 205  # 200 + len(".xlsx")


def test_clean_name_reserved_with_extension():
    """'CON.xlsx' must be sanitized — Windows rejects it otherwise."""
    assert metadata.clean_name("CON.xlsx") == "_CON.xlsx"
    assert metadata.clean_name("nul.xlsx") == "_nul.xlsx"
    assert metadata.clean_name("com1.XLSX") == "_com1.XLSX"  # extension case preserved


def test_clean_name_unicode_preserved():
    result = metadata.clean_name("café_résumé")
    assert result == "café_résumé.xlsx"


def test_clean_name_emoji_preserved():
    result = metadata.clean_name("📸_shoot")
    assert result == "📸_shoot.xlsx"


# ---------------------------------------------------------------------------
# verify_name boundaries
# ---------------------------------------------------------------------------

def test_verify_name_31_char_collision():
    metadata.used.clear()
    name = "a" * 31
    first = metadata.verify_name(name)
    second = metadata.verify_name(name)
    # Second should be truncated + suffixed, still ≤31 chars.
    assert len(second) <= 31
    assert first != second


def test_verify_name_only_apostrophes():
    metadata.used.clear()
    result = metadata.verify_name("'''")
    # strip("'") on "'''" gives "" → falls back to "Sheet".
    assert result == "Sheet"


def test_verify_name_history_lowercase():
    metadata.used.clear()
    assert metadata.verify_name("history") == "History_"


def test_verify_name_history_uppercase():
    metadata.used.clear()
    assert metadata.verify_name("HISTORY") == "History_"