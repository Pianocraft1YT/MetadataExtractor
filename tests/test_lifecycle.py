"""Lifecycle tests: _clean_up, _on_close, _run_scan_threaded,
_confirm_overwrite."""

from unittest.mock import MagicMock, patch
import pytest

import metadata
from metadata import ScanConfig


def _make_cfg(tmp_path):
    return ScanConfig(
        final_output=tmp_path / "out.xlsx",
        modifier=0,
        cutoff=2.0,
        output_summary=False,
        output_utc=False,
        output_dimensions=False,
        output_filesize=False,
        output_make=False,
        output_model=False,
        output_software=False,
        output_lens_model=False,
        output_aperture=False,
        output_exposure_time=False,
        output_focal_length=False,
        output_iso=False,
        output_gps=False,
        output_video_rows=False,
        date_range=False,
        date_format="%m/%d/%Y",
        time_format="%H:%M:%S",
        start_date=None,
        end_date=None,
        include_hiddens=False,
        include_undateable=True,
        media_filter="All Media",
        directory_path=tmp_path,
    )


# ---------------------------------------------------------------------------
# _clean_up
# ---------------------------------------------------------------------------


def test_clean_up_swallows_create_sheet_exception(extractor, tmp_path):
    extractor._cleanup_pending = True
    extractor.keepopen_var.set(True)
    with patch.object(extractor, "create_sheet", side_effect=RuntimeError("boom")):
        extractor._clean_up(tmp_path / "out.xlsx", 5, 0)
    assert "Unexpected" in extractor.collected_warnings
    assert any("boom" in w for w in extractor.collected_warnings["Unexpected"])


def test_clean_up_reenables_buttons_on_exception(extractor, tmp_path):
    extractor._cleanup_pending = True
    extractor.keepopen_var.set(True)
    extractor.execute_button = MagicMock()
    extractor.cancel_button = MagicMock()
    with patch.object(extractor, "create_sheet", side_effect=RuntimeError("boom")):
        extractor._clean_up(tmp_path / "out.xlsx", 5, 0)
    extractor.execute_button.config.assert_called_once_with(state="normal")
    extractor.cancel_button.config.assert_called_once_with(state="disabled")


def test_clean_up_cancelled_sets_labels(extractor, tmp_path):
    extractor._cleanup_pending = True
    extractor.cancel_event.set()
    with patch.object(extractor, "create_sheet") as fake:
        extractor._clean_up(tmp_path / "out.xlsx", 0, 0)
    fake.assert_not_called()
    assert extractor.current_directory.get() == "Cancelled"
    assert extractor.percentage_done.get() == "Cancelled"


def test_clean_up_no_op_when_destroyed(extractor, tmp_path):
    extractor._cleanup_pending = True
    extractor._destroyed = True
    with patch.object(extractor, "create_sheet") as fake:
        extractor._clean_up(tmp_path / "out.xlsx", 5, 0)
    fake.assert_not_called()


# ---------------------------------------------------------------------------
# _on_close
# ---------------------------------------------------------------------------


def test_on_close_saves_settings_and_sets_flags(extractor):
    extractor.root = MagicMock()
    extractor._save_settings = MagicMock()
    extractor._on_close()
    extractor._save_settings.assert_called_once()
    assert extractor._destroyed is True
    assert extractor.cancel_event.is_set()
    extractor.root.destroy.assert_called_once()


# ---------------------------------------------------------------------------
# cancel()
# ---------------------------------------------------------------------------


def test_cancel_sets_event_and_disables_button(extractor):
    extractor.cancel_button = MagicMock()
    extractor.cancel()
    assert extractor.cancel_event.is_set()
    extractor.cancel_button.config.assert_called_once_with(state="disabled")


# ---------------------------------------------------------------------------
# _run_scan_threaded exception handling
# ---------------------------------------------------------------------------


def test_scan_thread_swallows_unexpected_exception(extractor, tmp_path):
    extractor._cleanup_pending = True
    extractor.directory_path = tmp_path
    extractor.find_directories = MagicMock(side_effect=RuntimeError("boom"))
    extractor._clean_up = MagicMock()
    extractor._safe_after = MagicMock()

    cfg = _make_cfg(tmp_path)
    extractor._run_scan_threaded(cfg)

    assert "Unexpected" in extractor.collected_warnings
    assert any("boom" in w for w in extractor.collected_warnings["Unexpected"])
    extractor._safe_after.assert_any_call(
        extractor._clean_up,
        cfg.final_output,
        extractor.total_processed,
        extractor.total_skipped,
        cfg.output_summary,
        cfg.date_format,
    )


# ---------------------------------------------------------------------------
# _confirm_overwrite
# ---------------------------------------------------------------------------


def test_confirm_overwrite_missing_file_returns_true(tmp_path, monkeypatch):
    target = tmp_path / "nope.xlsx"
    called = []
    monkeypatch.setattr(
        metadata.messagebox,
        "askyesno",
        lambda *a, **k: called.append(True) or False,
    )
    assert metadata.MetadataExtractor._confirm_overwrite(target) is True
    assert called == [], "askyesno should not fire when file doesn't exist"


@pytest.mark.parametrize("answer", [True, False])
def test_confirm_overwrite_existing_file_returns_answer(tmp_path, monkeypatch, answer):
    target = tmp_path / "exists.xlsx"
    target.write_text("data")
    monkeypatch.setattr(metadata.messagebox, "askyesno", lambda *a, **k: answer)
    assert metadata.MetadataExtractor._confirm_overwrite(target) is answer
