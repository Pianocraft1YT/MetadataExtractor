"""Shared helpers for the test suite.

Centralizes the keyword defaults for sort_and_extract / find_directories
and the media file listing, so each test file doesn't re-define them.
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

    Matches the ordering walk_to_depth produces: alphabetical by stem,
    case-insensitive, extension ignored.
    """
    return sorted(
        [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))],
        key=lambda x: os.path.splitext(x)[0].lower(),
    )


def sort_scan(extractor, folder, modifier=0, debug=False, final_output=None, **overrides):
    """Run sort_and_extract with defaults. Override kwargs by passing them."""
    if final_output is None:
        final_output = Path("out.xlsx")
    return extractor.sort_and_extract(
        folder,
        False,
        final_output,
        modifier,
        debug,
        media_files(folder),
        **{**_EXTRA_OFF, **overrides},
    )


def find_scan(extractor, parent, modifier=0, debug=False, final_output=None, **overrides):
    """Run find_directories with defaults."""
    if final_output is None:
        final_output = Path("out.xlsx")
    return extractor.find_directories(
        parent,
        True,
        final_output,
        modifier,
        debug,
        **{**_EXTRA_OFF, **overrides},
    )
