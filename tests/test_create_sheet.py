"""
Tests for MetadataExtractor.create_sheet.

Opts out of the conftest create_sheet mock via the `real_create_sheet`
marker. tkinter keepopen_var is mocked to return False so the method
takes the destroy+exit path, which we catch.
"""

import sys
from unittest.mock import MagicMock

import pandas as pd
import pytest

import metadata


pytestmark = pytest.mark.real_create_sheet


@pytest.fixture
def simple_df():
    return pd.DataFrame({
        "Files": ["a.jpg", "b.jpg"],
        "Dates": ["01/01/2024", "01/02/2024"],
        "Time": ["12:00:00", "12:00:00"],
    })


@pytest.fixture
def isolated(extractor, monkeypatch):
    """Ensure keepopen_var is False and sys.exit raises SystemExit."""
    extractor.keepopen_var = MagicMock()
    extractor.keepopen_var.get.return_value = False
    extractor.root = MagicMock()

    def fake_exit(code=0):
        raise SystemExit(code)
    monkeypatch.setattr(sys, "exit", fake_exit)
    return extractor


def test_writes_new_file(isolated, tmp_path, simple_df):
    isolated.results.append((simple_df, "Sheet"))
    output = tmp_path / "out.xlsx"
    try:
        isolated.create_sheet(output, recursive=False, total_processed=2, total_skipped=0)
    except SystemExit:
        pass

    assert output.exists()
    df = pd.read_excel(output, sheet_name="Sheet")
    assert len(df) == 2


def test_overwrite_confirmed(isolated, tmp_path, simple_df, monkeypatch):
    isolated.results.append((simple_df, "Sheet"))
    output = tmp_path / "out.xlsx"
    output.write_text("old data")
    monkeypatch.setattr(metadata.messagebox, "askyesno", lambda *a, **k: True)

    try:
        isolated.create_sheet(output, recursive=False, total_processed=2, total_skipped=0)
    except SystemExit:
        pass

    df = pd.read_excel(output, sheet_name="Sheet")
    assert len(df) == 2


def test_overwrite_declined(isolated, tmp_path, simple_df, monkeypatch):
    isolated.results.append((simple_df, "Sheet"))
    output = tmp_path / "out.xlsx"
    output.write_text("old data")
    monkeypatch.setattr(metadata.messagebox, "askyesno", lambda *a, **k: False)

    cancel_calls = []
    monkeypatch.setattr(
        metadata.messagebox,
        "showinfo",
        lambda title, message, **k: cancel_calls.append((title, message)),
    )

    try:
        isolated.create_sheet(output, recursive=False, total_processed=2, total_skipped=0)
    except SystemExit:
        pass

    assert output.read_text() == "old data"
    assert any("Cancel" in t for t, _ in cancel_calls)


def test_recursive_no_data(isolated, tmp_path, monkeypatch):
    isolated.results.clear()
    output = tmp_path / "out.xlsx"

    errors = []
    monkeypatch.setattr(
        metadata.messagebox,
        "showerror",
        lambda title, message, **k: errors.append((title, message)),
    )

    try:
        isolated.create_sheet(output, recursive=True, total_processed=0, total_skipped=0)
    except SystemExit:
        pass

    assert not output.exists()
    assert any("No data" in t for t, _ in errors)