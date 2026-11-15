"""Internal invariants: reset, _empty_scan_data freshness, natural_key,
_sanitize_for_filename reserved names, group_by_timestamp tie-breaking.
"""

from datetime import datetime, timedelta
import pytest

# ---------------------------------------------------------------------------
# _empty_scan_data â€” must return a fresh dict every call
# ---------------------------------------------------------------------------


def test_empty_scan_data_returns_fresh_dict(extractor):
    d1 = extractor._empty_scan_data()
    d1["Images"].append("sentinel.jpg")
    assert extractor._empty_scan_data()["Images"] == []


def test_empty_scan_data_all_values_are_lists(extractor):
    for key, val in extractor._empty_scan_data().items():
        assert isinstance(val, list), f"{key} = {type(val).__name__}"


# ---------------------------------------------------------------------------
# reset â€” clears all scan state
# ---------------------------------------------------------------------------


def test_reset_clears_used_sheet_names(extractor):
    extractor.used.add("taken")
    extractor.reset()
    assert extractor.used == set()


def test_reset_clears_results(extractor):
    extractor.results.append(("df", "Sheet", "/tmp"))
    extractor.reset()
    assert extractor.results == []


def test_reset_clears_warnings(extractor):
    extractor.collected_warnings["Scan Error"].append("bad.jpg")
    extractor.reset()
    assert len(extractor.collected_warnings) == 0


def test_reset_clears_counters_and_cleanup_flag(extractor):
    extractor.total_processed = 50
    extractor.total_skipped = 5
    extractor.total_files = 100
    extractor._cleanup_pending = True
    extractor.reset()
    assert (extractor.total_processed, extractor.total_skipped, extractor.total_files) == (0, 0, 0)
    assert extractor._cleanup_pending is False


def test_reset_restores_default_sheet_name(extractor):
    extractor.current_sheet_name = "Trip_A"
    extractor.reset()
    assert extractor.current_sheet_name == "Sheet"


# ---------------------------------------------------------------------------
# natural_key â€” mixed alpha/numeric sequences
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("a1b2c3", [(0, "a"), (1, 1), (0, "b"), (1, 2), (0, "c"), (1, 3), (0, "")]),
        ("IMG_0001", [(0, "img_"), (1, 1), (0, "")]),
        ("IMG_0001.jpg", [(0, "img_"), (1, 1), (0, ".jpg")]),
        ("", [(0, "")]),
        ("123", [(0, ""), (1, 123), (0, "")]),
        ("ABC", [(0, "abc")]),
    ],
)
def test_natural_key_components(extractor, raw, expected):
    assert extractor.natural_key(raw) == expected


def test_natural_key_preserves_leading_zeros(extractor):
    assert extractor.natural_key("IMG_001") == extractor.natural_key("IMG_1")


# ---------------------------------------------------------------------------
# _sanitize_for_filename â€” Windows reserved names
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reserved",
    [
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    ],
)
def test_sanitize_reserved_windows_names(reserved):
    from metadata import MetadataExtractor

    assert MetadataExtractor._sanitize_for_filename(reserved, set()) == "_" + reserved


def test_sanitize_reserved_case_insensitive():
    from metadata import MetadataExtractor

    assert MetadataExtractor._sanitize_for_filename("con", set()) == "_con"
    assert MetadataExtractor._sanitize_for_filename("Con", set()) == "_Con"


def test_sanitize_dedupes_identical_names():
    from metadata import MetadataExtractor

    used = set()
    assert MetadataExtractor._sanitize_for_filename("Trip", used) == "Trip"
    assert MetadataExtractor._sanitize_for_filename("Trip", used) == "Trip_2"
    assert MetadataExtractor._sanitize_for_filename("Trip", used) == "Trip_3"


def test_sanitize_empty_becomes_underscore():
    from metadata import MetadataExtractor

    assert MetadataExtractor._sanitize_for_filename("", set()) == "_"


def test_sanitize_all_illegal_becomes_underscores():
    from metadata import MetadataExtractor

    assert MetadataExtractor._sanitize_for_filename('<>:"/\\|?*', set()) == "_" * 9


# ---------------------------------------------------------------------------
# group_by_timestamp â€” ties and stability
# ---------------------------------------------------------------------------


def test_identical_timestamps_group_together(extractor):
    ts = datetime(2024, 5, 15, 12, 0, 0)
    groups = extractor.group_by_timestamp([(ts, "a.jpg"), (ts, "b.jpg"), (ts, "c.jpg")], 0.0)
    assert len(groups) == 1


def test_input_order_reordered_chronologically(extractor):
    base = datetime(2024, 5, 15, 12, 0, 0)
    entries = [
        (base + timedelta(seconds=1), "b.jpg"),
        (base, "a.jpg"),
        (base + timedelta(seconds=2), "c.jpg"),
    ]
    groups = extractor.group_by_timestamp(entries, 2.0)
    assert len(groups) == 1
    assert [f for _, f in groups[0]] == ["a.jpg", "b.jpg", "c.jpg"]


def test_cutoff_as_int_works(extractor):
    ts = datetime(2024, 5, 15, 12, 0, 0)
    assert len(extractor.group_by_timestamp([(ts, "a.jpg"), (ts, "b.jpg")], 2)) == 1
