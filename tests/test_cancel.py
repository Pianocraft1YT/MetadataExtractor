"""Tests for the Cancel button (threading.Event based)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _capture_scanned(extractor):
    """Spy on scan_image so we can set the cancel event mid-loop."""
    original = extractor.scan_image
    calls = {"n": 0}

    def fake_scan(*a, **k):
        calls["n"] += 1
        return original(*a, **k)

    extractor.scan_image = fake_scan
    return calls


def test_sort_and_extract_stops_on_cancel(extractor, photos_only):
    """Cancel event set mid-scan aborts sort_and_extract's loop."""
    calls = _capture_scanned(extractor)
    original = extractor.scan_image

    def fake_scan(*a, **k):
        calls["n"] += 1
        extractor.cancel_event.set()  # set on first file
        return original(*a, **k)

    extractor.scan_image = fake_scan
    processed, skipped = extractor.sort_and_extract(
        photos_only,
        recursive=False,
        final_output=Path("out.xlsx"),
        modifier=0,
        output_series=True,
    )
    # Event set during first file -> loop exits at top of second iteration
    assert processed <= 1
    assert len(extractor.results) == 0  # dataframe never built


def test_sort_and_extract_irregular_stops_on_cancel(extractor, photos_and_videos):
    extractor.cancel_event.set()
    processed, skipped = extractor.sort_and_extract_irregular(
        photos_and_videos,
        recursive=False,
        final_output=Path("out.xlsx"),
        modifier=0,
    )
    assert processed == 0
    assert skipped == 0


def test_find_directories_breaks_on_cancel(extractor, tmp_path):
    """Directory listing loop honors the event before scanning any folder."""
    parent = tmp_path / "parent"
    for sub in ["A", "B"]:
        (parent / sub).mkdir(parents=True)

    extractor.maxdepth = 1
    extractor.cancel_event.set()
    extractor.sort_and_extract_irregular = MagicMock()

    extractor.find_directories(parent, tmp_path / "out.xlsx", modifier=0)
    extractor.sort_and_extract_irregular.assert_not_called()


def test_clean_up_skips_create_sheet_when_cancelled(extractor, tmp_path):
    extractor._scan_running = True
    extractor.cancel_event.set()
    extractor.create_sheet = MagicMock()

    extractor._clean_up(tmp_path / "out.xlsx", False, 5, 0)

    extractor.create_sheet.assert_not_called()
    assert extractor.percentage_done.get() == "Cancelled"


def test_clean_up_is_idempotent(extractor, tmp_path):
    """_scan_running guard prevents a queued _clean_up from firing twice."""
    extractor._scan_running = True
    extractor.create_sheet = MagicMock()

    extractor._clean_up(tmp_path / "out.xlsx", False, 5, 0)
    extractor._clean_up(tmp_path / "out.xlsx", False, 5, 0)  # no-op

    extractor.create_sheet.assert_called_once()


def test_cancel_before_start_does_nothing_bad(extractor, tmp_path):
    """cancel() with no scan in flight just sets the event and updates labels."""
    extractor.cancel()
    assert extractor.cancel_event.is_set()
    assert extractor.current_directory.get() == "Cancelling..."


def test_check_recursive_clears_event(extractor, tmp_path, monkeypatch):
    """A fresh scan must clear a stale cancel event from a previous run."""
    extractor.cancel_event.set()
    extractor.directory_path = tmp_path
    extractor.output_path = tmp_path
    (tmp_path / "IMG_001.jpg").write_bytes(b"fake")

    extractor._start_scan = MagicMock()
    extractor.series_entry.get.return_value = ""

    # Bypass widget mock plumbing; just confirm the event is cleared before start
    extractor.check_recursive()
    assert not extractor.cancel_event.is_set()
