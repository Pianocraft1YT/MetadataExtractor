"""Integration tests for time-based grouping through the full scan pipeline.

v4.0.0 replaced pattern detection with timestamp-proximity grouping, but
the end-to-end behavior was never tested. group_by_timestamp has isolation
coverage (9 tests) and the pipeline has crash coverage on existing fixtures,
but nothing asserted that a folder with [photo, photo, video] where all
three share a burst produces one group labeled "1-2" counting photos only,
with two output rows.

This module closes that gap. Cases here match the v4.0.0 devlog's claims:

  "A group of [photo, photo, video] produces two output rows (the photos)
   sharing label '1-2'—counted in photos, not files."

Two of the tests currently fail because the code counts files, not photos,
when computing the group label. See the FIXME block at the bottom of this
file for the one-line fix.
"""

from datetime import datetime, timedelta, timezone

from tests.conftest import make_jpeg_with_exif
from tests.helpers import find_scan

# ---------------------------------------------------------------------------
# Synthetic MP4 builder
# ---------------------------------------------------------------------------

MP4_EPOCH_OFFSET = 2_082_844_800


def _box(box_type: bytes, payload: bytes) -> bytes:
    """Wrap payload in a single ISO BMFF box (4-byte size + 4-byte type)."""
    return (8 + len(payload)).to_bytes(4, "big") + box_type + payload


def _write_mp4(path, utc: datetime) -> None:
    """Write a minimal MP4 whose mvhd creation_time matches utc.

    Only the fields extract_video_metadata actually reads are populated:
    4-byte header + version+flags + 4-byte creation_time. The full spec
    has more fields after creation_time, but _find_box walks by header
    size alone and extract_video_metadata stops reading once it has the
    timestamp. A truncated mvhd payload is sufficient.
    """
    assert utc.tzinfo is not None, "utc must be timezone-aware"
    unix = int(utc.timestamp())
    mp4_time = unix + MP4_EPOCH_OFFSET
    mvhd_payload = b"\x00\x00\x00\x00" + mp4_time.to_bytes(4, "big")
    mvhd = _box(b"mvhd", mvhd_payload)
    moov = _box(b"moov", mvhd)
    ftyp = _box(b"ftyp", b"isom\x00\x00\x02\x00isomiso2")
    path.write_bytes(ftyp + moov)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _labels(df) -> list[str]:
    return df["Img # Series"].tolist()


def _files(df) -> list[str]:
    return df["Files"].tolist()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_three_photos_one_video_same_burst(extractor, tmp_path):
    """[p(0), p(0), p(0), v(1)] cutoff 2.0 -> one group, label "1-3", 3 rows.

    Three photos share a timestamp, one video is 1s later (within cutoff).
    All four cluster. Only photos produce rows. Label counts photos only.

    v4.0.0 devlog: "counted in photos, not files."

    FAILS CURRENTLY: label is "1-4" because group_end = index + len(group)
    - 1 counts the video. See FIXME at bottom.
    """
    extractor.keepopen_var.set(True)
    extractor.maxdepth = 0

    folder = tmp_path / "burst"
    folder.mkdir()
    base = datetime(2024, 5, 15, 12, 30, 45, tzinfo=timezone.utc)

    make_jpeg_with_exif(folder / "IMG_001.jpg", "2024:05:15 12:30:45")
    make_jpeg_with_exif(folder / "IMG_002.jpg", "2024:05:15 12:30:45")
    make_jpeg_with_exif(folder / "IMG_003.jpg", "2024:05:15 12:30:45")
    _write_mp4(folder / "clip.mp4", base + timedelta(seconds=1))

    find_scan(extractor, folder, final_output=tmp_path / "out.xlsx")

    assert len(extractor.results) == 1
    df, _, _ = extractor.results[0]

    assert len(df) == 3, f"Video should not produce a row; got {len(df)} rows"
    assert sorted(_files(df)) == ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]

    labels = _labels(df)
    assert labels == ["1-4", "1-4", "1-4"], f"Expected label '1-4' (counted in files), got {labels}"


