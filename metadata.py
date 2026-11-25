# Dear programmer:
# When I wrote this code, only God and I knew how it worked.
# Now, only God knows!
#
# Therefore, if you trying to improve this,
# Please increment this counter as a warning
# For the next person:
#
# hours_spent_original = 106
# hours_wasted_here = 0

# Coded by Pianocraft1YT
# Tutorial: https://youtu.be/ruWNKBdbYoo
# GitHub Repo: https://github.com/Pianocraft1YT/MetadataExtractor/
# Releases: https://github.com/Pianocraft1YT/MetadataExtractor/releases/

# Imports
import argparse
import itertools
import json
import math
import os
import re
import stat
import struct
import sys
import threading
import time
import tkinter as tk
import traceback
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Generic, TypeVar

import openpyxl
import pandas as pd
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from PIL import Image
from tk_date_entry import DateEntry

from video_metadata import extract_video_metadata

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIF_SUPPORTED = True
except ImportError:
    HEIF_SUPPORTED = False

try:
    from hachoir.metadata import extractMetadata
    from hachoir.parser import createParser

    HACHOIR_SUPPORTED = True
except ImportError:
    HACHOIR_SUPPORTED = False

try:
    import exifread

    RAW_SUPPORTED = True
except ImportError:
    RAW_SUPPORTED = False

# EXIF Constants
EXIF_DATETIME = 306
EXIF_DATETIME_ORIGINAL = 36867
EXIF_DATETIME_DIGITIZED = 36868
EXIF_OFFSET_TIME = 36880
EXIF_OFFSET_TIME_ORIGINAL = 36881
EXIF_OFFSET_TIME_DIGITIZED = 36882
EXIF_CAMERA_MAKE = 271
EXIF_CAMERA_MODEL = 272
EXIF_ORIENTATION = 274
EXIF_SOFTWARE = 305
EXIF_LENS_MODEL = 42036
EXIF_APERTURE = 33437
EXIF_EXPOSURE_TIME = 33434
EXIF_FOCAL_LENGTH = 37386
EXIF_ISO = 34855

# General Constants
SHEET_NAME_MAX_CHARS = 31
# XML Illegals
XML_ILLEGAL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# Persistent Settings
SETTINGS_PATH = Path.home() / ".metadata-extractor" / "settings.json"
# Common video file formats to check
# Only .mp4 and .mov are scanned for metadata currently
VIDEO_TYPES = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv")
# Common and uncommon image formats to check
# TODO: TIFF-based RAWs are supported with exifread installed; non-TIFF RAWs (.cr3, .x3f) depend on exifread container support.
RAW_TYPES = (
    ".dng",
    ".crw",
    ".cr2",
    ".cr3",
    ".nef",
    ".nrw",
    ".arw",
    ".srf",
    ".sr2",
    ".raf",
    ".rw2",
    ".raw",
    ".orf",
    ".ori",
    ".pef",
    ".ptx",
    ".rwl",
    ".3fr",
    ".fff",
    ".iiq",
    ".mos",
    ".x3f",
    ".kdc",
    ".dcr",
    ".dcs",
    ".srw",
    ".mrw",
)

PHOTO_TYPES = (
    ".jpg",
    ".jpeg",
    ".heic",
    ".heif",
    ".png",
    ".tiff",
    ".tif",
) + RAW_TYPES


@dataclass
# Config options for scans, instead of passing through values
class ScanConfig:
    final_output: Path
    modifier: int
    cutoff: float
    date_range: bool
    date_format: str
    time_format: str
    start_date: date | None
    end_date: date | None
    include_hiddens: bool
    include_undateable: bool
    media_filter: str
    output_summary: bool = False
    output_utc: bool = False
    output_dimensions: bool = False
    output_filesize: bool = False
    output_make: bool = False
    output_model: bool = False
    output_software: bool = False
    output_lens_model: bool = False
    output_aperture: bool = False
    output_exposure_time: bool = False
    output_focal_length: bool = False
    output_iso: bool = False
    output_orientation: bool = False
    output_gps: bool = False
    output_gps_altitude: bool = False
    output_video_rows: bool = False
    filetype: str | None = None
    directory_path: Path | None = None


_T = TypeVar("_T")


class _CliVar(Generic[_T]):
    def __init__(self, value: _T) -> None:
        self._value: _T = value

    def get(self) -> _T:
        return self._value

    def set(self, value: _T) -> None:
        self._value = value


