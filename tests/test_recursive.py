"""Tests for recursive-mode scanning via find_directories."""

from pathlib import Path

from tests.conftest import make_jpeg_with_exif

_EXTRA_OFF = dict(
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
)


def _make_photos(folder, names):
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        make_jpeg_with_exif(folder / name, "2024:05:15 12:30:45")


def _capture(extractor):
    calls = []

    def fake(output_path, recursive, total_processed, total_skipped):
        calls.append(
            {
                "output_path": output_path,
                "recursive": recursive,
                "results": list(extractor.results),
                "total_processed": total_processed,
                "total_skipped": total_skipped,
            }
        )

    extractor.create_sheet = fake
    return calls


def _run(extractor, parent, out):
    extractor.find_directories(
        parent,
        out,
        modifier=0,
        debug=False,
        **_EXTRA_OFF,
    )


def test_two_clean_subfolders(extractor, tmp_path):
    parent = tmp_path / "parent"
    _make_photos(parent / "Trip_A", ["IMG_001.jpg", "IMG_002.jpg"])
    _make_photos(parent / "Trip_B", ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"])

    extractor.maxdepth = 1
    calls = _capture(extractor)
    _run(extractor, parent, tmp_path / "out.xlsx")

    assert len(calls) == 1
    assert calls[0]["recursive"] is True
    assert len(calls[0]["results"]) == 2
    assert calls[0]["total_processed"] == 5
    assert calls[0]["total_skipped"] == 0


def test_subfolder_with_skips(extractor, tmp_path):
    parent = tmp_path / "parent"
    _make_photos(parent / "Clean", ["IMG_001.jpg", "IMG_002.jpg"])
    _make_photos(parent / "Messy", ["IMG_001.jpg"])
    (parent / "Messy" / "IMG_002.jpg").write_text("not an image")

    extractor.maxdepth = 1
    calls = _capture(extractor)
    _run(extractor, parent, tmp_path / "out.xlsx")

    assert calls[0]["total_processed"] == 3
    assert calls[0]["total_skipped"] == 1


def test_subfolder_with_no_photos_ignored(extractor, tmp_path):
    parent = tmp_path / "parent"
    _make_photos(parent / "WithPhotos", ["IMG_001.jpg"])
    empty = parent / "NoPhotos"
    empty.mkdir()
    (empty / "readme.txt").write_text("nothing")

    extractor.maxdepth = 1
    calls = _capture(extractor)
    _run(extractor, parent, tmp_path / "out.xlsx")

    assert len(calls[0]["results"]) == 1


def test_subfolder_with_only_videos_ignored(extractor, tmp_path):
    parent = tmp_path / "parent"
    _make_photos(parent / "WithPhotos", ["IMG_001.jpg"])
    only_video = parent / "OnlyVideo"
    only_video.mkdir()
    (only_video / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")

    extractor.maxdepth = 1
    calls = _capture(extractor)
    _run(extractor, parent, tmp_path / "out.xlsx")

    assert len(calls[0]["results"]) == 1


def test_no_valid_subfolders(extractor, tmp_path):
    parent = tmp_path / "empty_parent"
    parent.mkdir()
    (parent / "notes.txt").write_text("nothing")

    extractor.maxdepth = 1
    calls = _capture(extractor)
    _run(extractor, parent, tmp_path / "out.xlsx")

    assert calls[0]["results"] == []
    assert calls[0]["total_processed"] == 0
    assert calls[0]["total_skipped"] == 0


def test_deep_tree_produces_relative_path_sheet_names(extractor, tmp_path):
    parent = tmp_path / "parent"
    _make_photos(parent / "2023" / "Beach", ["IMG_001.jpg"])

    extractor.maxdepth = 5
    calls = _capture(extractor)
    _run(extractor, parent, tmp_path / "out.xlsx")

    results = calls[0]["results"]
    assert len(results) == 1
    _, sheet_name, directory = results[0]
    assert sheet_name == "2023_Beach"
    assert directory == parent / "2023" / "Beach"


def test_sibling_branches_with_same_leaf_name(extractor, tmp_path):
    parent = tmp_path / "parent"
    _make_photos(parent / "trip_a" / "photos", ["IMG.jpg"])
    _make_photos(parent / "trip_b" / "photos", ["IMG.jpg"])

    extractor.maxdepth = 5
    calls = _capture(extractor)
    _run(extractor, parent, tmp_path / "out.xlsx")

    sheets = [name for _, name, _ in calls[0]["results"]]
    assert len(sheets) == 2
    assert "trip_a_photos" in sheets
    assert "trip_b_photos" in sheets
    assert len(set(sheets)) == 2


def test_intermediate_folder_without_direct_photos_skipped(extractor, tmp_path):
    parent = tmp_path / "parent"
    deep = parent / "mid" / "photos"
    deep.mkdir(parents=True)
    make_jpeg_with_exif(deep / "IMG.jpg", "2024:05:15 12:30:45")

    extractor.maxdepth = 5
    calls = _capture(extractor)
    _run(extractor, parent, tmp_path / "out.xlsx")

    sheets = [name for _, name, _ in calls[0]["results"]]
    assert sheets == ["mid_photos"]


def test_maxdepth_cuts_off_deeper_folders(extractor, tmp_path):
    parent = tmp_path / "parent"
    _make_photos(parent / "shallow", ["IMG.jpg"])
    _make_photos(parent / "a" / "b" / "deep", ["IMG.jpg"])

    extractor.maxdepth = 1
    calls = _capture(extractor)
    _run(extractor, parent, tmp_path / "out.xlsx")

    sheets = [name for _, name, _ in calls[0]["results"]]
    assert sheets == ["shallow"]


def test_root_folder_with_direct_photos_named_sheet(extractor, tmp_path):
    parent = tmp_path / "parent"
    parent.mkdir()
    make_jpeg_with_exif(parent / "IMG.jpg", "2024:05:15 12:30:45")
    _make_photos(parent / "sub", ["IMG.jpg"])

    extractor.maxdepth = 2
    calls = _capture(extractor)
    _run(extractor, parent, tmp_path / "out.xlsx")

    sheets = [name for _, name, _ in calls[0]["results"]]
    assert "Sheet" in sheets
    assert "sub" in sheets


def test_first_folder_corrupt_does_not_prevent_later_folders(extractor, tmp_path):
    """Regression: scan_image crash on a folder's first file used to swallow
    that folder's counts. Ensure A_bad records its skip and B_good processes."""
    parent = tmp_path / "parent"
    bad = parent / "A_bad"
    good = parent / "B_good"
    bad.mkdir(parents=True)
    good.mkdir()
    (bad / "broken.jpg").write_bytes(b"not an image")
    make_jpeg_with_exif(good / "IMG_001.jpg", "2024:05:15 12:30:45")

    extractor.maxdepth = 1
    p, s = extractor.find_directories(
        parent,
        tmp_path / "out.xlsx",
        modifier=0,
        debug=False,
        **_EXTRA_OFF,
    )
    # A_bad: 1 skipped; B_good: 1 processed
    assert p == 1
    assert s == 1
