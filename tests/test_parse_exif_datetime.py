"""Direct tests for MetadataExtractor._parse_exif_datetime."""

from datetime import datetime
import pytest


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2024:05:15 12:30:45", (datetime(2024, 5, 15, 12, 30, 45), True)),
        ("2024:05:15", (datetime(2024, 5, 15), False)),
        ("2024:05:15 ", (datetime(2024, 5, 15), False)),
        ("2024:05:15 12:30:45.123456", (datetime(2024, 5, 15, 12, 30, 45, 123456), True)),
        ("2024:02:29 00:00:00", (datetime(2024, 2, 29), True)),
    ],
)
def test_parses_valid_formats(extractor, raw, expected):
    assert extractor._parse_exif_datetime(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "garbage",
        "2024/05/15 12:30:45",
        "2024:13:45 12:30:45",
        "2024:02:30 00:00:00",
        "2023:02:29 00:00:00",
        "0000:00:00 00:00:00",
        "",
    ],
)
def test_returns_none_for_invalid(extractor, raw):
    assert extractor._parse_exif_datetime(raw) == (None, False)


def test_none_input(extractor):
    assert extractor._parse_exif_datetime(None) == (None, False)


def test_bytes_input_does_not_match(extractor):
    assert extractor._parse_exif_datetime(b"2024:05:15 12:30:45") == (None, False)


def test_datetime_input_uses_dashes_not_colons(extractor):
    """str(datetime) renders with '-' separators → doesn't match the EXIF
    ':' format → (None, False). Callers pass raw strings, not datetimes."""
    assert extractor._parse_exif_datetime(datetime(2024, 5, 15, 12, 30, 45)) == (None, False)
