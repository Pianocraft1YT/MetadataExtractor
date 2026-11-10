"""Tests for the include-hiddens toggle (v3.21.0).

The feature: an "Include Hidden Files" checkbox that, when on, disables
the dot-prefix and FILE_ATTRIBUTE_HIDDEN filters in walk_and_filter.

Layers covered:
- _check_hidden direct (flag short-circuits)
- walk_and_filter (flag plumbed through)
- get_total_files (flag plumbed through)
- find_directories (flag plumbed through, end-to-end DataFrame check)
- scan_image (defensive — doesn't filter, operates on media_files as-is)
- Settings persistence (save, load, round-trip both directions)
"""

import json

from tests.conftest import make_jpeg_with_exif
from tests.helpers import find_scan
import metadata

# ---------------------------------------------------------------------------
# _check_hidden — direct
# ---------------------------------------------------------------------------


def test_check_hidden_dot_prefix_default(extractor, tmp_path):
    """Default behavior unchanged: dot-prefix files are hidden."""
    (tmp_path / ".hidden.jpg").write_bytes(b"fake")
    assert extractor._check_hidden(".hidden.jpg", tmp_path) is True


def test_check_hidden_dot_prefix_flag_on(extractor, tmp_path):
    """Flag on short-circuits: dot-prefix files are NOT hidden."""
    (tmp_path / ".hidden.jpg").write_bytes(b"fake")
    assert extractor._check_hidden(".hidden.jpg", tmp_path, include_hiddens=True) is False


# ---------------------------------------------------------------------------
# walk_and_filter
# ---------------------------------------------------------------------------


def test_walk_excludes_hidden_by_default(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "visible.jpg", "2024:05:15 12:30:45")
    make_jpeg_with_exif(tmp_path / ".hidden.jpg", "2024:05:16 12:30:45")

    results = list(extractor.walk_and_filter(str(tmp_path), 0))
    _, _, files = results[0]
    assert "visible.jpg" in files
    assert ".hidden.jpg" not in files


def test_walk_includes_hidden_when_flag_on(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "visible.jpg", "2024:05:15 12:30:45")
    make_jpeg_with_exif(tmp_path / ".hidden.jpg", "2024:05:16 12:30:45")

    results = list(extractor.walk_and_filter(str(tmp_path), 0, include_hiddens=True))
    _, _, files = results[0]
    assert "visible.jpg" in files
    assert ".hidden.jpg" in files


# ---------------------------------------------------------------------------
# get_total_files
# ---------------------------------------------------------------------------


def test_get_total_files_default_excludes_hidden(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "visible.jpg", "2024:05:15 12:30:45")
    make_jpeg_with_exif(tmp_path / ".hidden.jpg", "2024:05:16 12:30:45")

    extractor.directory_path = tmp_path
    assert extractor.get_total_files(0) == 1


def test_get_total_files_includes_hidden_when_flag_on(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "visible.jpg", "2024:05:15 12:30:45")
    make_jpeg_with_exif(tmp_path / ".hidden.jpg", "2024:05:16 12:30:45")

    extractor.directory_path = tmp_path
    assert extractor.get_total_files(0, include_hiddens=True) == 2


# ---------------------------------------------------------------------------
# find_directories — full pipeline
# ---------------------------------------------------------------------------


def test_find_directories_default_excludes_hidden(extractor, tmp_path):
    parent = tmp_path / "parent"
    sub = parent / "sub"
    sub.mkdir(parents=True)
    make_jpeg_with_exif(sub / "visible.jpg", "2024:05:15 12:30:45")
    make_jpeg_with_exif(sub / ".hidden.jpg", "2024:05:16 12:30:45")

    extractor.maxdepth = 1
    processed, _ = find_scan(extractor, parent, write=False)

    assert processed == 1
    df, _, _ = extractor.results[0]
    assert list(df["Files"]) == ["visible.jpg"]


def test_find_directories_includes_hidden_when_flag_on(extractor, tmp_path):
    parent = tmp_path / "parent"
    sub = parent / "sub"
    sub.mkdir(parents=True)
    make_jpeg_with_exif(sub / "visible.jpg", "2024:05:15 12:30:45")
    make_jpeg_with_exif(sub / ".hidden.jpg", "2024:05:16 12:30:45")

    extractor.maxdepth = 1
    processed, _ = find_scan(extractor, parent, include_hiddens=True, write=False)

    assert processed == 2
    df, _, _ = extractor.results[0]
    assert sorted(df["Files"]) == [".hidden.jpg", "visible.jpg"]


# ---------------------------------------------------------------------------
# scan_image — no filter of its own
# ---------------------------------------------------------------------------


def test_scan_image_processes_hidden_filename(extractor, tmp_path):
    """scan_image operates on whatever media_files it's handed. No hidden check."""
    make_jpeg_with_exif(tmp_path / ".hidden.jpg", "2024:05:15 12:30:45")

    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        0,
        data,
        [".hidden.jpg"],
        output_utc=False,
        output_dimensions=False,
        output_make=False,
        output_model=False,
        output_software=False,
        output_lens_model=False,
        output_aperture=False,
        output_exposure_time=False,
        output_focal_length=False,
        output_iso=False,
        output_gps=False,
    )
    assert ok is True
    assert data["Images"] == [".hidden.jpg"]


# ---------------------------------------------------------------------------
# Settings persistence
# ---------------------------------------------------------------------------


def test_include_hiddens_saves_true(extractor):
    extractor.hidden_var.set(True)
    extractor._save_settings()

    data = json.loads(metadata.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert data["Include Hiddens"] is True


def test_include_hiddens_saves_false(extractor):
    extractor.hidden_var.set(False)
    extractor._save_settings()

    data = json.loads(metadata.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert data["Include Hiddens"] is False


def test_include_hiddens_true_round_trip(extractor):
    extractor.hidden_var.set(True)
    extractor._save_settings()
    extractor.hidden_var.set(False)
    extractor._load_settings()
    assert extractor.hidden_var.get() is True


def test_include_hiddens_false_round_trip(extractor):
    extractor.hidden_var.set(False)
    extractor._save_settings()
    extractor.hidden_var.set(True)
    extractor._load_settings()
    assert extractor.hidden_var.get() is False
