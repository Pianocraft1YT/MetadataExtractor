"""Tests for fix_time — EXIF date → spreadsheet date + time."""

import metadata


def test_standard_date_and_time():
    dates, times = metadata.fix_time(["2024:05:15 12:30:45"])
    assert dates == ["05/15/2024"]
    assert times == ["12:30:45"]


def test_date_only_gets_empty_time():
    dates, times = metadata.fix_time(["2024:05:15"])
    assert dates == ["05/15/2024"]
    assert times == [""]


def test_multiple_dates_preserve_order():
    dates, times = metadata.fix_time([
        "2024:01:01 08:00:00",
        "2024:06:15 14:30:00",
        "2024:12:31 23:59:59",
    ])
    assert dates == ["01/01/2024", "06/15/2024", "12/31/2024"]
    assert times == ["08:00:00", "14:30:00", "23:59:59"]


def test_leap_year_date():
    dates, times = metadata.fix_time(["2024:02:29 00:00:00"])
    assert dates == ["02/29/2024"]

