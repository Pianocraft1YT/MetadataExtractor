"""Shared helpers for the test suite."""

import os
import re
from pathlib import Path

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
    output_gps=False,
)


def media_files(folder, extractor=None):
    files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    if extractor is not None:
        files = [f for f in files if not extractor._check_hidden(f, folder)]
    return sorted(
        files,
        key=lambda x: (
            [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", os.path.splitext(x)[0])],
            (
                0
                if x.lower().endswith((".jpg", ".jpeg", ".png", ".tiff", ".tif", ".dng", ".heic", ".heif", ".raw"))
                else 1
            ),
        ),
    )


def sort_scan(extractor, folder, modifier=0, debug=False, final_output=None, write=True, cutoff=2.0, **overrides):
    if final_output is None:
        final_output = Path("out.xlsx")
    processed, skipped = extractor.sort_and_extract(
        folder,
        modifier,
        media_files(folder, extractor),
        cutoff,
        **{**_EXTRA_OFF, **overrides},
    )
    if write:
        extractor.create_sheet(final_output, processed, skipped)
    return processed, skipped


def find_scan(extractor, parent, modifier=0, debug=False, final_output=None, write=True, cutoff=2.0, **overrides):
    # `debug` is kept for backward compatibility with existing callers, but
    # find_directories() no longer takes it.
    if final_output is None:
        final_output = Path("out.xlsx")
    processed, skipped = extractor.find_directories(
        parent,
        modifier,
        cutoff,
        **{**_EXTRA_OFF, **overrides},
    )
    if write:
        extractor.create_sheet(final_output, processed, skipped)
    return processed, skipped
