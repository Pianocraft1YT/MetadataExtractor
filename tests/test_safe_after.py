"""Tests for _safe_after — worker-thread-safe root.after wrapper.

Under the test suite, tkinter is globally mocked (see conftest), so
app.root is a MagicMock and root.after does not actually schedule
anything. Tests here verify the call contract via MagicMock assertions
rather than event-loop behavior.
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
    """When the root is alive, _safe_after forwards to root.after(0, callback)."""
    app.root.after.reset_mock()
    called = []
    cb = lambda: called.append(True)
    app._safe_after(cb)
    app.root.after.assert_called_once_with(0, cb)


def test_safe_after_forwards_extra_args(app):
    """Extra positional args are passed through to root.after."""
    app.root.after.reset_mock()
    cb = lambda x, y: None
    app._safe_after(cb, "a", "b")
    app.root.after.assert_called_once_with(0, cb, "a", "b")


def test_safe_after_early_returns_when_destroyed(app):
    """When _destroyed is True, root.after is not called at all."""
    app.root.after.reset_mock()
    app._destroyed = True
    called = []
    app._safe_after(lambda: called.append(True))
    app.root.after.assert_not_called()
    assert called == []


def test_safe_after_swallows_exception_from_root_after(app):
    """When root.after raises (root destroyed mid-call), _safe_after must
    not propagate the exception.

    Under the test suite, tkinter is mocked and tk.TclError is a MagicMock
    attribute — not a real exception class. Patch it to a real exception
    class to exercise the except clause.
    """
    with patch.object(metadata.tk, "TclError", Exception):
        app.root.after.side_effect = Exception("application has been destroyed")
        app._safe_after(lambda: None)  # must not raise