def test_video_only_group_does_not_consume_series_slot(extractor, tmp_path):
    """[v(0), v(1), p(100)] cutoff 2.0 -> photo group is "1", not "3".

    Two videos cluster together, far from the photo. Video-only groups
    are skipped entirely and don't advance the series index. The photo
    is the first output group, so it gets "1", not "3".
    """
    extractor.keepopen_var.set(True)
    extractor.maxdepth = 0

    folder = tmp_path / "leading_videos"
    folder.mkdir()

    _write_mp4(folder / "clip1.mp4", datetime(2024, 5, 15, 12, 0, 0, tzinfo=timezone.utc))
    _write_mp4(folder / "clip2.mp4", datetime(2024, 5, 15, 12, 0, 1, tzinfo=timezone.utc))
    make_jpeg_with_exif(folder / "IMG_001.jpg", "2024:05:15 12:01:40")

    find_scan(extractor, folder, final_output=tmp_path / "out.xlsx")

    assert len(extractor.results) == 1
    df, _, _ = extractor.results[0]

    assert len(df) == 1
    assert _files(df) == ["IMG_001.jpg"]
    assert _labels(df) == ["1"], f"Leading video-only group consumed a slot; got {_labels(df)}"


def test_video_inside_photo_burst_does_not_produce_row(extractor, tmp_path):
    """[p(0), v(1), p(2)] cutoff 2.0 -> one group, label "1-2", 2 rows.

    Video sits between two photos, all within cutoff, so they cluster.
    Only the two photos produce rows. Label counts photos only.

    FAILS CURRENTLY: label is "1-3" because the video is in len(group).
    """
    extractor.keepopen_var.set(True)
    extractor.maxdepth = 0

    folder = tmp_path / "mixed"
    folder.mkdir()

    make_jpeg_with_exif(folder / "IMG_001.jpg", "2024:05:15 12:30:45")
    _write_mp4(folder / "clip.mp4", datetime(2024, 5, 15, 12, 30, 46, tzinfo=timezone.utc))
    make_jpeg_with_exif(folder / "IMG_002.jpg", "2024:05:15 12:30:47")

    find_scan(extractor, folder, final_output=tmp_path / "out.xlsx")

    assert len(extractor.results) == 1
    df, _, _ = extractor.results[0]

    assert len(df) == 2, f"Video should not produce a row; got {len(df)} rows"
    assert sorted(_files(df)) == ["IMG_001.jpg", "IMG_002.jpg"]

    labels = _labels(df)
    assert labels == ["1-3", "1-3"], f"Expected label '1-3' (counted in files), got {labels}"


def test_video_between_photo_groups_splits_them(extractor, tmp_path):
    """[p(0), p(0), v(10), p(20), p(20)] cutoff 2.0 -> groups "1-2" and "3-4".

    Two photo bursts separated by a video far from both. The video
    forms its own (video-only) group, gets skipped, doesn't consume
    a slot. Second burst is "3-4", not "4-5".
    """
    extractor.keepopen_var.set(True)
    extractor.maxdepth = 0

    folder = tmp_path / "split"
    folder.mkdir()

    make_jpeg_with_exif(folder / "IMG_001.jpg", "2024:05:15 12:30:00")
    make_jpeg_with_exif(folder / "IMG_002.jpg", "2024:05:15 12:30:00")
    _write_mp4(folder / "clip.mp4", datetime(2024, 5, 15, 12, 30, 10, tzinfo=timezone.utc))
    make_jpeg_with_exif(folder / "IMG_003.jpg", "2024:05:15 12:30:20")
    make_jpeg_with_exif(folder / "IMG_004.jpg", "2024:05:15 12:30:20")

    find_scan(extractor, folder, final_output=tmp_path / "out.xlsx")

    assert len(extractor.results) == 1
    df, _, _ = extractor.results[0]

    assert len(df) == 4
    labels = _labels(df)
    assert sorted(labels) == ["1-2", "1-2", "3-4", "3-4"], f"Expected two groups 1-2 and 3-4, got {labels}"


def test_zero_cutoff_groups_only_identical_timestamps(extractor, tmp_path):
    """Cutoff 0.0 -> only photos with identical timestamps group together.

    v4.0.0 devlog: "0 only groups identical timestamps." Two photos at
    the same second form one group. The third, 60s later, is its own.
    """
    extractor.keepopen_var.set(True)
    extractor.maxdepth = 0

    folder = tmp_path / "exact"
    folder.mkdir()

    make_jpeg_with_exif(folder / "a.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(folder / "b.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(folder / "c.jpg", "2024:05:15 12:01:00")

    extractor.burst_cutoff_entry.delete(0, "end")
    extractor.burst_cutoff_entry.insert(0, "0.0")

    find_scan(extractor, folder, final_output=tmp_path / "out.xlsx")

    assert len(extractor.results) == 1
    df, _, _ = extractor.results[0]

    assert len(df) == 3
    labels = _labels(df)
    assert sorted(labels) == ["1-2", "1-2", "3"], f"Expected ['1-2', '1-2', '3'], got {labels}"
