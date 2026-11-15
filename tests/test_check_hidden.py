"""Tests for MetadataExtractor._check_hidden.

Two branches:
- Dot-prefix short-circuit: runs on any platform, returns True before
  os.name is consulted. Tested cross-platform.
- Windows st_file_attributes: requires os.name == "nt" AND os.stat to
  return an object with .st_file_attributes. The WindowsPath branch of
  pathlib.Path() raises NotImplementedError on Linux when os.name is
  patched, so these tests are skipped outside Windows.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


def test_dotfile_short_circuits_before_os_name_check(extractor, tmp_path):
    """Dot-prefix check runs before os.name is consulted, so it works on
    any platform. Verify by asserting os.stat is never reached."""
    with patch("metadata.os.stat") as mock_stat:
        assert extractor._check_hidden(".ghost.jpg", tmp_path, False) is True
        mock_stat.assert_not_called()


def test_include_hiddens_short_circuits_all_checks(extractor, tmp_path):
    """include_hiddens=True returns False before Path() is even constructed."""
    with patch("metadata.os.stat") as mock_stat:
        assert extractor._check_hidden(".ghost.jpg", tmp_path, True) is False
        mock_stat.assert_not_called()


def test_visible_file_returns_false_on_non_windows(extractor, tmp_path):
    """Non-dotfile, include_hiddens=False, os.name != 'nt' → False,
    without touching os.stat."""
    if os.name == "nt":
        pytest.skip("posix branch")
    with patch("metadata.os.stat") as mock_stat:
        assert extractor._check_hidden("x.jpg", tmp_path, False) is False
        mock_stat.assert_not_called()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only st_file_attributes branch")
def test_windows_hidden_attribute_detected(extractor, tmp_path):
    with patch("os.stat") as mock_stat:
        mock_stat.return_value.st_file_attributes = 0x02  # FILE_ATTRIBUTE_HIDDEN
        assert extractor._check_hidden("x.jpg", tmp_path, False) is True


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only st_file_attributes branch")
def test_windows_visible_attribute_detected(extractor, tmp_path):
    with patch("os.stat") as mock_stat:
        mock_stat.return_value.st_file_attributes = 0x00
        assert extractor._check_hidden("x.jpg", tmp_path, False) is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only st_file_attributes branch")
def test_windows_missing_file_fails_open(extractor, tmp_path):
    with patch("os.stat", side_effect=FileNotFoundError):
        assert extractor._check_hidden("ghost.jpg", tmp_path, False) is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only st_file_attributes branch")
def test_windows_attributeerror_fails_open(extractor, tmp_path):
    class NoAttrs:
        pass
    with patch("os.stat", return_value=NoAttrs()):
        assert extractor._check_hidden("x.jpg", tmp_path, False) is False