class MetadataExtractor:

    # Cosmetic only, adds placeholder text in entry boxes
    def nameFocusIn(self, event: tk.Event) -> None:
        """Clears default text for name_entry on user focus in."""
        if self.name_entry.get() == "Filename (default output.filetype)":
            self.name_entry.delete(0, "end")
            self.name_entry.config(foreground="black")

    def nameFocusOut(self, event: tk.Event) -> None:
        """Inserts default text for name_entry on user focus out if blank."""
        if self.name_entry.get() == "":
            self.name_entry.insert(0, "Filename (default output.filetype)")
            self.name_entry.config(foreground="gray")

    def modifierFocusIn(self, event: tk.Event) -> None:
        """Clears default text for modifier_entry on user focus in."""
        if self.modifier_entry.get() == "Starting index (Img # Series)":
            self.modifier_entry.delete(0, "end")
            self.modifier_entry.config(foreground="black")

    def modifierFocusOut(self, event: tk.Event) -> None:
        """Inserts default text for modifier_entry on user focus out if blank."""
        if self.modifier_entry.get() == "":
            self.modifier_entry.insert(0, "Starting index (Img # Series)")
            self.modifier_entry.config(foreground="gray")

    def maxDepthFocusIn(self, event: tk.Event) -> None:
        """Clears default text for maxdepth_entry on user focus in."""
        if self.maxdepth_entry.get() == "Recursion Depth (#)":
            self.maxdepth_entry.delete(0, "end")
            self.maxdepth_entry.config(foreground="black")

    def maxDepthFocusOut(self, event: tk.Event) -> None:
        """Inserts default text for maxdepth_entry on user focus out if blank."""
        if self.maxdepth_entry.get() == "":
            self.maxdepth_entry.insert(0, "Recursion Depth (#)")
            self.maxdepth_entry.config(foreground="gray")

    def burstCutoffFocusIn(self, event: tk.Event) -> None:
        """Clears default text for burst_cutoff_entry on user focus in."""
        if self.burst_cutoff_entry.get() == "Photo grouping cutoff (default 2 seconds)":
            self.burst_cutoff_entry.delete(0, "end")
            self.burst_cutoff_entry.config(foreground="black")

    def burstCutoffFocusOut(self, event: tk.Event) -> None:
        """Inserts default text for burst_cutoff_entry on user focus out if blank."""
        if self.burst_cutoff_entry.get() == "":
            self.burst_cutoff_entry.insert(0, "Photo grouping cutoff (default 2 seconds)")
            self.burst_cutoff_entry.config(foreground="gray")

    def gps_warning(self) -> None:
        """Displays privacy warning when gps_checkbox is checked."""
        if self.gps_var.get():
            self.gps_warning_label.pack(after=self.gps_checkbox, fill="x", padx=4)
            self.gps_altitude_checkbox.pack(before=self.gps_warning_label, anchor="w", padx=4, pady=1)
        else:
            self.gps_warning_label.pack_forget()
            self.gps_altitude_checkbox.pack_forget()
        self._refresh_window()

    def debug_warning(self) -> None:
        """Prompts user with askokcancel dialog when debug_checkbox is checked, and explains what debug mode does."""
        if self.debug_var.get():
            self.debug_var.set(
                messagebox.askokcancel(
                    "Debug selected",
                    message="Debug mode has been enabled.\nThis means that output directory is Path.home()/Downloads/output.filetype.\n\nProceed?",
                )
            )

    # Show recursive_input entry box when recursive is checked
    def recursive_input(self) -> None:
        """Displays maxdepth_entry when recursive_checkbox is checked."""
        if self.recursive_var.get():
            self.maxdepth_entry.pack(after=self.recursive_checkbox)
        else:
            self.maxdepth_entry.pack_forget()
        self._refresh_window()  # flush pending layout

    # Show extra metadata checkboxes when extra_exif_checkbox is checked
    def extra_exif(self) -> None:
        """Displays exif_extra_frame and related checkboxes when extra_exif_checkbox is checked."""
        if self.extra_exif_var.get():
            # Pack Extra Checkboxes
            self.extra_exif_frame.pack(after=self.extra_scan_options_frame)
            for i, checkbox in enumerate(self.extra_exif_options):
                checkbox.grid(row=i // 2, column=i % 2, sticky="w", padx=4)
        else:
            for checkbox in self.extra_exif_options:
                checkbox.pack_forget()
            self.extra_exif_frame.pack_forget()
        self._refresh_window()

    # Show starting date and ending date calendar widgets on checkbox click only
    def date_range(self) -> None:
        """Displays date_notice_label informing user of required info as well as starting and ending date_entry calendar."""
        if self.date_range_var.get():
            self.date_frame.pack(after=self.extra_scan_options_frame, fill="x", pady=(0, 8))
            self.date_notice_label.pack()
            self.include_undateable_checkbox.pack(after=self.date_notice_label)
            self.start_date_label.pack(after=self.include_undateable_checkbox)
            self.start_date_entry.pack(after=self.start_date_label)
            self.end_date_label.pack(after=self.start_date_entry)
            self.end_date_entry.pack(after=self.end_date_label)
        else:
            self.start_date_label.pack_forget()
            self.include_undateable_checkbox.pack_forget()
            self.start_date_entry.pack_forget()
            self.end_date_label.pack_forget()
            self.end_date_entry.pack_forget()
            self.date_notice_label.pack_forget()
            self.date_frame.pack_forget()
        self._refresh_window()  # flush pending layout

    def user_mode(self) -> None:
        """Displays advanced_mode_frame when advanced mode radio is selected."""
        if self.user_mode_var.get() == "Advanced":
            self.advanced_mode_frame.pack(side="left", anchor="n", padx=10, pady=6)
            # Extra Scan Options Frame
            self.extra_scan_options_frame.pack(fill="x", padx=8, pady=4)
            # Date Format
            self.date_format_frame.pack(fill="x", padx=4, pady=4)
            self.date_format_combobox.pack(fill="x", padx=4, pady=2)
            # Time Format
            self.time_format_frame.pack(after=self.date_format_frame, fill="x", padx=4, pady=4)
            self.time_format_combobox.pack(fill="x", padx=4, pady=4)

            self.modifier_entry.pack(fill="x", padx=4, pady=3)
            self.video_rows_checkbox.pack(anchor="w", padx=4, pady=1)
            self.hidden_checkbox.pack(anchor="w", padx=4, pady=1)
            self.media_filter_combobox.pack(anchor="w", padx=4, pady=1)
            self.utc_checkbox.pack(anchor="w", padx=4, pady=1)
            self.gps_checkbox.pack(anchor="w", padx=4, pady=1)
            self.gps_warning()

            # Sort Methods Frame
            self.sort_methods_frame.pack(after=self.extra_scan_options_frame, fill="x", padx=8, pady=4)
            if len(self.sort_method_objects) > 0:
                for sm in self.sort_method_objects:
                    sm.pack(side="left", padx=2)
            else:
                for sm in self.sort_methods:
                    smr = tk.Radiobutton(self.sort_methods_frame, text=sm, variable=self.sort_methods_var, value=sm)
                    smr.pack(side="left", padx=2)
                    self.sort_method_objects.append(smr)

            # Date Range section
            self.date_range_checkbox.pack(anchor="w", padx=4, pady=1)
            self.date_range()

            # Extra Metadata section
            self.extra_exif_checkbox.pack(anchor="w", padx=4, pady=1)
            self.extra_exif()

            self.debug_checkbox.pack(padx=8, pady=2)

            self._refresh_window()
        else:
            self.advanced_mode_frame.pack_forget()
            self._refresh_window()

    # Updates path label variables
    def _update_path_labels(self) -> None:
        """Updates labels for source path and output path."""
        self.source_path_var.set(self._format_path_label("Source", self.directory_path))
        self.output_path_var.set(self._format_path_label("Output", self.output_path))

    # Opens warnings.log
    def _view_warnings_log(self):
        if self.last_warnings_log and self.last_warnings_log.is_file() and not self._headless:
            self._open_path(self.last_warnings_log, False)
        else:
            self._notify_info("Log file not found.", message="Log file not found.")

    # Sort helper
    @staticmethod
    def natural_key(text: str) -> list[tuple[int, int | str]]:
        """Sort key for natural/alphanumeric order."""
        return [(0, t.lower()) if not t.isdigit() else (1, int(t)) for t in re.split(r"(\d+)", text)]

    # Date filter helpers
    def _filter_by_date(
        self,
        dirpath: str,
        media_files: list[str],
        start_date: date | None,
        end_date: date | None,
        include_undateable: bool,
    ) -> list[str]:
        """Filters media_files by date if date_range_checkbox was checked."""
        return_files = []
        for file in media_files:
            if self.cancel_event.is_set():
                return return_files
            lower = file.lower()
            dt = None
            keep = True
            path = Path(dirpath) / file
            if lower.endswith(PHOTO_TYPES):
                dt, _, _ = self._get_photo_date_and_offset(path)
            elif lower.endswith((".mp4", ".mov")):
                dt = self._get_video_date(path)
            if dt is not None:
                dt = dt.date()
                if start_date and dt < start_date or end_date and dt > end_date:
                    keep = False
            elif dt is None and not include_undateable:
                keep = False
            if keep:
                return_files.append(file)
            else:
                if self._photo_cache is not None:
                    self._photo_cache.pop(path, None)
                if self._video_cache is not None:
                    self._video_cache.pop(path, None)
        return return_files

    def _select_photo_datetime(self, exif_data: Any, general_ifd: Any) -> tuple[datetime | None, bool, int | None]:
        """Select first valid EXIF datetime and return (datetime, has_time, paired_offset_tag)."""
        candidates = (
            (exif_data.get(EXIF_DATETIME_ORIGINAL), EXIF_OFFSET_TIME_ORIGINAL),
            (general_ifd.get(EXIF_DATETIME_ORIGINAL), EXIF_OFFSET_TIME_ORIGINAL),
            (exif_data.get(EXIF_DATETIME_DIGITIZED), EXIF_OFFSET_TIME_DIGITIZED),
            (general_ifd.get(EXIF_DATETIME_DIGITIZED), EXIF_OFFSET_TIME_DIGITIZED),
            (exif_data.get(EXIF_DATETIME), EXIF_OFFSET_TIME),
        )
        for raw, offset_tag in candidates:
            if raw is None:
                continue
            parsed, has_time = self._parse_exif_datetime(self._decode_exif_string(raw))
            if parsed is not None:
                return parsed, has_time, offset_tag
        return None, False, None

    def _read_photo_entry(
        self,
        path: Path,
        flags: tuple[bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool] | None,
    ) -> tuple[datetime | None, bool, str | None, dict[str, Any] | None, str | None]:
        """Extracts photo metadata based on flag state in flags, returns dict of values or None."""
        if flags is not None:
            output_utc = flags[0]
            output_dimensions = flags[1]
            output_filesize = flags[2]
            output_make = flags[3]
            output_model = flags[4]
            output_software = flags[5]
            output_lens_model = flags[6]
            output_aperture = flags[7]
            output_exposure_time = flags[8]
            output_focal_length = flags[9]
            output_iso = flags[10]
            output_orientation = flags[11]
            output_gps = flags[12]
            output_gps_altitude = flags[13]
        else:
            output_utc = output_dimensions = output_filesize = output_make = output_model = False
            output_software = output_lens_model = output_aperture = output_gps_altitude = False
            output_exposure_time = output_focal_length = output_iso = output_gps = output_orientation = False
        offset = None
        dimensions = None
        filesize = None
        make = None
        model = None
        software = None
        lens_model = None
        aperture = None
        exposure_time = None
        focal_length = None
        iso = None
        orientation = None
        gps_latitude = None
        gps_longitude = None
        gps_altitude = None
        try:
            if not HEIF_SUPPORTED and path.suffix.lower() in (".heic", ".heif"):
                return (None, False, None, None, "HEIC/HEIF requires pillow-heif")
            if path.suffix.lower() in RAW_TYPES:
                if not RAW_SUPPORTED:
                    return (None, False, None, None, "RAW files require exifread")
                else:
                    return self._read_raw_photo_entry(path, flags)
            with Image.open(path) as img:
                if output_dimensions and flags is not None:
                    dimensions = f"{img.size[0]}x{img.size[1]}"
                exif_data = img.getexif()
                general_ifd = exif_data.get_ifd(0x8769)
                gps_ifd = exif_data.get_ifd(0x8825) if flags is not None and output_gps else None
            parsed, has_time, offset_tag = self._select_photo_datetime(exif_data, general_ifd)
            if offset_tag is not None and (flags is None or output_utc):
                raw_offset = self._exif_get_str(offset_tag, general_ifd, exif_data)
                if isinstance(raw_offset, str):
                    offset = raw_offset.strip() or None
            if flags is not None:
                if output_filesize:
                    filesize = os.path.getsize(path)
                    filesize = self._convert_filesize(filesize)
                if output_make:
                    make = self._exif_get_str(EXIF_CAMERA_MAKE, None, exif_data)
                if output_model:
                    model = self._exif_get_str(EXIF_CAMERA_MODEL, None, exif_data)
                if output_software:
                    software = self._exif_get_str(EXIF_SOFTWARE, None, exif_data)
                if output_lens_model:
                    lens_model = self._exif_get_str(EXIF_LENS_MODEL, general_ifd, exif_data)
                if output_aperture:
                    aperture = self._format_aperture(self._exif_get(EXIF_APERTURE, general_ifd, exif_data))
                if output_exposure_time:
                    exposure_time = self._format_exposure_time(
                        self._exif_get(EXIF_EXPOSURE_TIME, general_ifd, exif_data)
                    )
                if output_focal_length:
                    focal_length = self._format_focal_length(self._exif_get(EXIF_FOCAL_LENGTH, general_ifd, exif_data))
                if output_iso:
                    iso = self._format_iso(self._exif_get(EXIF_ISO, general_ifd, exif_data))
                if output_orientation:
                    orientation = self._format_orientation(exif_data.get(EXIF_ORIENTATION))
                if output_gps and gps_ifd:
                    lat_ref = gps_ifd.get(1)
                    lat = gps_ifd.get(2)
                    long_ref = gps_ifd.get(3)
                    long = gps_ifd.get(4)
                    gps_latitude = self._format_gps_coord(lat, lat_ref)
                    gps_longitude = self._format_gps_coord(long, long_ref)
                    if output_gps_altitude:
                        gps_altitude_ref = gps_ifd.get(5)
                        gps_altitude = gps_ifd.get(6)
                        if gps_altitude_ref:
                            if gps_altitude_ref in (0, b"\x00", "0"):
                                ref = "+"
                            elif gps_altitude_ref in (1, b"\x01", "1"):
                                ref = "-"
                            elif gps_altitude_ref == "":
                                ref = "+"
                            else:
                                gps_altitude = None
                        else:
                            ref = "+"
                        if gps_altitude:
                            gps_altitude = self._format_gps_altitude(gps_altitude, ref)

                fields = {
                    "Offsets": offset,
                    "Dimensions": dimensions,
                    "Filesizes": filesize,
                    "Makes": make,
                    "Models": model,
                    "Softwares": software,
                    "Lens_Models": lens_model,
                    "Apertures": aperture,
                    "Exposure_Times": exposure_time,
                    "Focal_Lengths": focal_length,
                    "ISOs": iso,
                    "GPS_Latitudes": gps_latitude,
                    "GPS_Longitudes": gps_longitude,
                    "GPS_Altitudes": gps_altitude,
                    "Orientations": orientation,
                }
            else:
                fields = None
            return parsed, has_time, offset, fields, None
        except Exception as e:  # noqa: BLE001
            return None, False, None, None, str(e)

    def _read_raw_photo_entry(
        self,
        path: Path,
        flags: tuple[bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool] | None,
    ) -> tuple[datetime | None, bool, str | None, dict[str, Any] | None, str | None]:
        try:
            if flags is not None:
                output_utc = flags[0]
                output_dimensions = flags[1]
                output_filesize = flags[2]
                output_make = flags[3]
                output_model = flags[4]
                output_software = flags[5]
                output_lens_model = flags[6]
                output_aperture = flags[7]
                output_exposure_time = flags[8]
                output_focal_length = flags[9]
                output_iso = flags[10]
                output_orientation = flags[11]
                output_gps = flags[12]
                output_gps_altitude = flags[13]
            else:
                output_utc = output_dimensions = output_filesize = output_make = output_model = False
                output_software = output_lens_model = output_aperture = output_gps_altitude = False
                output_exposure_time = output_focal_length = output_iso = output_gps = output_orientation = False
            offset = None
            dimensions = None
            filesize = None
            make = None
            model = None
            software = None
            lens_model = None
            aperture = None
            exposure_time = None
            focal_length = None
            iso = None
            orientation = None
            gps_latitude = None
            gps_longitude = None
            gps_altitude = None
            with open(path, "rb") as f:
                tags = exifread.process_file(f, details=False)  # details=False skips makerinfo and thumbnails
            datetime_priority_pairs = [
                ("EXIF DateTimeOriginal", "EXIF OffsetTimeOriginal", "EXIF Tag 0x9011"),
                ("EXIF DateTimeDigitized", "EXIF OffsetTimeDigitized", "EXIF Tag 0x9012"),
                ("Image DateTime", "EXIF OffsetTime", "EXIF Tag 0x9010"),
            ]

            parsed, has_time, offset = None, False, None
            for dt_key, offset_key, fallback_offset_key in datetime_priority_pairs:
                dt_tag = tags.get(dt_key)
                if not dt_tag:
                    continue
                cand_dt, cand_has_time = self._parse_exif_datetime(self._decode_exif_string(str(dt_tag)))
                if cand_dt is not None:
                    parsed, has_time = cand_dt, cand_has_time
                    if flags is None or output_utc:
                        offset = self._raw_tag_str(tags, offset_key, fallback_offset_key)
                    break

            if flags is not None:
                if output_dimensions:
                    w_tag = tags.get("EXIF ExifImageWidth") or tags.get("Image ImageWidth")
                    h_tag = tags.get("EXIF ExifImageLength") or tags.get("Image ImageLength")
                    if w_tag and h_tag and getattr(w_tag, "values", None) and getattr(h_tag, "values", None):
                        w, h = w_tag.values[0], h_tag.values[0]
                        if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
                            dimensions = f"{w}x{h}"
                if output_filesize:
                    filesize = self._convert_filesize(os.path.getsize(path))
                if output_make:
                    make = self._raw_tag_str(tags, "Image Make")
                if output_model:
                    model = self._raw_tag_str(tags, "Image Model")
                if output_software:
                    software = self._raw_tag_str(tags, "Image Software")
                if output_lens_model:
                    lens_model = self._raw_tag_str(tags, "EXIF LensModel", "EXIF Tag 0xA434")
                if output_aperture:
                    aperture = self._format_aperture(self._raw_rational(tags.get("EXIF FNumber")))
                if output_exposure_time:
                    exposure_time = self._format_exposure_time(self._raw_rational(tags.get("EXIF ExposureTime")))
                if output_focal_length:
                    focal_length = self._format_focal_length(self._raw_rational(tags.get("EXIF FocalLength")))
                if output_iso:
                    iso_tag = tags.get("EXIF ISOSpeedRatings")
                    iso = self._format_iso(getattr(iso_tag, "values", None) if iso_tag is not None else None)
                if output_orientation:
                    orientation_tag = tags.get("Image Orientation")
                    raw_values = getattr(orientation_tag, "values", None)
                    orientation = raw_values[0] if isinstance(raw_values, (list, tuple)) and raw_values else raw_values
                    orientation = self._format_orientation(orientation)
                if output_gps:
                    lat_tag = tags.get("GPS GPSLatitude")
                    lat_ref = self._raw_tag_str(tags, "GPS GPSLatitudeRef")
                    lon_tag = tags.get("GPS GPSLongitude")
                    lon_ref = self._raw_tag_str(tags, "GPS GPSLongitudeRef")
                    if lat_tag and getattr(lat_tag, "values", None):
                        lat_dms = tuple(
                            (r.num, r.den) if hasattr(r, "num") and hasattr(r, "den") else r for r in lat_tag.values
                        )
                        gps_latitude = self._format_gps_coord(lat_dms, lat_ref)
                    if lon_tag and getattr(lon_tag, "values", None):
                        lon_dms = tuple(
                            (r.num, r.den) if hasattr(r, "num") and hasattr(r, "den") else r for r in lon_tag.values
                        )
                        gps_longitude = self._format_gps_coord(lon_dms, lon_ref)
                    if output_gps_altitude:
                        gps_altitude_tag = tags.get("GPS GPSAltitude")
                        gps_altitude = self._raw_rational(gps_altitude_tag)
                        gps_altitude_ref_tag = tags.get("GPS GPSAltitudeRef")
                        gps_altitude_ref_tag = self._raw_rational(gps_altitude_ref_tag)
                        if gps_altitude_ref_tag in (0, b"\x00", "0"):
                            ref = "+"
                        elif gps_altitude_ref_tag in (1, b"\x01", "1"):
                            ref = "-"
                        else:
                            gps_altitude = None
                        if gps_altitude:
                            gps_altitude = self._format_gps_altitude(gps_altitude_tag, ref)
                fields = {
                    "Offsets": offset,
                    "Dimensions": dimensions,
                    "Filesizes": filesize,
                    "Makes": make,
                    "Models": model,
                    "Softwares": software,
                    "Lens_Models": lens_model,
                    "Apertures": aperture,
                    "Exposure_Times": exposure_time,
                    "Focal_Lengths": focal_length,
                    "ISOs": iso,
                    "GPS_Latitudes": gps_latitude,
                    "GPS_Longitudes": gps_longitude,
                    "GPS_Altitudes": gps_altitude,
                    "Orientations": orientation,
                }
            else:
                fields = None

            return parsed, has_time, offset, fields, None
        except Exception as e:  # noqa: BLE001
            return (None, False, None, None, str(e))

    def _get_photo_date_and_offset(self, path: Path) -> tuple[datetime | None, bool, str | None]:
        """Opens given path as an Image to extract EXIF datetime."""
        try:
            if self._photo_cache is not None:
                if path not in self._photo_cache:
                    self._photo_cache[path] = self._read_photo_entry(path, self._scan_cache_flags)
                entry = self._photo_cache[path]
                return entry[0], entry[1], entry[2]
            else:
                entry = self._read_photo_entry(path, None)
                return entry[0], entry[1], entry[2]
        except Exception:  # noqa: BLE001
            return None, False, None

    def _get_video_date(self, path: Path) -> datetime | None:
        """Passes path to extract_video_metadata to get creation timestamp."""
        try:
            if self._video_cache is not None and path in self._video_cache:
                return self._video_cache[path]
            else:
                dt = extract_video_metadata(path)
                if dt is not None and dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                if self._video_cache is not None:
                    self._video_cache[path] = dt
                return dt
        except (OSError, ValueError, struct.error, OverflowError, KeyError):
            return None

    @staticmethod
    def _confirm_overwrite(path: Path) -> bool:
        """Helper to confirm overwriting of files."""
        if not path.exists():
            return True
        return messagebox.askyesno("Overwrite?", f"{path}\nalready exists. Overwrite?")

    def _should_overwrite(self, path: Path) -> bool:
        if not path.exists():
            return True
        if self._headless:
            if not self._cli_overwrite:
                print(
                    f"Error: {path.as_posix()} already exists (pass --overwrite to replace).",
                    file=sys.stderr,
                )
                return False
            return True
        return self._confirm_overwrite(path)

    def _notify_info(self, title: str, message: str) -> None:
        if self._headless:
            if not self._cli_quiet:
                print(message)
        else:
            messagebox.showinfo(title, message=message)

    def _notify_error(self, title: str, message: str) -> None:
        if self._headless:
            print(f"Error ({title}): {message}", file=sys.stderr)
        else:
            messagebox.showerror(title, message=message)

    def _notify_warning(self, title: str, message: str) -> None:
        if self._headless:
            print(f"Warning ({title}): {message}", file=sys.stderr)
        else:
            messagebox.showwarning(title, message=message)

    def _safe_after(self, callback: Callable[..., object], *args: Any) -> None:
        """Queue a callback on the main thread. Drops it silently if the root is gone."""
        if self._destroyed or self._headless or self.root is None:
            return

        def _run() -> None:
            if self._destroyed:
                return
            try:
                callback(*args)
            except tk.TclError:
                pass

        try:
            self.root.after(0, _run)
        except tk.TclError:
            pass

    # Conversion Helpers
    @staticmethod
    # Check if value is a float or int
    def is_number(value: Any) -> bool:
        """Check if value is a numeric string, float or int."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    # Apply formatting to Excel sheets
    def _format_excel_sheet(ws: Worksheet | None) -> None:
        """Applies formatting to Excel sheets (freeze, bold, autofilter, column width)"""
        if ws is None or ws.max_row < 1 or ws.max_column < 1:
            return
        ws.freeze_panes = "A2"
        for cell in ws[1]:
            cell.font = Font(bold=True)
        ws.auto_filter.ref = ws.dimensions
        for col_idx, col in enumerate(ws.columns, start=1):
            col_letter = get_column_letter(col_idx)
            max_len = 0
            for cell in col:
                if cell.value is None:
                    continue
                curr_len = max((len(line) for line in str(cell.value).splitlines()), default=0)
                max_len = max(max_len, curr_len)
            ws.column_dimensions[col_letter].width = min(max_len + 4, 50)

    @staticmethod
    # Turn only seconds into normal time measurements
    def _convert_seconds(seconds: float, mode: str = "ETA") -> str:
        """Turn seconds into human-readable durations, based on mode: "ETA" or "Time Elapsed"."""
        output = []
        minutes = 0
        hours = 0
        days = 0
        if seconds >= 60:
            minutes = int(seconds / 60)
            seconds = seconds - (minutes * 60)
            if minutes >= 60:
                hours = int(minutes / 60)
                minutes = minutes - (hours * 60)
                if hours >= 24:
                    days = int(hours / 24)
                    hours = hours - (days * 24)
        if days > 0:
            output.append(f"{days} day(s)")
        if hours > 0:
            output.append(f"{hours} hour(s)")
        if minutes > 0:
            output.append(f"{minutes} minute(s)")
        if seconds >= 1:
            output.append(f"{int(seconds)} second(s)")
        elif not output and mode != "ETA":
            output.append("< 1 second")
        if days == 0 and hours == 0 and minutes == 0 and seconds < 5 and mode == "ETA":
            output = "Starting/Ending Soon..."
        elif (days > 0 or hours > 0 or minutes > 0 or seconds > 0) and mode == "ETA":
            output = ", ".join(output) + " remaining."
        else:
            output = ", ".join(output)
        return output

    @staticmethod
    def _format_path_label(prefix: str, path: Path | None) -> str:
        """Formats path label and truncates if needed."""
        if path is None:
            return f"{prefix}: Not set"
        text = path.as_posix()
        if len(text) > 50:
            return f"{prefix}: ...{text[-47:]}"
        return f"{prefix}: {text}"

    @staticmethod
    # Turn filesize bytes into human-readable formats
    def _convert_filesize(v: int) -> str:
        """Converts filesize bytes into human-readable format (e.g. '4.5 MB')."""
        if v < 0:
            return "0 B"
        size = float(v)
        for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
            if size < 1000.0 or unit == "PB":
                if unit == "B":
                    return f"{int(size)} B"
                return f"{size:.1f} {unit}"
            size /= 1000.0
        return f"{size:.1f} PB"

    @staticmethod
    def _decode_exif_string(v: Any) -> Any:
        """Decodes v if v is bytes."""
        if isinstance(v, bytes):
            return v.decode("ascii", errors="replace").rstrip("\x00")
        if isinstance(v, str):
            return v.rstrip("\x00")
        return v

    @staticmethod
    def _exif_get(tag: int, ifd: Any, exif_data: Any) -> Any:
        """Look up tag in top-level EXIF, falling back to the sub-IFD if absent."""
        metadata = exif_data.get(tag)
        if metadata is None and ifd is not None:
            metadata = ifd.get(tag)
        return metadata

    @staticmethod
    def _exif_get_str(tag: int, ifd: Any, exif_data: Any) -> str | None:
        """Decode EXIF tag into string, strip NUL padding."""
        return __class__._decode_exif_string(__class__._exif_get(tag, ifd, exif_data))

    @staticmethod
    def _raw_tag_str(tags: dict[str, Any], *keys: str) -> str | None:
        """Return the first non-empty decoded string from tags for the given keys, or None."""
        for key in keys:
            tag = tags.get(key)
            if tag is not None:
                val = MetadataExtractor._decode_exif_string(str(tag)).strip()
                if val:
                    return val
        return None

    @staticmethod
    def _raw_rational(tag: Any) -> tuple[int, int] | float | None:
        """Convert an exifread tag's first value into a (num, den) tuple or numeric value."""
        if tag is None or not getattr(tag, "values", None):
            return None
        val = tag.values[0]
        if hasattr(val, "num") and hasattr(val, "den"):
            return (val.num, val.den)
        return val

    @staticmethod
    def _rational_to_float(value: Any) -> float | None:
        """Turns a rational (fraction) into a float"""
        if value is None:
            return None
        if isinstance(value, tuple):
            if len(value) != 2:
                return None
            num, den = value
            try:
                return num / den if den else None
            except (TypeError, ZeroDivisionError):
                return None
        try:
            return float(value)
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    def _format_aperture(self, value: Any) -> str | None:
        """Format an FNumber rational to "f/5.6" style."""
        v = self._rational_to_float(value)
        if v is None or v <= 0 or not math.isfinite(v):
            return None
        return f"f/{v:g}"  # 5.6 -> "f/5.6", 8.0 -> "f/8"

    def _format_exposure_time(self, value: Any) -> str | None:
        """Format an EXIF ExposureTime rational as "1/250" or "2.5s" style."""
        v = self._rational_to_float(value)
        if v is None or v <= 0 or not math.isfinite(v):
            return None
        if v >= 1:
            return f"{v:g}s"  # 1.0 -> "1s", 2.5 -> "2.5s", 30.0 -> "30s"
        inv = 1.0 / v
        rounded = round(inv)
        if rounded > 1 and abs(inv - rounded) / inv < 0.01:
            return f"1/{rounded}"  # 0.004 -> "1/250", 0.5 -> "1/2"
        return f"{round(v,2):g}s"  # 0.3 -> "0.3s" (not "1/3")

    def _format_focal_length(self, value: Any) -> str | None:
        """Format a focal length to "23mm" style."""
        v = self._rational_to_float(value)
        if v is None or v <= 0 or not math.isfinite(v):
            return None
        return f"{v:g}mm"  # 23.0 -> "23mm", 18.5 -> "18.5mm"

    @staticmethod
    def _format_iso(value: Any) -> int | str:
        """Formats ISO tag as integer"""
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            if not value:
                return ""
            value = value[0]
        try:
            return int(value)
        except (TypeError, ValueError):
            return ""

    @staticmethod
    def _format_orientation(val: Any) -> str | None:
        if val is None:
            return None
        try:
            code = int(val)
        except (TypeError, ValueError):
            return str(val)
        mapping = {
            1: "Normal",
            2: "Mirrored Horizontal",
            3: "Rotated 180°",
            4: "Mirrored Vertical",
            5: "Mirrored Horizontal & Rotated 270° CW",
            6: "Rotated 90° CW",
            7: "Mirrored Horizontal & Rotated 90° CW",
            8: "Rotated 270° CW",
        }
        return mapping.get(code, str(code))

    def _dataframe_to_txt(self, df: pd.DataFrame, directory: Any = None, hyperlinks: bool = False) -> str:
        """Renders a DataFrame as a Markdown table, using directory to create hyperlinks if hyperlinks is True."""

        def esc(v):
            if v is None:
                return ""
            try:
                # pd.isna returns array for list-like cells; guard truthiness
                na = pd.isna(v)
                if not hasattr(na, "__len__") and na:
                    return ""
            except (TypeError, ValueError):
                pass
            v = str(v)
            # Replacement rules, do not change order
            v = v.replace("\\", "\\\\")
            v = v.replace("|", "\\|")
            v = v.replace("\r\n", " ")
            v = v.replace("\n", " ")
            v = v.replace("\r", " ")
            return v

        lines = []
        fixed_columns = []
        columns = df.columns
        n = len(columns)
        for column in columns:
            fixed_columns.append(esc(column))
        fixed_columns = "|".join(fixed_columns)
        lines.append("|" + fixed_columns + "|")
        lines.append("|---" * n + "|")
        for _, row in df.iterrows():
            values = row.tolist()
            raw = values[0] if values else None
            for index, value in enumerate(values):
                values[index] = esc(value)
            if hyperlinks and directory is not None and isinstance(raw, str) and raw:
                url = (Path(directory) / raw).as_uri()
                values[0] = values[0].replace("[", "\\[").replace("]", "\\]")
                values[0] = f"[{values[0]}](<{url}>)"
            values = "|".join(values)
            values = "|" + values + "|"
            lines.append(values)
        return "\n".join(lines)

    @staticmethod
    def _parse_utc_offset(offset: Any) -> timedelta | None:
        """Parse EXIF/ISO UTC offsets ('Z', '±HH:MM', '±HHMM', '±HH') into a signed timedelta, or None."""
        if not isinstance(offset, str):
            return None
        s = offset.strip()
        if not s:
            return None
        if s.upper() == "Z":
            return timedelta(0)
        if s[0] not in ("+", "-"):
            return None
        sign = s[0]
        rest = s[1:]
        if ":" in rest:
            parts = rest.split(":")
            if len(parts) != 2:
                return None
            h_str, m_str = parts
            if len(h_str) not in (1, 2) or len(m_str) != 2:
                return None
        elif rest.isascii() and rest.isdigit():
            if len(rest) in (1, 2):
                h_str, m_str = rest, "00"
            elif len(rest) == 4:
                h_str, m_str = rest[:2], rest[2:]
            else:
                return None
        else:
            return None
        if not (h_str.isascii() and h_str.isdigit() and m_str.isascii() and m_str.isdigit()):
            return None
        hours, minutes = int(h_str), int(m_str)
        if hours > 23 or minutes > 59:
            return None
        td = timedelta(hours=hours, minutes=minutes)
        return -td if sign == "-" else td

    @staticmethod
    def _parse_exif_datetime(dt_value: Any) -> tuple[datetime | None, bool]:
        """Parse "YYYY:MM:DD HH:MM:SS" or "YYYY:MM:DD" and finally "YYYY:MM:DD HH:MM:SS.ffffff" to a datetime object, or None."""
        s = str(dt_value).strip()
        try:
            if " " in s:
                return datetime.strptime(s, "%Y:%m:%d %H:%M:%S"), True
            return datetime.strptime(s, "%Y:%m:%d"), False
        except ValueError:
            try:
                return datetime.strptime(s, "%Y:%m:%d %H:%M:%S.%f"), True
            except ValueError:
                return None, False

    def _format_gps_altitude(self, altitude: float | None, ref: str) -> str | None:
        """Turns GPS altitude rational into str."""
        altitude = self._rational_to_float(altitude)
        if altitude is not None and math.isfinite(altitude):
            if ref == "-":
                altitude *= -1.0
            return f"{altitude:.1f} m"
        return None

    def _format_gps_coord(self, dms_tuple: Any, ref: Any) -> str | None:
        """Turns a GPS degrees, minutes, seconds tuple to a string."""
        if isinstance(ref, bytes):
            try:
                ref = ref.decode("ascii")
            except UnicodeDecodeError:
                return None
        if not isinstance(ref, str):
            return None
        ref = ref.rstrip("\x00").strip().upper()
        if ref not in ("N", "S", "E", "W"):
            return None
        if not isinstance(dms_tuple, (tuple, list)) or len(dms_tuple) != 3:
            return None
        degree = self._rational_to_float(dms_tuple[0])
        minute = self._rational_to_float(dms_tuple[1])
        second = self._rational_to_float(dms_tuple[2])
        if degree is None or minute is None or second is None:
            return None
        if not all(math.isfinite(x) for x in (degree, minute, second)):
            return None
        converted = degree + minute / 60.0 + second / 3600.0
        if ref in ("S", "W"):
            converted = -converted
        return f"{converted:.6f}"

    # Sanitization Helpers
    # XML forbids control characters that sometimes are used as padding, so scrub them out.
    def _sanitize_for_excel(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans a dataframe of illegal characters and neutralizes Excel formula prefixes."""
        copy = df.copy()
        if copy.empty:
            return copy

        def _clean(v: Any, allow_negative_number: bool = False) -> Any:
            if not isinstance(v, str):
                return v
            v = XML_ILLEGAL_CHARS.sub("", v)
            if v.startswith(("=", "+", "-", "@", "\t", "\r")):
                if allow_negative_number and v.startswith("-") and self.is_number(v):
                    return v
                return "'" + v
            return v

        for col in copy.columns:
            current_col = copy[col]
            if current_col.dtype == object or pd.api.types.is_string_dtype(current_col):
                is_gps = col in ("GPS Latitude", "GPS Longitude")
                copy[col] = current_col.apply(lambda v, gps=is_gps: _clean(v, gps))
        return copy

    # For Sheet Names
    def verify_name(self, name: str, used: set[str]) -> str:
        illegal_chars = ("[", "]", ":", "*", "?", "/", "\\")  # Can't be in a sheet name
        for c in illegal_chars:
            name = name.replace(c, "_")  # Replace any instances with "_"
        # safety net; find_directories already trims to 31
        name = name[:SHEET_NAME_MAX_CHARS]  # Truncate to SHEET_NAME_MAX_CHARS (31) characters max
        # Excel restrictions: apostrophes at start/end, reserved name "History"
        if name.startswith("'") or name.endswith("'"):
            name = name.strip("'")
        if name.lower() == "history":
            name = "History_"
        if len(name) < 1:  # If no name, make default "Sheet"
            name = "Sheet"
        if name.lower() not in used:  # Check if used already, duplicate sheet names not allowed
            used.add(name.lower())
            return name
        f = 2
        while True:  # Name was used already
            suffix = "_" + str(f)  # Infinitely try increasing _X numbers, from 2
            candidate = name[: SHEET_NAME_MAX_CHARS - len(suffix)] + suffix  # Truncate original name
            if candidate.lower() not in used:
                used.add(candidate.lower())
                return candidate
            f += 1

    @staticmethod
    def _sanitize_for_filename(name: str, used: set[str]) -> str:
        """Sanitize a sheet name into a filesystem-safe filename stem."""
        illegal = ("<", ">", ":", '"', "/", "\\", "|", "?", "*")
        for c in illegal:
            name = name.replace(c, "_")
        name = name.rstrip(".")
        # Windows reserved names — case-insensitive, applies to the whole stem
        reserved = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }
        if name.upper() in reserved:
            name = "_" + name
        if not name:
            name = "_"
        if name.lower() not in used:  # Check if used already, duplicate filenames not allowed
            used.add(name.lower())
            return name[:255]  # Return if unused
        f = 2
        while True:  # Name was used already
            suffix = "_" + str(f)  # Infinitely try increasing _X numbers, from 2
            candidate = name[: 255 - len(suffix)] + suffix  # Truncate original name
            if candidate.lower() not in used:
                used.add(candidate.lower())
                return candidate
            f += 1

    # For filenames
    def clean_name(self, name: str) -> str:
        """Sanitize a user-typed filename and force its extension to match filetype_var."""
        # Trim whitespace and trailing dots (Windows strips trailing dots silently)
        name = name.strip().rstrip(".")
        # Check if anything useful survives stripping
        # Fall back if the user typed only illegal chars or spaces
        if not any(c.isalnum() for c in name):
            name = "output"
        # A name that is nothing but an extension (".xlsx") has no stem.
        # pathlib reports no suffix for dotfiles, so the parse below would
        # put the extension in both stem and ext. Normalize it first.
        stripped = name.lstrip(".")
        if name.startswith(".") and ("." + stripped.lower()) in self.extensions:
            name = "output." + stripped
        illegal_chars = ("<", ">", ":", '"', "/", "\\", "|", "?", "*")
        for c in illegal_chars:
            name = name.replace(c, "_")
        # Split extension once so reserved-name and length checks see the stem.
        suffix = Path(name).suffix.lower()
        selected = self.filetype_var.get()
        selected = self.filetype_to_ext[selected]
        if selected == suffix:
            stem = name[: -len(suffix)]
            ext = name[-len(suffix) :]
        elif suffix in self.extensions:
            ext = selected
            stem = name[: -len(suffix)]
        else:  # No valid filetype suffix
            ext = selected
            stem = name
        if not any(c.isalnum() for c in stem):
            stem = "output"
        # Windows reserved names — check the stem, not the full name
        reserved = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }
        if stem.upper() in reserved:
            stem = "_" + stem

        # Truncate overly long stems — Windows paths cap at ~260 chars total,
        # and the output directory path also consumes space.
        MAX_STEM = 200
        if len(stem) > MAX_STEM:
            stem = stem[:MAX_STEM]

        # Reassemble with the extension the user provided (or .xlsx if none)
        return stem + ext

    # Main-thread setter for total_files (queued via root.after from worker)
    def _set_total_files(self, count: int, started_at: float | None = None) -> None:
        """Reset progress state and start the ETA clock."""
        self.time_started = started_at if started_at is not None else time.perf_counter()
        self.total_files = count
        self.scanned_count.set(f"Scanned: 0 / {count}")
        if count > 0:
            self.percentage_done.set("0%")
            self.progress_var.set(0)

    # Updates the progress bar
    def update_progress(self, processed: int, skipped: int, current_dir: Path, timestamp: float | None = None) -> None:
        """Recompute progress, ETA, and elapsed time from the worker's per-file callback."""
        if not self.cancel_event.is_set():
            if self.time_started is not None:
                files_done = processed + skipped
                if timestamp is not None:
                    time_passed = max(0.0, timestamp - self.time_started)  # Given in seconds, float
                else:
                    time_passed = 0.0
                remaining = self.total_files - files_done
                if time_passed > 0 and files_done >= 10 and remaining > 0:
                    seconds_per_files = time_passed / files_done
                    self.eta.set(f"{self._convert_seconds(remaining * seconds_per_files, 'ETA')}")
                else:
                    self.eta.set("Estimating...")
                self.elapsed_time.set(f"Time Elapsed: {self._convert_seconds(time_passed, 'Time Elapsed')}")
            self.skipped_count.set(f"Skipped: {skipped}")
            if self.total_files > 0:  # No divide-by-zero errors
                done = min(processed + skipped, self.total_files)
                self.percentage_done.set(f"{round((done / self.total_files) * 100, 1)}%")
                self.progress_var.set(round((done / self.total_files) * 100, 1))
                self.scanned_count.set(f"Scanned: {done} / {self.total_files}")  # ← changed
            else:
                self.percentage_done.set("0%")
                self.progress_var.set(0)
            self.current_directory.set(str(current_dir)[-30:])  # Truncate to not be too long, last 30 characters

    def _refresh_window(self) -> None:
        if self.root is not None:
            self.root.update_idletasks()
            self.root.geometry(f"{self.root.winfo_reqwidth()}x{self.root.winfo_reqheight()}")

    # Starts the worker thread (called from main thread)
    def _start_scan(self, cfg: ScanConfig) -> None:
        """Sets _cleanup_pending, flip button states, spawns scan worker."""
        # Cleanup must run after this
        self._cleanup_pending = True
        self.execute_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.set_directory_button.config(state="disabled")
        self.set_output_button.config(state="disabled")
        self.reset_settings_button.config(state="disabled")
        threading.Thread(
            target=self._run_scan_threaded,
            args=(cfg,),
            daemon=True,  # If abruptly killed, don't wait on thread
        ).start()

    # Runs the scan on a thread
    def _run_scan_threaded(self, cfg: ScanConfig) -> None:
        """Worker-thread: count files, scan, then queue cleanup on the main thread."""

        def _on_progress(p: int, s: int, d: Path) -> None:
            """Capture timestamp, then queue update_progress on the main thread."""
            # Runs on worker thread — capture timestamp NOW so main-thread
            # scheduling delay doesn't distort the ETA average.
            t = time.perf_counter()
            if not self._destroyed:
                self._safe_after(lambda: self.update_progress(p, s, d, t))

        try:
            scan_dir = cfg.directory_path if cfg.directory_path is not None else self.directory_path
            if scan_dir is None:
                self.collected_warnings["Directory Error"].append("No root directory.")
                return
            self.find_directories(
                scan_dir,
                cfg.modifier,
                cfg.cutoff,
                cfg.output_utc,
                cfg.output_dimensions,
                cfg.output_filesize,
                cfg.output_make,
                cfg.output_model,
                cfg.output_software,
                cfg.output_lens_model,
                cfg.output_aperture,
                cfg.output_exposure_time,
                cfg.output_focal_length,
                cfg.output_iso,
                cfg.output_orientation,
                cfg.output_gps,
                cfg.output_gps_altitude,
                cfg.output_video_rows,
                cfg.include_hiddens,
                cfg.include_undateable,
                cfg.media_filter,
                cfg.date_range,
                cfg.date_format,
                cfg.time_format,
                cfg.start_date,
                cfg.end_date,
                progress_callback=_on_progress,
            )
        except Exception as e:  # noqa: BLE001
            self.collected_warnings["Unexpected"].append(f"{e}\n{traceback.format_exc()}")
        finally:  # Always clean up
            if not self._destroyed:
                self._safe_after(
                    self._clean_up,
                    cfg.final_output,
                    self.total_processed,
                    self.total_skipped,
                    cfg.output_summary,
                    cfg.date_format,
                )

    # Clean up and create sheet
    def _clean_up(
        self,
        final_output: Path,
        processed: int,
        skipped: int,
        output_summary: bool = False,
        date_format: str = "%m/%d/%Y",
    ) -> None:
        """Calls create_sheet and flips button states."""
        # Guard so a queued _clean_up can't fire twice (e.g. through nested dialogs)
        if not self._cleanup_pending or self._destroyed:
            return
        self._cleanup_pending = False
        cancelled = self.cancel_event.is_set()
        try:
            if not cancelled:
                self.create_sheet(final_output, processed, skipped, date_format, output_summary)
        except Exception as e:  # noqa: BLE001
            self.collected_warnings["Unexpected"].append(f"_clean_up/create_sheet: {e}\n{traceback.format_exc()}")
        finally:
            if not self._destroyed:
                self.eta.set("Done")
                self.execute_button.config(state="normal")
                self.cancel_button.config(state="disabled")
                self.set_directory_button.config(state="normal")
                self.set_output_button.config(state="normal")
                self.reset_settings_button.config(state="normal")
                self._active_filetype = None
                cancelled = self.cancel_event.is_set()
                if cancelled:
                    self.current_directory.set("Cancelled")
                    self.percentage_done.set("Cancelled")

    # Closing behavior
    def _on_close(self) -> None:
        """Saves settings and closes program."""
        if self._destroyed or self._headless or self.root is None:
            return
        self._destroyed = True
        self.cancel_event.set()
        self._save_settings()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # To clean up any past executions
    def reset(self) -> None:
        """Cleans up past executions and resets variables."""
        self.used = set()
        self.results.clear()
        self.collected_warnings.clear()
        self.current_sheet_name = "Sheet"
        self.current_directory.set("")
        self.total_files = 0
        self.total_processed = 0
        self.total_skipped = 0
        self.scanned_count.set("Scanned: 0 / …")
        self.skipped_count.set("Skipped: 0")
        self.percentage_done.set("0%")
        self.progress_var.set(0)
        self.eta.set("Estimating...")
        self.elapsed_time.set("Time Elapsed: ...")
        self.time_started = None
        self.last_warnings_log = None
        self.view_log_button.config(state="disabled")
        self._cleanup_pending = False

    def reset_settings(self) -> None:
        """Reset all settings to default by deleting SETTINGS_PATH."""
        if messagebox.askyesno("Reset Settings?", "Reset all settings to defaults and clear saved preferences?"):
            try:
                SETTINGS_PATH.unlink(missing_ok=True)
                self.directory_path = None
                self.output_path = None
                self.maxdepth = 0
                self.sort_method = "Timestamp"
                self._update_path_labels()
                self.hyperlink_var.set(True)
                self.include_undateable_var.set(True)
                for var in [
                    self.keepopen_var,
                    self.open_folder_var,
                    self.recursive_var,
                    self.summary_var,
                    self.video_rows_var,
                    self.hidden_var,
                    self.utc_var,
                    self.gps_var,
                    self.gps_altitude_var,
                    self.date_range_var,
                    self.extra_exif_var,
                    self.dimensions_var,
                    self.filesize_var,
                    self.make_var,
                    self.model_var,
                    self.software_var,
                    self.lens_model_var,
                    self.aperture_var,
                    self.exposure_time_var,
                    self.focal_length_var,
                    self.iso_var,
                    self.orientation_var,
                    self.debug_var,
                ]:
                    var.set(False)
                self.filetype_var.set("Excel")
                self.user_mode_var.set("Basic")
                self.sort_methods_var.set("Timestamp")
                self.media_filter_combobox.set("All Media")
                self.date_format_combobox.set("MM/DD/YYYY")
                self.time_format_combobox.set("24-Hour (HH:MM:SS)")
                self.start_date_entry.set_date(None)
                self.end_date_entry.set_date(None)
                for entry in [self.name_entry, self.modifier_entry, self.maxdepth_entry, self.burst_cutoff_entry]:
                    entry.delete(0, "end")
                    entry.config(foreground="gray")
                self.name_entry.insert(0, "Filename (default output.filetype)")
                self.modifier_entry.insert(0, "Starting index (Img # Series)")
                self.maxdepth_entry.insert(0, "Recursion Depth (#)")
                self.burst_cutoff_entry.insert(0, "Photo grouping cutoff (default 2 seconds)")
                self.recursive_input()
                self.gps_warning()
                self.date_range()
                self.extra_exif()
                self.user_mode()
            except OSError:
                self._notify_error(
                    "Setting Reset Failed", f"{SETTINGS_PATH} couldn't be removed. Manual removal may work."
                )

    def _clear_scan_cache(self) -> None:
        """Clears _photo_cache, _video_cache, and _scan_cache_flags."""
        self._photo_cache = None
        self._video_cache = None
        self._scan_cache_flags = None

    # Runs on "Cancel" button press
    def cancel(self) -> None:
        """Sets cancel_event and changes progress bar information."""
        self.cancel_event.set()
        self.cancel_button.config(state="disabled")
        self.current_directory.set("Cancelling...")
        self.percentage_done.set("Cancelling...")

    # Creates empty dict for data to fill
    def _empty_scan_data(self) -> dict:
        """Creates empty "data" dataframe for scans."""
        return {
            "Dates": [],
            "Images": [],
            "Offsets": [],
            "Dimensions": [],
            "Filesizes": [],
            "Makes": [],
            "Models": [],
            "Softwares": [],
            "Lens_Models": [],
            "Times": [],
            "Apertures": [],
            "Exposure_Times": [],
            "Focal_Lengths": [],
            "ISOs": [],
            "GPS_Latitudes": [],
            "GPS_Longitudes": [],
            "GPS_Altitudes": [],
            "Sort_Timestamps": [],
            "Orientations": [],
        }

    # Saves settings to a JSON file at SETTINGS_PATH
    def _save_settings(self) -> None:
        """Attempts to save all settings in JSON format at SETTINGS_PATH."""
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            # Don't add debug_var to settings persistence
            start = self.start_date_entry.get_date()
            end = self.end_date_entry.get_date()
            cutoff_text = self.burst_cutoff_entry.get().strip()
            cutoff_entry = None
            if self.is_number(cutoff_text):
                parsed = float(cutoff_text)
                if math.isfinite(parsed) and parsed >= 0:
                    cutoff_entry = parsed
            md_text = self.maxdepth_entry.get().strip()
            # Implicitly takes care of "Recursion Depth (#)" default case
            md_value = int(md_text) if md_text.isascii() and md_text.isdigit() and int(md_text) > 0 else None
            settings = {
                "Directory Path": self.directory_path.as_posix() if self.directory_path else None,
                "Output Path": self.output_path.as_posix() if self.output_path else None,
                "Filetype": self.filetype_var.get(),
                "Start Date": start.isoformat() if start else None,
                "End Date": end.isoformat() if end else None,
                "File Name": (
                    self.name_entry.get().strip()
                    if self.name_entry.get().strip() != "Filename (default output.filetype)"
                    and self.name_entry.get().strip() != ""
                    else None
                ),
                "Modifier": (
                    self.modifier_entry.get().strip()
                    if self.modifier_entry.get().strip() != "Starting index (Img # Series)"
                    and self.modifier_entry.get().strip() != ""
                    else None
                ),
                "Max Depth": (md_value),
                "Keep Open": self.keepopen_var.get(),
                "Recursive": self.recursive_var.get(),
                "UTC": self.utc_var.get(),
                "Hyperlinks": self.hyperlink_var.get(),
                "Date Range": self.date_range_var.get(),
                "Extra EXIF": self.extra_exif_var.get(),
                "Dimensions": self.dimensions_var.get(),
                "Make": self.make_var.get(),
                "Model": self.model_var.get(),
                "Software": self.software_var.get(),
                "Lens Model": self.lens_model_var.get(),
                "Aperture": self.aperture_var.get(),
                "Exposure Time": self.exposure_time_var.get(),
                "Focal Length": self.focal_length_var.get(),
                "ISO": self.iso_var.get(),
                "Orientation": self.orientation_var.get(),
                "GPS": self.gps_var.get(),
                "GPS Altitude": self.gps_altitude_var.get(),
                "Include Hiddens": self.hidden_var.get(),
                "Sort Method": self.sort_methods_var.get(),
                "User Mode": self.user_mode_var.get(),
                "Burst Cutoff": cutoff_entry,
                "Include Undateable": self.include_undateable_var.get(),
                "Auto-Open Output": self.open_folder_var.get(),
                "Filesize": self.filesize_var.get(),
                "Video Rows": self.video_rows_var.get(),
                "Summary": self.summary_var.get(),
                "Date Format": self.date_format_var.get(),
                "Time Format": self.time_format_var.get(),
            }
            SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        except (OSError, ValueError, TypeError, AttributeError, tk.TclError):
            try:
                self._notify_error("Setting Save Error", message=f"Your settings could not be saved at {SETTINGS_PATH}")
            except tk.TclError:
                pass

    # Loads settings from JSON at SETTINGS_PATH
    def _load_settings(self) -> None:
        """Attempts to load settings from SETTINGS_PATH."""
        try:
            key_to_checkbox_var = {
                "Date Range": self.date_range_var,
                "UTC": self.utc_var,
                "Keep Open": self.keepopen_var,
                "Recursive": self.recursive_var,
                "Hyperlinks": self.hyperlink_var,
                "Extra EXIF": self.extra_exif_var,
                "Dimensions": self.dimensions_var,
                "Make": self.make_var,
                "Model": self.model_var,
                "Software": self.software_var,
                "Lens Model": self.lens_model_var,
                "Aperture": self.aperture_var,
                "Exposure Time": self.exposure_time_var,
                "Focal Length": self.focal_length_var,
                "ISO": self.iso_var,
                "GPS": self.gps_var,
                "GPS Altitude": self.gps_altitude_var,
                "Include Hiddens": self.hidden_var,
                "Include Undateable": self.include_undateable_var,
                "Auto-Open Output": self.open_folder_var,
                "Filesize": self.filesize_var,
                "Video Rows": self.video_rows_var,
                "Summary": self.summary_var,
                "Orientation": self.orientation_var,
            }
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            for key, value in data.items():
                try:
                    if value is not None:
                        if key == "Directory Path":
                            if Path(value).is_dir():
                                self.directory_path = Path(value)
                        elif key == "Output Path":
                            if Path(value).is_dir():
                                self.output_path = Path(value)
                        elif key == "Filetype":
                            if value in self.filetypes:
                                self.filetype_var.set(value)
                        elif key == "Start Date":
                            self.start_date_entry.set_date(date.fromisoformat(value))
                        elif key == "End Date":
                            self.end_date_entry.set_date(date.fromisoformat(value))
                        elif key == "File Name":
                            self.name_entry.delete(0, "end")
                            self.name_entry.insert(0, value)
                            self.name_entry.config(foreground="black")
                        elif key == "Modifier":
                            self.modifier_entry.delete(0, "end")
                            self.modifier_entry.insert(0, value)
                            self.modifier_entry.config(foreground="black")
                        elif key == "Max Depth":
                            if isinstance(value, bool):
                                value = None
                            elif isinstance(value, float) and value.is_integer():
                                value = int(value)
                            if isinstance(value, int) and int(value) > 0:
                                self.maxdepth_entry.delete(0, "end")
                                self.maxdepth_entry.insert(0, str(value))
                                self.maxdepth = int(value)
                                self.maxdepth_entry.config(foreground="black")
                            else:
                                self.maxdepth_entry.delete(0, "end")
                                self.maxdepth_entry.insert(0, "Recursion Depth (#)")
                                self.maxdepth_entry.config(foreground="gray")
                                self.maxdepth = 0
                        elif key == "Sort Method":
                            if value in self.sort_methods:
                                self.sort_methods_var.set(value)
                        elif key == "User Mode":
                            if value in self.user_modes:
                                self.user_mode_var.set(value)
                        elif key == "Burst Cutoff":
                            if isinstance(value, bool):
                                value = None
                            if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
                                self.burst_cutoff_entry.delete(0, "end")
                                self.burst_cutoff_entry.insert(0, str(value))
                                self.burst_cutoff_entry.config(foreground="black")
                            else:
                                self.burst_cutoff_entry.delete(0, "end")
                                self.burst_cutoff_entry.insert(0, "Photo grouping cutoff (default 2 seconds)")
                                self.burst_cutoff_entry.config(foreground="gray")
                        elif key == "Date Format":
                            if value in self.date_formats:
                                self.date_format_combobox.set(value)
                        elif key == "Time Format":
                            if value in self.time_formats:
                                self.time_format_combobox.set(value)
                        elif key in key_to_checkbox_var and isinstance(value, bool):
                            key_to_checkbox_var[key].set(value)
                        elif key in key_to_checkbox_var:  # Value not a boolean
                            key_to_checkbox_var[key].set(False)
                    # Explicit null in the file means "this field was cleared"
                    else:
                        if key == "Start Date":
                            self.start_date_entry.set_date(None)
                        elif key == "End Date":
                            self.end_date_entry.set_date(None)
                        elif key == "Directory Path":
                            self.directory_path = None
                        elif key == "Output Path":
                            self.output_path = None
                        elif key == "Max Depth":
                            self.maxdepth_entry.delete(0, "end")
                            self.maxdepth_entry.insert(0, "Recursion Depth (#)")
                            self.maxdepth_entry.config(foreground="gray")
                            self.maxdepth = 0
                        elif key in key_to_checkbox_var:
                            key_to_checkbox_var[key].set(False)
                except (ValueError, TypeError):
                    pass
            self._update_path_labels()
        except (OSError, json.JSONDecodeError, AttributeError):
            return

    @staticmethod
    def _open_path(path: Path, open_parent: bool) -> None:
        """Opens a directory in the OS file explorer safely."""
        try:
            if open_parent and not path.is_dir():
                path = path.parent
            if not path.exists():
                return
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                import subprocess

                subprocess.Popen(["open", str(path)])
            else:
                import subprocess

                subprocess.Popen(["xdg-open", str(path)])
        except OSError:
            pass

    # Core Functions
    # Gets called on set directory button press to set image directory
    def set_dir(self) -> None:
        """Opens a filedialog to set the root directory of a scan."""
        selected = filedialog.askdirectory(title="Select a Directory")
        if selected:
            self.directory_path = Path(selected)
        self._update_path_labels()

    # Gets called on set output button press
    def set_output(self) -> None:
        """Opens a filedialog to set the output directory of a scan."""
        selected = filedialog.askdirectory(title="Select a Output Directory")
        if selected:
            self.output_path = Path(selected)
        self._update_path_labels()

    # Checks if given file is hidden
    def _check_hidden(self, filename: str, directory: str, include_hiddens: bool) -> bool:
        """Checks if a file is hidden if include_hiddens is False, based on leading period "." and file attributes."""
        if include_hiddens:
            return False
        filepath = Path(directory) / filename
        if filepath.name.startswith("."):
            return True
        try:
            st = os.stat(filepath)
        except OSError:
            return False
        if os.name == "nt":
            file_attrs = getattr(st, "st_file_attributes", 0)
            return bool(file_attrs & getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 0))
        st_flags = getattr(st, "st_flags", 0)
        return bool(st_flags & getattr(stat, "UF_HIDDEN", 0))

    # Image metadata extractor helper function
    def scan_image(
        self,
        directory_path: str,
        filename: str,
        data: dict,
        output_utc: bool = False,
        output_dimensions: bool = False,
        output_filesize: bool = False,
        output_make: bool = False,
        output_model: bool = False,
        output_software: bool = False,
        output_lens_model: bool = False,
        output_aperture: bool = False,
        output_exposure_time: bool = False,
        output_focal_length: bool = False,
        output_iso: bool = False,
        output_orientation: bool = False,
        output_gps: bool = False,
        output_gps_altitude: bool = False,
    ) -> bool:
        """Extracts EXIF metadata from an image file and appends each to a key in the "data" dict. Returns True on success."""
        flags = (
            output_utc,
            output_dimensions,
            output_filesize,
            output_make,
            output_model,
            output_software,
            output_lens_model,
            output_aperture,
            output_exposure_time,
            output_focal_length,
            output_iso,
            output_orientation,
            output_gps,
            output_gps_altitude,
        )
        path = Path(directory_path) / filename
        entry = None
        if self._photo_cache is not None and self._scan_cache_flags == flags:
            entry = self._photo_cache.pop(path, None)
        if entry is None:
            entry = self._read_photo_entry(path, flags)
        _, _, _, fields, err = entry
        if err is not None or fields is None:
            self.collected_warnings["Scan Error"].append(f"{path.as_posix()}: {err}")
            return False
        else:
            data["Images"].append(filename)
            for key, value in fields.items():
                data[key].append(value)
            return True

    # Hyperlink addition
    def add_hyperlinks(self, excel_file: str, summary_sheet_name: str | None = None) -> None:
        """Adds hyperlinks to Excel files in the first collumn of each sheet."""
        try:
            wb = openpyxl.load_workbook(excel_file)
            for sheet_df, sheet_name, directory in self.results:
                if not directory:
                    continue
                try:
                    ws = wb[sheet_name]
                    for filename, cell in zip(sheet_df["Files"], ws["A"][1:]):
                        if not isinstance(filename, str) or not filename:
                            continue
                        cell.hyperlink = (Path(directory) / filename).as_uri()
                        cell.font = Font(color="0563C1", underline="single")
                except Exception as e:  # noqa: BLE001
                    self.collected_warnings["Hyperlink Error"].append(sheet_name + f"\nError: {e}")
            try:
                if summary_sheet_name and summary_sheet_name in wb.sheetnames:
                    for (_, _, directory), cell in zip(self.results, wb[summary_sheet_name]["B"]):
                        if not directory:
                            continue
                        cell.hyperlink = Path(directory).as_uri()
                        cell.font = Font(color="0563C1", underline="single")
            except Exception as e:  # noqa: BLE001
                self.collected_warnings["Hyperlink Error"].append(
                    (summary_sheet_name or "Summary Sheet") + f"\nError: {e}"
                )
            wb.save(excel_file)
        except Exception as e:  # noqa: BLE001
            self.collected_warnings["Hyperlink Error"].append(f"Hyperlinks could not be added. \nError: {e}")

    # Finds subdirectories for recursive mode
    def find_directories(
        self,
        directory_path: Path,
        modifier: int,
        cutoff: float,
        output_utc: bool = False,
        output_dimensions: bool = False,
        output_filesize: bool = False,
        output_make: bool = False,
        output_model: bool = False,
        output_software: bool = False,
        output_lens_model: bool = False,
        output_aperture: bool = False,
        output_exposure_time: bool = False,
        output_focal_length: bool = False,
        output_iso: bool = False,
        output_orientation: bool = False,
        output_gps: bool = False,
        output_gps_altitude: bool = False,
        output_video_rows: bool = False,
        include_hiddens: bool = False,
        include_undateable: bool = False,
        media_filter: str = "All Media",
        date_range: bool = False,
        date_format: str = "%m/%d/%Y",
        time_format: str = "%H:%M:%S",
        start_date: date | None = None,
        end_date: date | None = None,
        progress_callback: Callable[[int, int, Path], None] | None = None,
    ) -> tuple[int, int]:
        """Lists subdirectories in recursive mode (single-folder has no subdirectories), runs sort_and_extract on both modes. Builds progress_callback and sheet_name."""
        try:
            sheet_names = []
            files_lists = []
            directories = []
            self._photo_cache = {}
            self._video_cache = {}
            self._scan_cache_flags = (
                output_utc,
                output_dimensions,
                output_filesize,
                output_make,
                output_model,
                output_software,
                output_lens_model,
                output_aperture,
                output_exposure_time,
                output_focal_length,
                output_iso,
                output_orientation,
                output_gps,
                output_gps_altitude,
            )
            file_count = 0
            if not self._destroyed:
                self._safe_after(self.current_directory.set, "Counting files...")
            for dirpath, _, files in self.walk_and_filter(
                directory_path,
                self.maxdepth,
                include_hiddens,
                date_range,
                start_date,
                end_date,
                include_undateable,
                media_filter,
            ):
                if self.cancel_event.is_set():
                    break
                if not files:
                    continue
                if (
                    not any(f.lower().endswith(PHOTO_TYPES) for f in files)
                    and not output_video_rows
                    and media_filter != "Videos Only"
                ):
                    # All-videos folder produces nothing — bail early
                    self.collected_warnings["Only Video(s)"].append(dirpath)
                    continue
                dirpath = Path(dirpath)
                try:
                    rel = Path(os.path.relpath(dirpath, directory_path))
                except ValueError:
                    self.collected_warnings["Directory Error"].append(str(dirpath))
                    continue
                sheet_name = "_".join(rel.parts)
                if not output_video_rows:
                    file_count += sum(1 for entry in files if entry.lower().endswith(PHOTO_TYPES))
                else:
                    file_count += sum(1 for entry in files if entry.lower().endswith(PHOTO_TYPES + VIDEO_TYPES))
                files_lists.append(files)
                sheet_names.append(sheet_name)
                directories.append(dirpath.as_posix())
            scan_started = time.perf_counter()
            if not self.cancel_event.is_set():
                self._safe_after(self._set_total_files, file_count, scan_started)
            for directory, media_files, sheet_name in zip(directories, files_lists, sheet_names):
                if self.cancel_event.is_set():
                    break
                self.current_sheet_name = sheet_name
                if progress_callback:
                    _base_p = self.total_processed
                    _base_s = self.total_skipped
                    wrapped_cb = lambda p, s, d, base_p=_base_p, base_s=_base_s: progress_callback(
                        base_p + p, base_s + s, d
                    )
                else:
                    wrapped_cb = None
                p, s = self.extract(
                    directory,
                    modifier,
                    media_files,
                    cutoff,
                    output_utc,
                    output_dimensions,
                    output_filesize,
                    output_make,
                    output_model,
                    output_software,
                    output_lens_model,
                    output_aperture,
                    output_exposure_time,
                    output_focal_length,
                    output_iso,
                    output_orientation,
                    output_gps,
                    output_gps_altitude,
                    output_video_rows,
                    date_format,
                    time_format,
                    progress_callback=wrapped_cb,
                )
                self.total_processed += p
                self.total_skipped += s
            return self.total_processed, self.total_skipped
        finally:
            self._clear_scan_cache()

    # Helper to find directories one-by-one to max_depth
    def walk_and_filter(
        self,
        root_dir: Path,
        max_depth: int,
        include_hiddens: bool,
        date_range: bool = False,
        start_date: date | None = None,
        end_date: date | None = None,
        include_undateable: bool = True,
        media_filter: str = "All Media",
    ) -> Iterator[tuple[str, list[str], list[str]]]:
        """Yields subdirectories one-by-one with os.walk to max_depth, while filtering based on include_hiddens, sorting using natural_key"""
        # Normalize the path and count baseline separators
        root_str = os.path.abspath(root_dir)
        baseline_depth = len(Path(root_str).parts)

        for dirpath, dirs, media_files in os.walk(
            root_str, topdown=True, followlinks=False
        ):  # Symlinked directories ignored
            # Calculate current depth relative to root_dir
            current_depth = len(Path(dirpath).parts) - baseline_depth
            if current_depth >= max_depth:
                del dirs[:]
            dirs[:] = [
                d
                for d in dirs
                if d.lower() not in {"system volume information", "$recycle.bin"}
                and not self._check_hidden(d, dirpath, include_hiddens)
            ]
            dirs.sort(key=lambda x: self.natural_key(x))
            if media_filter == "Photos Only":
                kept_filetypes = PHOTO_TYPES
            elif media_filter == "Videos Only":
                kept_filetypes = VIDEO_TYPES
            elif media_filter == "RAW Only":
                kept_filetypes = RAW_TYPES
            else:
                kept_filetypes = PHOTO_TYPES + VIDEO_TYPES
            # Symlinked files included for media_files, not directories
            media_files = [
                f
                for f in media_files
                if not self._check_hidden(f, dirpath, include_hiddens) and f.lower().endswith(kept_filetypes)
            ]
            # Sorts files alphabetically, ignoring file extensions and capitalization, ignoring any non-photo or non-video files
            media_files.sort(
                key=lambda x: (
                    self.natural_key(os.path.splitext(x)[0]),
                    0 if x.lower().endswith(PHOTO_TYPES) else 1,
                )
            )
            if date_range:
                media_files = self._filter_by_date(dirpath, media_files, start_date, end_date, include_undateable)
            yield dirpath, dirs, media_files

    # Initial function; runs on "Execute" button press
    def initialize(self) -> None:
        """Sets scan flags, builds configuration and starts scan."""
        modifier = 0  # For starting index of img_series
        user_mode = self.user_mode_var.get()
        filetype = self.filetype_var.get()  # CSV or Excel
        recursive = self.recursive_var.get()  # Get status of recursive_checkbox
        directory_path = self.directory_path
        debug = False
        output_summary = self.summary_var.get()
        output_utc = False
        date_range = False
        output_gps = False
        output_gps_altitude = False
        output_video_rows = False
        include_hiddens = False
        include_undateable = False
        output_dimensions = False
        output_filesize = False
        output_make = False
        output_model = False
        output_software = False
        output_lens_model = False
        output_aperture = False
        output_exposure_time = False
        output_focal_length = False
        output_iso = False
        output_orientation = False
        start_date = None
        end_date = None
        date_format = self.date_format_combobox.get() if user_mode == "Advanced" else "MM/DD/YYYY"
        date_formats_dict = {"MM/DD/YYYY": "%m/%d/%Y", "YYYY-MM-DD": "%Y-%m-%d", "DD/MM/YYYY": "%d/%m/%Y"}
        date_format = date_formats_dict.get(date_format, "%m/%d/%Y")  # Convert to python format string
        time_format = self.time_format_combobox.get() if user_mode == "Advanced" else "24-Hour (HH:MM:SS)"
        time_formats_dict = {"24-Hour (HH:MM:SS)": "%H:%M:%S", "12-Hour (hh:mm:ss AM/PM)": "%I:%M:%S %p"}
        time_format = time_formats_dict.get(time_format, "%H:%M:%S")
        media_filter = self.media_filter_var.get() if user_mode == "Advanced" else "All Media"
        self.sort_method = self.sort_methods_var.get() if user_mode == "Advanced" else "Timestamp"
        if user_mode == "Advanced":
            debug = self.debug_var.get()
            output_utc = self.utc_var.get()
            date_range = self.date_range_var.get()
            output_gps = self.gps_var.get()
            if output_gps:
                output_gps_altitude = self.gps_altitude_var.get()
            include_hiddens = self.hidden_var.get()
            val = self.modifier_entry.get().strip()
            output_video_rows = self.video_rows_var.get()
            if media_filter == "Videos Only":
                output_video_rows = True
            if val == "Starting index (Img # Series)" or val == "":
                modifier = 0
            elif val.isascii() and val.isdigit() and int(val) > 0:
                modifier = int(val) - 1
            else:
                self._notify_error("Numbers only.", message="Starting index must be a whole number greater than zero.")
                return
            if self.extra_exif_var.get():
                output_dimensions = self.dimensions_var.get()
                output_filesize = self.filesize_var.get()
                output_make = self.make_var.get()
                output_model = self.model_var.get()
                output_software = self.software_var.get()
                output_lens_model = self.lens_model_var.get()
                output_aperture = self.aperture_var.get()
                output_exposure_time = self.exposure_time_var.get()
                output_focal_length = self.focal_length_var.get()
                output_iso = self.iso_var.get()
                output_orientation = self.orientation_var.get()
            if date_range:
                include_undateable = self.include_undateable_var.get()
                start_date = self.start_date_entry.get_date()
                end_date = self.end_date_entry.get_date()
                if not (start_date or end_date):
                    self._notify_info(
                        "Date Range Unset",
                        message="Date Range is checked, but no date(s) were input. Proceeding without.",
                    )
                    self.date_range_var.set(False)
                    date_range = False
                    self.date_range()
                else:
                    if start_date and end_date and start_date > end_date:
                        self._notify_error("Invalid range", "Start date must be on or before end date.")
                        return
        if debug:  # Debug writes to ~/Downloads, but doesn't overwrite the user's saved setting
            effective_output = Path.home() / "Downloads"
        else:
            effective_output = self.output_path
            if effective_output is None:
                self._notify_info("No output path.", message="No output path was set, and debug is not checked.")
                return
        if directory_path is None:  # Validating paths
            self._notify_error(  # If no output/directory path was set, error to allow for changes
                "Image directory not set.", message="Please set an image/video directory path."
            )
            return
        if recursive:  # Get maxdepth entry
            val = self.maxdepth_entry.get().strip()
            if val.isascii() and val.isdigit() and int(val) > 0:  # Make sure starting index is valid digit
                self.maxdepth = int(val)  # We start at 1 by default
            elif val == "Recursion Depth (#)" or val == "":  # Placeholder or empty is rejected.
                self._notify_info(
                    "Recursion Depth not set.", message="Recursion Depth not set, defaulting to 1 subfolder."
                )
                self.maxdepth = 1
            else:
                self._notify_error("Numbers only.", message="Recursion Depth must be a whole number greater than zero.")
                return
        else:
            self.maxdepth = 0
        if (
            filetype == "CSV" or filetype == "JSON"
        ) and self.hyperlink_var.get():  # CSV and JSON don't have hyperlinks, ask if they want to continue or change options
            proceed = messagebox.askyesno(
                "Hyperlinks Unsupported.",
                message="Hyperlinks are Excel/Markdown only. Please select Excel/Markdown for hyperlinks. Proceed without?",
            )
            if not proceed:
                return
        cutoff_text = self.burst_cutoff_entry.get().strip()
        if cutoff_text == "" or cutoff_text == "Photo grouping cutoff (default 2 seconds)":
            cutoff = 2.0
        elif self.is_number(cutoff_text):
            cutoff = float(cutoff_text)
            if not math.isfinite(cutoff) or cutoff < 0:
                self._notify_error("Invalid cutoff.", message="Burst cutoff must be a non-negative finite number.")
                return
        else:
            self._notify_error("Numbers only.", message="Burst cutoff must be a number.")
            return
        name = self.name_entry.get().strip()
        if name and name != "Filename (default output.filetype)":
            final_output = effective_output / self.clean_name(name)
        else:
            ext = self.filetype_to_ext[filetype]
            final_output = effective_output / f"output{ext}"  # Default filename
        cfg = ScanConfig(
            directory_path=directory_path,
            filetype=filetype,
            final_output=final_output,
            modifier=modifier,
            cutoff=cutoff,
            output_summary=output_summary,
            output_utc=output_utc,
            output_dimensions=output_dimensions,
            output_filesize=output_filesize,
            output_make=output_make,
            output_model=output_model,
            output_software=output_software,
            output_lens_model=output_lens_model,
            output_aperture=output_aperture,
            output_exposure_time=output_exposure_time,
            output_focal_length=output_focal_length,
            output_iso=output_iso,
            output_orientation=output_orientation,
            output_gps=output_gps,
            output_gps_altitude=output_gps_altitude,
            output_video_rows=output_video_rows,
            date_range=date_range,
            date_format=date_format,
            time_format=time_format,
            start_date=start_date,
            end_date=end_date,
            include_hiddens=include_hiddens,
            include_undateable=include_undateable,
            media_filter=media_filter,
        )
        if (
            (filetype == "CSV" or filetype == "Markdown")
            and recursive
            and not messagebox.askyesno(
                f"Multiple {filetype} Files",
                message=f"Recursive mode on {filetype} output will create multiple {filetype} files, one for each valid folder. Proceed?",
            )
        ):
            # Prompt for multiple CSV or Markdown files output
            return
        # Fresh scan: explicitly clear the event, then reset UI state
        self._active_filetype = filetype
        self.cancel_event.clear()
        self.reset()
        self._start_scan(cfg)

    # Extracts EXIF metadata and groups photos/videos by timestamp
    def extract(
        self,
        directory_path: str,
        modifier: int,
        media_files: list[str],
        cutoff: float,
        output_utc: bool = False,
        output_dimensions: bool = False,
        output_filesize: bool = False,
        output_make: bool = False,
        output_model: bool = False,
        output_software: bool = False,
        output_lens_model: bool = False,
        output_aperture: bool = False,
        output_exposure_time: bool = False,
        output_focal_length: bool = False,
        output_iso: bool = False,
        output_orientation: bool = False,
        output_gps: bool = False,
        output_gps_altitude: bool = False,
        output_video_rows: bool = False,
        date_format: str = "%m/%d/%Y",
        time_format: str = "%H:%M:%S",
        progress_callback: Callable[[int, int, Path], None] | None = None,
    ) -> tuple[int, int]:
        """Creates pd.DataFrame from extracted EXIF metadata and groups by timestamp."""
        try:
            owns_cache = self._photo_cache is None
            if owns_cache:
                self._photo_cache = {}
                self._video_cache = {}
                self._scan_cache_flags = (
                    output_utc,
                    output_dimensions,
                    output_filesize,
                    output_make,
                    output_model,
                    output_software,
                    output_lens_model,
                    output_aperture,
                    output_exposure_time,
                    output_focal_length,
                    output_iso,
                    output_orientation,
                    output_gps,
                    output_gps_altitude,
                )
            processed = 0  # Processed files this turn; increments by photos_before_video, although scan_image only scans last photo of a series
            skipped = 0  # Skipped files this turn
            data = self._empty_scan_data()  # Data dictionary
            img_series = []
            timestamped = []
            timestamped_to_file = {}
            no_timestamp = []
            index = 1 + modifier
            date_only_dts: dict[str, datetime] = {}
            date_only_dates: dict[str, str] = {}
            try:
                for file in media_files:
                    if self.cancel_event.is_set():
                        return processed, skipped
                    ts = None
                    has_time = True
                    offset_str = None
                    path = Path(directory_path) / file
                    if file.lower().endswith(VIDEO_TYPES):
                        ts = self._get_video_date(path)
                        if self._video_cache is not None:
                            self._video_cache.pop(path, None)
                        if ts is None:
                            path = (path).as_posix()
                            if file.lower().endswith((".mp4", ".mov")):
                                self.collected_warnings["No Video Date"].append(path)
                            else:
                                self.collected_warnings["Unsupported Video Format"].append(path)
                            has_time = False
                            if output_video_rows:
                                skipped += 1
                    elif file.lower().endswith(PHOTO_TYPES):
                        ts, has_time, offset_str = self._get_photo_date_and_offset(path)
                    if ts is None or not has_time:
                        if ts is not None and not has_time:
                            date_only_dates[file] = ts.strftime("%Y:%m:%d")
                            date_only_dts[file] = ts
                        no_timestamp.append(file)
                    else:
                        group_ts = ts
                        if output_utc and offset_str is not None:
                            offset_td = self._parse_utc_offset(offset_str)
                            if offset_td is not None:
                                group_ts = ts - offset_td  # local - (+offset) = UTC; local - (-offset) = UTC
                        timestamped.append((group_ts, file))
                        timestamped_to_file[file] = ts, group_ts
                groups = self.group_by_timestamp(timestamped, cutoff)
                for group in groups:
                    if self.cancel_event.is_set():
                        break
                    # Video-only groups are orphans — don't consume a series slot
                    if not output_video_rows and not any(f.lower().endswith(PHOTO_TYPES) for _, f in group):
                        continue
                    temp_data_holder = self._empty_scan_data()
                    group_photos_ok = 0
                    group_slots = 0
                    for ts, file in group:
                        if self.cancel_event.is_set():
                            break
                        if file.lower().endswith(PHOTO_TYPES):
                            ok = self.scan_image(
                                directory_path,
                                file,
                                temp_data_holder,
                                output_utc,
                                output_dimensions,
                                output_filesize,
                                output_make,
                                output_model,
                                output_software,
                                output_lens_model,
                                output_aperture,
                                output_exposure_time,
                                output_focal_length,
                                output_iso,
                                output_orientation,
                                output_gps,
                                output_gps_altitude,
                            )
                            if ok:
                                ts_dt = timestamped_to_file[file][0].strftime("%Y:%m:%d %H:%M:%S")
                                temp_data_holder["Dates"].append(ts_dt)
                                temp_data_holder["Sort_Timestamps"].append(timestamped_to_file[file][1])
                                group_photos_ok += 1
                                group_slots += 1
                            else:
                                skipped += 1
                            if progress_callback:
                                progress_callback(processed + group_photos_ok, skipped, Path(directory_path))
                        else:
                            if output_video_rows:
                                for key in temp_data_holder:
                                    if not key in (
                                        "Dates",
                                        "Images",
                                        "Filesizes",
                                        "Sort_Timestamps",
                                        "Times",
                                        "ISOs",
                                        "Dimensions",
                                    ):
                                        temp_data_holder[key].append(None)
                                ts_dt = timestamped_to_file[file][0].strftime("%Y:%m:%d %H:%M:%S")
                                temp_data_holder["Dates"].append(ts_dt)
                                temp_data_holder["Sort_Timestamps"].append(timestamped_to_file[file][1])
                                temp_data_holder["Images"].append(file)
                                temp_data_holder["ISOs"].append("")
                                video_path = Path(directory_path) / file
                                if output_filesize:
                                    filesize = os.path.getsize(video_path)
                                    filesize = self._convert_filesize(filesize)
                                    temp_data_holder["Filesizes"].append(filesize)
                                else:
                                    temp_data_holder["Filesizes"].append(None)
                                dim = None
                                try:
                                    if output_dimensions and HACHOIR_SUPPORTED:
                                        parser = createParser(video_path.as_posix())
                                        if parser is not None:
                                            with parser:
                                                meta = extractMetadata(parser)
                                                if meta is not None and meta.has("width") and meta.has("height"):
                                                    dim = f"{meta.get('width')}x{meta.get('height')}"
                                except Exception:  # noqa: BLE001, S110
                                    pass
                                temp_data_holder["Dimensions"].append(dim)
                                group_photos_ok += 1
                                group_slots += 1
                                if progress_callback:
                                    progress_callback(processed + group_photos_ok, skipped, Path(directory_path))
                            else:
                                # Video in a mixed group still occupies its series slot
                                group_slots += 1
                    if group_photos_ok == 0:
                        continue
                    for key, value in temp_data_holder.items():
                        data[key].extend(value)
                    group_start = index
                    group_end = index + group_slots - 1
                    label = str(group_start) if group_start == group_end else f"{group_start}-{group_end}"
                    img_series.extend([label] * group_photos_ok)
                    processed += group_photos_ok
                    index = group_end + 1
                for file in no_timestamp:
                    if self.cancel_event.is_set():
                        break
                    if file.lower().endswith(PHOTO_TYPES):
                        ok = self.scan_image(
                            directory_path,
                            file,
                            data,
                            output_utc,
                            output_dimensions,
                            output_filesize,
                            output_make,
                            output_model,
                            output_software,
                            output_lens_model,
                            output_aperture,
                            output_exposure_time,
                            output_focal_length,
                            output_iso,
                            output_orientation,
                            output_gps,
                            output_gps_altitude,
                        )
                        if ok:
                            img_series.append("")
                            if file in date_only_dates:
                                data["Dates"].append(date_only_dates.get(file, ""))
                                data["Sort_Timestamps"].append(date_only_dts.get(file))
                            else:
                                data["Dates"].append("")
                                data["Sort_Timestamps"].append(None)
                                self.collected_warnings["No Metadata"].append((Path(directory_path) / file).as_posix())
                            processed += 1
                        else:
                            skipped += 1
                        if progress_callback:
                            progress_callback(processed, skipped, Path(directory_path))
            except Exception as e:  # noqa: BLE001
                self.collected_warnings["Unexpected"].append(f"[{directory_path}]: {e}\n{traceback.format_exc()}")
                if output_video_rows:
                    skipped = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES + VIDEO_TYPES)) - processed
                else:
                    skipped = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES)) - processed
            if not self.cancel_event.is_set():
                data["Dates"], data["Times"] = self.fix_time(
                    output_utc, data["Dates"], data["Offsets"], data["Images"], directory_path, date_format, time_format
                )
            if not self.cancel_event.is_set():
                self.create_dataframe(
                    img_series,
                    data,
                    directory_path,
                    output_dimensions,
                    output_filesize,
                    output_make,
                    output_model,
                    output_software,
                    output_lens_model,
                    output_aperture,
                    output_exposure_time,
                    output_focal_length,
                    output_iso,
                    output_orientation,
                    output_gps,
                    output_gps_altitude,
                    date_format,
                    time_format,
                )
            return processed, skipped  # For tallying total processed and skipped
        finally:
            if owns_cache:
                self._clear_scan_cache()

    @staticmethod
    def group_by_timestamp(entries: list[tuple[datetime, str]], cutoff: float) -> list[list[tuple[datetime, str]]]:
        """Groups entries by timestamp, within cutoff seconds of each other."""
        if cutoff < 0:
            raise ValueError("Invalid cutoff < 0")
        if len(entries) == 0:
            return []
        entries = sorted(entries, key=lambda e: e[0])
        groups = [[entries[0]]]
        timedelta_cutoff = timedelta(seconds=cutoff)
        for prev, current in itertools.pairwise(entries):
            if current[0] - prev[0] <= timedelta_cutoff:
                groups[-1].append(current)
            else:
                groups.append([current])
        return groups

    # Handles time and date formatting, along with UTC offsets
    def fix_time(
        self,
        output_utc: bool,
        list_of_dates: list[str],
        list_of_offsets: list[str | None],
        list_of_images: list[str],
        directory: str = "",
        date_format: str = "%m/%d/%Y",
        time_format: str = "%H:%M:%S",
    ) -> tuple[list[str], list[str]]:
        """Splits list_of_dates into dates and times, formatted in MM/DD/YYYY, HH:MM:SS, offset by list_of_offsets if output_utc is True."""
        # Input format: "YYYY:MM:DD HH:MM:SS"
        fixed_time = []
        fixed_date = []
        for offset_index, d in enumerate(list_of_dates):
            date_str = str(d)
            if " " not in date_str:
                try:
                    fixed_date.append(datetime.strptime(date_str, "%Y:%m:%d").strftime(date_format))
                except ValueError:
                    fixed_date.append(date_str)
                fixed_time.append("")
                continue
            try:
                dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            except ValueError:
                fixed_date.append(date_str)
                fixed_time.append("")
                continue
            if output_utc:
                offset = list_of_offsets[offset_index]
                offset_td = self._parse_utc_offset(offset)
                if offset_td is not None:
                    dt -= offset_td
                else:
                    if not list_of_images[offset_index].lower().endswith(VIDEO_TYPES):
                        self.collected_warnings["Bad Timestamp"].append(
                            f"{os.path.join(directory, list_of_images[offset_index])}"
                        )
            fixed_date.append(dt.strftime(date_format))
            fixed_time.append(dt.strftime(time_format))
        return fixed_date, fixed_time

    # Creates summary dataframe for create_sheet to use
    def _build_summary_dataframe(self, results: list, date_format: str = "%m/%d/%Y") -> tuple[pd.DataFrame, str, None]:
        """Builds summary dataframe with earliest and latest dates, total items, groups, as well as dated and undated."""
        rows = []
        total_items = 0
        total_dated = 0
        total_undated = 0
        total_series = 0
        all_dates = []
        total_bytes = 0
        for df, sheet_name, directory_path in results:
            items = len(df)
            sheet_dates = []
            dated = 0
            undated = 0
            folder_bytes = 0
            if "Dates" in df.columns:
                for value in df["Dates"]:
                    if value is None or pd.isna(value) or value == "":
                        undated += 1
                    else:
                        try:
                            sheet_dates.append(datetime.strptime(str(value).strip(), date_format).date())
                        except ValueError:
                            undated += 1
                            continue
                        dated += 1
            else:
                undated = items
            series_count = (
                len({str(v).strip() for v in df["Img # Series"].dropna() if str(v).strip()})
                if "Img # Series" in df.columns
                else 0
            )
            if sheet_dates:
                min_date = min(sheet_dates).strftime(date_format)
                max_date = max(sheet_dates).strftime(date_format)
            else:
                min_date = None
                max_date = None
            if "Files" in df.columns and directory_path:
                for value in df["Files"]:
                    if not isinstance(value, str) or not value:
                        continue
                    path = Path(directory_path) / value
                    try:
                        folder_bytes += os.path.getsize(path)
                    except OSError:
                        pass
            rows.append(
                {
                    "Sheet": sheet_name,
                    "Source Path": Path(directory_path).as_posix() if directory_path else "",
                    "Items": items,
                    "Dated": dated,
                    "Undated": undated,
                    "Series Groups": series_count,
                    "Earliest Date": min_date if min_date else "",
                    "Latest Date": max_date if max_date else "",
                    "File Size": self._convert_filesize(folder_bytes),
                }
            )
            all_dates.extend(sheet_dates)
            total_items += items
            total_dated += dated
            total_undated += undated
            total_series += series_count
            total_bytes += folder_bytes
        rows.append(
            {
                "Sheet": "Total",
                "Source Path": "",
                "Items": total_items,
                "Dated": total_dated,
                "Undated": total_undated,
                "Series Groups": total_series,
                "Earliest Date": min(all_dates).strftime(date_format) if all_dates else "",
                "Latest Date": max(all_dates).strftime(date_format) if all_dates else "",
                "File Size": self._convert_filesize(total_bytes),
            }
        )
        return pd.DataFrame(rows), self.verify_name("Summary", {name.lower() for _, name, _ in results}), None

    # Creates dataframes for create_sheet to use
    def create_dataframe(
        self,
        img_series: list[str],
        data: dict,
        directory_path: str,
        output_dimensions: bool = False,
        output_filesize: bool = False,
        output_make: bool = False,
        output_model: bool = False,
        output_software: bool = False,
        output_lens_model: bool = False,
        output_aperture: bool = False,
        output_exposure_time: bool = False,
        output_focal_length: bool = False,
        output_iso: bool = False,
        output_orientation: bool = False,
        output_gps: bool = False,
        output_gps_altitude: bool = False,
        date_format: str = "%m/%d/%Y",
        time_format: str = "%H:%M:%S",
    ) -> None:
        """Creates a pd.DataFrame from EXIF metadata for each key in "data", sorts by Date/Time if set, appends to self.results with current_sheet_name."""
        if data["Images"]:  # Make sure images are present.
            df_data = {
                "Files": data["Images"],
                "Dates": data["Dates"],
                "Time": data["Times"],
                "Img # Series": img_series,
            }
            if output_dimensions:
                df_data["Dimensions"] = data["Dimensions"]
            if output_filesize:
                df_data["File Size"] = data["Filesizes"]
            if output_make:
                df_data["Camera Make"] = data["Makes"]
            if output_model:
                df_data["Camera Model"] = data["Models"]
            if output_software:
                df_data["Software"] = data["Softwares"]
            if output_lens_model:
                df_data["Lens Model"] = data["Lens_Models"]
            if output_aperture:
                df_data["Aperture / FNumber"] = data["Apertures"]
            if output_exposure_time:
                df_data["Exposure Time"] = data["Exposure_Times"]
            if output_focal_length:
                df_data["Focal Length"] = data["Focal_Lengths"]
            if output_iso:
                df_data["ISO"] = data["ISOs"]
            if output_orientation:
                df_data["Orientation"] = data["Orientations"]
            if output_gps:
                df_data["GPS Latitude"] = data["GPS_Latitudes"]
                df_data["GPS Longitude"] = data["GPS_Longitudes"]
                if output_gps_altitude:
                    df_data["GPS Altitude"] = data["GPS_Altitudes"]
            df = pd.DataFrame(df_data)  # Create DataFrame
            if self.sort_method in ("Date (Oldest)", "Date (Newest)"):
                raw_ts = data.get("Sort_Timestamps")
                sort_dts: list[datetime | None] = []
                for idx in range(len(df)):
                    dt_val = raw_ts[idx] if raw_ts and idx < len(raw_ts) else None
                    if not isinstance(dt_val, datetime):
                        date_str = str(df["Dates"].iloc[idx]).strip()
                        time_str = str(df["Time"].iloc[idx]).strip() or "00:00:00"
                        try:
                            dt_val = datetime.strptime(f"{date_str} {time_str}", f"{date_format} {time_format}")
                        except ValueError:
                            dt_val = None
                    sort_dts.append(dt_val)

                if self.sort_method == "Date (Oldest)":
                    order = sorted(
                        range(len(df)),
                        key=lambda i: (0, sort_dts[i], i) if sort_dts[i] is not None else (1, datetime.max, i),
                    )
                else:
                    series_col = df["Img # Series"].astype(str).tolist()
                    group_max: dict[str, datetime] = {}
                    for series, dt_val in zip(series_col, sort_dts):
                        if (series and dt_val is not None) and (series not in group_max or dt_val > group_max[series]):
                            group_max[series] = dt_val

                    def _newest_key(i: int) -> tuple[int, timedelta, datetime, int]:
                        dt_val = sort_dts[i]
                        if dt_val is None:
                            return (1, timedelta.max, datetime.max, i)
                        grp_dt = group_max[series_col[i]] if series_col[i] else dt_val
                        return (0, datetime.max - grp_dt, dt_val, i)

                    order = sorted(range(len(df)), key=_newest_key)
                df = df.iloc[order].reset_index(drop=True)
            current_sheet_name = self.verify_name(self.current_sheet_name, self.used)
            self.results.append((df, current_sheet_name, directory_path))
        else:
            # No files are present
            return

    # Makes final output files
    def create_sheet(
        self,
        output_path: Path,
        total_processed: int,
        total_skipped: int,
        date_format: str = "%m/%d/%Y",
        output_summary: bool = False,
    ) -> None:
        """Creates Excel, CSV, JSON, and Markdown File(s) using self.results DataFrame(s). Displays total images processed and skipped, as well as writes a warning log if needed."""
        try:
            summary_name = None
            if output_summary and len(self.results) > 1:
                summary_df, summary_name, _ = self._build_summary_dataframe(self.results, date_format)
                self.results.insert(0, (summary_df, summary_name, _))
            files_written = 0
            filetype = self._active_filetype or self.filetype_var.get()
            # Check for empty results before prompting so the user isn't asked to overwrite for nothing
            if not self.results:
                if total_processed == 0 and total_skipped == 0:
                    self._notify_error(
                        "Empty directory", "No photos or videos were found. Please select a valid directory."
                    )
                    self.current_directory.set("No Files")
                else:
                    self._notify_error("No data", "No valid photos with metadata were found.")
            else:
                proceed = not (filetype in ("Excel", "JSON") and output_path.exists()) or self._should_overwrite(
                    output_path
                )
                if proceed:
                    # Data was found
                    if filetype == "Excel":
                        with pd.ExcelWriter(output_path) as writer:  # Opens ExcelWriter and closes automatically
                            for sheet_df, sheet_name, _ in self.results:
                                self._sanitize_for_excel(sheet_df).to_excel(writer, sheet_name=sheet_name, index=False)
                                self._format_excel_sheet(writer.sheets[sheet_name])
                        if self.hyperlink_var.get():
                            self.add_hyperlinks(output_path.as_posix(), summary_name)
                        files_written += 1
                    elif filetype == "CSV":
                        used_filenames: set[str] = set()
                        for sheet_df, sheet_name, _ in self.results:
                            if self.cancel_event.is_set():
                                break
                            if len(self.results) == 1:
                                csv_path = output_path
                            else:
                                csv_path = Path(
                                    output_path.with_suffix("").as_posix()
                                    + f"_{self._sanitize_for_filename(sheet_name, used_filenames)}.csv"
                                )
                            if not self._should_overwrite(csv_path):
                                continue
                            sheet_df.to_csv(csv_path, index=False)
                            files_written += 1
                    elif filetype == "JSON":  # Local export time
                        json_data = {"exported_at": datetime.now().isoformat(), "sheets": {}}
                        for sheet_df, sheet_name, _ in self.results:
                            json_data["sheets"][sheet_name] = json.loads(sheet_df.to_json(orient="records"))
                        output_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
                        files_written += 1
                    elif filetype == "Markdown":
                        used_filenames: set[str] = set()
                        for sheet_df, sheet_name, directory in self.results:
                            if self.cancel_event.is_set():
                                break
                            if len(self.results) == 1:
                                md_path = output_path
                            else:
                                md_path = Path(
                                    output_path.with_suffix("").as_posix()
                                    + f"_{self._sanitize_for_filename(sheet_name, used_filenames)}.md"
                                )
                            if not self._should_overwrite(md_path):
                                continue
                            md_path.write_text(
                                self._dataframe_to_txt(sheet_df, directory, hyperlinks=self.hyperlink_var.get()),
                                encoding="utf-8",
                            )
                            files_written += 1
                    if files_written > 0:
                        msg = f"\nFiles written: {files_written}"
                        if self.cancel_event.is_set():
                            msg += " (cancelled)"
                        self._notify_info(
                            "Success!",
                            message="Images: "
                            + str(total_processed)
                            + "\nImages skipped: "
                            + str(total_skipped)
                            + msg
                            + "\nLocated at: "
                            + (
                                output_path.parent.as_posix()
                                if filetype in ("CSV", "Markdown") and len(self.results) > 1
                                else output_path.as_posix()
                            ),
                        )
                        if not self.cancel_event.is_set():
                            self.progress_var.set(100)
                            self.percentage_done.set("100%")
                    else:
                        self._notify_info("No output.", message="No files were written.")
                else:  # Proceed is False; output errors then close
                    self._notify_info("Cancelled", message="File not overwritten. Cancelled successfully.")
            if self.collected_warnings:
                output = ""
                # Writes error messages from the dictionary collected_warnings
                for error, file in self.collected_warnings.items():
                    output += f"{error}\n"
                    if error == "No Metadata":
                        output += "These photos had no readable timestamp to scan and were placed at the bottom of the output."
                    elif error == "Scan Error":
                        output += "These photos could not be opened or parsed and were skipped."
                    elif error == "No Video Date":
                        output += "These videos had no readable timestamp and could not contribute to grouping."
                    elif error == "Unsupported Video Format":
                        output += "These videos' filetype(s) are not currently supported, and could not contribute."
                    elif error == "Only Video(s)":
                        output += "These directories only had videos present, or only videos after date filtering."
                    elif error == "Directory Error":
                        output += "File/Directory couldn't be accessed."
                    elif error == "Hyperlink Error":
                        output += "The following sheets do not have hyperlinks."
                    elif error == "Bad Timestamp":
                        output += "The following files did not have embedded UTC offsets. If they had valid date/time data, it is in local time."
                    elif error == "Unexpected":
                        output += (
                            "Unexpected Errors - please report at https://github.com/Pianocraft1YT/MetadataExtractor/"
                        )
                    for filename in file:
                        output += f"\n{filename}\n"
                try:
                    log_path = None
                    if not self.results or proceed:
                        log_path = output_path.parent / "warnings.log"
                        log_path.write_text(output, encoding="utf-8")
                        self.last_warnings_log = log_path
                        if not self._destroyed and not self._headless:
                            self.view_log_button.config(state="normal")
                        summary = f"{len(self.collected_warnings)} warning categories.\n\nFull details: {log_path.as_posix()}\n\nPlease verify any issues"
                        self._notify_warning("Warning(s)", message=summary)
                except OSError:
                    self._notify_error("Log Error", message=f"Couldn't write log file to {log_path}.")
            if self.open_folder_var.get() and proceed and not self._headless:
                self._open_path(output_path, True)
            self._last_files_written = files_written
            if not self.keepopen_var.get():  # Checks to close program or not
                self._on_close()
        except OSError as e:
            err_target = (
                output_path.parent.as_posix()
                if filetype in ("CSV", "Markdown") and len(self.results) > 1
                else output_path.as_posix()
            )
            self._notify_error(
                "Error writing output",
                f"Is another program using {err_target}?\n\nError: {e}",
            )
            if not self.keepopen_var.get():
                self._on_close()
        except Exception as e:  # noqa: BLE001
            self._notify_error("Unexpected error", f"{e}\n\n{traceback.format_exc()}")
            if not self.keepopen_var.get():
                self._on_close()

    # Initialization function when constructed
    def __init__(self, headless: bool = False) -> None:
        """Initializes all Tkinter objects, core variables, and loads previous settings, if applicable."""
        self._headless = headless
        self._cli_overwrite = False
        self._cli_quiet = False
        self._last_files_written = 0
        # Set default sheet name
        self.current_sheet_name = "Sheet"
        # Collect warnings
        self.collected_warnings = defaultdict(list)  # Makes a list out of keys if not found in dictionary
        # Main directory path
        self.directory_path = None
        # Directory to output .xlsx file to
        self.output_path = None
        # For verify_name
        self.used = set()
        # Variable for use with recursive directories, list of dataframes
        self.results = []
        # For output filetypes
        self.filetypes = ["Excel", "CSV", "JSON", "Markdown"]
        self.extensions = [".xlsx", ".csv", ".json", ".md"]
        # For media filter
        self.media_filters = ["All Media", "Photos Only", "Videos Only", "RAW Only"]
        # For sorting
        self.sort_methods = ["Timestamp", "Date (Oldest)", "Date (Newest)"]
        self.sort_method = "Timestamp"
        self.sort_method_objects = []
        # For recursion
        self.maxdepth = 0
        # For cancel event (set by cancel(), checked in loops, cleared in check_recursive)
        self.cancel_event = threading.Event()
        # Guard sfo _clean_up can't fire twice through nested dialogs
        self._cleanup_pending = False
        # For ETA
        self.time_started = None
        # For filetype resolving
        self.filetype_to_ext = {"Excel": ".xlsx", "CSV": ".csv", "JSON": ".json", "Markdown": ".md"}
        # Tracking destroyed root
        self._destroyed = False
        # For reporting results, partial and complete
        self.total_processed = 0
        self.total_skipped = 0
        # To minimize image open operations
        self._photo_cache = None
        self._video_cache = None
        self._scan_cache_flags = None
        # For filetype and file counts
        self._active_filetype: str | None = None
        self.total_files = 0

        if not self._headless:
            self.root = tk.Tk()
            self.root.title("Metadata Extractor")
            self.columns_frame = tk.Frame(self.root)
            self.basic_mode_frame = tk.Frame(self.columns_frame)
            self.advanced_mode_frame = tk.Frame(self.columns_frame)
            self.file_options_frame = tk.LabelFrame(self.basic_mode_frame, text="File Options", padx=8, pady=6)
            self.sort_methods_frame = tk.LabelFrame(
                self.advanced_mode_frame, text="Sort Method (default Timestamp)", padx=8, pady=6
            )
            self.date_frame = tk.LabelFrame(self.advanced_mode_frame, text="Date Range", padx=8, pady=6)
            self.extra_exif_frame = tk.LabelFrame(self.advanced_mode_frame, text="Extra Metadata", padx=8, pady=6)
            self.actions_frame = tk.LabelFrame(self.basic_mode_frame, text="Actions", padx=8, pady=6)
            self.folders_frame = tk.LabelFrame(self.basic_mode_frame, text="Folders", padx=8, pady=6)
            self.progress_frame = tk.LabelFrame(self.basic_mode_frame, text="Progress", padx=8, pady=6)
            self.open_options_frame = tk.LabelFrame(self.basic_mode_frame, text="Open Options", padx=8, pady=6)
            self.scan_options_frame = tk.LabelFrame(self.basic_mode_frame, text="Scan Options", padx=8, pady=6)
            self.extra_scan_options_frame = tk.LabelFrame(
                self.advanced_mode_frame, text="Extra Scan Options", padx=8, pady=6
            )
            self.date_format_frame = tk.LabelFrame(self.extra_scan_options_frame, text="Date Format", padx=8, pady=6)
            self.time_format_frame = tk.LabelFrame(self.extra_scan_options_frame, text="Time Format", padx=8, pady=6)
            self.execute_button = tk.Button(self.actions_frame, command=self.initialize, text="Execute")
            self.cancel_button = tk.Button(self.actions_frame, command=self.cancel, text="Cancel", state="disabled")
            self.set_directory_button = tk.Button(
                self.folders_frame, command=self.set_dir, text="Set folder with images"
            )
            self.set_output_button = tk.Button(self.folders_frame, command=self.set_output, text="Set output folder")
            self.reset_settings_button = tk.Button(
                self.actions_frame, command=self.reset_settings, text="Reset Settings"
            )
            self.keepopen_var = tk.BooleanVar(value=False)
            self.keepopen_checkbox = tk.Checkbutton(
                self.open_options_frame, text="Keep Open After Scan", variable=self.keepopen_var
            )
            self.open_folder_var = tk.BooleanVar(value=False)
            self.open_folder_checkbox = tk.Checkbutton(
                self.open_options_frame, text="Auto-Open Output Folder", variable=self.open_folder_var
            )
            self.recursive_var = tk.BooleanVar(value=False)
            self.recursive_checkbox = tk.Checkbutton(
                self.scan_options_frame,
                text="Recursive Mode",
                variable=self.recursive_var,
                command=self.recursive_input,
            )
            self.video_rows_var = tk.BooleanVar(value=False)
            self.video_rows_checkbox = tk.Checkbutton(
                self.extra_scan_options_frame, text="Create Video Rows", variable=self.video_rows_var
            )
            self.utc_var = tk.BooleanVar(value=False)
            self.utc_checkbox = tk.Checkbutton(self.extra_scan_options_frame, text="Time in UTC", variable=self.utc_var)
            self.debug_var = tk.BooleanVar(value=False)
            self.debug_checkbox = tk.Checkbutton(
                self.advanced_mode_frame, text="Debug Mode", variable=self.debug_var, command=self.debug_warning
            )
            self.filetype_var = tk.StringVar(value="Excel")
            self.sort_methods_var = tk.StringVar(value="Timestamp")
            self.hyperlink_var = tk.BooleanVar(value=True)
            self.hyperlink_checkbox = tk.Checkbutton(
                self.scan_options_frame, text="Add Hyperlinks", variable=self.hyperlink_var
            )
            self.burst_cutoff_entry = tk.Entry(self.scan_options_frame, width=40, foreground="gray")
            self.burst_cutoff_entry.insert(0, "Photo grouping cutoff (default 2 seconds)")
            self.name_entry = tk.Entry(self.file_options_frame, width=30, foreground="gray")
            self.name_entry.insert(0, "Filename (default output.filetype)")
            self.modifier_entry = tk.Entry(self.extra_scan_options_frame, width=30, foreground="gray")
            self.modifier_entry.insert(0, "Starting index (Img # Series)")
            self.maxdepth_entry = tk.Entry(self.scan_options_frame, width=20, foreground="gray")
            self.maxdepth_entry.insert(0, "Recursion Depth (#)")
            self.date_range_var = tk.BooleanVar(value=False)
            self.date_range_checkbox = tk.Checkbutton(
                self.extra_scan_options_frame,
                text="Date Range (Local Time)",
                variable=self.date_range_var,
                command=self.date_range,
            )
            self.include_undateable_var = tk.BooleanVar(value=True)
            self.include_undateable_checkbox = tk.Checkbutton(
                self.date_frame, text="Include undateable files", variable=self.include_undateable_var
            )
            self.start_date_entry = DateEntry(self.date_frame, date_pattern="%Y/%m/%d", value=None)
            self.end_date_entry = DateEntry(self.date_frame, date_pattern="%Y/%m/%d", value=None)
            self.date_notice_label = tk.Label(self.date_frame, text="One date required; two dates accepted")
            self.start_date_label = tk.Label(self.date_frame, text="Start Date")
            self.end_date_label = tk.Label(self.date_frame, text="End Date")
            self.name_entry.bind("<FocusIn>", self.nameFocusIn)
            self.name_entry.bind("<FocusOut>", self.nameFocusOut)
            self.modifier_entry.bind("<FocusIn>", self.modifierFocusIn)
            self.modifier_entry.bind("<FocusOut>", self.modifierFocusOut)
            self.maxdepth_entry.bind("<FocusIn>", self.maxDepthFocusIn)
            self.maxdepth_entry.bind("<FocusOut>", self.maxDepthFocusOut)
            self.burst_cutoff_entry.bind("<FocusIn>", self.burstCutoffFocusIn)
            self.burst_cutoff_entry.bind("<FocusOut>", self.burstCutoffFocusOut)
            self.gps_var = tk.BooleanVar(value=False)
            self.gps_checkbox = tk.Checkbutton(
                self.extra_scan_options_frame, text="GPS", variable=self.gps_var, command=self.gps_warning
            )
            self.gps_warning_label = tk.Label(
                self.extra_scan_options_frame,
                text="Coordinates may reveal sensitive location information",
                foreground="gray",
            )
            self.gps_altitude_var = tk.BooleanVar(value=False)
            self.gps_altitude_checkbox = tk.Checkbutton(
                self.extra_scan_options_frame, text="GPS Altitude", variable=self.gps_altitude_var
            )
            self.hidden_var = tk.BooleanVar(value=False)
            self.hidden_checkbox = tk.Checkbutton(
                self.extra_scan_options_frame, text="Include Hidden Files", variable=self.hidden_var
            )
            # User modes (basic or advanced)
            self.user_modes_frame = tk.LabelFrame(self.basic_mode_frame, text="Mode", padx=8, pady=8)
            self.user_modes = ["Basic", "Advanced"]
            self.user_mode_var = tk.StringVar(value="Basic")
            # Extra EXIF checkboxes
            self.extra_exif_var = tk.BooleanVar(value=False)
            self.extra_exif_checkbox = tk.Checkbutton(
                self.extra_scan_options_frame,
                text="Extra Metadata",
                variable=self.extra_exif_var,
                command=self.extra_exif,
            )
            self.dimensions_var = tk.BooleanVar(value=False)
            self.dimensions_checkbox = tk.Checkbutton(
                self.extra_exif_frame, text="Image Dimensions", variable=self.dimensions_var
            )
            self.make_var = tk.BooleanVar(value=False)
            self.make_checkbox = tk.Checkbutton(self.extra_exif_frame, text="Camera Make", variable=self.make_var)
            self.model_var = tk.BooleanVar(value=False)
            self.model_checkbox = tk.Checkbutton(self.extra_exif_frame, text="Camera Model", variable=self.model_var)
            self.software_var = tk.BooleanVar(value=False)
            self.software_checkbox = tk.Checkbutton(self.extra_exif_frame, text="Software", variable=self.software_var)
            self.lens_model_var = tk.BooleanVar(value=False)
            self.lens_model_checkbox = tk.Checkbutton(
                self.extra_exif_frame, text="Lens Model", variable=self.lens_model_var
            )
            self.aperture_var = tk.BooleanVar(value=False)
            self.aperture_checkbox = tk.Checkbutton(
                self.extra_exif_frame, text="FNumber / Aperture", variable=self.aperture_var
            )
            self.exposure_time_var = tk.BooleanVar(value=False)
            self.exposure_checkbox = tk.Checkbutton(
                self.extra_exif_frame, text="Exposure Time", variable=self.exposure_time_var
            )
            self.focal_length_var = tk.BooleanVar(value=False)
            self.focal_length_checkbox = tk.Checkbutton(
                self.extra_exif_frame, text="Focal Length", variable=self.focal_length_var
            )
            self.iso_var = tk.BooleanVar(value=False)
            self.iso_checkbox = tk.Checkbutton(self.extra_exif_frame, text="ISO", variable=self.iso_var)
            self.orientation_var = tk.BooleanVar(value=False)
            self.orientation_checkbox = tk.Checkbutton(
                self.extra_exif_frame, text="Orientation", variable=self.orientation_var
            )
            self.filesize_var = tk.BooleanVar(value=False)
            self.filesize_checkbox = tk.Checkbutton(self.extra_exif_frame, text="File Size", variable=self.filesize_var)
            self.extra_exif_options = [
                self.dimensions_checkbox,
                self.make_checkbox,
                self.model_checkbox,
                self.software_checkbox,
                self.lens_model_checkbox,
                self.aperture_checkbox,
                self.exposure_checkbox,
                self.focal_length_checkbox,
                self.iso_checkbox,
                self.filesize_checkbox,
                self.orientation_checkbox,
            ]
            self.source_path_var = tk.StringVar()
            self.output_path_var = tk.StringVar()
            self.source_path_label = tk.Label(self.folders_frame, foreground="gray", textvariable=self.source_path_var)
            self.output_path_label = tk.Label(self.folders_frame, foreground="gray", textvariable=self.output_path_var)
            self.last_warnings_log: Path | None = None
            self.view_log_button = tk.Button(
                self.actions_frame, text="View warnings.log", command=self._view_warnings_log, state="disabled"
            )
            self.summary_var = tk.BooleanVar(value=False)
            self.summary_checkbox = tk.Checkbutton(
                self.scan_options_frame, text="Summary Sheet", variable=self.summary_var
            )
            self.date_formats = ["MM/DD/YYYY", "YYYY-MM-DD", "DD/MM/YYYY"]
            self.date_format_var = tk.StringVar(value=self.date_formats[0])
            self.date_format_combobox = ttk.Combobox(
                self.date_format_frame, values=self.date_formats, state="readonly", textvariable=self.date_format_var
            )
            self.time_formats = ["24-Hour (HH:MM:SS)", "12-Hour (hh:mm:ss AM/PM)"]
            self.time_format_var = tk.StringVar(value="24-Hour (HH:MM:SS)")
            self.time_format_combobox = ttk.Combobox(
                self.time_format_frame, values=self.time_formats, state="readonly", textvariable=self.time_format_var
            )
            self.media_filter_var = tk.StringVar(value=self.media_filters[0])
            self.media_filter_combobox = ttk.Combobox(
                self.extra_scan_options_frame,
                values=self.media_filters,
                state="readonly",
                textvariable=self.media_filter_var,
            )
            # Progress bar widgets
            self.current_directory = tk.StringVar()
            self.scanned_count = tk.StringVar()
            self.skipped_count = tk.StringVar()
            self.percentage_done = tk.StringVar()
            self.eta = tk.StringVar()
            self.elapsed_time = tk.StringVar()
            self.progress_var = tk.DoubleVar(value=0)
            self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var)
            self.directory_label = tk.Label(self.progress_frame, textvariable=self.current_directory)
            self.scanned_label = tk.Label(self.progress_frame, textvariable=self.scanned_count)
            self.percent_label = tk.Label(self.progress_frame, textvariable=self.percentage_done)
            self.skipped_label = tk.Label(self.progress_frame, textvariable=self.skipped_count)
            self.eta_label = tk.Label(self.progress_frame, textvariable=self.eta)
            self.elapsed_label = tk.Label(self.progress_frame, textvariable=self.elapsed_time)
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
            self._load_settings()
            self._update_path_labels()
        else:
            self.root = None
            self.filetype_var = _CliVar("")
            self.hyperlink_var = _CliVar(False)
            self.open_folder_var = _CliVar(False)
            self.keepopen_var = _CliVar(True)
            self.current_directory = _CliVar("")
            self.scanned_count = _CliVar("")
            self.skipped_count = _CliVar("")
            self.percentage_done = _CliVar("")
            self.eta = _CliVar("")
            self.elapsed_time = _CliVar("")
            self.progress_var = _CliVar(0.0)

    # After initialization
    def run(self) -> None:
        if self._headless or self.root is None:
            return
        assert isinstance(self.filetype_var, tk.StringVar)
        """Displays main window and widgets."""
        # Pack main widgets
        self.columns_frame.pack(fill="both", expand=True)
        self.progress_frame.pack()
        self.basic_mode_frame.pack(side="left", anchor="n", padx=10, pady=6)
        self.actions_frame.pack(before=self.progress_frame, anchor="s", padx=10, pady=6)
        self.folders_frame.pack(before=self.actions_frame, padx=10, pady=6)
        self.file_options_frame.pack(after=self.folders_frame, side="top")
        self.scan_options_frame.pack(after=self.file_options_frame)
        self.open_options_frame.pack(after=self.scan_options_frame)
        self.set_directory_button.pack()
        self.source_path_label.pack(after=self.set_directory_button)
        self.set_output_button.pack(after=self.source_path_label)
        self.output_path_label.pack(after=self.set_output_button)
        self.recursive_checkbox.pack()
        self.hyperlink_checkbox.pack(after=self.recursive_checkbox)
        self.summary_checkbox.pack(after=self.hyperlink_checkbox)
        self.burst_cutoff_entry.pack(after=self.summary_checkbox)
        self.name_entry.pack()
        for ft in self.filetypes:
            tk.Radiobutton(self.file_options_frame, text=ft, variable=self.filetype_var, value=ft).pack(side="left")
        self.keepopen_checkbox.pack()
        self.open_folder_checkbox.pack(after=self.keepopen_checkbox)
        self.user_modes_frame.pack(side="top", after=self.open_options_frame)
        for um in self.user_modes:
            tk.Radiobutton(
                self.user_modes_frame, text=um, variable=self.user_mode_var, value=um, command=self.user_mode
            ).pack(side="left")
        self.execute_button.pack()
        self.cancel_button.pack(after=self.execute_button)
        self.view_log_button.pack(after=self.cancel_button)
        self.reset_settings_button.pack(after=self.view_log_button)
        self.progress_bar.pack()  # First in progress_frame
        self.directory_label.pack()
        self.scanned_label.pack()
        self.percent_label.pack()
        self.skipped_label.pack()
        self.eta_label.pack()
        self.elapsed_label.pack()

        self.recursive_input()
        self.user_mode()
        self.root.mainloop()


