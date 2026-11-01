"""Tests for GPS coordinate formatting (EXIF tag 34853 sub-IFD)."""

import pytest

# ---------------------------------------------------------------------------
# Happy path — four cardinal directions
# ---------------------------------------------------------------------------


def test_north_positive(extractor):
    result = extractor._format_gps_coord(((37, 1), (46, 1), (30, 1)), "N")
    assert result == "37.775000"


def test_south_negative(extractor):
    result = extractor._format_gps_coord(((37, 1), (46, 1), (30, 1)), "S")
    assert result == "-37.775000"


def test_east_positive(extractor):
    result = extractor._format_gps_coord(((122, 1), (25, 1), (0, 1)), "E")
    assert result == "122.416667"


def test_west_negative(extractor):
    result = extractor._format_gps_coord(((122, 1), (25, 1), (0, 1)), "W")
    assert result == "-122.416667"


# ---------------------------------------------------------------------------
# Zero-component cases (IFDRational(0, 1) is falsy but valid)
# ---------------------------------------------------------------------------


def test_zero_seconds(extractor):
    result = extractor._format_gps_coord(((37, 1), (46, 1), (0, 1)), "N")
    assert result == "37.766667"


def test_zero_minutes(extractor):
    result = extractor._format_gps_coord(((37, 1), (0, 1), (30, 1)), "N")
    assert result == "37.008333"


def test_zero_seconds_and_minutes(extractor):
    result = extractor._format_gps_coord(((37, 1), (0, 1), (0, 1)), "N")
    assert result == "37.000000"


def test_equator_origin(extractor):
    result = extractor._format_gps_coord(((0, 1), (0, 1), (0, 1)), "N")
    assert result == "0.000000"


# ---------------------------------------------------------------------------
# Precision and formatting
# ---------------------------------------------------------------------------


def test_precision_is_exactly_six_decimals(extractor):
    result = extractor._format_gps_coord(((37, 1), (0, 1), (0, 1)), "N")
    assert result is not None
    assert result.count(".") == 1
    assert len(result.split(".")[1]) == 6


def test_negative_result_includes_minus_sign(extractor):
    result = extractor._format_gps_coord(((37, 1), (46, 1), (30, 1)), "S")
    assert result is not None
    assert result.startswith("-")
    assert result[1].isdigit()


# ---------------------------------------------------------------------------
# Malformed input — every branch returns None, never raises
# ---------------------------------------------------------------------------


def test_none_tuple_returns_none(extractor):
    assert extractor._format_gps_coord(None, "N") is None


def test_none_ref_returns_none(extractor):
    assert extractor._format_gps_coord(((37, 1), (46, 1), (30, 1)), None) is None


def test_empty_string_ref_returns_none(extractor):
    assert extractor._format_gps_coord(((37, 1), (46, 1), (30, 1)), "") is None


def test_whitespace_ref_returns_none(extractor):
    assert extractor._format_gps_coord(((37, 1), (46, 1), (30, 1)), "  ") is None


def test_two_tuple_returns_none(extractor):
    assert extractor._format_gps_coord(((37, 1), (46, 1)), "N") is None


def test_four_tuple_returns_none(extractor):
    assert extractor._format_gps_coord(((37, 1), (46, 1), (30, 1), (0, 1)), "N") is None


def test_empty_tuple_returns_none(extractor):
    assert extractor._format_gps_coord((), "N") is None


def test_list_instead_of_tuple_returns_none(extractor):
    assert extractor._format_gps_coord([37, 46, 30], "N") is None


def test_component_that_fails_conversion_returns_none(extractor):
    result = extractor._format_gps_coord(("bad", (46, 1), (30, 1)), "N")
    assert result is None


def test_zero_denominator_returns_none(extractor):
    result = extractor._format_gps_coord(((37, 0), (46, 1), (30, 1)), "N")
    assert result is None


# ---------------------------------------------------------------------------
# Accepts whatever _rational_to_float accepts
# ---------------------------------------------------------------------------


def test_accepts_plain_integers(extractor):
    result = extractor._format_gps_coord((37, 46, 30), "N")
    assert result == "37.775000"


def test_accepts_plain_floats(extractor):
    result = extractor._format_gps_coord((37.0, 46.0, 30.0), "N")
    assert result == "37.775000"


def test_accepts_mixed_types(extractor):
    result = extractor._format_gps_coord(((37, 1), 46, 30.0), "N")
    assert result == "37.775000"


def test_lowercase_ref_still_works(extractor):
    result = extractor._format_gps_coord(((37, 1), (46, 1), (30, 1)), "n")
    assert result == "37.775000"


def test_bytes_ref_decoded(extractor):
    result = extractor._format_gps_coord(((37, 1), (46, 1), (30, 1)), b"S")
    assert result == "-37.775000"
