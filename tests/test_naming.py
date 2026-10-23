"""Tests for clean_name (filename) and verify_name (sheet name)."""

# clean_name


def test_clean_name_appends_xlsx(extractor):
    assert extractor.clean_name("report") == "report.xlsx"


def test_clean_name_leaves_existing_extension(extractor):
    assert extractor.clean_name("report.xlsx") == "report.xlsx"


def test_clean_name_case_insensitive_extension(extractor):
    assert extractor.clean_name("report.XLSX") == "report.XLSX"


def test_clean_name_replaces_illegal_chars(extractor):
    assert extractor.clean_name("my:file?name") == "my_file_name.xlsx"


def test_clean_name_falls_back_when_all_illegal(extractor):
    assert extractor.clean_name("...") == "output.xlsx"
    assert extractor.clean_name("   ") == "output.xlsx"


def test_clean_name_reserved_windows_name(extractor):
    assert extractor.clean_name("CON") == "_CON.xlsx"


def test_clean_name_reserved_lowercase(extractor):
    assert extractor.clean_name("con") == "_con.xlsx"


def test_clean_name_strips_trailing_dots(extractor):
    assert extractor.clean_name("report...") == "report.xlsx"


def test_clean_name_strips_whitespace(extractor):
    assert extractor.clean_name("   spaced   ") == "spaced.xlsx"


def test_clean_name_empty_uses_default(extractor):
    assert extractor.clean_name("") == "output.xlsx"


# verify_name — each test gets its own local set, no shared state


def test_verify_name_normal(extractor):
    assert extractor.verify_name("Vacation", set()) == "Vacation"


def test_verify_name_replaces_illegal_chars(extractor):
    assert extractor.verify_name("Trip:2024", set()) == "Trip_2024"


def test_verify_name_history_reserved(extractor):
    assert extractor.verify_name("History", set()) == "History_"


def test_verify_name_truncates_to_31_chars(extractor):
    result = extractor.verify_name("a" * 40, set())
    assert len(result) == 31


def test_verify_name_duplicate_suffix(extractor):
    used = set()
    assert extractor.verify_name("Trip", used) == "Trip"
    assert extractor.verify_name("Trip", used) == "Trip_2"
    assert extractor.verify_name("Trip", used) == "Trip_3"


def test_verify_name_strips_apostrophes(extractor):
    assert extractor.verify_name("'rare'", set()) == "rare"


def test_verify_name_empty_becomes_sheet(extractor):
    assert extractor.verify_name("", set()) == "Sheet"


def test_verify_name_31_char_name_unchanged(extractor):
    name = "x" * 31
    assert extractor.verify_name(name, set()) == name
