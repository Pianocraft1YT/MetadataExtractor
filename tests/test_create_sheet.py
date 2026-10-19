"""
Tests for create_sheet — the Excel writer.

Uses the real metadata.create_sheet (opting out of the conftest mock
via the `real_create_sheet` marker) with tkinter variables mocked so no
window is created. sys.exit is patched so the test survives when
create_sheet tries to close the app.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock

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


@pytest.fixture(autouse=True)
def mock_tk_variables(monkeypatch):
    mock_keepopen = MagicMock()
    mock_keepopen.get.return_value = False
    monkeypatch.setattr(metadata, "keepopen_var", mock_keepopen)
    monkeypatch.setattr(metadata, "root", MagicMock())


@pytest.fixture(autouse=True)
def patch_sys_exit(monkeypatch):
    import sys

    def fake_exit(code=0):
        raise SystemExit(code)

    monkeypatch.setattr(sys, "exit", fake_exit)


def test_writes_new_file(tmp_path, simple_df):
    output = tmp_path / "out.xlsx"
    try:
        metadata.create_sheet(
            output, recursive=False, df=simple_df,
            total_processed=2, total_skipped=0,
        )
    except SystemExit:
        pass

    assert output.exists()
    df = pd.read_excel(output, sheet_name="Output")
    assert len(df) == 2


def test_overwrite_confirmed(tmp_path, simple_df, monkeypatch):
    output = tmp_path / "out.xlsx"
    output.write_text("old data")

    monkeypatch.setattr(metadata.messagebox, "askyesno", lambda *a, **k: True)

    try:
        metadata.create_sheet(
            output, recursive=False, df=simple_df,
            total_processed=2, total_skipped=0,
        )
    except SystemExit:
        pass

    df = pd.read_excel(output, sheet_name="Output")
    assert len(df) == 2


def test_overwrite_declined(tmp_path, simple_df, monkeypatch):
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
        metadata.create_sheet(
            output, recursive=False, df=simple_df,
            total_processed=2, total_skipped=0,
        )
    except SystemExit:
        pass

    assert output.read_text() == "old data"
    assert any("Cancel" in t for t, _ in cancel_calls)


def test_recursive_no_data(tmp_path, monkeypatch):
    metadata.results.clear()
    output = tmp_path / "out.xlsx"

    errors = []
    monkeypatch.setattr(
        metadata.messagebox,
        "showerror",
        lambda title, message, **k: errors.append((title, message)),
    )

    try:
        metadata.create_sheet(
            output, recursive=True, df=None,
            total_processed=0, total_skipped=0,
        )
    except SystemExit:
        pass

    assert not output.exists()
    assert any("No data" in t for t, _ in errors)