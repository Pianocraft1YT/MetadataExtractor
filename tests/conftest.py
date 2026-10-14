"""
Shared fixtures and Tkinter mocking for the metadata test suite.

Tkinter is replaced with MagicMock before metadata.py is imported, so
`root = tk.Tk()` and `root.mainloop()` at module scope don't try to open
a real window. This lets the whole suite run headless on CI.
"""

import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Mock tkinter BEFORE importing metadata
# ---------------------------------------------------------------------------
sys.modules["tkinter"] = MagicMock()
sys.modules["tkinter.messagebox"] = MagicMock()
sys.modules["tkinter.filedialog"] = MagicMock()
sys.modules["tkinter.ttk"] = MagicMock()

import pytest
from pathlib import Path
from PIL import Image

import metadata  # safe now


# ---------------------------------------------------------------------------
# Auto-use fixtures — reset state and neuter side-effecting calls
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_module_state():
    """Wipe module-level state before and after every test."""
    metadata.reset()
    metadata.directory_path = None
    metadata.output_path = None
    yield
    metadata.reset()
    metadata.directory_path = None
    metadata.output_path = None


@pytest.fixture(autouse=True)
def silence_messageboxes(monkeypatch):
    """
    Replace every messagebox call with a MagicMock so nothing blocks.
    askyesno defaults to True (proceed). Individual tests can override.
    """
    monkeypatch.setattr(metadata.messagebox, "showerror", MagicMock())
    monkeypatch.setattr(metadata.messagebox, "showinfo", MagicMock())
    monkeypatch.setattr(metadata.messagebox, "showwarning", MagicMock())
    monkeypatch.setattr(metadata.messagebox, "askyesno", MagicMock(return_value=True))


@pytest.fixture(autouse=True)
def mute_create_sheet(request, monkeypatch):
    """
    Block the default Excel-writing path — except for tests that need
    the real one. Those should use @pytest.mark.real_create_sheet.
    """
    if request.node.get_closest_marker("real_create_sheet"):
        return  # don't mock — let the test use the real function
    monkeypatch.setattr(metadata, "create_sheet", MagicMock())

# ---------------------------------------------------------------------------
# Helpers for building test images
# ---------------------------------------------------------------------------

def make_jpeg_with_exif(path: Path, date_str: str, field: int = metadata.EXIF_DATETIME_ORIGINAL) -> Path:
    """Create a tiny JPEG with one EXIF date field set."""
    img = Image.new("RGB", (10, 10), color="red")
    exif = Image.Exif()
    exif[field] = date_str
    img.save(path, format="JPEG", exif=exif)
    return path


def make_jpeg_no_exif(path: Path) -> Path:
    """Create a tiny JPEG with no EXIF date fields."""
    img = Image.new("RGB", (10, 10), color="blue")
    img.save(path, format="JPEG")
    return path


def make_corrupt_file(path: Path) -> Path:
    """Write text to a .jpg so Image.open() raises UnidentifiedImageError."""
    path.write_text("this is not an image")
    return path


# ---------------------------------------------------------------------------
# Folder fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def photos_only(tmp_path):
    """3 JPEGs with EXIF, no videos."""
    folder = tmp_path / "photos_only"
    folder.mkdir()
    for i, name in enumerate(["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]):
        make_jpeg_with_exif(folder / name, f"2024:05:{15 + i:02d} 12:30:45")
    return folder


@pytest.fixture
def photos_and_videos(tmp_path):
    """
    Classic 3-photos + 1-video pattern, repeated 3 times:
        P P P V | P P P V | P P P V
    Files are numbered so videos sort *between* photo groups, not after
    them. Using "IMG_" and "VID_" prefixes would put all photos first,
    because "IMG" < "VID" alphabetically.
    """
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
    """3 valid JPEGs + 1 corrupt 'jpg' + 3 more valid."""
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
    """2 valid JPEGs + 1 JPEG missing all EXIF dates."""
    folder = tmp_path / "missing_exif"
    folder.mkdir()
    make_jpeg_with_exif(folder / "IMG_001.jpg", "2024:05:15 12:30:45")
    make_jpeg_no_exif(folder / "IMG_002.jpg")
    make_jpeg_with_exif(folder / "IMG_003.jpg", "2024:05:17 12:30:45")
    return folder