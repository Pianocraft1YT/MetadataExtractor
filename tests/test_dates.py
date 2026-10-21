"""Tests for MetadataExtractor.fix_time — date/time splitting & formatting."""


def test_standard_date_and_time(extractor):
    dates, times = extractor.fix_time(["2024:05:15 12:30:45"], [None])
    assert dates == ["05/15/2024"]
    assert times == ["12:30:45"]


def test_date_only_gets_empty_time(extractor):
    dates, times = extractor.fix_time(["2024:05:15"], [None])
    assert dates == ["05/15/2024"]
    assert times == [""]


def test_multiple_dates_preserve_order(extractor):
    dates, times = extractor.fix_time(
        ["2024:05:15 12:30:45",
         "2024:05:16 08:00:00",
         "2024:05:14 23:59:59"],
        [None, None, None],
    )
    assert dates == ["05/15/2024", "05/16/2024", "05/14/2024"]
    assert times == ["12:30:45", "08:00:00", "23:59:59"]


def test_leap_year_date(extractor):
    dates, times = extractor.fix_time(["2024:02:29 00:00:00"], [None])
    assert dates == ["02/29/2024"]
    assert times == ["00:00:00"]


def test_lists_stay_in_sync_on_mixed_inputs(extractor):
    """Regression: both output lists must have one entry per input."""
    raw = [
        "2024:05:15 12:30:45",     # normal
        "0000:00:00 00:00:00",     # zero EXIF date
        "2024:05:15",              # date-only
        "garbage",                 # garbage
    ]
    dates, times = extractor.fix_time(raw, [None, None, None, None])
    assert len(dates) == len(times) == len(raw)