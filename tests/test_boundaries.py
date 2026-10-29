"""Boundary-condition tests for MetadataExtractor.fix_time."""


def test_fix_time_empty_list(extractor):
    dates, times = extractor.fix_time([], [], [])
    assert dates == []
    assert times == []


def test_fix_time_invalid_date_preserved(extractor):
    dates, times = extractor.fix_time(["not-a-date"], [None], ["a.jpg"])
    assert dates == ["not-a-date"]
    assert times == [""]


def test_fix_time_invalid_calendar_date_preserved(extractor):
    dates, times = extractor.fix_time(["2024:13:45"], [None], ["a.jpg"])
    assert dates == ["2024:13:45"]
    assert times == [""]


def test_fix_time_with_timezone_suffix_preserved(extractor):
    dates, times = extractor.fix_time(["2024:05:15 12:30:45+00:00"], [None], ["a.jpg"])
    assert dates == ["2024:05:15 12:30:45+00:00"]
    assert times == [""]


def test_fix_time_zero_date_preserved(extractor):
    dates, times = extractor.fix_time(["0000:00:00 00:00:00"], [None], ["a.jpg"])
    assert dates == ["0000:00:00 00:00:00"]
    assert times == [""]