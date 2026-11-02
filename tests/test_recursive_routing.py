"""
Regression tests for check_recursive's filetype routing.

Before the fix: `if filetype != "CSV" or filetype != "Markdown":` was always
True, so the "Multiple X Files" prompt was dead code for CSV and Markdown.
These tests would all fail against that bug.
"""

from unittest.mock import MagicMock

import pytest


def _mock_widgets(extractor, filetype, recursive):
    extractor.filetype_var.set(filetype)
    extractor.recursive_var = MagicMock()
    extractor.recursive_var.get.return_value = recursive
    extractor.modifier_entry = MagicMock()
    extractor.modifier_entry.get.return_value = "Starting index (Img # Series)"
    extractor.maxdepth_entry = MagicMock()
    extractor.maxdepth_entry.get.return_value = "1"
    extractor.name_entry = MagicMock()
    extractor.name_entry.get.return_value = "Filename (default output.filetype)"
    extractor.keepopen_var.set(True)
    extractor.hyperlink_var.set(False)  # silence the CSV/JSON/Markdown hyperlink warning
    extractor.directory_path = extractor.output_path = None  # set below


@pytest.fixture
def populated(tmp_path):
    (tmp_path / "IMG_001.jpg").write_bytes(b"fake")
    return tmp_path


def _capture_start_scan(extractor):
    calls = []
    extractor._start_scan = lambda *a, **k: calls.append(a)
    return calls


def _capture_askyesno(monkeypatch):
    calls = []

    def fake(title, message, **k):
        calls.append((title, message))
        return True

    monkeypatch.setattr("metadata.messagebox.askyesno", fake)
    return calls


@pytest.mark.parametrize("filetype", ["CSV", "Markdown"])
def test_recursive_prompts_multiple_files(extractor, populated, monkeypatch, filetype):
    """The regression: `or` made this branch unreachable."""
    _mock_widgets(extractor, filetype, recursive=True)
    extractor.directory_path = extractor.output_path = populated
    _capture_start_scan(extractor)
    prompts = _capture_askyesno(monkeypatch)

    extractor.check_recursive()

    assert any(
        f"Multiple {filetype} Files" in t for t, _ in prompts
    ), f"no 'Multiple {filetype} Files' prompt — is the `or` still in check_recursive?"


@pytest.mark.parametrize("filetype", ["Excel", "JSON"])
def test_non_multi_recursive_skips_multiple_prompt(extractor, populated, monkeypatch, filetype):
    """Excel/JSON never had the prompt and still shouldn't."""
    _mock_widgets(extractor, filetype, recursive=True)
    extractor.directory_path = extractor.output_path = populated
    _capture_start_scan(extractor)
    prompts = _capture_askyesno(monkeypatch)

    extractor.check_recursive()

    assert not any("Multiple" in t for t, _ in prompts)


def test_recursive_markdown_declined_returns_without_scan(extractor, populated, monkeypatch):
    _mock_widgets(extractor, "Markdown", recursive=True)
    extractor.directory_path = extractor.output_path = populated
    calls = _capture_start_scan(extractor)
    monkeypatch.setattr("metadata.messagebox.askyesno", lambda *a, **k: False)

    extractor.check_recursive()

    assert calls == []


def test_markdown_non_recursive_skips_multiple_prompt(extractor, populated, monkeypatch):
    """Non-recursive = one folder = one file; no 'Multiple' prompt."""
    _mock_widgets(extractor, "Markdown", recursive=False)
    extractor.directory_path = extractor.output_path = populated
    _capture_start_scan(extractor)
    prompts = _capture_askyesno(monkeypatch)

    extractor.check_recursive()

    assert not any("Multiple" in t for t, _ in prompts)


@pytest.mark.parametrize("filetype", ["CSV", "JSON", "Markdown"])
def test_hyperlink_warning_fires_for_non_excel(extractor, populated, monkeypatch, filetype):
    """Markdown was added to this condition alongside CSV and JSON."""
    _mock_widgets(extractor, filetype, recursive=False)
    extractor.hyperlink_var.set(True)
    extractor.directory_path = extractor.output_path = populated
    _capture_start_scan(extractor)
    prompts = _capture_askyesno(monkeypatch)

    extractor.check_recursive()

    assert any("Hyperlink" in t for t, _ in prompts), f"no hyperlink warning shown for {filetype}"
