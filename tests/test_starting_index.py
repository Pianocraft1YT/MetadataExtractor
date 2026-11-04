"""Tests for the "Starting index" entry in check_recursive.

Mocks _start_scan rather than the old sort_and_extract_irregular, which
no longer exists after the scanner refactor.
"""

from unittest.mock import MagicMock

import pytest


def _mock_widgets(extractor, series_value, name_value="Filename (default output.filetype)", recursive=False):
    modifier_entry = MagicMock()
    modifier_entry.get.return_value = series_value
    extractor.modifier_entry = modifier_entry

    name_entry = MagicMock()
    name_entry.get.return_value = name_value
    extractor.name_entry = name_entry

    recursive_var = MagicMock()
    recursive_var.get.return_value = recursive
    extractor.recursive_var = recursive_var

    keepopen_var = MagicMock()
    keepopen_var.get.return_value = False
    extractor.keepopen_var = keepopen_var

    maxdepth_entry = MagicMock()
    maxdepth_entry.get.return_value = "Recursion Depth (#)"
    extractor.maxdepth_entry = maxdepth_entry


def _capture_errors(monkeypatch):
    errors = []
    monkeypatch.setattr(
        "metadata.messagebox.showerror",
        lambda *a, **k: errors.append(a[0] if a else k.get("title", "")),
    )
    return errors


@pytest.mark.parametrize("value", ["0", "abc", "-1", "5.5", "1.0", ""])
def test_invalid_starting_index_rejected(extractor, monkeypatch, tmp_path, value):
    _mock_widgets(extractor, series_value=value)
    errors = _capture_errors(monkeypatch)

    extractor.directory_path = tmp_path
    extractor.output_path = tmp_path
    extractor.check_recursive()

    assert errors, f"expected rejection for {value!r}"


@pytest.mark.parametrize(
    "value,expected_modifier",
    [("1", 0), ("5", 4), ("100", 99)],
)
def test_valid_starting_index_accepted(extractor, monkeypatch, tmp_path, value, expected_modifier):
    _mock_widgets(extractor, series_value=value)
    (tmp_path / "IMG_001.jpg").write_bytes(b"fake")

    captured = {}

    def fake_start(recursive, final_output, modifier, *args, **kwargs):
        captured["modifier"] = modifier

    extractor._start_scan = fake_start

    extractor.directory_path = tmp_path
    extractor.output_path = tmp_path
    extractor.check_recursive()

    assert captured.get("modifier") == expected_modifier, f"value={value!r} should give modifier={expected_modifier}"
