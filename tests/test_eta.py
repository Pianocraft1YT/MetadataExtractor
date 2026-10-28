# tests/test_eta.py
from unittest.mock import MagicMock


def _set_total(extractor, n, started_at=None):
    extractor.total_files = n
    extractor.time_started = started_at


def test_eta_estimating_when_no_timestamp(extractor):
    _set_total(extractor, 100, started_at=1000.0)
    extractor.update_progress(5, 0, "/x", timestamp=None)
    assert extractor.eta.get() == "Estimating..."


def test_eta_estimating_under_10_files(extractor):
    """ETA hides for small scans; only shows after 10 files of data."""
    _set_total(extractor, 100, started_at=1000.0)
    extractor.update_progress(3, 0, "/x", timestamp=1000.5)
    assert extractor.eta.get() == "Estimating..."


def test_eta_computes_with_reasonable_numbers(extractor):
    """10 files in 1s -> 10 files/s. 90 remaining -> 9s."""
    _set_total(extractor, 100, started_at=1000.0)
    extractor.update_progress(10, 0, "/x", timestamp=1001.0)
    # 1.0s / 10 files = 0.1 s/file; * 90 = 9s
    assert extractor.eta.get() == "9 second(s) remaining."


def test_eta_never_exceeds_total_reasonably(extractor):
    """Regression: old code multiplied instead of divided and showed 'days'."""
    _set_total(extractor, 32000, started_at=1000.0)
    # 250 files/sec -> 127s for remaining ~31750
    extractor.update_progress(250, 0, "/x", timestamp=1001.0)
    eta = extractor.eta.get()
    # Must be seconds/minutes, never days/hours for this pace
    assert "day" not in eta
    assert "hour" not in eta


def test_eta_skipped_counts_toward_progress(extractor):
    """files_done = processed + skipped, not just processed."""
    _set_total(extractor, 100, started_at=1000.0)
    extractor.update_progress(5, 5, "/x", timestamp=1001.0)
    # 10 files total in 1s -> same as test_eta_computes_with_reasonable_numbers
    assert extractor.eta.get() == "9 second(s) remaining."


def test_progress_never_exceeds_100(extractor):
    """Regression: overlapping rescan pushed the bar past 100%."""
    _set_total(extractor, 10, started_at=1000.0)
    extractor.update_progress(15, 0, "/x", timestamp=1001.0)
    assert extractor.percentage_done.get() == "100.0%"
    assert extractor.progress_var.get() == 100.0


def test_set_total_files_starts_clock(extractor):
    extractor.time_started = None
    extractor._set_total_files(42)
    assert extractor.time_started is not None
    assert extractor.total_files == 42


def test_reset_clears_eta_state(extractor):
    extractor.time_started = 12345.0
    extractor.eta.set("some stale value")
    extractor.reset()
    assert extractor.time_started is None
    assert extractor.eta.get() == "Estimating..."