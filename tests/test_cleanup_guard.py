"""Tests for _clean_up — the sole create_sheet caller after the refactor."""

from unittest.mock import MagicMock, patch

from tests.conftest import make_jpeg_with_exif


def test_clean_up_skipped_when_scan_not_running(extractor, tmp_path):
    """_clean_up returns early if _cleanup_pending is False."""
    extractor._cleanup_pending = False
    with patch.object(extractor, "create_sheet") as fake:
        extractor._clean_up(tmp_path / "out.xlsx", 5, 0)
    fake.assert_not_called()


def test_clean_up_writes_sheet_on_success(extractor, tmp_path):
    extractor._cleanup_pending = True
    extractor.keepopen_var.set(True)
    with patch.object(extractor, "create_sheet") as fake:
        extractor._clean_up(tmp_path / "out.xlsx", 5, 0)
    fake.assert_called_once_with(tmp_path / "out.xlsx", 5, 0)


def test_clean_up_skips_write_on_cancel(extractor, tmp_path):
    extractor._cleanup_pending = True
    extractor.cancel_event.set()
    with patch.object(extractor, "create_sheet") as fake:
        extractor._clean_up(tmp_path / "out.xlsx", 5, 0)
    fake.assert_not_called()


def test_clean_up_cannot_fire_twice(extractor, tmp_path):
    extractor._cleanup_pending = True
    extractor.keepopen_var.set(True)
    with patch.object(extractor, "create_sheet") as fake:
        extractor._clean_up(tmp_path / "out.xlsx", 5, 0)
        extractor._clean_up(tmp_path / "out.xlsx", 5, 0)  # second call should be a no-op
    assert fake.call_count == 1
