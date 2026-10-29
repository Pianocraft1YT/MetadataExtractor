"""
Shared fixtures for the metadata test suite.
"""

import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image

sys.modules["tkinter"] = MagicMock()
sys.modules["tkinter.messagebox"] = MagicMock()
sys.modules["tkinter.filedialog"] = MagicMock()
sys.modules["tkinter.ttk"] = MagicMock()

import tkinter as _tk


class FakeVar:
    def __init__(self, master=None, value=None, name=None):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def trace_add(self, *a, **k):
        return "trace_id"

    def trace_remove(self, *a, **k):
        pass


_tk.BooleanVar.side_effect = FakeVar
_tk.StringVar.side_effect = FakeVar
_tk.DoubleVar.side_effect = FakeVar

import metadata


def _set_timezone(app, value):
    app.timezone_var.set(value)


def _set_filetype(app, value):
    app.filetype_var.set(value)


def _build_extractor(request, filetype, timezone=False):
    app = metadata.MetadataExtractor()
    if not request.node.get_closest_marker("real_create_sheet"):
        app.create_sheet = MagicMock()
    _set_timezone(app, timezone)
    _set_filetype(app, filetype)
    app.keepopen_var.set(True)
    app.debug_var.set(False)
    return app


@pytest.fixture
def extractor(request):
    return _build_extractor(request, "Excel", timezone=False)


@pytest.fixture
def extractor_csv(request):
    return _build_extractor(request, "CSV", timezone=False)


@pytest.fixture
def extractor_tz_off(request):
    return _build_extractor(request, "Excel", timezone=False)


@pytest.fixture
def extractor_tz_on(request):
    return _build_extractor(request, "Excel", timezone=True)


@pytest.fixture(autouse=True)
def silence_messageboxes(monkeypatch):
    fake = MagicMock()
    fake.askyesno.return_value = True
    fake.askokcancel.return_value = True
    monkeypatch.setattr(metadata, "messagebox", fake)
    return fake


@pytest.fixture(autouse=True)
def bypass_threadsafe_dialog(monkeypatch):
    """Bypass _ask_yes_no_threadsafe which blocks on threading.Event.

    The real method uses root.after() to marshal to the main thread.
    In tests root is a MagicMock so after() is a no-op and the event
    never gets set -- the test hangs. Call messagebox.askyesno directly.
    """
    def fake_ask(self, title, msg):
        return bool(metadata.messagebox.askyesno(title, msg))
    monkeypatch.setattr(metadata.MetadataExtractor, "_ask_yes_no_threadsafe", fake_ask)


@pytest.fixture(autouse=True)
def patch_sys_exit(monkeypatch):
    def fake_exit(code=0):
        raise SystemExit(code)
    monkeypatch.setattr(sys, "exit", fake_exit)


@pytest.fixture(autouse=True)
def run_threads_synchronously(monkeypatch):
    class FakeThread:
        def __init__(self, target=None, args=(), kwargs=None, daemon=None, **_):
            self._target = target
            self._args = args
            self._kwargs = kwargs or {}

        def start(self):
            if self._target:
                self._target(*self._args, **self._kwargs)

    monkeypatch.setattr(threading, "Thread", FakeThread)


# ---------------------------------------------------------------------------
# Image builders
# ---------------------------------------------------------------------------


def make_jpeg_with_exif(path: Path, date_str: str, field: int = metadata.EXIF_DATETIME_ORIGINAL) -> Path:
    img = Image.new("RGB", (10, 10), color="red")
    exif = Image.Exif()
    exif[field] = date_str
    img.save(path, format="JPEG", exif=exif)
    return path


def make_jpeg_no_exif(path: Path) -> Path:
    img = Image.new("RGB", (10, 10), color="blue")
    img.save(path, format="JPEG")
    return path


def make_corrupt_file(path: Path) -> Path:
    path.write_text("this is not an image")
    return path


# ---------------------------------------------------------------------------
# Folder fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def photos_only(tmp_path):
    folder = tmp_path / "photos_only"
    folder.mkdir()
    for i, name in enumerate(["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]):
        make_jpeg_with_exif(folder / name, f"2024:05:{15 + i:02d} 12:30:45")
    return folder


@pytest.fixture
def photos_and_videos(tmp_path):
    folder = tmp_path / "photos_and_videos"
    folder.mkdir()
    counter = 1
    for series in range(3):
        for _ in range(3):
            make_jpeg_with_exif(folder / f"{counter:04d}_photo.jpg", f"2024:05:{15 + series:02d} 12:30:45")
            counter += 1
        (folder / f"{counter:04d}_video.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
        counter += 1
    return folder


@pytest.fixture
def folder_with_corrupt_photo(tmp_path):
    folder = tmp_path / "with_corrupt"
    folder.mkdir()
    for name in ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]:
        make_jpeg_with_exif(folder / name, "2024:05:15 12:30:45")
    make_corrupt_file(folder / "IMG_004.jpg")
    for name in ["IMG_005.jpg", "IMG_006.jpg", "IMG_007.jpg"]:
        make_jpeg_with_exif(folder / name, "2024:05:16 12:30:45")
    return folder


@pytest.fixture
def folder_missing_exif(tmp_path):
    folder = tmp_path / "missing_exif"
    folder.mkdir()
    make_jpeg_with_exif(folder / "IMG_001.jpg", "2024:05:15 12:30:45")
    make_jpeg_no_exif(folder / "IMG_002.jpg")
    make_jpeg_with_exif(folder / "IMG_003.jpg", "2024:05:17 12:30:45")
    return folder


@pytest.fixture
def make_jpeg(tmp_path):
    def _make(filename, *, datetime_original=None, datetime_digitized=None, datetime_general=None, offset_original=None):
        img = Image.new("RGB", (10, 10), color="red")
        exif = Image.Exif()
        if datetime_general is not None:
            exif[metadata.EXIF_DATETIME] = datetime_general
        if datetime_original is not None:
            exif[metadata.EXIF_DATETIME_ORIGINAL] = datetime_original
        if datetime_digitized is not None:
            exif[metadata.EXIF_DATETIME_DIGITIZED] = datetime_digitized
        if offset_original is not None:
            exif[metadata.EXIF_OFFSET_TIME_ORIGINAL] = offset_original
        path = tmp_path / filename
        img.save(path, format="JPEG", exif=exif)
        return path
    return _make