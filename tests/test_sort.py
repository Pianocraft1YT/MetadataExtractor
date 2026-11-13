"""Tests for sort_and_extract (the merged scan function)."""

from tests.conftest import make_jpeg_with_exif, make_jpeg_no_exif
from tests.helpers import sort_scan


def test_sort_and_extract_all_photos(extractor, photos_only):
    sort_scan(extractor, photos_only, write=False)
    assert len(extractor.results) == 1
    df, _, _ = extractor.results[0]
    assert len(df) == 3
    assert list(df["Files"]) == ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]


def test_sort_and_extract_missing_exif_appends_to_bottom(extractor, folder_missing_exif):
    processed, skipped = sort_scan(extractor, folder_missing_exif, write=False)
    df, _, _ = extractor.results[0]
    assert len(df) == 3
    assert "IMG_002.jpg" in list(df["Files"])
    no_exif_row = df[df["Files"] == "IMG_002.jpg"].iloc[0]
    assert no_exif_row["Img # Series"] == ""
    assert processed == 3
    assert skipped == 0


def test_sort_and_extract_corrupt_file_does_not_hang(extractor, folder_with_corrupt_photo):
    processed, skipped = sort_scan(extractor, folder_with_corrupt_photo, write=False)
    df, _, _ = extractor.results[0]
    assert len(df) == 6
    assert skipped == 1
    assert processed == 6


def test_sort_and_extract_no_exif_gap_in_series(extractor, tmp_path):
    folder = tmp_path / "gap"
    folder.mkdir()
    for name in ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]:
        make_jpeg_with_exif(folder / name, "2024:05:15 12:30:45")
    make_jpeg_no_exif(folder / "IMG_002.jpg")

    processed, skipped = sort_scan(extractor, folder, write=False)
    assert processed == 3
    assert skipped == 0


def test_3_photos_1_no_timestamp_video_pattern(extractor, photos_and_videos):
    """Fake videos have no readable mvhd timestamp, so they route to the
    no_timestamp bucket and never join a group. Labels count only the
    photos that clustered."""
    sort_scan(extractor, photos_and_videos, write=False)
    df, _, _ = extractor.results[0]
    assert len(df) == 9
    assert "Img # Series" in df.columns
    # Labels count photos only. Videos contribute timestamps but not output rows.
    assert list(df["Img # Series"]) == [
        "1-3",
        "1-3",
        "1-3",
        "4-6",
        "4-6",
        "4-6",
        "7-9",
        "7-9",
        "7-9",
    ]


def test_pattern_with_modifier(extractor, photos_and_videos):
    sort_scan(extractor, photos_and_videos, modifier=4, write=False)
    df, _, _ = extractor.results[0]
    if "Img # Series" in df.columns:
        assert list(df["Img # Series"]) == [
            "5-7",
            "5-7",
            "5-7",
            "8-10",
            "8-10",
            "8-10",
            "11-13",
            "11-13",
            "11-13",
        ]


def test_video_first_orphan_returns_correctly(extractor, tmp_path, monkeypatch):
    folder = tmp_path / "video_first"
    folder.mkdir()
    (folder / "A_video.mp4").write_bytes(b"fake")
    make_jpeg_with_exif(folder / "B_photo.jpg", "2024:05:15 12:30:45")

    monkeypatch.setattr("metadata.messagebox.askyesno", lambda *args, **kwargs: True)

    sort_scan(extractor, folder, write=False)

    assert "Video First" not in extractor.collected_warnings
    assert extractor.results[0][0].shape[0] == 1


def test_video_first_not_orphan_groups_trailing(extractor, tmp_path, monkeypatch):
    """v4.0.0 dropped the orphan prompt. The leading video contributes its
    timestamp to grouping but produces no output row. B (May 15) and C
    (May 16) fall into separate timestamp groups."""
    folder = tmp_path / "video_first_pattern"
    folder.mkdir()
    (folder / "A_video.mp4").write_bytes(b"fake")
    make_jpeg_with_exif(folder / "B_photo.jpg", "2024:05:15 12:30:45")
    make_jpeg_with_exif(folder / "C_photo.jpg", "2024:05:16 12:30:45")

    monkeypatch.setattr("metadata.messagebox.askyesno", lambda *args, **kwargs: False)

    sort_scan(extractor, folder, write=False)

    assert len(extractor.results) == 1
    df = extractor.results[0][0]
    assert df.shape[0] == 2
    assert list(df["Files"]) == ["B_photo.jpg", "C_photo.jpg"]
    assert list(df["Img # Series"]) == ["1", "2"]


def test_multiple_leading_videos_stripped(extractor, tmp_path):
    folder = tmp_path / "multi_video_first"
    folder.mkdir()
    (folder / "A1.mp4").write_bytes(b"fake")
    (folder / "A2.mp4").write_bytes(b"fake")
    (folder / "A3.mp4").write_bytes(b"fake")
    make_jpeg_with_exif(folder / "B.jpg", "2024:05:15 12:30:45")
    make_jpeg_with_exif(folder / "C.jpg", "2024:05:16 12:30:45")

    sort_scan(extractor, folder, write=False)

    df, _, _ = extractor.results[0]
    assert sorted(list(df["Files"])) == ["B.jpg", "C.jpg"]
