"""Pattern detection edge cases for sort_and_extract_irregular."""

from pathlib import Path
import metadata
from tests.conftest import make_jpeg_with_exif


def _build_folder(folder, layout):
    counter = 1
    for ch in layout:
        if ch == "P":
            make_jpeg_with_exif(folder / f"{counter:04d}_photo.jpg", "2024:05:15 12:30:45")
        elif ch == "V":
            (folder / f"{counter:04d}_video.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
        counter += 1


def _capture(extractor):
    captured = {}

    def fake(output_path, recursive, df, processed, skipped):
        captured["df"] = df

    extractor.create_sheet = fake
    return captured


def test_two_videos_in_a_row(extractor, tmp_path):
    folder = tmp_path / "vv"
    folder.mkdir()
    _build_folder(folder, "PPVVPPVV")
    captured = _capture(extractor)
    extractor.sort_and_extract_irregular(folder, recursive=False, final_output=Path("out.xlsx"), modifier=0)
    assert captured.get("df") is not None


def test_pattern_breaks_midway(extractor, tmp_path):
    folder = tmp_path / "break"
    folder.mkdir()
    _build_folder(folder, "PPPVPPPVPPPPP")
    captured = _capture(extractor)
    extractor.sort_and_extract_irregular(folder, recursive=False, final_output=Path("out.xlsx"), modifier=0)
    assert captured.get("df") is not None


def test_exactly_five_photos_before_video(extractor, tmp_path):
    folder = tmp_path / "five"
    folder.mkdir()
    _build_folder(folder, "PPPPPV")
    captured = _capture(extractor)
    extractor.sort_and_extract_irregular(folder, recursive=False, final_output=Path("out.xlsx"), modifier=0)
    df = captured.get("df")
    assert df is not None
    assert len(df) == 1


def test_exactly_six_photos_before_video(extractor, tmp_path):
    folder = tmp_path / "six"
    folder.mkdir()
    _build_folder(folder, "PPPPPPV")
    captured = _capture(extractor)
    extractor.sort_and_extract_irregular(folder, recursive=False, final_output=Path("out.xlsx"), modifier=0)
    df = captured.get("df")
    assert df is not None
    assert len(df) == 6


def test_trailing_photos_with_no_video(extractor, tmp_path):
    folder = tmp_path / "trailing"
    folder.mkdir()
    _build_folder(folder, "PPPVPPP")
    captured = _capture(extractor)
    extractor.sort_and_extract_irregular(folder, recursive=False, final_output=Path("out.xlsx"), modifier=0)
    assert captured.get("df") is not None


def test_all_videos_no_photos(extractor, tmp_path):
    folder = tmp_path / "all_videos"
    folder.mkdir()
    for i in range(3):
        (folder / f"{i:04d}_video.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    extractor.sort_and_extract_irregular(folder, recursive=False, final_output=Path("out.xlsx"), modifier=0)
    assert "Video First" in extractor.collected_warnings


def test_starting_index_zero(extractor, tmp_path):
    folder = tmp_path / "idx0"
    folder.mkdir()
    _build_folder(folder, "PPPV")
    captured = _capture(extractor)
    extractor.sort_and_extract_irregular(folder, recursive=False, final_output=Path("out.xlsx"), modifier=-1)
    df = captured.get("df")
    assert df is not None
    assert len(df) == 1