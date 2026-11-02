"""Tests for MetadataExtractor._dataframe_to_txt (Markdown table rendering)."""

import pandas as pd
import pytest


def _count_unescaped_pipes(line):
    return line.replace("\\|", "").count("|")


class TestDataframeToTxt:
    def test_basic_two_column_table(self, extractor):
        df = pd.DataFrame({"Files": ["a.jpg", "b.jpg"], "Dates": ["01/01/2024", "01/02/2024"]})
        lines = extractor._dataframe_to_txt(df).split("\n")

        assert lines[0] == "|Files|Dates|"
        assert lines[1] == "|---|---|"
        assert lines[2] == "|a.jpg|01/01/2024|"
        assert len(lines) == 4

    def test_empty_dataframe_has_header_and_separator_only(self, extractor):
        df = pd.DataFrame({"Files": [], "Dates": [], "Time": []})
        lines = extractor._dataframe_to_txt(df).split("\n")
        assert lines[0] == "|Files|Dates|Time|"
        assert lines[1] == "|---|---|---|"
        assert len(lines) == 2

    def test_separator_column_count_matches_headers(self, extractor):
        df = pd.DataFrame({"A": [], "B": [], "C": [], "D": []})
        separator = extractor._dataframe_to_txt(df).split("\n")[1]
        assert separator == "|---|---|---|---|"

    def test_returns_string(self, extractor):
        assert isinstance(extractor._dataframe_to_txt(pd.DataFrame({"A": [1]})), str)

    # --- Null / NaN handling ---

    def test_scalar_nan_blanked(self, extractor):
        df = pd.DataFrame({"A": ["x", float("nan")]})
        result = extractor._dataframe_to_txt(df)
        assert "|x|" in result
        assert "nan" not in result.lower()

    def test_pandas_na_blanked(self, extractor):
        df = pd.DataFrame({"A": ["x", pd.NA]})
        result = extractor._dataframe_to_txt(df)
        assert "<NA>" not in result
        assert "nan" not in result.lower()

    def test_none_blanked(self, extractor):
        df = pd.DataFrame({"A": [None, "x"]})
        assert "||" in extractor._dataframe_to_txt(df)

    def test_list_cell_stringified_not_blanked(self, extractor):
        """Regression for the old isinstance(na, bool) guard blanking list cells."""
        df = pd.DataFrame({"A": [[1, 2, 3]]})
        assert "[1, 2, 3]" in extractor._dataframe_to_txt(df)

    # --- Escaping ---

    def test_pipe_in_cell_escaped(self, extractor):
        df = pd.DataFrame({"A": ["a|b"]})
        result = extractor._dataframe_to_txt(df)
        assert "a\\|b" in result
        assert _count_unescaped_pipes(result.split("\n")[2]) == 2   # was 3

    def test_backslash_then_pipe_escaping_order(self, extractor):
        """Critical: backslash escapes BEFORE pipe, or \\| becomes \\\\| (broken)."""
        df = pd.DataFrame({"A": ["a\\b|c"]})
        result = extractor._dataframe_to_txt(df)
        assert "a\\\\b\\|c" in result
        assert "a\\\\b\\\\|c" not in result

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("a\nb", "a b"),
            ("a\r\nb", "a b"),
            ("a\rb", "a b"),
        ],
    )
    def test_newlines_become_spaces(self, extractor, raw, expected):
        df = pd.DataFrame({"A": [raw]})
        assert extractor._dataframe_to_txt(df).split("\n")[2] == f"|{expected}|"

    def test_column_header_pipe_escaped(self, extractor):
        df = pd.DataFrame({"A|B": [1]})
        assert extractor._dataframe_to_txt(df).split("\n")[0] == "|A\\|B|"

    def test_unicode_preserved(self, extractor):
        df = pd.DataFrame({"A": ["café ☕", "日本語"]})
        result = extractor._dataframe_to_txt(df)
        assert "café ☕" in result
        assert "日本語" in result
