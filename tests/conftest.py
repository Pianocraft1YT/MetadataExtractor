"""
Shared fixtures for the metadata test suite.

Tkinter is mocked before metadata.py is imported, so MetadataExtractor's
__init__ creates Mock widgets instead of real ones. Each test gets a fresh
instance — no module-level state to reset.
"""

import sys
from unittest.mock import MagicMock

# Mock tkinter BEFORE importing metadata
sys.modules["tkinter"] = MagicMock()
sys.modules["tkinter.messagebox"] = MagicMock()
sys.modules["tkinter.filedialog"] = MagicMock()
sys.modules["tkinter.ttk"] = MagicMock()

import pytest
from pathlib import Path
from PIL import Image

import metadata


@pytest.fixture(autouse=True)
def silence_messageboxes(monkeypatch):
    monkeypatch.setattr(metadata.messagebox, "showerror", MagicMock())
    monkeypatch.setattr(metadata.messagebox, "showinfo", MagicMock())
    monkeypatch.setattr(metadata.messagebox, "showwarning", MagicMock())
    monkeypatch.setattr(metadata.messagebox, "askyesno", MagicMock(return_value=True))


@pytest.fixture
def extractor(request):
    """
    Fresh MetadataExtractor with create_sheet mocked by default.

    Tests marked with @pytest.mark.real_create_sheet keep the real
    create_sheet and can assert on the actual xlsx output.
    """
    app = metadata.MetadataExtractor()
    if not request.node.get_closest_marker("real_create_sheet"):
        app.create_sheet = MagicMock()
    return app


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