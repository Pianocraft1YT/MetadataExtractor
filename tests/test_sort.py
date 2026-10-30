"""Tests for sort_and_extract and sort_and_extract_irregular."""

from pathlib import Path

from tests.conftest import make_jpeg_with_exif, make_jpeg_no_exif


def _capture_create_sheet(extractor):
    captured = {}

    def fake(output_path, recursive, processed, skipped):
        captured["output_path"] = output_path
        captured["processed"] = processed
        captured["skipped"] = skipped

    extractor.create_sheet = fake
    return captured


def _sort(extractor, folder, modifier=0, output_series=True):
    return extractor.sort_and_extract(
        folder,
        recursive=False,
        final_output=Path("out.xlsx"),
        modifier=modifier,
        output_series=output_series,
        output_utc=False,
        output_dimensions=False,
        output_make=False,
        output_model=False,
        output_software=False,
        output_lens_model=False,
    )


def _sort_irregular(extractor, folder, modifier=0):
    return extractor.sort_and_extract_irregular(
        folder,
        recursive=False,
        final_output=Path("out.xlsx"),
        modifier=modifier,
        debug=False,
        output_utc=False,
        output_dimensions=False,
        output_make=False,
        output_model=False,
        output_software=False,
        output_lens_model=False,
    )


def test_sort_and_extract_all_photos(extractor, photos_only):
    _capture_create_sheet(extractor)
    _sort(extractor, photos_only)
    assert len(extractor.results) == 1
    df, _, _ = extractor.results[0]
    assert len(df) == 3
    assert list(df["Files"]) == ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]


def test_sort_and_extract_missing_exif_skips_file(extractor, folder_missing_exif):
    captured = _capture_create_sheet(extractor)
    _sort(extractor, folder_missing_exif)
    df, _, _ = extractor.results[0]
    assert len(df) == 2
    assert "IMG_002.jpg" not in list(df["Files"])
    assert captured["skipped"] == 1
    assert captured["processed"] == 2


def test_sort_and_extract_corrupt_file_does_not_hang(extractor, folder_with_corrupt_photo):
    captured = _capture_create_sheet(extractor)
    _sort(extractor, folder_with_corrupt_photo)
    df, _, _ = extractor.results[0]
    assert len(df) == 6
    assert captured["skipped"] == 1
    assert captured["processed"] == 6


def test_sort_and_extract_no_exif_gap_in_series(extractor, tmp_path):
    folder = tmp_path / "gap"
    folder.mkdir()
    for name in ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]:
        make_jpeg_with_exif(folder / name, "2024:05:15 12:30:45")
    make_jpeg_no_exif(folder / "IMG_002.jpg")

    captured = _capture_create_sheet(extractor)
    _sort(extractor, folder)
    assert captured["processed"] == 2
    assert captured["skipped"] == 1


def test_irregular_3_photos_1_video_pattern(extractor, photos_and_videos):
    _capture_create_sheet(extractor)
    _sort_irregular(extractor, photos_and_videos)
    df, _, _ = extractor.results[0]
    assert len(df) == 3
    if "Img # Series" in df.columns:
        assert list(df["Img # Series"]) == ["1-4", "5-8", "9-12"]


def test_irregular_all_photos_falls_through_to_sort_and_extract(extractor, photos_only):
    _capture_create_sheet(extractor)
    _sort_irregular(extractor, photos_only)
    df, _, _ = extractor.results[0]
    assert len(df) == 3


def test_irregular_video_first_shows_warning_and_returns(extractor, tmp_path, monkeypatch):
    folder = tmp_path / "video_first"
    folder.mkdir()
    (folder / "A_video.mp4").write_bytes(b"fake")
    make_jpeg_with_exif(folder / "B_photo.jpg", "2024:05:15 12:30:45")

    monkeypatch.setattr("metadata.messagebox.askyesno", lambda *args, **kwargs: True)

    _sort_irregular(extractor, folder)

    assert "Video First" not in extractor.collected_warnings
    assert extractor.results[0][0].shape[0] == 1


def test_irregular_with_modifier(extractor, photos_and_videos):
    _capture_create_sheet(extractor)
    _sort_irregular(extractor, photos_and_videos, modifier=4)
    df, _, _ = extractor.results[0]
    if "Img # Series" in df.columns:
        assert list(df["Img # Series"]) == ["5-8", "9-12", "13-16"]
