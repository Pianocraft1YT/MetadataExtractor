"""Tests for MetadataExtractor._sanitize_for_excel and the Excel write boundary.

Real cameras pad EXIF string fields with null bytes. XML forbids them.
The sanitizer strips them at the Excel boundary only — CSV/JSON/Markdown
keep the raw bytes so users can inspect them if needed.
"""

from unittest.mock import MagicMock

import pandas as pd
import pytest

pytestmark = pytest.mark.real_create_sheet


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
    extractor.keepopen_var = _FakeBool(False)
    extractor.hyperlink_var = _FakeBool(False)
    extractor.root = MagicMock()  # stays a mock — nothing checks specific calls on it
    return extractor


# ---------------------------------------------------------------------------
# Unit tests — _sanitize_for_excel
# ---------------------------------------------------------------------------


def test_strips_null_pads(isolated):
    df = pd.DataFrame({"A": ["\x00\x00\x00", "clean"]})
    result = isolated._sanitize_for_excel(df)
    assert result.iloc[0, 0] == ""
    assert result.iloc[1, 0] == "clean"


def test_strips_all_xml_illegal_control_chars(isolated):
    df = pd.DataFrame({"A": ["a\x00b\x01c\x08d\x0be\x0cf\x0eg\x1fh"]})
    result = isolated._sanitize_for_excel(df)
    assert result.iloc[0, 0] == "abcdefgh"


def test_preserves_tab_cr_lf(isolated):
    df = pd.DataFrame({"A": ["line1\nline2\ttabbed\rCR"]})
    result = isolated._sanitize_for_excel(df)
    assert result.iloc[0, 0] == "line1\nline2\ttabbed\rCR"


def test_preserves_none(isolated):
    df = pd.DataFrame({"A": [None]})
    result = isolated._sanitize_for_excel(df)
    assert result.iloc[0, 0] is None


def test_preserves_integers(isolated):
    df = pd.DataFrame({"A": [123, 456]})
    result = isolated._sanitize_for_excel(df)
    assert result.iloc[0, 0] == 123
    assert result.iloc[1, 0] == 456


def test_preserves_floats(isolated):
    df = pd.DataFrame({"A": [3.14, 2.71]})
    result = isolated._sanitize_for_excel(df)
    assert result.iloc[0, 0] == 3.14
    assert result.iloc[1, 0] == 2.71


def test_preserves_nan(isolated):
    df = pd.DataFrame({"A": [float("nan")]})
    result = isolated._sanitize_for_excel(df)
    assert pd.isna(result.iloc[0, 0])


def test_does_not_mutate_original(isolated):
    df = pd.DataFrame({"A": ["\x00\x00"]})
    result = isolated._sanitize_for_excel(df)
    assert df.iloc[0, 0] == "\x00\x00"
    assert result.iloc[0, 0] == ""


def test_returns_a_new_object(isolated):
    df = pd.DataFrame({"A": ["x"]})
    result = isolated._sanitize_for_excel(df)
    assert result is not df


def test_empty_dataframe_returns_copy(isolated):
    df = pd.DataFrame()
    result = isolated._sanitize_for_excel(df)
    assert result.empty
    assert result is not df


def test_barn_owl_real_model_value(isolated):
    df = pd.DataFrame({"Camera Model": ["\x00" * 19]})
    result = isolated._sanitize_for_excel(df)
    assert result.iloc[0, 0] == ""


def test_mixed_types_in_one_column(isolated):
    df = pd.DataFrame({"A": ["Canon", None, 123, 3.14, "\x00\x00"]})
    result = isolated._sanitize_for_excel(df)
    assert result.iloc[0, 0] == "Canon"
    assert result.iloc[1, 0] is None
    assert result.iloc[2, 0] == 123
    assert result.iloc[3, 0] == 3.14
    assert result.iloc[4, 0] == ""


# ---------------------------------------------------------------------------
# Integration — create_sheet with Excel output
# ---------------------------------------------------------------------------


def test_excel_write_succeeds_with_null_model(isolated, tmp_path):
    df = pd.DataFrame({"Files": ["a.jpg"], "Camera Model": ["\x00" * 19], "Dates": ["10/18/2025"]})
    isolated.results.append((df, "Sheet", tmp_path))
    output = tmp_path / "out.xlsx"

    isolated.create_sheet(output, 1, 0)

    assert output.exists()


def test_excel_model_reads_back_blank(isolated, tmp_path):
    df = pd.DataFrame({"Files": ["a.jpg"], "Camera Model": ["\x00" * 19], "Dates": ["10/18/2025"]})
    isolated.results.append((df, "Sheet", tmp_path))
    output = tmp_path / "out.xlsx"

    isolated.create_sheet(output, 1, 0)

    back = pd.read_excel(output, sheet_name="Sheet")
    assert pd.isna(back.iloc[0]["Camera Model"]) or back.iloc[0]["Camera Model"] == ""


def test_excel_mixed_photos_write_cleanly(isolated, tmp_path):
    barn_owl = pd.DataFrame({"Files": ["owl.jpg"], "Camera Make": ["barn owl"], "Camera Model": ["\x00" * 19]})
    phone = pd.DataFrame({"Files": ["phone.jpg"], "Camera Make": ["Apple"], "Camera Model": ["iPhone 15"]})
    isolated.results.append((barn_owl, "Owl", tmp_path))
    isolated.results.append((phone, "Phone", tmp_path))
    output = tmp_path / "out.xlsx"

    isolated.create_sheet(output, 2, 0)

    owl = pd.read_excel(output, sheet_name="Owl")
    phone_df = pd.read_excel(output, sheet_name="Phone")
    assert owl.iloc[0]["Camera Make"] == "barn owl"
    assert pd.isna(owl.iloc[0]["Camera Model"]) or owl.iloc[0]["Camera Model"] == ""
    assert phone_df.iloc[0]["Camera Model"] == "iPhone 15"


def test_csv_keeps_null_pads_raw(isolated, tmp_path):
    isolated.filetype_var.set("CSV")
    df = pd.DataFrame({"Files": ["a.jpg"], "Camera Model": ["\x00\x00"]})
    isolated.results.append((df, "Sheet", tmp_path))
    output = tmp_path / "out.csv"

    isolated.create_sheet(output, 1, 0)

    csv_path = tmp_path / "out_Sheet.csv"
    content = csv_path.read_text(encoding="utf-8")
    assert "\x00" in content
