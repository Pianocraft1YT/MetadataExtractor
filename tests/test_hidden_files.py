"""End-to-end behaviour of hidden file handling."""

import os

from tests.conftest import make_jpeg_with_exif
from tests.helpers import sort_scan


def _filtered_listing(extractor, folder):
    """What walk_to_depth would hand to sort_and_extract."""
    return sorted(
        [
            f
            for f in os.listdir(folder)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".mp4", ".mov")) and not extractor._check_hidden(f, folder)
        ],
        key=lambda x: os.path.splitext(x)[0].lower(),
    )


def test_hidden_photo_not_scanned(extractor, tmp_path):
    make_jpeg_with_exif(tmp_path / "visible.jpg", "2024:05:15 12:30:45")
    make_jpeg_with_exif(tmp_path / ".hidden.jpg", "2024:05:16 12:30:45")

    media_files = _filtered_listing(extractor, tmp_path)
    assert media_files == ["visible.jpg"]

    sort_scan(extractor, tmp_path, write=False)
    df, _, _ = extractor.results[0]
    assert list(df["Files"]) == ["visible.jpg"]
