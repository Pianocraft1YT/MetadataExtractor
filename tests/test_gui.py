"""Tests for the GUI placeholder handlers."""

from unittest.mock import MagicMock


def test_placeholder_focus_in(extractor):
    extractor.name_entry = MagicMock()
    extractor.name_entry.get.return_value = "Filename (default output.filetype)"

    extractor.nameFocusIn(None)

    extractor.name_entry.delete.assert_called_once_with(0, "end")
    extractor.name_entry.config.assert_called_once_with(foreground="black")


def test_placeholder_focus_out(extractor):
    extractor.name_entry = MagicMock()
    extractor.name_entry.get.return_value = ""

    extractor.nameFocusOut(None)

    extractor.name_entry.insert.assert_called_once_with(0, "Filename (default output.filetype)")
    extractor.name_entry.config.assert_called_once_with(foreground="gray")