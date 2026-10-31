"""Tests for the extra metadata feature."""

import pandas as pd

# Full off dict for scan_image / sort_and_extract / find_directories calls.
# Includes output_utc since those methods take it.
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
    date_range=False,
    start_date=None,
    end_date=None,
)


# Narrower off dict for create_dataframe calls. That function doesn't
# take output_utc, and the four tests below pass output_dimensions /
# output_make / etc. explicitly, so those keys must not be in the dict.
_DF_OFF = dict(
    output_aperture=False,
    output_exposure_time=False,
    output_focal_length=False,
    output_iso=False,
    date_range=False,
    start_date=None,
    end_date=None,
)


def test_empty_scan_data_has_all_expected_keys(extractor):
    data = extractor._empty_scan_data()
    expected = {
        "Dates",
        "Times",
        "Images",
        "Offsets",
        "Dimensions",
        "Makes",
        "Models",
        "Softwares",
        "Lens_Models",
        "Apertures",
        "Exposure_Times",
        "Focal_Lengths",
        "ISOs",
    }
    assert set(data.keys()) == expected
    for value in data.values():
        assert isinstance(value, list)
        assert value == []


def _scan_extras(extractor, tmp_path, media_files, **extras):
    data = extractor._empty_scan_data()
    ok = extractor.scan_image(
        tmp_path,
        0,
        data,
        media_files,
        output_utc=False,
        output_dimensions=extras.get("dimensions", False),
        output_make=extras.get("make", False),
        output_model=extras.get("model", False),
        output_software=extras.get("software", False),
        output_lens_model=extras.get("lens", False),
        output_aperture=extras.get("aperture", False),
        output_exposure_time=extras.get("exposure_time", False),
        output_focal_length=extras.get("focal_length", False),
        output_iso=extras.get("iso", False),
        date_range=False,
        start_date=None,
        end_date=None,
    )
    return ok, data


def test_scan_image_dimensions_when_enabled(extractor, make_jpeg, tmp_path):
    make_jpeg("photo.jpg", datetime_original="2024:05:15 12:30:45")
    ok, data = _scan_extras(extractor, tmp_path, ["photo.jpg"], dimensions=True)
    assert ok is True
    assert data["Dimensions"] == ["10x10"]


def test_scan_image_dimensions_when_disabled(extractor, make_jpeg, tmp_path):
    make_jpeg("photo.jpg", datetime_original="2024:05:15 12:30:45")
    ok, data = _scan_extras(extractor, tmp_path, ["photo.jpg"], dimensions=False)
    assert ok is True
    assert data["Dimensions"] == [None]


def test_scan_image_make_and_model(extractor, make_jpeg, tmp_path):
    make_jpeg("photo.jpg", datetime_original="2024:05:15 12:30:45")
    from PIL import Image

    path = tmp_path / "photo.jpg"
    with Image.open(path) as img:
        exif = img.getexif()
    exif[271] = "Canon"
    exif[272] = "EOS 70D"
    with Image.open(path) as img:
        img.save(path, format="JPEG", exif=exif)

    ok, data = _scan_extras(
        extractor,
        tmp_path,
        ["photo.jpg"],
        make=True,
        model=True,
    )
    assert ok is True
    assert data["Makes"] == ["Canon"]
    assert data["Models"] == ["EOS 70D"]


def test_scan_image_all_extras_enabled_populates_each(extractor, make_jpeg, tmp_path):
    make_jpeg("photo.jpg", datetime_original="2024:05:15 12:30:45")
    ok, data = _scan_extras(
        extractor,
        tmp_path,
        ["photo.jpg"],
        dimensions=True,
        make=True,
        model=True,
        software=True,
        lens=True,
    )
    assert ok is True
    assert data["Dimensions"] == ["10x10"]
    assert data["Makes"] == [None]
    assert data["Models"] == [None]
    assert data["Softwares"] == [None]
    assert data["Lens_Models"] == [None]


