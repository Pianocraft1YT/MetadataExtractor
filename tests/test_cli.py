"""Tests for v5.0.0 CLI / Headless mode (build_parser & run_cli)."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import pytest
from PIL.TiffImagePlugin import IFDRational

import metadata
from tests.conftest import make_jpeg_with_exif, make_jpeg_with_nested_exif


def _write_minimal_mp4(path: Path, utc: datetime) -> None:
    mp4_time = int(utc.timestamp()) + 2_082_844_800
    mvhd_payload = b"\x00\x00\x00\x00" + mp4_time.to_bytes(4, "big")
    mvhd = (8 + len(mvhd_payload)).to_bytes(4, "big") + b"mvhd" + mvhd_payload
    moov = (8 + len(mvhd)).to_bytes(4, "big") + b"moov" + mvhd
    ftyp_payload = b"isom\x00\x00\x02\x00isomiso2"
    ftyp = (8 + len(ftyp_payload)).to_bytes(4, "big") + b"ftyp" + ftyp_payload
    path.write_bytes(ftyp + moov)


# ---------------------------------------------------------------------------
# Headless isolation & help / syntax
# ---------------------------------------------------------------------------


def test_headless_init_skips_tk_and_settings(tmp_path):
    metadata.tk.Tk.reset_mock()
    metadata.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    metadata.SETTINGS_PATH.write_text(json.dumps({"UTC": True, "Filetype": "JSON"}), encoding="utf-8")

    app = metadata.MetadataExtractor(headless=True)

    metadata.tk.Tk.assert_not_called()
    assert app.root is None
    assert app._headless is True
    assert app.directory_path is None


def test_cli_does_not_call_messagebox_or_touch_settings(tmp_path, silence_messageboxes):
    metadata.SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    saved_before = {"UTC": True, "Filetype": "Markdown"}
    metadata.SETTINGS_PATH.write_text(json.dumps(saved_before), encoding="utf-8")

    src = tmp_path / "src"
    src.mkdir()
    make_jpeg_with_exif(src / "shot.jpg", "2024:05:15 12:30:45")
    out = tmp_path / "out.xlsx"

    rc = metadata.run_cli(["-i", str(src), "-o", str(out), "-q"])

    assert rc == 0
    assert out.is_file()
    silence_messageboxes.showinfo.assert_not_called()
    silence_messageboxes.showerror.assert_not_called()
    silence_messageboxes.showwarning.assert_not_called()
    silence_messageboxes.askyesno.assert_not_called()
    assert json.loads(metadata.SETTINGS_PATH.read_text(encoding="utf-8")) == saved_before


def test_cli_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        metadata.run_cli(["--help"])
    assert exc.value.code == 0
    assert "Extract metadata from media files." in capsys.readouterr().out


def test_cli_missing_required_args_exits_two():
    with pytest.raises(SystemExit) as exc:
        metadata.run_cli(["-i", "."])
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# Input validation & exit code 1
# ---------------------------------------------------------------------------


def test_cli_nonexistent_input_returns_1(tmp_path, capsys):
    rc = metadata.run_cli(["-i", str(tmp_path / "missing"), "-o", str(tmp_path / "out.xlsx")])
    assert rc == 1
    assert "directory" in capsys.readouterr().err.lower()


def test_cli_nonexistent_output_parent_returns_1(tmp_path, capsys):
    src = tmp_path / "src"
    src.mkdir()
    rc = metadata.run_cli(["-i", str(src), "-o", str(tmp_path / "no_such_dir" / "out.xlsx")])
    assert rc == 1
    assert "parent" in capsys.readouterr().err.lower()


@pytest.mark.parametrize("bad_cutoff", ["-1", "nan", "inf"])
def test_cli_invalid_cutoff_returns_1(tmp_path, bad_cutoff):
    src = tmp_path / "src"
    src.mkdir()
    rc = metadata.run_cli(["-i", str(src), "-o", str(tmp_path / "out.xlsx"), "-c", bad_cutoff])
    assert rc == 1


@pytest.mark.parametrize("bad_args", [["-r", "-md", "0"], ["-m", "-1"]])
def test_cli_invalid_maxdepth_and_modifier_returns_1(tmp_path, bad_args):
    src = tmp_path / "src"
    src.mkdir()
    rc = metadata.run_cli(["-i", str(src), "-o", str(tmp_path / "out.xlsx"), *bad_args])
    assert rc == 1


@pytest.mark.parametrize(
    "date_args",
    [
        ["-sd", "05/01/2024"],
        ["-ed", "not-a-date"],
        ["-sd", "2024-06-01", "-ed", "2024-05-01"],
    ],
)
def test_cli_invalid_dates_return_1(tmp_path, date_args):
    src = tmp_path / "src"
    src.mkdir()
    rc = metadata.run_cli(["-i", str(src), "-o", str(tmp_path / "out.xlsx"), *date_args])
    assert rc == 1


def test_cli_empty_directory_returns_1(tmp_path, capsys):
    src = tmp_path / "empty"
    src.mkdir()
    out = tmp_path / "out.xlsx"
    rc = metadata.run_cli(["-i", str(src), "-o", str(out)])
    assert rc == 1
    assert not out.exists()
    assert "Error" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Overwrite protection
# ---------------------------------------------------------------------------


def test_cli_refuses_overwrite_without_flag_and_succeeds_with_y(tmp_path, capsys):
    src = tmp_path / "src"
    src.mkdir()
    make_jpeg_with_exif(src / "shot.jpg", "2024:05:15 12:30:45")
    out = tmp_path / "out.xlsx"
    out.write_bytes(b"sentinel")

    rc_no = metadata.run_cli(["-i", str(src), "-o", str(out)])
    assert rc_no == 1
    assert out.read_bytes() == b"sentinel"
    assert "--overwrite" in capsys.readouterr().err

    rc_yes = metadata.run_cli(["-i", str(src), "-o", str(out), "-y", "-q"])
    assert rc_yes == 0
    wb = openpyxl.load_workbook(out)
    assert wb.active["A2"].value == "shot.jpg"


def test_cli_csv_refuses_overwrite_without_flag_in_recursive_mode(tmp_path):
    src = tmp_path / "src"
    sub_a = src / "A"
    sub_b = src / "B"
    sub_a.mkdir(parents=True)
    sub_b.mkdir(parents=True)
    make_jpeg_with_exif(sub_a / "a.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(sub_b / "b.jpg", "2024:05:15 12:00:00")

    out = tmp_path / "report.csv"
    existing_a = tmp_path / "report_A.csv"
    existing_b = tmp_path / "report_B.csv"
    existing_a.write_text("keep-a", encoding="utf-8")
    existing_b.write_text("keep-b", encoding="utf-8")

    rc_no = metadata.run_cli(["-i", str(src), "-o", str(out), "-r", "-q"])
    assert rc_no == 1
    assert existing_a.read_text(encoding="utf-8") == "keep-a"
    assert existing_b.read_text(encoding="utf-8") == "keep-b"

    rc_yes = metadata.run_cli(["-i", str(src), "-o", str(out), "-r", "-y", "-q"])
    assert rc_yes == 0
    assert "a.jpg" in existing_a.read_text(encoding="utf-8")
    assert "b.jpg" in existing_b.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Formats, hyperlinks, quiet
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ext", [".xlsx", ".csv", ".json", ".md"])
def test_cli_infers_format_from_extension(tmp_path, ext):
    src = tmp_path / "src"
    src.mkdir()
    make_jpeg_with_exif(src / "shot.jpg", "2024:05:15 12:30:45")
    out = tmp_path / f"report{ext}"

    rc = metadata.run_cli(["-i", str(src), "-o", str(out), "-q"])

    assert rc == 0
    assert out.is_file()


def test_cli_filetype_flag_overrides_extension(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    make_jpeg_with_exif(src / "shot.jpg", "2024:05:15 12:30:45")
    out = tmp_path / "report.csv"

    rc = metadata.run_cli(["-i", str(src), "-o", str(out), "-f", "json", "-q"])

    assert rc == 0
    json_out = tmp_path / "report.json"
    assert json_out.is_file()
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["sheets"]["Sheet"][0]["Files"] == "shot.jpg"


def test_cli_hyperlinks_default_and_no_hyperlinks_flag(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    make_jpeg_with_exif(src / "shot.jpg", "2024:05:15 12:30:45")

    out_default = tmp_path / "default.xlsx"
    assert metadata.run_cli(["-i", str(src), "-o", str(out_default), "-q"]) == 0
    assert openpyxl.load_workbook(out_default).active["A2"].hyperlink is not None

    out_no_hl = tmp_path / "no_hl.xlsx"
    assert metadata.run_cli(["-i", str(src), "-o", str(out_no_hl), "--no-hyperlinks", "-q"]) == 0
    assert openpyxl.load_workbook(out_no_hl).active["A2"].hyperlink is None


def test_cli_quiet_suppresses_stdout(tmp_path, capsys):
    src = tmp_path / "src"
    src.mkdir()
    make_jpeg_with_exif(src / "shot.jpg", "2024:05:15 12:30:45")

    assert metadata.run_cli(["-i", str(src), "-o", str(tmp_path / "q.json"), "-q"]) == 0
    assert capsys.readouterr().out == ""

    assert metadata.run_cli(["-i", str(src), "-o", str(tmp_path / "loud.json")]) == 0
    assert "Files written: 1" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Recursive, summary, cutoff, modifier
# ---------------------------------------------------------------------------


def test_cli_recursive_depth_and_summary_sheet(tmp_path):
    src = tmp_path / "src"
    a = src / "A"
    b = src / "B"
    deep = a / "Deep"
    deep.mkdir(parents=True)
    b.mkdir(parents=True)
    make_jpeg_with_exif(a / "a.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(b / "b.jpg", "2024:05:16 12:00:00")
    make_jpeg_with_exif(deep / "deep.jpg", "2024:05:17 12:00:00")

    out_d1 = tmp_path / "d1.xlsx"
    assert metadata.run_cli(["-i", str(src), "-o", str(out_d1), "-r", "-s", "-q"]) == 0
    wb1 = openpyxl.load_workbook(out_d1)
    assert wb1.sheetnames == ["Summary", "A", "B"]
    assert wb1["Summary"]["B2"].hyperlink is not None

    out_d2 = tmp_path / "d2.xlsx"
    assert metadata.run_cli(["-i", str(src), "-o", str(out_d2), "-r", "-md", "2", "-s", "-q"]) == 0
    wb2 = openpyxl.load_workbook(out_d2)
    assert wb2.sheetnames == ["Summary", "A", "A_Deep", "B"]


def test_cli_cutoff_and_modifier(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    make_jpeg_with_exif(src / "p1.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(src / "p2.jpg", "2024:05:15 12:00:03")

    out = tmp_path / "out.json"
    rc = metadata.run_cli(["-i", str(src), "-o", str(out), "-c", "5.0", "-m", "10", "-q"])
    assert rc == 0
    rows = json.loads(out.read_text(encoding="utf-8"))["sheets"]["Sheet"]
    assert [r["Img # Series"] for r in rows] == ["11-12", "11-12"]


# ---------------------------------------------------------------------------
# UTC, formats, sorting, date range, hidden, media filter
# ---------------------------------------------------------------------------


def test_cli_utc_formats_and_sort_oldest(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    # 14:30 -05:00 = 19:30 UTC (later)
    make_jpeg_with_nested_exif(
        src / "b_later.jpg",
        exif_tags={36867: "2024:05:15 14:30:00", 36881: "-05:00"},
    )
    # 14:30 +02:00 = 12:30 UTC (earlier)
    make_jpeg_with_nested_exif(
        src / "a_earlier.jpg",
        exif_tags={36867: "2024:05:15 14:30:00", 36881: "+02:00"},
    )

    out = tmp_path / "out.json"
    rc = metadata.run_cli(
        [
            "-i",
            str(src),
            "-o",
            str(out),
            "-u",
            "-df",
            "YYYY-MM-DD",
            "-t",
            "12h",
            "-S",
            "oldest",
            "-q",
        ]
    )
    assert rc == 0
    rows = json.loads(out.read_text(encoding="utf-8"))["sheets"]["Sheet"]
    assert [r["Files"] for r in rows] == ["a_earlier.jpg", "b_later.jpg"]
    assert [r["Dates"] for r in rows] == ["2024-05-15", "2024-05-15"]
    assert [r["Time"] for r in rows] == ["12:30:00 PM", "07:30:00 PM"]


def test_cli_date_range_and_no_include_undateable(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    make_jpeg_with_exif(src / "in_range.jpg", "2024:05:15 12:00:00")
    make_jpeg_with_exif(src / "out_range.jpg", "2024:07:01 12:00:00")
    make_jpeg_with_nested_exif(src / "nodate.jpg")

    out = tmp_path / "out.json"
    rc = metadata.run_cli(
        [
            "-i",
            str(src),
            "-o",
            str(out),
            "-sd",
            "2024-05-01",
            "-ed",
            "2024-05-31",
            "--no-include-undateable",
            "-q",
        ]
    )
    assert rc == 0
    rows = json.loads(out.read_text(encoding="utf-8"))["sheets"]["Sheet"]
    assert [r["Files"] for r in rows] == ["in_range.jpg"]


def test_cli_hidden_and_videos_only_media_filter(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    make_jpeg_with_exif(src / ".hidden.jpg", "2024:05:15 12:00:00")
    _write_minimal_mp4(src / "clip.mp4", datetime(2024, 5, 15, 12, 0, 1, tzinfo=timezone.utc))

    out_hidden = tmp_path / "hidden.json"
    assert metadata.run_cli(["-i", str(src), "-o", str(out_hidden), "-H", "-M", "photos", "-q"]) == 0
    assert [r["Files"] for r in json.loads(out_hidden.read_text(encoding="utf-8"))["sheets"]["Sheet"]] == [".hidden.jpg"]

    out_videos = tmp_path / "videos.json"
    assert metadata.run_cli(["-i", str(src), "-o", str(out_videos), "-M", "videos", "-q"]) == 0
    assert [r["Files"] for r in json.loads(out_videos.read_text(encoding="utf-8"))["sheets"]["Sheet"]] == ["clip.mp4"]


# ---------------------------------------------------------------------------
# Extra metadata flags (--all, individual flags, --gps, --gps-altitude)
# ---------------------------------------------------------------------------


def test_cli_all_exif_and_gps_altitude(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    img_path = src / "full.jpg"
    make_jpeg_with_nested_exif(
        img_path,
        exif_tags={
            36867: "2024:05:15 12:30:45",
            42036: "RF 50mm F1.2L",
            33437: IFDRational(28, 10),
            33434: IFDRational(1, 500),
            37386: IFDRational(50, 1),
            34855: 400,
        },
        gps_tags={
            1: "N",
            2: (IFDRational(48, 1), IFDRational(51, 1), IFDRational(24, 1)),
            3: "E",
            4: (IFDRational(2, 1), IFDRational(21, 1), IFDRational(7, 1)),
            5: 0,
            6: IFDRational(1245, 10),
        },
    )
    from PIL import Image

    with Image.open(img_path) as im:
        ex = im.getexif()
        ex[271] = "Canon"
        ex[272] = "Canon EOS R5"
        ex[305] = "Extractor"
        ex[274] = 6
        im.save(img_path, format="JPEG", exif=ex)

    out = tmp_path / "all.json"
    # -ga implies --gps even without passing -g explicitly
    rc = metadata.run_cli(["-i", str(src), "-o", str(out), "-a", "-ga", "-q"])
    assert rc == 0

    row = json.loads(out.read_text(encoding="utf-8"))["sheets"]["Sheet"][0]
    assert row["Dimensions"] == "10x10"
    assert isinstance(row["File Size"], str)
    assert row["Camera Make"] == "Canon"
    assert row["Camera Model"] == "Canon EOS R5"
    assert row["Software"] == "Extractor"
    assert row["Lens Model"] == "RF 50mm F1.2L"
    assert row["Aperture / FNumber"] == "f/2.8"
    assert row["Exposure Time"] == "1/500"
    assert row["Focal Length"] == "50mm"
    assert row["ISO"] == 400
    assert row["Orientation"] == "Rotated 90° CW"
    assert row["GPS Latitude"] == "48.856667"
    assert row["GPS Longitude"] == "2.351944"
    assert row["GPS Altitude"] == "124.5 m"


def test_cli_individual_exif_flags(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    img_path = src / "cam.jpg"
    make_jpeg_with_nested_exif(img_path, exif_tags={36867: "2024:05:15 12:30:45", 34855: 200})
    from PIL import Image

    with Image.open(img_path) as im:
        ex = im.getexif()
        ex[271] = "Nikon"
        ex[272] = "Z8"
        im.save(img_path, format="JPEG", exif=ex)

    out = tmp_path / "subset.json"
    rc = metadata.run_cli(["-i", str(src), "-o", str(out), "-mk", "-mo", "-q"])
    assert rc == 0
    row = json.loads(out.read_text(encoding="utf-8"))["sheets"]["Sheet"][0]
    assert row["Camera Make"] == "Nikon"
    assert row["Camera Model"] == "Z8"
    assert "ISO" not in row
    assert "Software" not in row


# ---------------------------------------------------------------------------
# Real subprocess CLI smoke test
# ---------------------------------------------------------------------------


def test_cli_subprocess_smoke(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    make_jpeg_with_exif(src / "shot.jpg", "2024:05:15 12:30:45")
    out = tmp_path / "sub.json"
    stdout_log = tmp_path / "stdout.txt"
    stderr_log = tmp_path / "stderr.txt"

    with open(stdout_log, "w", encoding="utf-8") as out_f, open(stderr_log, "w", encoding="utf-8") as err_f:
        proc = subprocess.run(
            [sys.executable, str(Path(metadata.__file__)), "-i", str(src), "-o", str(out), "-q"],
            stdout=out_f,
            stderr=err_f,
            check=False,
        )

    assert proc.returncode == 0, stderr_log.read_text(encoding="utf-8")
    assert out.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["sheets"]["Sheet"][0]["Files"] == "shot.jpg"