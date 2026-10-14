# tests/test_gui.py
import pytest
from unittest.mock import MagicMock, patch
import metadata
def test_placeholder_focus_in():
    # Directly test the helper functions with a mocked entry
    mock_entry = MagicMock()
    mock_entry.get.return_value = "Filename (default output.xlsx)"

    with patch('metadata.name_entry', mock_entry):
        metadata.nameFocusIn(None)
        mock_entry.delete.assert_called_once_with(0, "end")