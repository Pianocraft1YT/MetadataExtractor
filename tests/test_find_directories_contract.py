"""Contract tests for find_directories' return value.

REGRESSION: find_directories accumulated into self.total_processed /
self.total_skipped but never returned them, breaking every caller that
unpacked the result. The contract mirrors sort_and_extract: return
(processed, skipped). These tests require the Option A source fix.
"""

from tests.conftest import make_jpeg_with_exif
from tests.helpers import find_scan


def _call(extractor, path, **kw):
    return extractor.find_directories(
        path,
        0,
        2.0,
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
        **{"include_hiddens": False, "include_undateable": True, **kw},
    )


def test_returns_processed_and_skipped_tuple(extractor, tmp_path):
    sub = tmp_path / "photos"
    sub.mkdir()
    make_jpeg_with_exif(sub / "a.jpg", "2024:05:15 12:30:45")
    make_jpeg_with_exif(sub / "b.jpg", "2024:05:15 12:30:45")

    extractor.maxdepth = 1
    result = _call(extractor, tmp_path)

    assert isinstance(result, tuple) and len(result) == 2
    processed, skipped = result
    assert processed == 2
    assert skipped == 0


def test_returns_zero_when_no_dirs(extractor, tmp_path):
    extractor.maxdepth = 1
    assert _call(extractor, tmp_path) == (0, 0)


def test_returns_zero_on_cancel(extractor, tmp_path):
    sub = tmp_path / "photos"
    sub.mkdir()
    make_jpeg_with_exif(sub / "a.jpg", "2024:05:15 12:30:45")

    extractor.maxdepth = 1
    extractor.cancel_event.set()
    assert _call(extractor, tmp_path) == (0, 0)


def test_video_only_folder_emits_warning(extractor, tmp_path):
    only_video = tmp_path / "OnlyVideo"
    only_video.mkdir()
    (only_video / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")

    extractor.maxdepth = 1
    find_scan(extractor, tmp_path, write=False)

    assert "Only Video(s)" in extractor.collected_warnings
    assert len(extractor.collected_warnings["Only Video(s)"]) == 1


def test_processed_sums_across_subfolders(extractor, tmp_path):
    for sub in ("A", "B", "C"):
        d = tmp_path / sub
        d.mkdir()
        make_jpeg_with_exif(d / "x.jpg", "2024:05:15 12:30:45")

    extractor.maxdepth = 1
    processed, skipped = find_scan(extractor, tmp_path, write=False)
    assert processed == 3
    assert skipped == 0
