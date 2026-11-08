"""Tests for leading-video handling and the trailing-group fix.

Background: single non-orphan leading video means "video opens the group."
Trailing photos belong to the last-opened group even with no closing video.
Multi-strip and orphan-strip stay in video-closes mode: once the leading
video is gone, no group has been opened, so trailing photos are one-offs.
"""

import json

import pytest

import metadata
from tests.conftest import make_jpeg_with_exif
from tests.helpers import sort_scan


def _build(folder, layout):
    """layout is a string like 'vpppvppp' — v=video, p=photo.
    Files are numbered 1..N so they sort in the given order."""
    for idx, kind in enumerate(layout, start=1):
        if kind == "p":
            make_jpeg_with_exif(folder / f"{idx}.jpg", f"2024:05:{10 + idx:02d} 12:30:45")
        else:
            (folder / f"{idx}.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")


@pytest.fixture
def folder(tmp_path):
    f = tmp_path / "videos"
    f.mkdir()
    return f


@pytest.fixture
def orphan_prompt(monkeypatch):
    """Controls what the 'Video First' dialog returns.
    Set .answer = True (orphan) or False (non-orphan) in the test body."""
    state = {"answer": True}

    def fake_ask(self, title, msg):
        return state["answer"]

    monkeypatch.setattr("metadata.MetadataExtractor._ask_yes_no_threadsafe", fake_ask)
    return state


# ---------------------------------------------------------------------------
# Mode A: single non-orphan leading video opens the group.
# ---------------------------------------------------------------------------


def test_non_orphan_trailing_group_labeled(extractor, folder, orphan_prompt):
    """[v, p, p, p, v, p, p, p] → '1-4', '5-8' (not '1-4', '5', '6', '7')."""
    _build(folder, "vpppvppp")
    orphan_prompt["answer"] = False

    sort_scan(extractor, folder, write=False)

    df, _, _ = extractor.results[0]
    assert len(df) == 2, "second group missing — is the tail-end guard returning early?"
    assert list(df["Files"]) == ["4.jpg", "8.jpg"]
    assert list(df["Img # Series"]) == ["1-4", "5-8"]


def test_non_orphan_no_closing_video(extractor, folder, orphan_prompt):
    """[v, p, p, p] → '1-4' (not one-offs '1', '2', '3')."""
    _build(folder, "vppp")
    orphan_prompt["answer"] = False

    sort_scan(extractor, folder, write=False)

    df, _, _ = extractor.results[0]
    assert len(df) == 1
    assert list(df["Files"]) == ["4.jpg"]
    assert list(df["Img # Series"]) == ["1-4"]


# ---------------------------------------------------------------------------
# Mode B: single orphan leading video → trailing photos are one-offs.
# ---------------------------------------------------------------------------


def test_orphan_trailing_group_one_offs(extractor, folder, orphan_prompt):
    """[v, p, p, p, v, p, p, p] with orphan=True → '1-4', '5', '6', '7'."""
    _build(folder, "vpppvppp")
    orphan_prompt["answer"] = True

    sort_scan(extractor, folder, write=False)

    df, _, _ = extractor.results[0]
    assert list(df["Img # Series"]) == ["1-4", "5", "6", "7"]


# ---------------------------------------------------------------------------
# Mode C: multiple leading videos → stripped, warned, video-closes mode.
# ---------------------------------------------------------------------------


def test_multiple_leading_videos_stripped_and_warned(extractor, folder):
    """[v, v, p, p, p, v, p, p, p] → strip both, then [p,p,p,v,p,p,p]
    → '1-4', '5', '6', '7'. The strip must log a warning."""
    _build(folder, "vvpppvppp")

    sort_scan(extractor, folder, write=False)

    assert "Leading Video" in extractor.collected_warnings
    df, _, _ = extractor.results[0]
    assert list(df["Img # Series"]) == ["1-4", "5", "6", "7"]


# ---------------------------------------------------------------------------
# Mode D: only videos, no photos → "Only Video(s)" warning, empty results.
# ---------------------------------------------------------------------------


def test_all_videos_single_warned(extractor, folder):
    """[v] → 'Only Video(s)' warning, empty results."""
    _build(folder, "v")

    sort_scan(extractor, folder, write=False)

    assert "Only Video(s)" in extractor.collected_warnings
    assert extractor.results == []


def test_all_videos_multi_warned(extractor, folder):
    """[v, v, v] → 'Only Video(s)', NOT 'Leading Video'.
    Catches the elif-precedence bug where leading_videos>1 swallowed
    the all-videos case before it could be classified."""
    _build(folder, "vvv")

    sort_scan(extractor, folder, write=False)

    assert "Only Video(s)" in extractor.collected_warnings
    assert "Leading Video" not in extractor.collected_warnings
    assert extractor.results == []


# ---------------------------------------------------------------------------
# Debug mode: single leading video is always kept, never prompted.
# ---------------------------------------------------------------------------


def test_debug_mode_keeps_leading_video(extractor, folder, orphan_prompt):
    """In debug, single leading video is kept with no prompt.
    Setting orphan_prompt to True would strip it in non-debug — debug
    must ignore the prompt and behave as non-orphan."""
    _build(folder, "vppp")
    orphan_prompt["answer"] = True  # would strip if the prompt ran

    sort_scan(extractor, folder, debug=True, write=False)

    df, _, _ = extractor.results[0]
    assert list(df["Img # Series"]) == ["1-4"]


def test_non_orphan_trailing_group_modifier(extractor, folder, orphan_prompt):
    """Modifier must apply to both ends of the tail-end group label."""
    _build(folder, "vpppvppp")
    orphan_prompt["answer"] = False
    sort_scan(extractor, folder, modifier=4, write=False)
    df, _, _ = extractor.results[0]
    assert list(df["Img # Series"]) == ["5-8", "9-12"]
