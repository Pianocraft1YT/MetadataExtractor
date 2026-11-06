"""
Tests for MetadataExtractor.create_sheet.

create_sheet no longer takes `recursive` — the empty-results guard fires
for every format now.
"""

import sys
from unittest.mock import MagicMock

import pandas as pd
import pytest

import metadata

pytestmark = pytest.mark.real_create_sheet


@pytest.fixture
def simple_df():
    return pd.DataFrame(
        {
            "Files": ["a.jpg", "b.jpg"],
            "Dates": ["01/01/2024", "01/02/2024"],
            "Time": ["12:00:00", "12:00:00"],
        }
    )


class _FakeBool:
    """Minimal stand-in for tk.BooleanVar — supports .get() and .set()."""

    def __init__(self, value=False):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


@pytest.fixture
def isolated(extractor):
    extractor.keepopen_var = _FakeBool(False)  # also swap this — same latent bug
    extractor.hyperlink_var = _FakeBool(False)
    extractor.root = MagicMock()
    return extractor


def test_writes_new_file(isolated, tmp_path, simple_df):
    isolated.results.append((simple_df, "Sheet", tmp_path))
    output = tmp_path / "out.xlsx"
    isolated.create_sheet(output, 2, 0)

    assert output.exists()
    df = pd.read_excel(output, sheet_name="Sheet")
    assert len(df) == 2


def test_overwrite_confirmed(isolated, tmp_path, simple_df, monkeypatch):
    isolated.results.append((simple_df, "Sheet", tmp_path))
    output = tmp_path / "out.xlsx"
    output.write_text("old data")
    monkeypatch.setattr(metadata.messagebox, "askyesno", lambda *a, **k: True)

    isolated.create_sheet(output, 2, 0)

    df = pd.read_excel(output, sheet_name="Sheet")
    assert len(df) == 2


def test_overwrite_declined(isolated, tmp_path, simple_df, monkeypatch):
    isolated.results.append((simple_df, "Sheet", tmp_path))
    output = tmp_path / "out.xlsx"
    output.write_text("old data")
    monkeypatch.setattr(metadata.messagebox, "askyesno", lambda *a, **k: False)

    cancel_calls = []
    monkeypatch.setattr(
        metadata.messagebox,
        "showinfo",
        lambda title, message, **k: cancel_calls.append((title, message)),
    )

    isolated.create_sheet(output, 2, 0)

    assert output.read_text() == "old data"
    assert any("Cancel" in t for t, _ in cancel_calls)


def test_empty_results_shows_no_data(isolated, tmp_path, monkeypatch):
    isolated.results.clear()
    output = tmp_path / "out.xlsx"

    errors = []
    monkeypatch.setattr(
        metadata.messagebox,
        "showerror",
        lambda title, message, **k: errors.append((title, message)),
    )

    isolated.create_sheet(output, 0, 0)

    assert not output.exists()
    assert any("No data" in t for t, _ in errors)


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_md(isolated):
    isolated.filetype_var.set("Markdown")
    return isolated


def test_markdown_writes_new_file(isolated_md, tmp_path, simple_df):
    isolated_md.hyperlink_var.set(False)
    isolated_md.results.append((simple_df, "Sheet", tmp_path))
    output = tmp_path / "out.md"

    isolated_md.create_sheet(output, 2, 0)

    md_file = tmp_path / "out_Sheet.md"
    assert md_file.exists(), "Markdown file was not written"
    content = md_file.read_text(encoding="utf-8")
    assert content.startswith("|Files|Dates|Time|")
    assert "|a.jpg|01/01/2024|12:00:00|" in content


def test_markdown_writes_hyperlinks_when_enabled(isolated_md, tmp_path, simple_df):
    isolated_md.hyperlink_var.set(True)
    isolated_md.results.append((simple_df, "Sheet", tmp_path))
    output = tmp_path / "out.md"

    isolated_md.create_sheet(output, 2, 0)

    content = (tmp_path / "out_Sheet.md").read_text(encoding="utf-8")
    assert "[a.jpg](<" in content


def test_markdown_writes_one_per_sheet(isolated_md, tmp_path):
    df1 = pd.DataFrame({"Files": ["a.jpg"]})
    df2 = pd.DataFrame({"Files": ["b.jpg"]})
    isolated_md.results = [(df1, "Folder1", None), (df2, "Folder2", None)]
    output = tmp_path / "out.md"

    isolated_md.create_sheet(output, 2, 0)

    names = sorted(p.name for p in tmp_path.glob("*.md"))
    assert names == ["out_Folder1.md", "out_Folder2.md"]


def test_markdown_overwrite_confirmed(isolated_md, tmp_path, simple_df, monkeypatch):
    existing = tmp_path / "out_Sheet.md"
    existing.write_text("OLD", encoding="utf-8")

    isolated_md.results.append((simple_df, "Sheet", tmp_path))
    output = tmp_path / "out.md"

    errors = []
    monkeypatch.setattr(
        metadata.messagebox,
        "showerror",
        lambda title, message, **k: errors.append((title, message)),
    )
    monkeypatch.setattr(metadata.messagebox, "askyesno", lambda *a, **k: True)

    isolated_md.create_sheet(output, 2, 0)

    assert "Unexpected" not in str(errors), f"unexpected error raised: {errors}"
    assert existing.read_text(encoding="utf-8").startswith("|Files|")


def test_markdown_overwrite_declined(isolated_md, tmp_path, simple_df, monkeypatch):
    existing = tmp_path / "out_Sheet.md"
    existing.write_text("OLD", encoding="utf-8")

    isolated_md.results.append((simple_df, "Sheet", tmp_path))
    output = tmp_path / "out.md"

    monkeypatch.setattr(metadata.messagebox, "askyesno", lambda *a, **k: False)

    isolated_md.create_sheet(output, 2, 0)

    assert existing.read_text(encoding="utf-8") == "OLD"
