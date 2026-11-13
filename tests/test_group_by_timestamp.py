"""Direct tests for MetadataExtractor.group_by_timestamp."""

from datetime import datetime, timedelta

import pytest


def _dt(day, hour=12, minute=0, second=0):
    return datetime(2024, 5, day, hour, minute, second)


def test_empty_returns_empty(extractor):
    assert extractor.group_by_timestamp([], 2.0) == []


def test_single_entry_one_group(extractor):
    groups = extractor.group_by_timestamp([(_dt(15), "a.jpg")], 2.0)
    assert len(groups) == 1
    assert len(groups[0]) == 1


def test_within_cutoff_groups_together(extractor):
    entries = [(_dt(15, 12, 0, 0), "a.jpg"), (_dt(15, 12, 0, 1), "b.jpg")]
    groups = extractor.group_by_timestamp(entries, 2.0)
    assert len(groups) == 1
    assert {g[1] for g in groups[0]} == {"a.jpg", "b.jpg"}


def test_exact_cutoff_boundary_groups_together(extractor):
    """Diff == cutoff should still group (<= not <)."""
    entries = [(_dt(15, 12, 0, 0), "a.jpg"), (_dt(15, 12, 0, 2), "b.jpg")]
    groups = extractor.group_by_timestamp(entries, 2.0)
    assert len(groups) == 1


def test_just_over_cutoff_splits(extractor):
    entries = [(_dt(15, 12, 0, 0), "a.jpg"), (_dt(15, 12, 0, 3), "b.jpg")]
    groups = extractor.group_by_timestamp(entries, 2.0)
    assert len(groups) == 2


def test_zero_cutoff_splits_any_difference(extractor):
    entries = [(_dt(15, 12, 0, 0), "a.jpg"), (_dt(15, 12, 0, 1), "b.jpg")]
    groups = extractor.group_by_timestamp(entries, 0.0)
    assert len(groups) == 2


def test_entries_are_sorted_by_timestamp(extractor):
    """Unsorted input must still yield chronologically ordered groups.
    With cutoff 2.0 the two timestamps (4h apart) land in separate
    groups; what matters is that they appear in the right order."""
    entries = [
        (_dt(15, 14, 0, 0), "late.jpg"),
        (_dt(15, 10, 0, 0), "early.jpg"),
    ]
    groups = extractor.group_by_timestamp(entries, 2.0)
    assert len(groups) == 2
    assert groups[0][0][1] == "early.jpg"
    assert groups[1][0][1] == "late.jpg"


def test_negative_cutoff_raises(extractor):
    with pytest.raises(ValueError):
        extractor.group_by_timestamp([(_dt(15), "a.jpg")], -1.0)


def test_transitive_chaining(extractor):
    """A-B within 2s and B-C within 2s puts all three in one group,
    even though A-C is 4s apart (pairwise chaining)."""
    entries = [
        (_dt(15, 12, 0, 0), "a.jpg"),
        (_dt(15, 12, 0, 2), "b.jpg"),
        (_dt(15, 12, 0, 4), "c.jpg"),
    ]
    groups = extractor.group_by_timestamp(entries, 2.0)
    assert len(groups) == 1
    assert [g[1] for g in groups[0]] == ["a.jpg", "b.jpg", "c.jpg"]
