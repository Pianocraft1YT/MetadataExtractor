"""
Tests for the "Starting index" entry in check_recursive.

Policy: integer > 0 is accepted, everything else shows an error and
aborts the run. "0" is rejected.
"""

from unittest.mock import MagicMock

import pytest

import metadata


def _mock_widgets(monkeypatch, series_value, name_value="Filename (default output.xlsx)", recursive=False):
    for name, value in [
        ("series_entry", series_value),
        ("name_entry", name_value),
    ]:
        m = MagicMock()
        m.get.return_value = value
        monkeypatch.setattr(metadata, name, m)

    rv = MagicMock()
    rv.get.return_value = recursive
    monkeypatch.setattr(metadata, "recursive_var", rv)

    keep = MagicMock()
    keep.get.return_value = False
    monkeypatch.setattr(metadata, "keepopen_var", keep)


def _capture_errors(monkeypatch):
    errors = []
    monkeypatch.setattr(
        metadata.messagebox, "showerror",
        lambda *a, **k: errors.append(a[0] if a else k.get("title", "")),
    )
    return errors


@pytest.mark.parametrize("value", ["0", "abc", "-1", "5.5", "1.0", ""])
def test_invalid_starting_index_rejected(value, monkeypatch, tmp_path):
    _mock_widgets(monkeypatch, series_value=value)
    errors = _capture_errors(monkeypatch)

    metadata.output_path = tmp_path
    metadata.check_recursive(tmp_path)

    assert errors, f"expected rejection for {value!r}"


@pytest.mark.parametrize("value,expected_modifier", [
    ("1", 0),
    ("5", 4),
    ("100", 99),
])
def test_valid_starting_index_accepted(value, expected_modifier, monkeypatch, tmp_path):
    _mock_widgets(monkeypatch, series_value=value)

    # check_recursive requires at least one photo, otherwise it takes the
    # "Empty directory" branch and never calls the scanner.
    (tmp_path / "IMG_001.jpg").write_bytes(b"fake")

    captured = {}
    def fake_scan(dp, r, fo, m):
        captured["modifier"] = m
        return 0, 0

    monkeypatch.setattr(metadata, "sort_and_extract_irregular", fake_scan)

    metadata.output_path = tmp_path
    metadata.check_recursive(tmp_path)

    assert captured.get("modifier") == expected_modifier, (
        f"value={value!r} should give modifier={expected_modifier}"
    )