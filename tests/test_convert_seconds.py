"""Direct tests for _convert_seconds."""

import pytest


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0, "Almost done"),
        (1, "Almost done"),
        (4, "Almost done"),
        (5, "5 second(s)"),
        (59, "59 second(s)"),
        (60, "1 minute(s)"),
        (61, "1 minute(s), 1 second(s)"),
        (119, "1 minute(s), 59 second(s)"),
        (120, "2 minute(s)"),
        (3600, "1 hour(s)"),
        (3661, "1 hour(s), 1 minute(s), 1 second(s)"),
        (86399, "23 hour(s), 59 minute(s), 59 second(s)"),
        (86400, "1 day(s)"),
        (90061, "1 day(s), 1 hour(s), 1 minute(s), 1 second(s)"),
    ],
)
def test_convert_seconds(extractor, seconds, expected):
    assert extractor._convert_seconds(seconds) == expected
