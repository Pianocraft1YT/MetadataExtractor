"""Boundary values for Tier-3 EXIF formatting helpers."""

import pytest


@pytest.mark.parametrize(
    "value,expected",
    [
        (0.7, "f/0.7"),
        (1.0, "f/1"),
        (1.4, "f/1.4"),
        (22.0, "f/22"),
        (32.0, "f/32"),
        (1.234, "f/1.234"),
    ],
)
def test_aperture_edge_values(extractor, value, expected):
    assert extractor._format_aperture(value) == expected


@pytest.mark.parametrize("value", [None, 0, -1, -0.5])
def test_aperture_invalid_returns_none(extractor, value):
    assert extractor._format_aperture(value) is None


@pytest.mark.parametrize(
    "value,expected",
    [
        (0.999, "1s"),  # round(0.999, 2) == 1.0 → "1s"
        (1.0, "1s"),
        (1.001, "1.001s"),
        (1.5, "1.5s"),
        (30.0, "30s"),
        (0.5, "1/2"),
        (0.4, "0.4s"),  # 1/0.4 = 2.5, drift too large → decimal
        (0.3, "0.3s"),  # existing
        (0.0333, "1/30"),
        (0.004, "1/250"),
        (0.00025, "1/4000"),
        (0.001, "1/1000"),
    ],
)
def test_exposure_time_boundary_values(extractor, value, expected):
    assert extractor._format_exposure_time(value) == expected


def test_exposure_time_below_one_rounds_cleanly(extractor):
    assert extractor._format_exposure_time(1 / 250) == "1/250"


@pytest.mark.parametrize(
    "value,expected",
    [
        (0.5, "0.5mm"),
        (5.0, "5mm"),
        (5.5, "5.5mm"),
        (200.0, "200mm"),
        (23.456, "23.456mm"),
    ],
)
def test_focal_length_edge_values(extractor, value, expected):
    assert extractor._format_focal_length(value) == expected


@pytest.mark.parametrize("value", [None, 0, -5])
def test_focal_length_invalid_returns_none(extractor, value):
    assert extractor._format_focal_length(value) is None


@pytest.mark.parametrize(
    "value,expected",
    [
        (1, 1),
        (400, 400),
        ("800", 800),
        ((1600,), 1600),
        ([3200], 3200),
    ],
)
def test_iso_accepts_various_shapes(extractor, value, expected):
    assert extractor._format_iso(value) == expected


@pytest.mark.parametrize("value", [None, (), "not-a-number"])
def test_iso_invalid_returns_empty(extractor, value):
    assert extractor._format_iso(value) == ""


@pytest.mark.parametrize(
    "value,expected",
    [
        ((28, 10), 2.8),
        ((56, 10), 5.6),
        ((1, 1), 1.0),
        ((0, 1), 0.0),
    ],
)
def test_rational_to_float_exact(extractor, value, expected):
    assert extractor._rational_to_float(value) == pytest.approx(expected)


def test_rational_to_float_zero_denominator(extractor):
    assert extractor._rational_to_float((5, 0)) is None


def test_rational_to_float_none_numerator(extractor):
    assert extractor._rational_to_float((None, 10)) is None
