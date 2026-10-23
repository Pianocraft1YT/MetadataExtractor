"""Boundary-condition tests for MetadataExtractor.fix_time."""


def test_fix_time_empty_list(extractor):
    dates, times = extractor.fix_time([], [])
    assert dates == []
    assert times == []


def test_fix_time_invalid_date_preserved(extractor):
    """Code catches ValueError and preserves raw string (not raise).

    Real EXIF often contains '0000:00:00 00:00:00' or malformed strings;
    killing the batch would be hostile, so preserve-and-continue is correct.
    """
    dates, times = extractor.fix_time(["not-a-date"], [None])
    assert dates == ["not-a-date"]
    assert times == [""]


def test_fix_time_invalid_calendar_date_preserved(extractor):
    """Month 13 fails strptime; raw string preserved."""
    dates, times = extractor.fix_time(["2024:13:45"], [None])
    assert dates == ["2024:13:45"]
    assert times == [""]


def test_fix_time_with_timezone_suffix_preserved(extractor):
    """EXIF OffsetTime is a separate tag, not embedded. Suffix breaks strptime → preserved."""
    dates, times = extractor.fix_time(["2024:05:15 12:30:45+00:00"], [None])
    assert dates == ["2024:05:15 12:30:45+00:00"]
    assert times == [""]


def test_fix_time_zero_date_preserved(extractor):
    dates, times = extractor.fix_time(["0000:00:00 00:00:00"], [None])
    assert dates == ["0000:00:00 00:00:00"]
    assert times == [""]