def run_cli(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    directory_path = Path(args.input)
    output_path = Path(args.output)
    if not directory_path.is_dir():
        print("Input must be a directory.", file=sys.stderr)
        return 1
    if not output_path.parent.is_dir():
        print("Output path parent must be a directory.", file=sys.stderr)
        return 1
    if not (math.isfinite(args.cutoff) and args.cutoff >= 0):
        print("Cutoff must be greater or equal to 0 seconds.", file=sys.stderr)
        return 1
    if args.maxdepth is not None:
        if args.maxdepth < 1:
            print("Maxdepth must be greater or equal to 1 subfolder.", file=sys.stderr)
            return 1
        maxdepth = args.maxdepth
    elif args.recursive:
        maxdepth = 1
    else:
        maxdepth = 0
    if args.modifier < 0:
        print("Starting index (modifier) cannot be less than 0.", file=sys.stderr)
        return 1
    try:
        start_date = date.fromisoformat(args.start_date) if args.start_date else None
        end_date = date.fromisoformat(args.end_date) if args.end_date else None
    except ValueError:
        print("Start and end dates must be in YYYY-MM-DD format.", file=sys.stderr)
        return 1
    date_range = bool(start_date or end_date)
    if start_date and end_date and start_date > end_date:
        print("Start date must be earlier than end date.", file=sys.stderr)
        return 1
    app = MetadataExtractor(headless=True)
    app._cli_overwrite = args.overwrite
    app._cli_quiet = args.quiet
    app.maxdepth = maxdepth
    sort_method = {"timestamp": "Timestamp", "oldest": "Date (Oldest)", "newest": "Date (Newest)"}[args.sort]
    app.sort_method = sort_method
    fmt_map = {"excel": "Excel", "csv": "CSV", "json": "JSON", "markdown": "Markdown"}
    ext_map = {".xlsx": "Excel", ".csv": "CSV", ".json": "JSON", ".md": "Markdown"}
    if args.filetype is not None:
        filetype = fmt_map[args.filetype.lower()]
    else:
        filetype = ext_map.get(output_path.suffix.lower(), "Excel")
    app.filetype_var.set(filetype)
    app._active_filetype = filetype
    if not args.hyperlinks:
        hyperlinks = (filetype in ("Excel", "Markdown")) if args.hyperlinks is None else args.hyperlinks
    else:
        hyperlinks = args.hyperlinks
    app.hyperlink_var.set(hyperlinks)
    date_format = {"MM/DD/YYYY": "%m/%d/%Y", "YYYY-MM-DD": "%Y-%m-%d", "DD/MM/YYYY": "%d/%m/%Y"}[args.date_format]
    time_format = {"24h": "%H:%M:%S", "12h": "%I:%M:%S %p"}[args.time_format]
    media_filter = {"all": "All Media", "photos": "Photos Only", "videos": "Videos Only", "raw": "RAW Only"}[args.media]
    if args.all == True:
        output_dimensions = True
        output_filesize = True
        output_make = True
        output_model = True
        output_software = True
        output_lens_model = True
        output_aperture = True
        output_exposure_time = True
        output_focal_length = True
        output_iso = True
        output_orientation = True
    else:
        output_dimensions = args.dimensions
        output_filesize = args.filesize
        output_make = args.make
        output_model = args.model
        output_software = args.software
        output_lens_model = args.lens
        output_aperture = args.aperture
        output_exposure_time = args.exposure
        output_focal_length = args.focal_length
        output_iso = args.iso
        output_orientation = args.orientation
    output_video_rows = args.videorows or (media_filter == "Videos Only")
    output_utc = args.utc
    output_gps = args.gps or args.gps_altitude
    output_gps_altitude = args.gps_altitude
    include_hiddens = args.hidden
    include_undateable = args.include_undateable
    modifier = args.modifier
    cutoff = args.cutoff
    final_output = output_path.parent / app.clean_name(output_path.name)
    processed, skipped = app.find_directories(
        directory_path,
        modifier,
        cutoff,
        output_utc,
        output_dimensions,
        output_filesize,
        output_make,
        output_model,
        output_software,
        output_lens_model,
        output_aperture,
        output_exposure_time,
        output_focal_length,
        output_iso,
        output_orientation,
        output_gps,
        output_gps_altitude,
        output_video_rows,
        include_hiddens,
        include_undateable,
        media_filter,
        date_range,
        date_format,
        time_format,
        start_date,
        end_date,
        progress_callback=None,
    )
    app.create_sheet(final_output, processed, skipped, date_format, args.summary)
    return 0 if app._last_files_written > 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="Metadata Extractor", description="Extract metadata from media files.")
    parser.add_argument("-i", "--input", required=True, help="Folder to scan")
    parser.add_argument("-o", "--output", required=True, help="Output file path")
    parser.add_argument(
        "-f",
        "--filetype",
        choices=["excel", "csv", "json", "markdown"],
        required=False,
        type=str.lower,
        default=None,
        help="File output type",
    )
    parser.add_argument("-y", "--overwrite", action="store_true", help="Force overwrites files")
    parser.add_argument(
        "-hl",
        "--hyperlinks",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Adds hyperlinks to Excel and Markdown files",
    )
    parser.add_argument("-s", "--summary", action="store_true", help="Add summary of scan")
    parser.add_argument("-q", "--quiet", action="store_true", help="Supress non-error stdout")
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Enables recursive mode to --maxdepth subfolders, default 1 if unspecified",
    )
    parser.add_argument(
        "-md", "--maxdepth", required=False, type=int, default=None, help="Sets maxdepth for recursive mode"
    )
    parser.add_argument(
        "-c", "--cutoff", required=False, type=float, default=2.0, help="Sets photo grouping cutoff in seconds"
    )
    parser.add_argument(
        "-m", "--modifier", required=False, type=int, default=0, help="Sets starting index modifier for Img # Series"
    )
    parser.add_argument("-vr", "--videorows", action="store_true", help="Adds video row output")
    parser.add_argument("-H", "--hidden", action="store_true", help="Includes hidden files")
    parser.add_argument("-u", "--utc", action="store_true", help="Output time in UTC")
    parser.add_argument(
        "-S",
        "--sort",
        required=False,
        default="timestamp",
        choices=["timestamp", "oldest", "newest"],
        help="Sort output by this method",
    )
    parser.add_argument(
        "-df",
        "--date-format",
        required=False,
        default="MM/DD/YYYY",
        choices=["MM/DD/YYYY", "YYYY-MM-DD", "DD/MM/YYYY"],
        help="Format output dates",
    )
    parser.add_argument(
        "-t", "--time-format", required=False, default="24h", choices=["24h", "12h"], help="Format output times"
    )
    parser.add_argument("-sd", "--start-date", required=False, default=None, help="Filter files to be after this date")
    parser.add_argument("-ed", "--end-date", required=False, default=None, help="Filter files to be before this date")
    parser.add_argument(
        "-iu",
        "--include-undateable",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include undateable files",
    )
    parser.add_argument("-d", "--dimensions", action="store_true", help="Output media dimensions")
    parser.add_argument("-fs", "--filesize", action="store_true", help="Output file size")
    parser.add_argument("-mk", "--make", action="store_true", help="Output camera manufacturer")
    parser.add_argument("-mo", "--model", action="store_true", help="Output camera model")
    parser.add_argument("-sft", "--software", action="store_true", help="Output processing software")
    parser.add_argument("-l", "--lens", action="store_true", help="Output lens model")
    parser.add_argument("-apt", "--aperture", action="store_true", help="Output aperture (f-number)")
    parser.add_argument("-e", "--exposure", action="store_true", help="Output exposure time / shutter speed")
    parser.add_argument("-fl", "--focal-length", action="store_true", help="Output focal length")
    parser.add_argument("-iso", "--iso", action="store_true", help="Output ISO sensitivity")
    parser.add_argument("-or", "--orientation", action="store_true", help="Output image orientation")
    parser.add_argument("-a", "--all", action="store_true", help="Output all available EXIF data")
    parser.add_argument("-g", "--gps", action="store_true", help="Output GPS location")
    parser.add_argument("-ga", "--gps-altitude", action="store_true", help="Output GPS Altitude")
    parser.add_argument(
        "-M", "--media", choices=["all", "photos", "videos", "raw"], default="all", help="Fiter by media type"
    )
    return parser


# Always runs
if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(run_cli(sys.argv[1:]))
    app = MetadataExtractor(headless=False)  # Java: MetadataExtractor app = new MetadataExtractor(); (Constructor)
    app.run()
