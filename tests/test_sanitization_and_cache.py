"""Tests for Excel formula-injection sanitization, hyperlink preservation,
and #11 single-open photo/video scan caching.
"""

from datetime import date, datetime, timezone
from unittest.mock import patch

import openpyxl
import pandas as pd
import PIL.Image
import pytest

import video_metadata
from tests.conftest import make_jpeg_with_exif
from tests.helpers import find_scan

# ---------------------------------------------------------------------------
# Excel formula neutralization + hyperlink preservation
# ---------------------------------------------------------------------------


def test_sanitize_for_excel_escapes_formulas_but_keeps_negative_gps(extractor):
    df = pd.DataFrame(
        {
            "Files": ["=1+1.jpg", "+cmd.jpg", "-cmd.jpg", "@sum.jpg"],
            "GPS Latitude": ["-33.868800", "37.775000", None, "-0.000001"],
            "GPS Longitude": ["-122.419400", "0.000000", "10.000000", "-73.985700"],
        }
    )
    cleaned = extractor._sanitize_for_excel(df)
    assert list(cleaned["Files"]) == ["'=1+1.jpg", "'+cmd.jpg", "'-cmd.jpg", "'@sum.jpg"]
    assert cleaned["GPS Latitude"].iloc[0] == "-33.868800"
    assert cleaned["GPS Longitude"].iloc[0] == "-122.419400"


@pytest.mark.real_create_sheet
def test_formula_filename_hyperlink_points_to_real_disk_name(extractor, tmp_path):
    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    df = pd.DataFrame(
        {
            "Files": ["=test.jpg"],
            "Dates": ["05/15/2024"],
            "Time": ["12:00:00"],
            "Img # Series": ["1"],
        }
    )
    extractor.results.append((df, "Sheet", photo_dir))
    extractor.hyperlink_var.set(True)
    extractor.keepopen_var.set(True)
    output = tmp_path / "out.xlsx"

    extractor.create_sheet(output, 1, 0)

    wb = openpyxl.load_workbook(output)
    ws = wb["Sheet"]
    assert ws["A2"].value == "'=test.jpg"
    assert ws["A2"].hyperlink.target == (photo_dir / "=test.jpg").as_uri()


# ---------------------------------------------------------------------------
# #11 Single-open cache verification
# ---------------------------------------------------------------------------


def _write_minimal_mp4(path, utc: datetime) -> None:
    mp4_time = int(utc.timestamp()) + 2_082_844_800
    mvhd_payload = b"\x00\x00\x00\x00" + mp4_time.to_bytes(4, "big")
    mvhd = (8 + len(mvhd_payload)).to_bytes(4, "big") + b"mvhd" + mvhd_payload
    moov = (8 + len(mvhd)).to_bytes(4, "big") + b"moov" + mvhd
    ftyp_payload = b"isom\x00\x00\x02\x00isomiso2"
    ftyp = (8 + len(ftyp_payload)).to_bytes(4, "big") + b"ftyp" + ftyp_payload
    path.write_bytes(ftyp + moov)


def test_date_range_scan_opens_each_photo_and_video_only_once(extractor, tmp_path):
    folder = tmp_path / "shoot"
    folder.mkdir()
    make_jpeg_with_exif(folder / "keep1.jpg", "2024:05:10 10:00:00")
    make_jpeg_with_exif(folder / "keep2.jpg", "2024:05:10 10:00:01")
    make_jpeg_with_exif(folder / "drop.jpg", "2024:06:15 10:00:00")
    (folder / "corrupt.jpg").write_bytes(b"not an image")
    _write_minimal_mp4(folder / "clip.mp4", datetime(2024, 5, 10, 10, 0, 2, tzinfo=timezone.utc))

    real_open = PIL.Image.open
    real_video = video_metadata.extract_video_metadata
    photo_opens = {}
    video_opens = {}

    def count_photo(fp, *a, **k):
        name = fp.name if hasattr(fp, "name") else str(fp)
        photo_opens[name] = photo_opens.get(name, 0) + 1
        return real_open(fp, *a, **k)

    def count_video(fp, *a, **k):
        name = fp.name if hasattr(fp, "name") else str(fp)
        video_opens[name] = video_opens.get(name, 0) + 1
        return real_video(fp, *a, **k)

    extractor.maxdepth = 0
    with (
        patch("metadata.Image.open", side_effect=count_photo),
        patch("metadata.extract_video_metadata", side_effect=count_video),
    ):
        processed, skipped = find_scan(
            extractor,
            folder,
            date_range=True,
            start_date=date(2024, 5, 1),
            end_date=date(2024, 5, 31),
            include_undateable=True,
            write=False,
        )

    assert (processed, skipped) == (2, 1)
    assert photo_opens == {"keep1.jpg": 1, "keep2.jpg": 1, "drop.jpg": 1, "corrupt.jpg": 1}
    assert video_opens == {"clip.mp4": 1}
    assert len(extractor.collected_warnings["Scan Error"]) == 1
    assert extractor._photo_cache is None
    assert extractor._video_cache is None
