"""Tests for clean_name (filename) and verify_name (sheet name)."""

import metadata


# ---------------------------------------------------------------------------
# clean_name — Windows-safe output filenames
# ---------------------------------------------------------------------------

def test_clean_name_appends_xlsx():
    assert metadata.clean_name("report") == "report.xlsx"


def test_clean_name_leaves_existing_extension():
    assert metadata.clean_name("report.xlsx") == "report.xlsx"


def test_clean_name_case_insensitive_extension():
    assert metadata.clean_name("report.XLSX") == "report.XLSX"


def test_clean_name_replaces_illegal_chars():
    assert metadata.clean_name("my:file?name") == "my_file_name.xlsx"


def test_clean_name_falls_back_when_all_illegal():
    # "///" becomes "___" which is still a valid (if ugly) name.
    # Only whitespace/dots-only input triggers the fallback.
    assert metadata.clean_name("...") == "output.xlsx"
    assert metadata.clean_name("   ") == "output.xlsx"

def test_clean_name_reserved_windows_name():
    assert metadata.clean_name("CON") == "_CON.xlsx"


def test_clean_name_reserved_lowercase():
    assert metadata.clean_name("con") == "_con.xlsx"


def test_clean_name_strips_trailing_dots():
    assert metadata.clean_name("report...") == "report.xlsx"


def test_clean_name_strips_whitespace():
    assert metadata.clean_name("   spaced   ") == "spaced.xlsx"


def test_clean_name_empty_uses_default():
    assert metadata.clean_name("") == "output.xlsx"


# ---------------------------------------------------------------------------
# verify_name — Excel sheet name sanitization
# ---------------------------------------------------------------------------

def test_verify_name_normal():
    metadata.used.clear()
    assert metadata.verify_name("Vacation") == "Vacation"


def test_verify_name_replaces_illegal_chars():
    metadata.used.clear()
    assert metadata.verify_name("Trip:2024") == "Trip_2024"


def test_verify_name_history_reserved():
    metadata.used.clear()
    assert metadata.verify_name("History") == "History_"


def test_verify_name_truncates_to_31_chars():
    metadata.used.clear()
    long_name = "a" * 40
    result = metadata.verify_name(long_name)
    assert len(result) == 31


def test_verify_name_duplicate_suffix():
    metadata.used.clear()
    assert metadata.verify_name("Trip") == "Trip"
    assert metadata.verify_name("Trip") == "Trip_2"
    assert metadata.verify_name("Trip") == "Trip_3"


def test_verify_name_strips_apostrophes():
    metadata.used.clear()
    assert metadata.verify_name("'rare'") == "rare"


def test_verify_name_empty_becomes_sheet():
    metadata.used.clear()
    assert metadata.verify_name("") == "Sheet"


def test_verify_name_31_char_name_unchanged():
    metadata.used.clear()
    name = "x" * 31
    assert metadata.verify_name(name) == name