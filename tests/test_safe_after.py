"""Tests for _safe_after — worker-thread-safe root.after wrapper.

Under the test suite, tkinter is globally mocked (see conftest), so
app.root is a MagicMock and root.after does not actually schedule
anything. Tests here verify the wrapper closure contract via MagicMock
assertions rather than event-loop behavior.
"""

from unittest.mock import patch

import pytest

import metadata
from metadata import MetadataExtractor


@pytest.fixture
def app():
    try:
        instance = MetadataExtractor()
    except Exception as e:  # headless CI
        pytest.skip(f"Cannot create Tk root: {e}")
    yield instance
    try:
        if not instance._destroyed:
            instance.root.destroy()
    except Exception:
        pass


def test_safe_after_calls_root_after_when_alive(app):
    """When the root is alive, _safe_after schedules a wrapper via root.after(0, _run)
    that executes the callback."""
    app.root.after.reset_mock()
    called = []
    app._safe_after(lambda: called.append(True))
    assert app.root.after.call_count == 1
    delay, scheduled = app.root.after.call_args[0]
    assert delay == 0
    scheduled()
    assert called == [True]


def test_safe_after_forwards_extra_args(app):
    """Extra positional args are forwarded when the scheduled wrapper executes."""
    app.root.after.reset_mock()
    received = []
    app._safe_after(lambda x, y: received.append((x, y)), "a", "b")
    assert app.root.after.call_count == 1
    _, scheduled = app.root.after.call_args[0]
    scheduled()
    assert received == [("a", "b")]


def test_safe_after_early_returns_when_destroyed(app):
    """When _destroyed is True, root.after is not called at all."""
    app.root.after.reset_mock()
    app._destroyed = True
    called = []
    app._safe_after(lambda: called.append(True))
    app.root.after.assert_not_called()
    assert called == []


def test_safe_after_skips_execution_if_destroyed_before_run(app):
    """If _destroyed turns True between scheduling and execution, the callback is dropped."""
    app.root.after.reset_mock()
    called = []
    app._safe_after(lambda: called.append(True))
    _, scheduled = app.root.after.call_args[0]
    app._destroyed = True
    scheduled()
    assert called == []


def test_safe_after_swallows_exception_from_root_after(app):
    """When root.after raises (root destroyed mid-call), _safe_after must
    not propagate the exception."""
    with patch.object(metadata.tk, "TclError", Exception):
        app.root.after.side_effect = Exception("application has been destroyed")
        app._safe_after(lambda: None)  # must not raise


def test_safe_after_swallows_tclerror_inside_callback(app):
    """When the scheduled callback raises tk.TclError at execution time, _run swallows it."""
    app.root.after.reset_mock()
    with patch.object(metadata.tk, "TclError", RuntimeError):
        app._safe_after(lambda: (_ for _ in ()).throw(RuntimeError("widget destroyed")))
        _, scheduled = app.root.after.call_args[0]
        scheduled()  # must not raise
