"""Tests for _check_hidden's behavior beyond the dot-prefix case.

Force the Windows branch via patching os.name so FILE_ATTRIBUTE_HIDDEN
handling can be exercised on any host.
"""

import os
import stat
from unittest.mock import patch


def test_flag_on_short_circuits_before_stat(extractor, tmp_path):
    (tmp_path / "x.jpg").write_bytes(b"fake")
    with patch.object(os, "stat", side_effect=AssertionError("should not stat")):
        assert extractor._check_hidden("x.jpg", tmp_path, True) is False


def test_dotfile_short_circuits_before_stat_on_windows(extractor, tmp_path):
    with patch.object(os, "name", "nt"), patch.object(os, "stat", side_effect=AssertionError("no stat for dotfiles")):
        assert extractor._check_hidden(".ghost.jpg", tmp_path, False) is True


def test_windows_missing_file_fails_open(extractor, tmp_path):
    with patch.object(os, "name", "nt"):
        assert extractor._check_hidden("ghost.jpg", tmp_path, False) is False


def test_windows_hidden_attribute_detected(extractor, tmp_path):
    (tmp_path / "x.jpg").write_bytes(b"fake")

    class S:
        st_file_attributes = stat.FILE_ATTRIBUTE_HIDDEN

    with patch.object(os, "name", "nt"), patch.object(os, "stat", return_value=S()):
        assert extractor._check_hidden("x.jpg", tmp_path, False) is True


def test_windows_visible_attribute_detected(extractor, tmp_path):
    (tmp_path / "x.jpg").write_bytes(b"fake")

    class S:
        st_file_attributes = 0

    with patch.object(os, "name", "nt"), patch.object(os, "stat", return_value=S()):
        assert extractor._check_hidden("x.jpg", tmp_path, False) is False


def test_windows_attributeerror_fails_open(extractor, tmp_path):
    (tmp_path / "x.jpg").write_bytes(b"fake")

    class S:
        pass  # no st_file_attributes

    with patch.object(os, "name", "nt"), patch.object(os, "stat", return_value=S()):
        assert extractor._check_hidden("x.jpg", tmp_path, False) is False
