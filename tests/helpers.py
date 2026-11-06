"""Shared helpers for the test suite.

Centralizes the keyword defaults for sort_and_extract / find_directories
and the media file listing, so each test file doesn't re-define them.

The refactored scan functions no longer call create_sheet themselves —
only _clean_up (in the worker thread) does. Tests that want output on disk
call sort_scan / find_scan, which drive the scan then invoke create_sheet
directly.
"""

import os
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
    date_range=False,
    start_date=None,
    end_date=None,
)


def media_files(folder):
    """Return the list sort_and_extract expects as its media_files argument.

    Matches the ordering walk_to_depth produces: alphabetical by stem
    (natural), photos before videos at the same stem.
    """
    return sorted(
        [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))],
        key=lambda x: (
            [int(t) if t.isdigit() else t.lower() for t in __import__("re").split(r"(\d+)", os.path.splitext(x)[0])],
            (
                0
                if x.lower().endswith((".jpg", ".jpeg", ".png", ".tiff", ".tif", ".dng", ".heic", ".heif", ".raw"))
                else 1
            ),
        ),
    )


def sort_scan(extractor, folder, modifier=0, debug=False, final_output=None, write=True, **overrides):
    """Run sort_and_extract, then create_sheet. Returns (processed, skipped)."""
    if final_output is None:
        final_output = Path("out.xlsx")
    processed, skipped = extractor.sort_and_extract(
        folder,
        False,
        final_output,
        modifier,
        debug,
        media_files(folder),
        **{**_EXTRA_OFF, **overrides},
    )
    if write:
        extractor.create_sheet(final_output, processed, skipped)
    return processed, skipped


def find_scan(extractor, parent, modifier=0, debug=False, final_output=None, write=True, **overrides):
    """Run find_directories, then create_sheet. Returns (processed, skipped)."""
    if final_output is None:
        final_output = Path("out.xlsx")
    processed, skipped = extractor.find_directories(
        parent,
        True,
        final_output,
        modifier,
        debug,
        **{**_EXTRA_OFF, **overrides},
    )
    if write:
        extractor.create_sheet(final_output, processed, skipped)
    return processed, skipped
