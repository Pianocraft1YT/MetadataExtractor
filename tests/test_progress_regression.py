"""Regression tests for the >100% progress bug and trailing-photo rescan."""

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


def _build(folder, layout):
    for idx, ch in enumerate(layout, start=1):
        name = f"{idx:04d}_{'photo' if ch == 'P' else 'video'}"
        ext = ".jpg" if ch == "P" else ".mp4"
        if ch == "P":
            make_jpeg_with_exif(folder / (name + ext), "2024:05:15 12:30:45")
        else:
            (folder / (name + ext)).write_bytes(b"\x00\x00\x00\x18ftypmp42")


def test_trailing_photos_do_not_exceed_total(extractor, tmp_path):
    """3 photos, 1 video, 6 photos -- end block must scan the tail once."""
    folder = tmp_path / "trailing"
    folder.mkdir()
    _build(folder, "PPPVPPPPPP")

    extractor.debug_var.set(False)
    extractor.sort_and_extract_irregular(
        folder,
        recursive=False,
        final_output=Path("out.xlsx"),
        modifier=0,
        debug=False,
        **_EXTRA_OFF,
    )
    assert len(extractor.results) == 1
    df = extractor.results[0][0]
    assert len(df) <= 9


def test_no_duplicate_series_after_tail(extractor, tmp_path):
    """Series numbers must not repeat after the tail block runs."""
    folder = tmp_path / "trailing2"
    folder.mkdir()
    _build(folder, "PPPVPPPPPP")

    extractor.debug_var.set(False)
    extractor.sort_and_extract_irregular(
        folder,
        recursive=False,
        final_output=Path("out.xlsx"),
        modifier=0,
        debug=False,
        **_EXTRA_OFF,
    )
    df = extractor.results[0][0]
    if "Img # Series" in df.columns:
        assert len(df["Img # Series"]) == len(set(df["Img # Series"]))
