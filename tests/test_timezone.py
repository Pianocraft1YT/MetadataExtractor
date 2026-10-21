"""Timezone offset adjustment in MetadataExtractor.fix_time.

EXIF `OffsetTimeOriginal` = local − UTC (spec: ±HH:MM).
Converting to UTC subtracts a positive offset, adds a negative one.
"""
import pytest


@pytest.mark.parametrize("raw, offset, expect_date, expect_time", [
    # Positive offset: local → UTC subtracts
    ("2024:01:31 14:30:00", "+05:30", "01/31/2024", "09:00:00"),
    ("2024:01:31 14:30:00", "+00:00", "01/31/2024", "14:30:00"),

    # Negative offset: local → UTC adds
    ("2024:01:31 14:30:00", "-08:00", "01/31/2024", "22:30:00"),

    # Day rollover forward
    ("2024:01:31 22:00:00", "-05:00", "02/01/2024", "03:00:00"),

    # Day rollover backward
    ("2024:02:01 02:00:00", "+05:00", "01/31/2024", "21:00:00"),

    # Month rollover (April = 30 days)
    ("2024:04:30 23:00:00", "-02:00", "05/01/2024", "01:00:00"),

    # Year rollover
    ("2024:12:31 23:00:00", "-02:00", "01/01/2025", "01:00:00"),

    # Leap year: Feb 28 → Feb 29
    ("2024:02:28 23:00:00", "-02:00", "02/29/2024", "01:00:00"),

    # Non-leap year: Feb 28 → Mar 1
    ("2023:02:28 23:00:00", "-02:00", "03/01/2023", "01:00:00"),

    # Half-hour offsets (India, Newfoundland)
    ("2024:01:31 12:00:00", "+05:30", "01/31/2024", "06:30:00"),
    ("2024:01:31 12:00:00", "-03:30", "01/31/2024", "15:30:00"),
])
def test_offset_applied_when_timezone_on(
        extractor_tz_on, raw, offset, expect_date, expect_time):
    dates, times = extractor_tz_on.fix_time([raw], [offset])
    assert dates == [expect_date]
    assert times == [expect_time]


def test_offset_ignored_when_timezone_off(extractor_tz_off):
    """timezone_var.get() == False → raw EXIF time passes through unchanged."""
    dates, times = extractor_tz_off.fix_time(["2024:01:31 14:30:00"], ["+05:30"])
    assert dates == ["01/31/2024"]
    assert times == ["14:30:00"]


def test_none_offset_no_change(extractor_tz_on):
    dates, times = extractor_tz_on.fix_time(["2024:01:31 14:30:00"], [None])
    assert dates == ["01/31/2024"]
    assert times == ["14:30:00"]


def test_empty_offset_no_change(extractor_tz_on):
    dates, times = extractor_tz_on.fix_time(["2024:01:31 14:30:00"], [""])
    assert dates == ["01/31/2024"]
    assert times == ["14:30:00"]


def test_multiple_images_use_matching_offsets(extractor_tz_on):
    """Offset list indexed per-image, not globally applied."""
    dates, times = extractor_tz_on.fix_time(
        ["2024:01:31 14:30:00", "2024:01:31 14:30:00"],
        ["+05:30", "-08:00"],
    )
    assert dates == ["01/31/2024", "01/31/2024"]
    assert times == ["09:00:00", "22:30:00"]