"""Tests for small helpers used by the output pipeline."""

import pytest

# ---------------------------------------------------------------------------
# natural_key
# ---------------------------------------------------------------------------


def test_natural_key_numeric_sort(extractor):
    names = ["IMG_10.jpg", "IMG_2.jpg", "IMG_1.jpg"]
    sorted_names = sorted(names, key=lambda x: extractor.natural_key(x))
    assert sorted_names == ["IMG_1.jpg", "IMG_2.jpg", "IMG_10.jpg"]


def test_natural_key_case_insensitive(extractor):
    assert extractor.natural_key("IMG_1") == extractor.natural_key("img_1")


def test_natural_key_no_digits(extractor):
    assert extractor.natural_key("abc") == [(0, "abc")]


# ---------------------------------------------------------------------------
# is_number
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["1", "1.5", "-3", "0", "1e5"])
def test_is_number_true(value):
    from metadata import MetadataExtractor

    assert MetadataExtractor.is_number(value) is True


@pytest.mark.parametrize("value", ["", "abc", "1.2.3", "1 2"])
def test_is_number_false(value):
    from metadata import MetadataExtractor

    assert MetadataExtractor.is_number(value) is False


# ---------------------------------------------------------------------------
# _rational_to_float
# ---------------------------------------------------------------------------


def test_rational_to_float_tuple(extractor):
    assert extractor._rational_to_float((28, 10)) == 2.8


def test_rational_to_float_none(extractor):
    assert extractor._rational_to_float(None) is None


def test_rational_to_float_zero_denominator(extractor):
    assert extractor._rational_to_float((5, 0)) is None


def test_rational_to_float_plain_int(extractor):
    assert extractor._rational_to_float(7) == 7.0


def test_rational_to_float_plain_float(extractor):
    assert extractor._rational_to_float(3.14) == 3.14


def test_rational_to_float_bad_string(extractor):
    assert extractor._rational_to_float("not a number") is None


def test_rational_to_float_wrong_tuple_length(extractor):
    assert extractor._rational_to_float((1, 2, 3)) is None


# ---------------------------------------------------------------------------
# _sanitize_for_filename
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Trip_A", "Trip_A"),
        ("Trip:A", "Trip_A"),
        ("Trip/A", "Trip_A"),
        ("Trip*A", "Trip_A"),
        ("Trip?A", "Trip_A"),
        ("Trip<A>", "Trip_A_"),
        ("Trip|A", "Trip_A"),
        ('Trip"A', "Trip_A"),
        ("trailing.", "trailing"),
        ("a.b.c", "a.b.c"),
    ],
)
def test_sanitize_for_filename(raw, expected):
    from metadata import MetadataExtractor

    # Signature is (name, used) — pass a fresh set per call so dedupe state
    # doesn't leak between parametrized cases.
    assert MetadataExtractor._sanitize_for_filename(raw, set()) == expected


# ---------------------------------------------------------------------------
# clean_name — dotfile / extension-only edge cases
# ---------------------------------------------------------------------------


def test_clean_name_dotfile_keeps_name_and_appends_ext(extractor):
    """Non-extension dotfiles keep their stem instead of being replaced with 'output'."""
    assert extractor.clean_name(".hidden") == ".hidden.xlsx"


def test_clean_name_bare_extension_normalized_to_output(extractor):
    assert extractor.clean_name(".xlsx") == "output.xlsx"
    assert extractor.clean_name("..xlsx") == "output.xlsx"


def test_clean_name_dotfile_multi_dot_keeps_stem(extractor):
    """Two or more dots means the leading dot isn't the extension marker,
    so the stem survives (with dots treated as regular characters)."""
    result = extractor.clean_name(".archive.tar")
    assert result.startswith(".archive")
    assert result.endswith(".xlsx")


def test_clean_name_long_stem_truncated(extractor):
    long_name = "a" * 300
    result = extractor.clean_name(long_name)
    stem = result.removesuffix(".xlsx")
    assert len(stem) <= 200
    assert result.endswith(".xlsx")


def test_clean_name_markdown_mode_with_no_stem_falls_back_to_output(extractor):
    extractor.filetype_var.set("Markdown")
    assert extractor.clean_name("") == "output.md"
