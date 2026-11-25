"""Tests for GPS Altitude formatting and extraction (v4.9.0)."""

import pytest


def test_format_gps_altitude_above_sea_level(extractor):
    assert extractor._format_gps_altitude((1245, 10), "+") == "124.5 m"
    assert extractor._format_gps_altitude(100.0, "+") == "100.0 m"
    assert extractor._format_gps_altitude(100.0, None) == "100.0 m"
    assert extractor._format_gps_altitude(100.0, "") == "100.0 m"


def test_format_gps_altitude_below_sea_level(extractor):
    assert extractor._format_gps_altitude((120, 10), "-") == "-12.0 m"
    assert extractor._format_gps_altitude(50.0, "-") == "-50.0 m"


def test_format_gps_altitude_invalid_returns_none(extractor):
    assert extractor._format_gps_altitude(None, "+") is None
    assert extractor._format_gps_altitude((5, 0), "+") is None
    assert extractor._format_gps_altitude("not-a-number", "+") is None
    assert extractor._format_gps_altitude(float("nan"), "+") is None
    assert extractor._format_gps_altitude(float("inf"), "+") is None
    assert extractor._format_gps_altitude(float("-inf"), "-") is None
