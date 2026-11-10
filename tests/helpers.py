"""Shared helpers for the test suite.

Centralizes the keyword defaults for sort_and_extract / find_directories
and the media file listing, so each test file doesn't re-define them.

The refactored scan functions no longer accept `recursive` or
`final_output` — the scan is always recursive when invoked via
find_directories, and file writing is done by create_sheet after the
scan returns. The helpers drive the scan then call create_sheet
explicitly, since the scan functions no longer call it.
"""

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
    # date_range / start_date / end_date removed — sort_and_extract no longer accepts them
)


def media_files(folder, extractor=None):
    """Return the list sort_and_extract expects as its media_files argument.

    Matches walk_and_filter: natural sort by stem, photos before videos at
    the same stem, hidden files filtered (if extractor is provided — it
    owns _check_hidden, which needs the platform-specific logic).
    """
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


def sort_scan(extractor, folder, modifier=0, debug=False, final_output=None, write=True, **overrides):
    if final_output is None:
        final_output = Path("out.xlsx")
    processed, skipped = extractor.sort_and_extract(
        folder,
        modifier,
        debug,
        media_files(folder, extractor),
        **{**_EXTRA_OFF, **overrides},
    )
    if write:
        extractor.create_sheet(final_output, processed, skipped)
    return processed, skipped


def find_scan(extractor, parent, modifier=0, debug=False, final_output=None, write=True, **overrides):
    if final_output is None:
        final_output = Path("out.xlsx")
    processed, skipped = extractor.find_directories(
        parent,
        modifier,
        debug,
        **{**_EXTRA_OFF, **overrides},
    )
    if write:
        extractor.create_sheet(final_output, processed, skipped)
    return processed, skipped