def _populated_data(extractor):
    data = extractor._empty_scan_data()
    data["Images"] = ["a.jpg", "b.jpg"]
    data["Dates"] = ["05/15/2024", "05/16/2024"]
    data["Times"] = ["12:30:45", "13:00:00"]
    data["Dimensions"] = ["1920x1080", "1080x1920"]
    data["Makes"] = ["Canon", "Nikon"]
    data["Models"] = ["EOS 70D", "D750"]
    data["Softwares"] = ["Lightroom", None]
    data["Lens_Models"] = ["EF 50mm", None]
    return data


def test_create_dataframe_all_extras_enabled(extractor, tmp_path):
    data = _populated_data(extractor)
    extractor.create_dataframe(
        ["1", "2"],
        data,
        tmp_path,
        output_series=True,
        output_dimensions=True,
        output_make=True,
        output_model=True,
        output_software=True,
        output_lens_model=True,
        **_DF_OFF,
    )
    df = extractor.results[0][0]
    assert list(df["Files"]) == ["a.jpg", "b.jpg"]
    assert list(df["Camera Make"]) == ["Canon", "Nikon"]
    assert list(df["Camera Model"]) == ["EOS 70D", "D750"]
    assert list(df["Dimensions"]) == ["1920x1080", "1080x1920"]
    assert df["Software"].iloc[0] == "Lightroom"
    assert pd.isna(df["Software"].iloc[1])
    assert df["Lens Model"].iloc[0] == "EF 50mm"
    assert pd.isna(df["Lens Model"].iloc[1])
    assert list(df["Img # Series"]) == ["1", "2"]


def test_create_dataframe_all_extras_disabled(extractor, tmp_path):
    data = _populated_data(extractor)
    extractor.create_dataframe(
        ["1", "2"],
        data,
        tmp_path,
        output_series=True,
        output_dimensions=False,
        output_make=False,
        output_model=False,
        output_software=False,
        output_lens_model=False,
        **_DF_OFF,
    )
    df = extractor.results[0][0]
    assert list(df.columns) == ["Files", "Dates", "Time", "Img # Series"]


def test_create_dataframe_selective_columns(extractor, tmp_path):
    data = _populated_data(extractor)
    extractor.create_dataframe(
        None,
        data,
        tmp_path,
        output_series=False,
        output_dimensions=True,
        output_make=False,
        output_model=False,
        output_software=True,
        output_lens_model=False,
        **_DF_OFF,
    )
    df = extractor.results[0][0]
    assert "Dimensions" in df.columns
    assert "Camera Make" not in df.columns
    assert "Software" in df.columns
    assert "Lens Model" not in df.columns
    assert "Img # Series" not in df.columns


def test_create_dataframe_empty_data_creates_empty_sheet(extractor, tmp_path):
    data = extractor._empty_scan_data()
    extractor.create_dataframe(
        None,
        data,
        tmp_path,
        output_series=True,
        output_dimensions=True,
        output_make=True,
        output_model=True,
        output_software=True,
        output_lens_model=True,
        **_DF_OFF,
    )
    df, _, directory = extractor.results[0]
    assert df.empty
    assert list(df.columns) == ["Files", "Dates", "Time"]
    assert directory is None


def test_extra_exif_checkbox_shows_frame(extractor):
    extractor.extra_exif_frame.pack.reset_mock()
    extractor.extra_exif_frame.pack_forget.reset_mock()
    extractor.extra_exif_var.set(True)
    extractor.extra_exif()
    extractor.extra_exif_frame.pack.assert_called_once()
    extractor.extra_exif_frame.pack_forget.assert_not_called()


def test_extra_exif_checkbox_hides_frame(extractor):
    extractor.extra_exif_frame.pack.reset_mock()
    extractor.extra_exif_frame.pack_forget.reset_mock()
    extractor.extra_exif_var.set(False)
    extractor.extra_exif()
    extractor.extra_exif_frame.pack.assert_not_called()
    extractor.extra_exif_frame.pack_forget.assert_called_once()
