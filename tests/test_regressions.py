"""Regression tests for bugs fixed in v3.20.2.

Each test would fail on the pre-fix code. Named for the specific bug
they lock in, so a future change that reintroduces one breaks a test
with a clear failure message.
"""

import json
from unittest.mock import MagicMock

from tests.conftest import make_jpeg_with_exif
from tests.helpers import sort_scan


# ---------------------------------------------------------------------------
# Bug 1: first_video_orphan UnboundLocalError on photo-first directories
# ---------------------------------------------------------------------------
def test_photo_first_directory_end_to_end(extractor, tmp_path):
    """Regression: first_video_orphan UnboundLocalError on photo-first
    directories. Three photos on different days each form their own
    timestamp group, producing labels "1", "2", "3"."""
    folder = tmp_path / "photo_first"
    folder.mkdir()
    for i, name in enumerate(["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"], start=1):
        make_jpeg_with_exif(folder / name, f"2024:05:{14 + i:02d} 12:30:45")
    (folder / "IMG_004.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")

    processed, skipped = sort_scan(extractor, folder, write=False)

    assert processed == 3
    assert skipped == 0
    assert len(extractor.results) == 1
    df, _, _ = extractor.results[0]
    assert len(df) == 3
    assert list(df["Files"]) == ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]
    assert list(df["Img # Series"]) == ["1", "2", "3"]
    assert "Unexpected" not in extractor.collected_warnings


def _mock_widgets(extractor, series_value, name_value="Filename (default output.filetype)", recursive=False):
    modifier_entry = MagicMock()
    modifier_entry.get.return_value = series_value
    extractor.modifier_entry = modifier_entry

    name_entry = MagicMock()
    name_entry.get.return_value = name_value
    extractor.name_entry = name_entry

    recursive_var = MagicMock()
    recursive_var.get.return_value = recursive
    extractor.recursive_var = recursive_var

    keepopen_var = MagicMock()
    keepopen_var.get.return_value = False
    extractor.keepopen_var = keepopen_var

    maxdepth_entry = MagicMock()
    maxdepth_entry.get.return_value = "Recursion Depth (#)"
    extractor.maxdepth_entry = maxdepth_entry

    # Tests in this file exercise the modifier entry, which only exists in
    # Advanced mode. Force it so initialize() reads the mock.
    extractor.user_mode_var.set("Advanced")


def test_starting_index_zero_padded_accepted(extractor, tmp_path):
    """Regression: '01' was rejected even though int('01') == 1, and
    `int(val)` was called before `val.isdigit()` so garbage input raised
    ValueError before the 'Numbers only.' dialog could fire."""
    _mock_widgets(extractor, series_value="01")
    (tmp_path / "IMG_001.jpg").write_bytes(b"fake")

    captured = {}

    def fake_start(recursive, final_output, modifier, *args, **kwargs):
        captured["modifier"] = modifier

    extractor._start_scan = fake_start
    extractor.directory_path = tmp_path
    extractor.output_path = tmp_path
    extractor.initialize()

    assert "modifier" in captured, "initialize returned before _start_scan — ValueError or rejection"
    assert captured["modifier"] == 0, f"'01' should map to modifier 0, got {captured['modifier']}"


def test_starting_index_placeholder_uses_zero_modifier(extractor, tmp_path):
    """Placeholder text left unmodified must default to modifier 0."""
    _mock_widgets(extractor, series_value="Starting index (Img # Series)")
    (tmp_path / "IMG_001.jpg").write_bytes(b"fake")

    captured = {}

    def fake_start(recursive, final_output, modifier, *args, **kwargs):
        captured["modifier"] = modifier

    extractor._start_scan = fake_start
    extractor.directory_path = tmp_path
    extractor.output_path = tmp_path
    extractor.initialize()

    assert captured.get("modifier") == 0


# ---------------------------------------------------------------------------
# Bug 3: De Morgan mistake on the default-filename check
# ---------------------------------------------------------------------------


def test_default_filename_when_placeholder_left(extractor, tmp_path):
    """Regression: `name != placeholder or name != ''` was always true,
    so the `output.<ext>` default branch was unreachable. The output
    filename became the placeholder text itself."""
    _mock_widgets(
        extractor,
        series_value="1",
        name_value="Filename (default output.filetype)",
    )
    (tmp_path / "IMG_001.jpg").write_bytes(b"fake")

    captured = {}

    def fake_start(recursive, final_output, modifier, *args, **kwargs):
        captured["final_output"] = final_output

    extractor._start_scan = fake_start
    extractor.directory_path = tmp_path
    extractor.output_path = tmp_path
    extractor.initialize()

    assert "final_output" in captured, "initialize returned before _start_scan"
    assert (
        captured["final_output"].name == "output.xlsx"
    ), f"expected 'output.xlsx', got '{captured['final_output'].name}' — De Morgan bug?"


# ---------------------------------------------------------------------------
# Bug 4: _save_settings did not strip the max-depth entry
# ---------------------------------------------------------------------------


def test_maxdepth_save_strips_whitespace(extractor):
    """Regression: ' 5 ' persisted as None because isdigit() fails on
    leading/trailing whitespace in a narrow entry."""
    import metadata

    extractor.maxdepth_entry.delete(0, "end")
    extractor.maxdepth_entry.insert(0, " 5 ")

    extractor._save_settings()

    data = json.loads(metadata.SETTINGS_PATH.read_text(encoding="utf-8"))
    assert data["Max Depth"] == 5, f"expected 5, got {data['Max Depth']!r} — strip missing?"
