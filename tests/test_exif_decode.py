"""Tests for MetadataExtractor._decode_exif_string.

EXIF string tags (Make, Model, Software, LensModel) are ASCII by spec, but
some cameras and some Pillow versions hand them back as bytes. The decoder
converts to str; non-bytes values pass through untouched.
"""

from PIL import Image
import pytest

# ---------------------------------------------------------------------------
# Pass-through — the common path (Barn Owl and most modern cameras)
# ---------------------------------------------------------------------------


def test_str_passes_through(extractor):
    assert extractor._decode_exif_string("Canon") == "Canon"


def test_empty_str_passes_through(extractor):
    assert extractor._decode_exif_string("") == ""


def test_none_passes_through(extractor):
    assert extractor._decode_exif_string(None) is None


def test_int_passes_through(extractor):
    assert extractor._decode_exif_string(123) == 123


def test_float_passes_through(extractor):
    assert extractor._decode_exif_string(3.14) == 3.14


def test_tuple_passes_through(extractor):
    # Rational tuples (aperture, exposure) shouldn't be touched
    assert extractor._decode_exif_string((28, 10)) == (28, 10)


# ---------------------------------------------------------------------------
# Bytes decoding — defensive path for older Canon/Nikon firmware
# ---------------------------------------------------------------------------


def test_ascii_bytes_decoded(extractor):
    assert extractor._decode_exif_string(b"Canon") == "Canon"


def test_empty_bytes_decoded(extractor):
    assert extractor._decode_exif_string(b"") == ""


def test_non_ascii_bytes_replaced(extractor):
    # errors="replace" uses U+FFFD (the Unicode replacement character)
    assert extractor._decode_exif_string(b"Can\xffon") == "Can\ufffdon"


def test_multi_byte_utf8_replaced_per_byte(extractor):
    # UTF-8 continuation bytes (>0x7f) each become one U+FFFD
    assert extractor._decode_exif_string("café".encode("utf-8")) == "caf\ufffd\ufffd"


def test_nulls_preserved_through_decode(extractor):
    # Decoder doesn't strip nulls — that's _sanitize_for_excel's job.
    assert extractor._decode_exif_string(b"Canon\x00\x00") == "Canon\x00\x00"


def test_barn_owl_software_value(extractor):
    """The exact Software string from the probe, as bytes."""
    raw = b"BO897WIDENC2Dx1418014"
    assert extractor._decode_exif_string(raw) == "BO897WIDENC2Dx1418014"


# ---------------------------------------------------------------------------
# Integration — the pipeline produces str even when the reader returns bytes
# ---------------------------------------------------------------------------


def test_scan_image_make_is_str(extractor, tmp_path):
    """End-to-end: Make column always ends up as str in the DataFrame."""
    path = tmp_path / "owl.jpg"
    img = Image.new("RGB", (10, 10))
    exif = Image.Exif()
    exif[306] = "2025:10:18 12:36:54"
    exif[271] = "barn owl"  # Pillow writes as str, but decoder normalizes either way
    img.save(path, format="JPEG", exif=exif)

    from tests.test_scan import _EXTRA_OFF

    data = extractor._empty_scan_data()
    ok = extractor.scan_image(tmp_path, 0, data, ["owl.jpg"], **{**_EXTRA_OFF, "output_make": True})
    assert ok
    assert isinstance(data["Makes"][0], str)
    assert data["Makes"][0] == "barn owl"
