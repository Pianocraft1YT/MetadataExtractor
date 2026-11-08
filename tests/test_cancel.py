"""Cancel behaviour tests."""

from pathlib import Path
from unittest.mock import MagicMock
from tests.conftest import make_jpeg_with_exif
from tests.helpers import find_scan, media_files, sort_scan


def test_sort_and_extract_stops_on_cancel(extractor, tmp_path):
    for name in ["a.jpg", "b.jpg", "c.jpg"]:
        make_jpeg_with_exif(tmp_path / name, "2024:05:15 12:30:45")

    extractor.cancel_event.set()
    processed, skipped = sort_scan(extractor, tmp_path)

    assert processed == 0
    assert skipped == 0


def test_find_directories_breaks_on_cancel(extractor, tmp_path):
    extractor.cancel_event.set()
    p, s = find_scan(extractor, tmp_path)
    assert p == 0
    assert s == 0


def test_cancel_reenables_buttons(extractor, tmp_path):
    """_clean_up must re-enable Execute even when the scan was cancelled."""
    extractor._cleanup_pending = True
    extractor.cancel_event.set()
    extractor.execute_button = MagicMock()
    extractor.cancel_button = MagicMock()

    extractor._clean_up(tmp_path / "out.xlsx", 0, 0)

    extractor.execute_button.config.assert_called_once_with(state="normal")
    extractor.cancel_button.config.assert_called_once_with(state="disabled")
