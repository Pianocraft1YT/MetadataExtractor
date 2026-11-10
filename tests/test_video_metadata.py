"""Tests for video_metadata.extract_video_metadata."""

from datetime import datetime, UTC
from pathlib import Path

import pytest

from video_metadata import extract_video_metadata, MP4_EPOCH_OFFSET


def make_box(box_type, payload):
    """Build a box: 4-byte big-endian size + 4-byte ASCII type + payload."""
    size = 8 + len(payload)
    return size.to_bytes(4, "big") + box_type.encode("ascii") + payload


def make_mp4_with_mvhd(path, creation_time, version=0):
    """Write a minimal valid MP4 with the given mvhd creation_time.

    creation_time is raw seconds since 1904-01-01 (MP4 epoch).
    version 0 uses 4-byte timestamps, version 1 uses 8-byte.
    """
    if version == 0:
        vf = b"\x00\x00\x00\x00"
        cb = creation_time.to_bytes(4, "big")
        mb = creation_time.to_bytes(4, "big")
        db = (0).to_bytes(4, "big")
    elif version == 1:
        vf = b"\x01\x00\x00\x00"
        cb = creation_time.to_bytes(8, "big")
        mb = creation_time.to_bytes(8, "big")
        db = (0).to_bytes(8, "big")
    else:
        raise ValueError("version must be 0 or 1")

    mvhd_payload = (
        vf  # version + flags
        + cb  # creation_time
        + mb  # modification_time
        + (1000).to_bytes(4, "big")  # timescale
        + db  # duration
        + (0x00010000).to_bytes(4, "big")  # rate (1.0x)
        + (0x0100).to_bytes(2, "big")  # volume (1.0x)
        + b"\x00\x00"  # reserved1
        + b"\x00" * 8  # reserved2
        + b"\x00" * 36  # matrix
        + b"\x00" * 24  # predefined
        + (2).to_bytes(4, "big")  # next_track_id
    )

    mvhd = make_box("mvhd", mvhd_payload)
    moov = make_box("moov", mvhd)
    ftyp = make_box("ftyp", b"mp42" + b"\x00\x00\x00\x00" + b"mp42isom")

    Path(path).write_bytes(ftyp + moov)


def dt_to_mp4_epoch(dt):
    """Convert an aware datetime to raw 1904-epoch seconds."""
    return int(dt.timestamp()) + MP4_EPOCH_OFFSET


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_reads_v0_creation_time(tmp_path):
    target = datetime(2024, 5, 15, 12, 30, 45, tzinfo=UTC)
    path = tmp_path / "v0.mp4"
    make_mp4_with_mvhd(path, creation_time=dt_to_mp4_epoch(target), version=0)

    assert extract_video_metadata(path) == target


def test_reads_v1_creation_time(tmp_path):
    target = datetime(2024, 5, 15, 12, 30, 45, tzinfo=UTC)
    path = tmp_path / "v1.mp4"
    make_mp4_with_mvhd(path, creation_time=dt_to_mp4_epoch(target), version=1)

    assert extract_video_metadata(path) == target


def test_moov_after_mdat_returns_correct(tmp_path):
    """The walker must skip past mdat by its size field, not string-search."""
    target = datetime(2024, 5, 15, 12, 30, 45, tzinfo=UTC)
    path = tmp_path / "mdat_first.mp4"

    ftyp = make_box("ftyp", b"mp42" + b"\x00\x00\x00\x00" + b"mp42isom")
    mdat = make_box("mdat", b"\x00" * 1000)

    cb = dt_to_mp4_epoch(target).to_bytes(4, "big")
    mvhd_payload = (
        b"\x00\x00\x00\x00"
        + cb
        + cb
        + (1000).to_bytes(4, "big")
        + (0).to_bytes(4, "big")
        + (0x00010000).to_bytes(4, "big")
        + (0x0100).to_bytes(2, "big")
        + b"\x00\x00"
        + b"\x00" * 8
        + b"\x00" * 36
        + b"\x00" * 24
        + (2).to_bytes(4, "big")
    )
    mvhd = make_box("mvhd", mvhd_payload)
    moov = make_box("moov", mvhd)

    path.write_bytes(ftyp + mdat + moov)

    assert extract_video_metadata(path) == target


# ---------------------------------------------------------------------------
# Rejections — must return None, never raise
# ---------------------------------------------------------------------------


def test_creation_time_zero_returns_none(tmp_path):
    """creation_time == 0 means 'no timestamp set' per spec."""
    path = tmp_path / "zero.mp4"
    make_mp4_with_mvhd(path, creation_time=0, version=0)

    assert extract_video_metadata(path) is None


def test_pre_1970_returns_none(tmp_path):
    """A creation_time that produces a pre-Unix-epoch date is corrupt."""
    path = tmp_path / "ancient.mp4"
    make_mp4_with_mvhd(path, creation_time=1_000_000, version=0)

    assert extract_video_metadata(path) is None


def test_no_moov_returns_none(tmp_path):
    """A file with ftyp but no moov box."""
    path = tmp_path / "nomovie.mp4"
    ftyp = make_box("ftyp", b"mp42" + b"\x00\x00\x00\x00" + b"mp42isom")
    path.write_bytes(ftyp)

    assert extract_video_metadata(path) is None


def test_empty_file_returns_none(tmp_path):
    path = tmp_path / "empty.mp4"
    path.write_bytes(b"")

    assert extract_video_metadata(path) is None


def test_non_mp4_returns_none(tmp_path):
    path = tmp_path / "text.mp4"
    path.write_bytes(b"this is not an MP4 file")

    assert extract_video_metadata(path) is None


def test_nonexistent_file_returns_none(tmp_path):
    path = tmp_path / "does_not_exist.mp4"

    assert extract_video_metadata(path) is None


# ---------------------------------------------------------------------------
# Real-file validation (skipped unless the file is on this machine)
# ---------------------------------------------------------------------------


REAL_FILE = Path.home() / "Downloads/MetadataExtractor/test.mp4"


@pytest.mark.skipif(not REAL_FILE.exists(), reason="manual test, requires local file")
def test_real_mp4():
    """Real-world validation against a known-good MP4."""
    dt = extract_video_metadata(REAL_FILE)
    assert dt is not None
    assert dt.year == 2000
    assert dt.month == 1
    assert dt.day == 1
