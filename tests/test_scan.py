"""Tests for MetadataExtractor.scan_image."""

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
)


def _scan(extractor, tmp_path, media_files, output_utc=False):
    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        0,
        data,
        media_files,
        output_utc=output_utc,
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
    return ok, data


def test_valid_image_with_exif_returns_true(extractor_tz_off, make_jpeg, tmp_path):
    make_jpeg("ok.jpg", datetime_original="2024:05:15 12:30:45")
    ok, data = _scan(extractor_tz_off, tmp_path, ["ok.jpg"])
    assert ok is True
    assert data["Dates"] == ["2024:05:15 12:30:45"]
    assert data["Images"] == ["ok.jpg"]
    assert data["Offsets"] == [None]


def test_image_missing_exif_returns_false(extractor_tz_off, make_jpeg, tmp_path):
    make_jpeg("no_exif.jpg")
    ok, data = _scan(extractor_tz_off, tmp_path, ["no_exif.jpg"])
    assert ok is False
    assert "No Metadata" in extractor_tz_off.collected_warnings
    assert data["Dates"] == [] and data["Images"] == [] and data["Offsets"] == []


def test_corrupt_file_returns_false(extractor_tz_off, tmp_path):
    (tmp_path / "bad.jpg").write_bytes(b"this is not a jpeg")
    ok, data = _scan(extractor_tz_off, tmp_path, ["bad.jpg"])
    assert ok is False
    assert "Scan Error" in extractor_tz_off.collected_warnings


def test_prefers_datetime_original_over_others(extractor_tz_off, make_jpeg, tmp_path):
    make_jpeg(
        "all_exif.jpg",
        datetime_original="2024:01:01 01:01:01",
        datetime_digitized="2024:02:02 02:02:02",
        datetime_general="2024:03:03 03:03:03",
    )
    ok, data = _scan(extractor_tz_off, tmp_path, ["all_exif.jpg"])
    assert ok is True
    assert data["Dates"] == ["2024:01:01 01:01:01"]


def test_falls_back_to_datetime_when_original_missing(extractor_tz_off, make_jpeg, tmp_path):
    make_jpeg("only_datetime.jpg", datetime_general="2024:03:03 03:03:03")
    ok, data = _scan(extractor_tz_off, tmp_path, ["only_datetime.jpg"])
    assert ok is True
    assert data["Dates"] == ["2024:03:03 03:03:03"]


def test_falls_back_to_digitized_when_original_missing(extractor_tz_off, make_jpeg, tmp_path):
    make_jpeg("only_digitized.jpg", datetime_digitized="2024:02:02 02:02:02")
    ok, data = _scan(extractor_tz_off, tmp_path, ["only_digitized.jpg"])
    assert ok is True
    assert data["Dates"] == ["2024:02:02 02:02:02"]


def test_scan_image_timezone_off_does_not_crash(extractor_tz_off, make_jpeg, tmp_path):
    make_jpeg("t.jpg", datetime_original="2024:05:15 12:30:45")
    ok, data = _scan(extractor_tz_off, tmp_path, ["t.jpg"], output_utc=False)
    assert ok is True
    assert data["Offsets"] == [None]


def test_scan_image_captures_offset_when_timezone_on(extractor_tz_on, make_jpeg, tmp_path):
    make_jpeg("t.jpg", datetime_original="2024:05:15 12:30:45", offset_original="+05:30")
    ok, data = _scan(extractor_tz_on, tmp_path, ["t.jpg"], output_utc=True)
    assert ok is True
    assert data["Offsets"] == ["+05:30"]


def test_scan_image_missing_offset_when_timezone_on(extractor_tz_on, make_jpeg, tmp_path):
    make_jpeg("t.jpg", datetime_original="2024:05:15 12:30:45")
    ok, data = _scan(extractor_tz_on, tmp_path, ["t.jpg"], output_utc=True)
    assert ok is True
    assert data["Offsets"] == [None]


def test_scan_image_first_corrupt_file_does_not_abort_folder(extractor, make_jpeg, tmp_path):
    (tmp_path / "a_bad.jpg").write_bytes(b"not a jpeg")
    make_jpeg("b_good.jpg", datetime_original="2024:05:15 12:30:45")

    processed, skipped = extractor.sort_and_extract(
        tmp_path,
        recursive=False,
        final_output=Path("out.xlsx"),
        modifier=0,
        output_series=True,
        **_EXTRA_OFF,
    )
    assert processed == 1
    assert skipped == 1
    assert len(extractor.results) == 1
    assert len(extractor.results[0][0]) == 1
    assert extractor.results[0][0].iloc[0]["Files"] == "b_good.jpg"


def test_scan_image_warning_uses_actual_filename(extractor, tmp_path):
    (tmp_path / "specific_name.jpg").write_bytes(b"not a jpeg")
    data = extractor._empty_scan_data()
    extractor.scan_image(
        tmp_path,
        0,
        data,
        ["specific_name.jpg"],
        **_EXTRA_OFF,
    )
    assert any("specific_name.jpg" in warn for warn in extractor.collected_warnings["Scan Error"])
