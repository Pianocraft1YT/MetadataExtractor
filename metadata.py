# Dear programmer:
# When I wrote this code, only God and I knew how it worked.
# Now, only God knows!
#
# Therefore, if you trying to improve this,
# Please increment this counter as a warning
# For the next person:
#
# hours_spent_original = 76
# hours_wasted_here = 0

# Coded by Pianocraft1YT
# Tutorial: https://youtu.be/ruWNKBdbYoo
# GitHub Repo: https://github.com/Pianocraft1YT/MetadataExtractor/

# Imports
import json
import os
import re
import stat
import threading
import time
import tkinter as tk
import traceback
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

# For spreadsheet making
import openpyxl
import pandas as pd
from openpyxl.styles import Font
from PIL import Image, UnidentifiedImageError
from tk_date_entry import DateEntry

# Constants
EXIF_DATETIME = 306
EXIF_DATETIME_ORIGINAL = 36867
EXIF_DATETIME_DIGITIZED = 36868
MAX_PHOTOS_BEFORE_VIDEO = 5
SHEET_NAME_MAX_CHARS = 31
EXIF_OFFSET_TIME_ORIGINAL = 36881
EXIF_CAMERA_MAKE = 271
EXIF_CAMERA_MODEL = 272
EXIF_SOFTWARE = 305
EXIF_LENS_MODEL = 42036
EXIF_APERTURE = 33437
EXIF_EXPOSURE_TIME = 33434
EXIF_FOCAL_LENGTH = 37386
EXIF_ISO = 34855

# XML Illegals
XML_ILLEGAL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# Persistent Settings
SETTINGS_PATH = Path.home() / ".metadata-extractor" / "settings.json"
# Common video file formats to check
VIDEO_TYPES = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv")
# Common and uncommon image formats to check
PHOTO_TYPES = (
    ".jpg",
    ".jpeg",
    ".heic",
    ".heif",
    ".png",
    ".tiff",
    ".tif",
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


class MetadataExtractor:

    # Cosmetic only, adds placeholder text in entry boxes
    def nameFocusIn(self, event):
        if self.name_entry.get() == "Filename (default output.filetype)":
            self.name_entry.delete(0, "end")
            self.name_entry.config(foreground="black")

    def nameFocusOut(self, event):
        if self.name_entry.get() == "":
            self.name_entry.insert(0, "Filename (default output.filetype)")
            self.name_entry.config(foreground="gray")

    def seriesFocusIn(self, event):
        if self.modifier_entry.get() == "Starting index (Img # Series)":
            self.modifier_entry.delete(0, "end")
            self.modifier_entry.config(foreground="black")

    def seriesFocusOut(self, event):
        if self.modifier_entry.get() == "":
            self.modifier_entry.insert(0, "Starting index (Img # Series)")
            self.modifier_entry.config(foreground="gray")

    def maxDepthFocusIn(self, event):
        if self.maxdepth_entry.get() == "Recursion Depth (#)":
            self.maxdepth_entry.delete(0, "end")
            self.maxdepth_entry.config(foreground="black")

    def maxDepthFocusOut(self, event):
        if self.maxdepth_entry.get() == "":
            self.maxdepth_entry.insert(0, "Recursion Depth (#)")
            self.maxdepth_entry.config(foreground="gray")

    def gps_warning(self):
        if self.gps_var.get():
            self.gps_warning_label.pack(after=self.gps_checkbox)
        else:
            self.gps_warning_label.pack_forget()
        self.root.update_idletasks()  # flush pending layout
        self.root.geometry(f"350x{self.root.winfo_reqheight()}")

    def debug_warning(self):
        if self.debug_var.get():
            self.debug_var.set(
                messagebox.askokcancel(
                    "Debug selected",
                    message="Debug mode has been enabled.\nThis means that output directory is Path.home()/Downloads/output.filetype.\nSeries will always output regardles of irregularity.\n\nProceed?",
                )
            )

    # Show recursive_input entry box when recursive is checked
    def recursive_input(self):
        if self.recursive_var.get():
            self.maxdepth_entry.pack(before=self.hyperlink_checkbox)
        else:
            self.maxdepth_entry.pack_forget()
        self.root.update_idletasks()  # flush pending layout
        self.root.geometry(f"350x{self.root.winfo_reqheight()}")  # fixed width, auto height

    # Show extra metadata checkboxes when extra_exif_checkbox is checked
    def extra_exif(self):
        # Pack all 9 checkboxes inside the frame ONCE, at init time (see below)
        # The toggle only moves the frame itself in/out of root's layout.
        if self.extra_exif_var.get():
            self.extra_exif_frame.pack(before=self.progress_frame)
        else:
            self.extra_exif_frame.pack_forget()
        self.root.update_idletasks()
        self.root.geometry(f"350x{self.root.winfo_reqheight()}")

    def date_range(self):
        if self.date_range_var.get():
            self.date_notice_label.pack(after=self.date_range_checkbox)
            self.start_date_label.pack(after=self.date_notice_label)
            self.start_date_entry.pack(after=self.start_date_label)
            self.end_date_label.pack(after=self.start_date_entry)
            self.end_date_entry.pack(after=self.end_date_label)
        else:
            self.start_date_label.pack_forget()
            self.start_date_entry.pack_forget()
            self.end_date_label.pack_forget()
            self.end_date_entry.pack_forget()
            self.date_notice_label.pack_forget()
        self.root.update_idletasks()  # flush pending layout
        self.root.geometry(f"350x{self.root.winfo_reqheight()}")  # fixed width, auto height

    # Helpers for progress bar
    def get_total_files(self, max_depth):
        file_count = 0
        for _, _, files in self.walk_to_depth(self.directory_path, max_depth):
            if self.cancel_event.is_set():
                return file_count
            file_count += sum(1 for entry in files if entry.lower().endswith(PHOTO_TYPES))
        return file_count

    # Main-thread setter for total_files (queued via root.after from worker)
    def _set_total_files(self, count):
        self.time_started = time.perf_counter()
        self.total_files = count
        self.scanned_count.set(f"Scanned: 0 / {count}")
        if count > 0:
            self.percentage_done.set("0%")
            self.progress_var.set(0)

    # Turn only seconds into normal time measurements
    def _convert_seconds(self, seconds, mode="ETA"):
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

    # Updates the progress bar
    def update_progress(self, processed, skipped, current_dir, timestamp=None):
        if not self.cancel_event.is_set():
            if self.time_started:
                files_done = processed + skipped
                if timestamp:
                    time_passed = timestamp - self.time_started  # Given in seconds, float
                else:
                    time_passed = 0
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
                self.scanned_count.set(f"Scanned: {min(processed, self.total_files)} / {self.total_files}")
            else:
                self.percentage_done.set("0%")
                self.progress_var.set(0)
            self.current_directory.set(str(current_dir)[-30:])  # Truncate to not be too long, last 30 characters

    # Starts the worker thread (called from main thread)
    def _start_scan(
        self,
        recursive,
        final_output,
        modifier,
        debug,
        output_utc,
        output_dimensions,
        output_make,
        output_model,
        output_software,
        output_lens_model,
        output_aperture,
        output_exposure_time,
        output_focal_length,
        output_iso,
        output_gps,
        date_range,
        start_date,
        end_date,
    ):
        self._scan_running = True
        self.execute_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        threading.Thread(
            target=self._run_scan_threaded,
            args=(
                recursive,
                final_output,
                modifier,
                debug,
                output_utc,
                output_dimensions,
                output_make,
                output_model,
                output_software,
                output_lens_model,
                output_aperture,
                output_exposure_time,
                output_focal_length,
                output_iso,
                output_gps,
                date_range,
                start_date,
                end_date,
            ),
            daemon=True,
        ).start()

    # Runs the threaded versions of the scan(s)
    def _run_scan_threaded(
        self,
        recursive,
        final_output,
        modifier,
        debug,
        output_utc,
        output_dimensions,
        output_make,
        output_model,
        output_software,
        output_lens_model,
        output_aperture,
        output_exposure_time,
        output_focal_length,
        output_iso,
        output_gps,
        date_range,
        start_date,
        end_date,
    ):
        total_scanned, total_skipped = 0, 0

        def _on_progress(p, s, d):
            # Runs on worker thread — capture timestamp NOW so main-thread
            # scheduling delay doesn't distort the ETA average.
            t = time.perf_counter()
            if not self._destroyed:
                self.root.after(0, lambda: self.update_progress(p, s, d, t))

        try:
            if recursive and not self._destroyed:
                self.root.after(0, self.current_directory.set, "Counting files...")
                count = self.get_total_files(self.maxdepth)
                if self.cancel_event.is_set():
                    return
                self.root.after(0, self._set_total_files, count)
                if self.cancel_event.is_set():
                    return
            total_scanned, total_skipped = self.find_directories(
                self.directory_path,
                modifier,
                debug,
                output_utc,
                output_dimensions,
                output_make,
                output_model,
                output_software,
                output_lens_model,
                output_aperture,
                output_exposure_time,
                output_focal_length,
                output_iso,
                output_gps,
                date_range,
                start_date,
                end_date,
                progress_callback=_on_progress,
            )
        except Exception as e:  # noqa: BLE001
            self.collected_warnings["Unexpected"].append(f"{e}\n{traceback.format_exc()}")
        finally:
            if not self._destroyed:
                self.root.after(
                    0,
                    self._clean_up,
                    final_output,
                    total_scanned,
                    total_skipped,
                )

    def _clean_up(self, final_output, processed, skipped):
        # Guard so a queued _clean_up can't fire twice (e.g. through nested dialogs)
        if not self._scan_running:
            return
        self._scan_running = False
        cancelled = self.cancel_event.is_set()
        try:
            if not cancelled:
                self.create_sheet(final_output, processed, skipped)
        except Exception as e:  # noqa: BLE001
            self.collected_warnings["Unexpected"].append(f"_clean_up/create_sheet: {e}\n{traceback.format_exc()}")
        finally:
            if not self._destroyed:
                self.eta.set("Done")
                self.execute_button.config(state="normal")
                self.cancel_button.config(state="disabled")
                if cancelled:
                    self.current_directory.set("Cancelled")
                    self.percentage_done.set("Cancelled")

    def _on_close(self):
        try:
            self._save_settings()
        except Exception:  # noqa: BLE001
            messagebox.showerror("Setting Save Error", message=f"Your settings could not be saved at {SETTINGS_PATH}")
        self.cancel_event.set()
        self._destroyed = True
        self.root.destroy()

    def _ask_yes_no_threadsafe(self, title, msg):
        """Call from a worker thread. Blocks until the main thread answers."""
        # Use a lock to ensure only one worker thread manages a dialog at a time
        if threading.current_thread() is threading.main_thread():
            return bool(messagebox.askyesno(title, msg))  # already on main, just call it
        with self._dialog_lock:
            self._dialog_answer = None
            self._dialog_event.clear()

            def _show():
                try:
                    self._dialog_answer = messagebox.askyesno(title, msg)
                finally:
                    self._dialog_event.set()

            if not self._destroyed:
                self.root.after(0, _show)  # enqueue, return immediately
                self._dialog_event.wait()  # now block the worker for real
            return bool(self._dialog_answer)

    # Conversion Helpers
    def _rational_to_float(self, value: Any) -> float | None:
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

    def _format_aperture(self, value):
        v = self._rational_to_float(value)
        if v is None or v <= 0:
            return None
        return f"f/{v:g}"  # 5.6 -> "f/5.6", 8.0 -> "f/8"

    def _format_exposure_time(self, value):
        v = self._rational_to_float(value)
        if v is None or v <= 0:
            return None
        if v >= 1:
            return f"{v:g}s"  # 1.0 -> "1s", 2.5 -> "2.5s", 30.0 -> "30s"
        inv = 1.0 / v
        rounded = round(inv)
        if rounded > 1 and abs(inv - rounded) / inv < 0.01:
            return f"1/{rounded}"  # 0.004 -> "1/250", 0.5 -> "1/2"
        return f"{v:g}s"  # 0.3 -> "0.3s" (not "1/3")

    def _format_focal_length(self, value):
        v = self._rational_to_float(value)
        if v is None or v <= 0:
            return None
        return f"{v:g}mm"  # 23.0 -> "23mm", 18.5 -> "18.5mm"

    def _format_iso(self, value):
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            return value[0] if value else None  # multi-ISO capture, take first
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _dataframe_to_txt(self, df, directory=None, hyperlinks=False):
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
        for index, column in enumerate(columns):
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
                url = (Path(directory) / raw).as_posix()
                values[0] = f"[{values[0]}](<{url}>)"
            values = "|".join(values)
            values = "|" + values + "|"
            lines.append(values)
        return "\n".join(lines)

    def _parse_exif_datetime(self, dt_value):
        """Parse "YYYY:MM:DD HH:MM:SS" or "YYYY:MM:DD" to a date object, or None."""
        s = str(dt_value)
        try:
            if " " in s:
                return datetime.strptime(s, "%Y:%m:%d %H:%M:%S").date()
            return datetime.strptime(s, "%Y:%m:%d").date()
        except ValueError:
            return None

    def _format_gps_coord(self, dms_tuple, ref):
        if isinstance(ref, bytes):
            try:
                ref = ref.decode("ascii")
            except UnicodeDecodeError:
                return None
        if not isinstance(ref, str) or not ref.strip():
            return None
        if not isinstance(dms_tuple, (tuple, list)) or len(dms_tuple) != 3:
            return None
        degree = self._rational_to_float(dms_tuple[0])
        minute = self._rational_to_float(dms_tuple[1])
        second = self._rational_to_float(dms_tuple[2])
        if degree is None or minute is None or second is None:
            return None
        converted = degree + minute / 60.0 + second / 3600.0
        if ref.upper() in ("S", "W"):
            converted = -converted
        return f"{converted:.6f}"

    # Creates empty dict for data to fill
    def _empty_scan_data(self):
        return {
            "Dates": [],
            "Images": [],
            "Offsets": [],
            "Dimensions": [],
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
        }

    def _save_settings(self):
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            # Don't add debug_var to settings persistence
            start = self.start_date_entry.get_date()
            end = self.end_date_entry.get_date()
            settings = {
                "Directory Path": self.directory_path.as_posix() if self.directory_path else None,
                "Output Path": self.output_path.as_posix() if self.output_path else None,
                "Filetype": self.filetype_var.get(),
                "Start Date": start.isoformat() if start else None,
                "End Date": end.isoformat() if end else None,
                "File Name": (
                    self.name_entry.get() if self.name_entry.get() != "Filename (default output.filetype)" else None
                ),
                "Modifier": (
                    self.modifier_entry.get() if self.modifier_entry.get() != "Starting index (Img # Series)" else None
                ),
                "Max Depth": (
                    int(self.maxdepth_entry.get().strip()) if self.maxdepth_entry.get().strip().isdigit() else None
                ),  # Implicitly takes care of "Recursion Depth (#)" default case
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
                "GPS": self.gps_var.get(),
            }
            SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        except (OSError, ValueError, TypeError):
            pass

    def _load_settings(self):
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
            }
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            for key, value in data.items():
                try:
                    if value is not None:
                        if key == "Directory Path":
                            if Path(value).is_dir() and Path(value).exists():
                                self.directory_path = Path(value)
                        elif key == "Output Path":
                            if Path(value).is_dir() and Path(value).exists():
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
                            if (isinstance(value, int) or (isinstance(value, float) and value.is_integer())) and int(
                                value
                            ) > 0:
                                self.maxdepth_entry.delete(0, "end")
                                self.maxdepth_entry.insert(0, str(value))
                                self.maxdepth = int(value)
                                self.maxdepth_entry.config(foreground="black")
                            else:
                                self.maxdepth_entry.delete(0, "end")
                                self.maxdepth_entry.insert(0, "Recursion Depth (#)")
                                self.maxdepth = 0
                        elif key in (
                            "Date Range",
                            "UTC",
                            "Keep Open",
                            "Recursive",
                            "Hyperlinks",
                            "Extra EXIF",
                            "Dimensions",
                            "Make",
                            "Model",
                            "Software",
                            "Lens Model",
                            "Aperture",
                            "Exposure Time",
                            "Focal Length",
                            "ISO",
                            "GPS",
                        ) and isinstance(value, bool):
                            key_to_checkbox_var[key].set(value)
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
                except (ValueError, TypeError):
                    pass
        except (OSError, json.JSONDecodeError, AttributeError):
            return

    # To clean up any past executions
    def reset(self):
        self.used = set()
        self.results.clear()
        self.collected_warnings.clear()
        self.current_sheet_name = "Sheet"
        self.current_directory.set("")
        self.total_files = 0
        self.scanned_count.set("Scanned: 0 / …")
        self.skipped_count.set("Skipped: 0")
        self.percentage_done.set("0%")
        self.progress_var.set(0)
        self.eta.set("Estimating...")
        self.elapsed_time.set("Time Elapsed: ...")
        self.time_started = None

    # Runs on "Cancel" button press
    def cancel(self):
        self.cancel_event.set()
        self.cancel_button.config(state="disabled")
        self.current_directory.set("Cancelling...")
        self.percentage_done.set("Cancelling...")

    # Core Functions
    # Gets called on set directory button press to set image directory
    def set_dir(self):
        selected = filedialog.askdirectory(title="Select a Directory")
        if selected:
            self.directory_path = Path(selected)

    # Gets called on set output button press
    def set_output(self):
        selected = filedialog.askdirectory(title="Select a Output Directory")
        if selected:
            self.output_path = Path(selected)

    @staticmethod
    def _decode_exif_string(v):
        if isinstance(v, bytes):
            return v.decode("ascii", errors="replace")
        return v

    def _check_hidden(self, filepath, directory):
        filepath = Path(directory) / filepath
        if filepath.name.startswith("."):
            return True
        if os.name != "nt":
            return False
        try:
            file_attrs = os.stat(filepath).st_file_attributes
            return bool(file_attrs & stat.FILE_ATTRIBUTE_HIDDEN)
        except (FileNotFoundError, AttributeError):
            return False

    # Image metadata extractor helper function
    def scan_image(
        self,
        directory_path,
        i,
        data,
        media_files,
        output_utc,
        output_dimensions,
        output_make,
        output_model,
        output_software,
        output_lens_model,
        output_aperture,
        output_exposure_time,
        output_focal_length,
        output_iso,
        output_gps,
        date_range,
        start_date,
        end_date,
    ):
        offset = None
        dimensions = None
        make = None
        model = None
        software = None
        lens_model = None
        aperture = None
        exposure_time = None
        focal_length = None
        iso = None
        gps_latitude = None
        gps_longitude = None
        process_image = True

        def _exif_get(tag, ifd, exif_data):
            metadata = exif_data.get(tag)
            if metadata is None and ifd is not None:
                metadata = ifd.get(tag)
            return metadata

        def _exif_get_str(tag, ifd, exif_data):
            return self._decode_exif_string(_exif_get(tag, ifd, exif_data))

        if media_files:
            try:
                with Image.open(Path(directory_path) / media_files[i]) as img:
                    if output_dimensions:
                        dimensions = f"{img.size[0]}x{img.size[1]}"
                    exif_data = img.getexif()
                    general_ifd = exif_data.get_ifd(0x8769)
                    gps_ifd = exif_data.get_ifd(0x8825)
                dt = (
                    _exif_get(EXIF_DATETIME_ORIGINAL, general_ifd, exif_data)
                    or _exif_get(EXIF_DATETIME_DIGITIZED, general_ifd, exif_data)
                    or _exif_get(EXIF_DATETIME, None, exif_data)
                )
                dt = self._decode_exif_string(dt)
                if dt is None:
                    self.collected_warnings["No Metadata"].append(f"[{directory_path}]\\{media_files[i]}")
                    return False
                if output_utc:
                    offset = self._decode_exif_string(_exif_get(EXIF_OFFSET_TIME_ORIGINAL, general_ifd, exif_data))
                if output_make:
                    make = _exif_get_str(EXIF_CAMERA_MAKE, None, exif_data)
                if output_model:
                    model = _exif_get_str(EXIF_CAMERA_MODEL, None, exif_data)
                if output_software:
                    software = _exif_get_str(EXIF_SOFTWARE, None, exif_data)
                if output_lens_model:
                    lens_model = _exif_get_str(EXIF_LENS_MODEL, general_ifd, exif_data)
                if output_aperture:
                    aperture = self._format_aperture(_exif_get(EXIF_APERTURE, general_ifd, exif_data))
                if output_exposure_time:
                    exposure_time = self._format_exposure_time(_exif_get(EXIF_EXPOSURE_TIME, general_ifd, exif_data))
                if output_focal_length:
                    focal_length = self._format_focal_length(_exif_get(EXIF_FOCAL_LENGTH, general_ifd, exif_data))
                if output_iso:
                    iso = self._format_iso(_exif_get(EXIF_ISO, general_ifd, exif_data))
                if output_gps and gps_ifd:
                    lat_ref = gps_ifd.get(1)
                    lat = gps_ifd.get(2)
                    long_ref = gps_ifd.get(3)
                    long = gps_ifd.get(4)
                    gps_latitude = self._format_gps_coord(lat, lat_ref)
                    gps_longitude = self._format_gps_coord(long, long_ref)
                if date_range:
                    d = self._parse_exif_datetime(dt)
                    if not d:
                        return False
                    if start_date and d < start_date or end_date and d > end_date:
                        process_image = False
            except (OSError, SyntaxError, ValueError, UnidentifiedImageError):
                self.collected_warnings["Scan Error"].append(f"[{directory_path}]\\{media_files[i]}")
                return False
            else:
                if process_image:
                    data["Images"].append(media_files[i])
                    data["Dates"].append(dt)
                    data["Offsets"].append(offset)
                    data["Dimensions"].append(dimensions)
                    data["Makes"].append(make)
                    data["Models"].append(model)
                    data["Softwares"].append(software)
                    data["Lens_Models"].append(lens_model)
                    data["Apertures"].append(aperture)
                    data["Exposure_Times"].append(exposure_time)
                    data["Focal_Lengths"].append(focal_length)
                    data["ISOs"].append(iso)
                    data["GPS_Latitudes"].append(gps_latitude)
                    data["GPS_Longitudes"].append(gps_longitude)
                    return True
                else:
                    return False
        else:
            return False

    # Hyperlink feature
    def add_hyperlinks(self, excel_file):
        try:
            wb = openpyxl.load_workbook(excel_file)
            for _, sheet_name, directory in self.results:
                if not directory:
                    continue
                try:
                    ws = wb[sheet_name]
                    for cell in ws["A"][1:]:
                        if cell.value:
                            cell.hyperlink = (Path(directory) / cell.value).as_posix()
                            cell.font = Font(color="0563C1", underline="single")
                except Exception as e:  # noqa: BLE001
                    self.collected_warnings["Hyperlink Error"].append(sheet_name + f"\nError: {e}")
            wb.save(excel_file)
        except Exception as e:  # noqa: BLE001
            self.collected_warnings["Hyperlink Error"].append(f"Hyperlinks could not be added. \nError: {e}")

    # Finds subdirectories for recursive mode
    def find_directories(
        self,
        directory_path,
        modifier,
        debug,
        output_utc,
        output_dimensions,
        output_make,
        output_model,
        output_software,
        output_lens_model,
        output_aperture,
        output_exposure_time,
        output_focal_length,
        output_iso,
        output_gps,
        date_range,
        start_date,
        end_date,
        progress_callback=None,
    ):
        sheet_names = []
        files_lists = []
        directories = []
        total_skipped = 0
        total_processed = 0
        for dirpath, _, files in self.walk_to_depth(directory_path, self.maxdepth):
            if self.cancel_event.is_set():
                break
            if not any(f.lower().endswith(PHOTO_TYPES) for f in files):
                continue
            dirpath = Path(dirpath)
            try:
                rel = Path(os.path.relpath(dirpath, directory_path))
            except ValueError:
                self.collected_warnings["Directory Error"].append(str(dirpath))
                continue
            sheet_name = "_".join(rel.parts)
            files_lists.append(files)
            if len(sheet_name) > SHEET_NAME_MAX_CHARS:
                sheet_name = sheet_name[-SHEET_NAME_MAX_CHARS:]
            sheet_names.append(sheet_name)
            directories.append(dirpath.as_posix())
        for directory, media_files, sheet_name in zip(directories, files_lists, sheet_names):
            if self.cancel_event.is_set():
                break
            self.current_sheet_name = sheet_name
            if progress_callback:
                _base_p = total_processed
                _base_s = total_skipped
                wrapped_cb = lambda p, s, d, base_p=_base_p, base_s=_base_s: progress_callback(
                    base_p + p, base_s + s, d
                )
            else:
                wrapped_cb = None
            try:
                p, s = self.sort_and_extract(
                    directory,
                    modifier,
                    debug,
                    media_files,
                    output_utc,
                    output_dimensions,
                    output_make,
                    output_model,
                    output_software,
                    output_lens_model,
                    output_aperture,
                    output_exposure_time,
                    output_focal_length,
                    output_iso,
                    output_gps,
                    date_range,
                    start_date,
                    end_date,
                    progress_callback=wrapped_cb,
                )
            except OSError:
                skipped_count = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES))
                self.collected_warnings["Directory Error"].append(f"{directory}")
                p, s = 0, skipped_count  # match the existing convention in sort_and_extract
            except Exception as e:  # noqa: BLE001
                self.collected_warnings["Unexpected"].append(f"[{directory}]: {e}\n{traceback.format_exc()}")
                skipped_count = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES))
                p, s = 0, skipped_count
            total_processed += p
            total_skipped += s
        return total_processed, total_skipped

    def natural_key(self, s):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

    # Helper to find directories one-by-one to max_depth
    def walk_to_depth(self, root_dir, max_depth):
        # Normalize the path and count baseline separators
        root_dir = os.path.abspath(str(root_dir))
        baseline_depth = len(Path(root_dir).parts)

        for dirpath, dirs, media_files in os.walk(
            root_dir, topdown=True, followlinks=False
        ):  # Symlinked directories ignored
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d.lower() not in {"system volume information", "$recycle.bin"}
            ]
            dirs.sort(key=lambda x: self.natural_key(os.path.splitext(x)[0]))
            # Symlinked files included for media_files, not directories
            media_files[:] = [
                f
                for f in media_files
                if not self._check_hidden(f, dirpath) and f.lower().endswith(PHOTO_TYPES + VIDEO_TYPES)
            ]
            # Sorts files alphabetically, ignoring file extensions and capitalization, ignoring any non-photo or non-video files
            media_files.sort(
                key=lambda x: (
                    self.natural_key(os.path.splitext(x)[0]),
                    0 if x.lower().endswith(PHOTO_TYPES) else 1,
                )
            )
            yield dirpath, dirs, media_files

            # Calculate current depth relative to root_dir
            current_depth = len(Path(dirpath).parts) - baseline_depth

            # If we have reached the max depth, clear 'dirs' in-place
            # so os.walk won't dig any deeper
            if current_depth >= max_depth:
                del dirs[:]  # or dirs.clear()

    # Initial function; runs on "Execute" button press
    def check_recursive(self):
        modifier = 0  # For starting index of img_series
        filetype = self.filetype_var.get()  # CSV or Excel
        recursive = self.recursive_var.get()  # Get status of recursive_checkbox
        debug = self.debug_var.get()
        output_utc = self.utc_var.get()
        date_range = self.date_range_var.get()
        output_gps = self.gps_var.get()
        output_dimensions = False
        output_make = False
        output_model = False
        output_software = False
        output_lens_model = False
        output_aperture = False
        output_exposure_time = False
        output_focal_length = False
        output_iso = False
        start_date = None
        end_date = None
        if self.extra_exif_var.get():
            output_dimensions = self.dimensions_var.get()
            output_make = self.make_var.get()
            output_model = self.model_var.get()
            output_software = self.software_var.get()
            output_lens_model = self.lens_model_var.get()
            output_aperture = self.aperture_var.get()
            output_exposure_time = self.exposure_time_var.get()
            output_focal_length = self.focal_length_var.get()
            output_iso = self.iso_var.get()
        if debug:  # No need to set output_path every time on debug mode
            self.output_path = Path.home() / "Downloads"
        else:
            if self.output_path is None:
                messagebox.showinfo("No output path.", message="No output path was set, and debug is not checked.")
                return
        if self.directory_path is None:  # Validating paths
            messagebox.showerror(  # If no output/directory path was set, error to allow for changes
                "Image directory not set.", message="Please set an image/video directory path."
            )
            return
        val = self.modifier_entry.get().strip()
        if val == "Starting index (Img # Series)" or val == "":
            modifier = 0
        elif val.isdigit() and int(val) > 0:
            modifier = int(val) - 1
        else:
            messagebox.showerror("Numbers only.", message="Starting index must be a whole number greater than zero.")
            return
        if recursive:  # Get maxdepth entry
            val = self.maxdepth_entry.get().strip()
            if val.isdigit() and int(val) > 0:  # Make sure starting index is valid digit
                self.maxdepth = int(val)  # We start at 1 by default
            elif val == "Recursion Depth (#)" or val == "":  # Placeholder or empty is rejected.
                messagebox.showinfo(
                    "Recursion Depth not set.", message="Recursion Depth not set, defaulting to 1 subfolder."
                )
                self.maxdepth = 1
            else:
                messagebox.showerror(
                    "Numbers only.", message="Recursion Depth must be a whole number greater than zero."
                )
                return
        else:
            self.maxdepth = 0
        if (
            filetype == "CSV" or filetype == "JSON"
        ) and self.hyperlink_var.get():  # CSV doesn't have hyperlinks, ask if they want to continue or change options
            proceed = messagebox.askyesno(
                "Hyperlinks Unsupported.",
                message="Hyperlinks are Excel/Markdown only. Please select Excel/Markdown for hyperlinks. Proceed without?",
            )
            if not proceed:
                return
        if date_range:
            start_date = self.start_date_entry.get_date()
            end_date = self.end_date_entry.get_date()
            if not (start_date or end_date):
                messagebox.showinfo(
                    "Date Range Unset", message="Date Range is checked, but no date(s) were input. Proceeding without."
                )
                self.date_range_var.set(False)
            else:
                if start_date and end_date and start_date > end_date:
                    messagebox.showerror("Invalid range", "Start date must be on or before end date.")
                    return
        # Fresh scan: explicitly clear the event, then reset UI state
        self.cancel_event.clear()
        self.reset()
        name = self.name_entry.get().strip()
        if name and name != "Filename (default output.filetype)":
            final_output = Path(self.output_path) / self.clean_name(name)
        else:
            ext = self.filetype_to_ext[filetype]
            final_output = Path(self.output_path) / f"output.{ext}"  # Default filename
        if not recursive:
            try:
                with os.scandir(self.directory_path) as entries:
                    count = sum(
                        1
                        for e in entries
                        if e.is_file()
                        and e.name.lower().endswith(PHOTO_TYPES)
                        and not self._check_hidden(e.name, self.directory_path)
                    )
            except OSError:
                count = 0
            self._set_total_files(count)
        if filetype != "CSV" and filetype != "Markdown":
            if recursive:
                self._start_scan(
                    recursive,
                    final_output,
                    modifier,
                    debug,
                    output_utc,
                    output_dimensions,
                    output_make,
                    output_model,
                    output_software,
                    output_lens_model,
                    output_aperture,
                    output_exposure_time,
                    output_focal_length,
                    output_iso,
                    output_gps,
                    date_range,
                    start_date,
                    end_date,
                )
            else:
                if self.total_files > 0:
                    self._start_scan(
                        recursive,
                        final_output,
                        modifier,
                        debug,
                        output_utc,
                        output_dimensions,
                        output_make,
                        output_model,
                        output_software,
                        output_lens_model,
                        output_aperture,
                        output_exposure_time,
                        output_focal_length,
                        output_iso,
                        output_gps,
                        date_range,
                        start_date,
                        end_date,
                    )
                else:
                    messagebox.showerror(
                        "Empty directory", message="No photos were found. Please select a valid directory"
                    )
                    return
        else:  # Prompt for multiple CSV or Markdown files output
            if recursive:
                ok = messagebox.askyesno(
                    f"Multiple {filetype} Files",
                    message=f"Recursive mode on {filetype} output will create multiple {filetype} files, one for each valid folder. Proceed?",
                )
                if ok:
                    self._start_scan(
                        recursive,
                        final_output,
                        modifier,
                        debug,
                        output_utc,
                        output_dimensions,
                        output_make,
                        output_model,
                        output_software,
                        output_lens_model,
                        output_aperture,
                        output_exposure_time,
                        output_focal_length,
                        output_iso,
                        output_gps,
                        date_range,
                        start_date,
                        end_date,
                    )
                else:
                    return
            else:
                if self.total_files > 0:
                    self._start_scan(
                        recursive,
                        final_output,
                        modifier,
                        debug,
                        output_utc,
                        output_dimensions,
                        output_make,
                        output_model,
                        output_software,
                        output_lens_model,
                        output_aperture,
                        output_exposure_time,
                        output_focal_length,
                        output_iso,
                        output_gps,
                        date_range,
                        start_date,
                        end_date,
                    )
                else:
                    messagebox.showerror(
                        "Empty directory", message="No files were found. Please select a valid directory"
                    )
                    return

    # XML forbids control characters that sometimes are used as padding, so scrub them out.
    def _sanitize_for_excel(self, df):
        copy = df.copy()
        if copy.empty:
            return copy
        for col in copy.columns:
            current_col = copy[col]
            if current_col.dtype == object or pd.api.types.is_string_dtype(current_col):
                copy[col] = current_col.apply(lambda v: XML_ILLEGAL_CHARS.sub("", v) if isinstance(v, str) else v)
        return copy

    # For Sheet Names
    def verify_name(self, name, used):
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

    # For filenames
    def clean_name(self, name):
        # Windows-illegal filename characters
        illegal_chars = ("<", ">", ":", '"', "/", "\\", "|", "?", "*")
        for c in illegal_chars:
            name = name.replace(c, "_")
        # Trim whitespace and trailing dots (Windows strips trailing dots silently)
        name = name.strip().rstrip(".")
        # Fall back if the user typed only illegal chars or spaces
        if len(name) < 1:
            name = "output"
        # Split extension once so reserved-name and length checks see the stem.
        # Preserve the case of the extension as typed by the user.
        suffix = Path(name).suffix.lower()
        selected = self.filetype_var.get()
        selected = self.filetype_to_ext[selected]
        if selected == suffix:
            stem = name[: -len(suffix)]
            ext = name[-len(suffix) :]
        elif suffix:
            ext = selected
            stem = name[: -len(suffix)]
        else:  # No suffix
            ext = selected
            stem = name

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

    # Gets called as first scan function, assumes irregular pattern
    # Paths supplied by user or debug mode
    def sort_and_extract(
        self,
        directory_path,
        modifier,
        debug,
        media_files,
        output_utc,
        output_dimensions,
        output_make,
        output_model,
        output_software,
        output_lens_model,
        output_aperture,
        output_exposure_time,
        output_focal_length,
        output_iso,
        output_gps,
        date_range,
        start_date,
        end_date,
        progress_callback=None,
    ):
        processed = 0  # Processed files this turn; increments by photos_before_video, although scan_image only scans last photo of a series
        skipped = 0  # Skipped files this turn
        output_series = True  # If photos_before_video is less than MAX_PHOTOS_BEFORE_VIDEO.
        data = self._empty_scan_data()  # Data dictionary
        img_series = []
        photos_before_video_updated = False
        i = 0  # Internal usage to scan files
        index = 1  # For img_series generation
        regular_pattern_found = False  # If a regular pattern from pattern_check and photos_before_video found
        photos_before_video = 0  # Default all images
        first_photo_found = False
        try:
            # Initial check: if the first file is a video and second file is photo
            first_video_orphan = False
            if media_files and media_files[0].lower().endswith(VIDEO_TYPES):
                leading_videos = 0
                while leading_videos < len(media_files) and media_files[leading_videos].lower().endswith(VIDEO_TYPES):
                    leading_videos += 1

                if leading_videos > 1:
                    media_files = media_files[leading_videos:]
                elif leading_videos == 1 and len(media_files) > 1 and media_files[1].lower().endswith(PHOTO_TYPES):
                    if debug:
                        first_video_orphan = False  # keep it as part of the series
                    else:
                        first_video_orphan = self._ask_yes_no_threadsafe(
                            "Video First",
                            f"Video was found first in {directory_path}. Is it an orphan? (Please check)",
                        )
                        if first_video_orphan:
                            media_files = media_files[1:]
                    if self.cancel_event.is_set():
                        return processed, skipped
            # Iterates through every file in the directory
            for file in media_files:
                if self.cancel_event.is_set():
                    return processed, skipped
                # If file is a photo, extract metadata
                if file.lower().endswith(PHOTO_TYPES):
                    pattern_check = 1  # Lookahead counter for finding regular patterns/irregularities
                    if not first_photo_found and not first_video_orphan:
                        index = 1
                        first_photo_found = True
                    if not photos_before_video_updated:
                        photos_before_video += 1
                        while not photos_before_video_updated:  # Find the pattern
                            if i + pattern_check < len(media_files):
                                if (
                                    media_files[i + pattern_check].lower().endswith(PHOTO_TYPES)
                                ):  # Keep incrementing until video is found
                                    pattern_check += 1
                                    photos_before_video += 1
                                else:  # Video was detected
                                    photos_before_video_updated = True
                                    if (
                                        photos_before_video > MAX_PHOTOS_BEFORE_VIDEO and not debug
                                    ):  # Pattern not found, usually not more than 5 images + 1 video. Do not output series.
                                        output_series = False
                            else:  # All photos found
                                photos_before_video_updated = True
                                photos_before_video = 0
                        pattern_check = 1  # Reset for next check
                    if (i == 0 and photos_before_video == 0) or output_series == False:
                        # For images-only or no Img # Series collumn
                        processed = 0
                        skipped = 0
                        data = self._empty_scan_data()
                        i = 0
                        img_series = None
                        try:
                            # Iterates through every file in the directory
                            while media_files and i < len(media_files):
                                if self.cancel_event.is_set():
                                    return processed, skipped
                                # If file is an image, extract metadata, skips videos
                                if media_files[i].lower().endswith(PHOTO_TYPES):
                                    ok = self.scan_image(
                                        directory_path,
                                        i,
                                        data,
                                        media_files,
                                        output_utc,
                                        output_dimensions,
                                        output_make,
                                        output_model,
                                        output_software,
                                        output_lens_model,
                                        output_aperture,
                                        output_exposure_time,
                                        output_focal_length,
                                        output_iso,
                                        output_gps,
                                        date_range,
                                        start_date,
                                        end_date,
                                    )
                                    if not ok:
                                        i += 1
                                        skipped += 1
                                        if progress_callback:
                                            progress_callback(processed, skipped, directory_path)
                                        continue
                                    processed += 1
                                    if progress_callback:
                                        progress_callback(processed, skipped, directory_path)
                                i += 1
                        except (FileNotFoundError, PermissionError):
                            self.collected_warnings["Directory Error"].append(f"{directory_path}")
                            skipped_count = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES))
                            return 0, skipped_count
                        except OSError:
                            if media_files and i < len(media_files):
                                self.collected_warnings["Scan Error"].append(f"[{directory_path}]\\{media_files[i]}")
                            skipped_count = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES))
                            return 0, skipped_count
                        except Exception as e:  # noqa: BLE001
                            self.collected_warnings["Unexpected"].append(
                                f"[{directory_path}]: {e}\n{traceback.format_exc()}"
                            )
                            skipped_count = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES))
                            return 0, skipped_count

                        fixed_date, fixed_time = self.fix_time(
                            output_utc, data["Dates"], data["Offsets"], data["Images"], directory_path
                        )
                        data["Dates"] = fixed_date
                        data["Times"] = fixed_time
                        if output_series:
                            img_series = [str(i + modifier) for i in range(1, len(data["Images"]) + 1)]
                        self.create_dataframe(
                            img_series,
                            data,
                            directory_path,
                            output_series,
                            output_dimensions,
                            output_make,
                            output_model,
                            output_software,
                            output_lens_model,
                            output_aperture,
                            output_exposure_time,
                            output_focal_length,
                            output_iso,
                            output_gps,
                        )
                        return processed, skipped  # Recursive mode
                    if (
                        photos_before_video_updated and regular_pattern_found == False
                    ):  # No pattern found yet, or is in between sets
                        end = False  # For scanning last files in a pattern
                        while pattern_check < photos_before_video:
                            if photos_before_video + i > len(media_files) - 1:
                                regular_pattern_found = True
                                end = True
                                break
                            pattern_check += 1
                        if not end:  # Not nearing the end of files to scan/check yet
                            if i + pattern_check < len(media_files) and media_files[i + pattern_check].lower().endswith(
                                VIDEO_TYPES
                            ):  # Verifies expected pattern
                                regular_pattern_found = True
                                for photo_check in range(photos_before_video):
                                    idx = i + photo_check
                                    if idx >= len(media_files) or not media_files[idx].lower().endswith(PHOTO_TYPES):
                                        regular_pattern_found = False
                                        break
                            else:
                                regular_pattern_found = False
                            if not regular_pattern_found:  # Not regular pattern
                                ok = self.scan_image(
                                    directory_path,
                                    i,
                                    data,
                                    media_files,
                                    output_utc,
                                    output_dimensions,
                                    output_make,
                                    output_model,
                                    output_software,
                                    output_lens_model,
                                    output_aperture,
                                    output_exposure_time,
                                    output_focal_length,
                                    output_iso,
                                    output_gps,
                                    date_range,
                                    start_date,
                                    end_date,
                                )  # Scan image as one-off
                                if not ok:
                                    i += 1
                                    index += 1  # Skipped image still consumes a series number; continue skips bottom increment
                                    skipped += 1
                                    if progress_callback:
                                        progress_callback(processed, skipped, directory_path)
                                    continue
                                processed += 1  # Scan went ok, add one-off as processed
                                img_series.append(str(index + modifier))  # Incorrect pattern found, images first
                                if progress_callback:
                                    progress_callback(processed, skipped, directory_path)
                        else:  # Nearing end of directory listing
                            for r in range(i, len(media_files)):
                                if self.cancel_event.is_set():
                                    return processed, skipped
                                if media_files[r].lower().endswith(PHOTO_TYPES):
                                    ok = self.scan_image(
                                        directory_path,
                                        r,
                                        data,
                                        media_files,
                                        output_utc,
                                        output_dimensions,
                                        output_make,
                                        output_model,
                                        output_software,
                                        output_lens_model,
                                        output_aperture,
                                        output_exposure_time,
                                        output_focal_length,
                                        output_iso,
                                        output_gps,
                                        date_range,
                                        start_date,
                                        end_date,
                                    )
                                    if not ok:
                                        skipped += 1
                                    else:
                                        processed += 1
                                        img_series.append(str(r - i + index + modifier))
                                    if progress_callback:
                                        progress_callback(processed, skipped, directory_path)
                            break  # exit the outer `for file in data["Images"]:` loop
                    # Always increment
                    i += 1
                    index += 1
                else:  # File was a video
                    # If the first file was a video (not orphan), count the photos after it to set the pattern
                    if (
                        i == 0 and not first_video_orphan
                    ):  # First video is part of series, so it is video, photos_before_video photos, then start of next block with video.
                        pattern_check = 1
                        while photos_before_video_updated == False:  # Find the pattern
                            if i + pattern_check < len(media_files):
                                if media_files[i + pattern_check].lower().endswith(PHOTO_TYPES):
                                    photos_before_video += 1
                                    pattern_check += 1
                                else:
                                    photos_before_video_updated = True
                                    if photos_before_video > MAX_PHOTOS_BEFORE_VIDEO and not debug:
                                        output_series = False
                            else:
                                photos_before_video_updated = True
                                photos_before_video = 0
                        pattern_check = 1  # Reset as always

                    # Standard pattern found logic otherwise
                    if regular_pattern_found:
                        ok = self.scan_image(
                            directory_path,
                            i - 1,
                            data,
                            media_files,
                            output_utc,
                            output_dimensions,
                            output_make,
                            output_model,
                            output_software,
                            output_lens_model,
                            output_aperture,
                            output_exposure_time,
                            output_focal_length,
                            output_iso,
                            output_gps,
                            date_range,
                            start_date,
                            end_date,
                        )
                        if not ok:
                            i += 1
                            index += 1
                            skipped += photos_before_video
                            regular_pattern_found = False
                            continue
                        processed += photos_before_video
                        if not first_video_orphan:
                            img_series.append(
                                str(index - photos_before_video + modifier)
                                + "-"
                                + str(index + modifier)  # Not index - 1 + modifier b/c videos count in a series
                            )  # Image + video series
                        if progress_callback:
                            progress_callback(processed, skipped, directory_path)
                        regular_pattern_found = False
                    i += 1  # increment, essentially skipping videos
                    index += 1
        except (FileNotFoundError, PermissionError):
            self.collected_warnings["Directory Error"].append(f"{directory_path}")
            skipped_count = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES))
            return 0, skipped_count
        except OSError:
            if media_files and i < len(media_files):
                self.collected_warnings["Scan Error"].append(f"[{directory_path}]\\{media_files[i]}")
            skipped_count = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES))
            return 0, skipped_count
        except Exception as e:  # noqa: BLE001
            self.collected_warnings["Unexpected"].append(f"[{directory_path}]: {e}\n{traceback.format_exc()}")
            skipped_count = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES))
            return 0, skipped_count
        fixed_date, fixed_time = self.fix_time(
            output_utc, data["Dates"], data["Offsets"], data["Images"], directory_path
        )
        data["Dates"] = fixed_date
        data["Times"] = fixed_time
        self.create_dataframe(
            img_series,
            data,
            directory_path,
            output_series,
            output_dimensions,
            output_make,
            output_model,
            output_software,
            output_lens_model,
            output_aperture,
            output_exposure_time,
            output_focal_length,
            output_iso,
            output_gps,
        )
        return processed, skipped  # For tallying total processed and skipped

    # Handles time and date formatting, along with UTC offsets
    def fix_time(self, output_utc, list_of_dates, list_of_offsets, list_of_images, directory):
        # Input format: "YYYY:MM:DD HH:MM:SS"
        fixed_time = []
        fixed_date = []
        for offset_index, d in enumerate(list_of_dates):  # Split the EXIF metadata into a date list and time list (24h)
            date_str = str(d)
            if " " in date_str:
                try:
                    dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    fixed_date.append(date_str)
                    fixed_time.append("")
                    continue
                if output_utc:
                    offset = list_of_offsets[offset_index]
                    if offset:
                        try:
                            offset = offset.split(":")  # Format is +-XX:00 so turn into +-XX
                            hours = offset[0]
                            minutes = int(offset[1])
                            sign = hours[0:1]
                            hours = int(hours[1:])
                            if sign == "-":
                                dt += timedelta(hours=hours, minutes=minutes)
                            else:
                                dt -= timedelta(hours=hours, minutes=minutes)
                        except (AttributeError, IndexError, ValueError, TypeError):
                            self.collected_warnings["Bad Timestamp"].append(
                                f"{os.path.join(directory, list_of_images[offset_index])}"
                            )
                            fixed_date.append(date_str)
                            fixed_time.append("")  # or "00:00:00" if preferred
                            continue
                dt = dt.strftime("%m/%d/%Y %H:%M:%S")
                dt = dt.split(" ")
                fixed_time.append(dt[1])
                fixed_date.append(dt[0])
            else:
                try:
                    fixed_date.append(datetime.strptime(date_str, "%Y:%m:%d").strftime("%m/%d/%Y"))
                except ValueError:
                    fixed_date.append(date_str)
                fixed_time.append("")  # or "00:00:00" if preferred
        return fixed_date, fixed_time

    # Creates dataframes for create_sheet to use
    def create_dataframe(
        self,
        img_series,
        data,
        directory_path,
        output_series,
        output_dimensions,
        output_make,
        output_model,
        output_software,
        output_lens_model,
        output_aperture,
        output_exposure_time,
        output_focal_length,
        output_iso,
        output_gps,
    ):
        if data["Images"]:  # Make sure images are present.
            df_data = {
                "Files": data["Images"],
                "Dates": data["Dates"],
                "Time": data["Times"],
            }
            if output_dimensions:
                df_data["Dimensions"] = data["Dimensions"]
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
            if output_gps:
                df_data["GPS Latitude"] = data["GPS_Latitudes"]
                df_data["GPS Longitude"] = data["GPS_Longitudes"]
            if output_series:
                df_data["Img # Series"] = img_series  # Add on img_series
            else:
                self.collected_warnings["Irregular"].append(
                    directory_path
                )  # If irregular pattern starts with more than MAX_PHOTOS_BEFORE_VIDEO images in a row, will break program, so error.
            df = pd.DataFrame(df_data)  # Create DataFrame
            current_sheet_name = self.verify_name(self.current_sheet_name, self.used)
            self.results.append((df, current_sheet_name, directory_path))
        else:
            # No files are present
            return

    # Makes CSVs or Excel files
    def create_sheet(self, output_path, total_processed, total_skipped):  # File creation
        try:
            # Check for empty results before prompting so the user isn't asked to overwrite for nothing
            if not self.results:
                messagebox.showerror("No data", message="No valid photos with metadata were found.")
                if not self.keepopen_var.get():
                    self._on_close()
                return
            filetype = self.filetype_var.get()
            proceed = True
            if (filetype == "Excel" or filetype == "JSON") and output_path.exists():
                proceed = messagebox.askyesno(
                    "Overwrite?", message=output_path.as_posix() + " \nalready exists. Overwrite?"
                )
            if proceed:
                # Data was found
                if filetype == "Excel":
                    with pd.ExcelWriter(output_path) as writer:  # Opens ExcelWriter and closes automatically
                        for sheet_df, sheet_name, _ in self.results:
                            self._sanitize_for_excel(sheet_df).to_excel(writer, sheet_name=sheet_name, index=False)
                    if self.hyperlink_var.get():
                        self.add_hyperlinks(output_path.as_posix())
                    if not self.cancel_event.is_set():
                        messagebox.showinfo(
                            "Success!",
                            message="Images: "
                            + str(total_processed)
                            + "\nImages skipped: "
                            + str(total_skipped)
                            + "\nOutput: "
                            + output_path.as_posix(),
                        )
                elif filetype == "CSV":  # CSV mode
                    files_written = 0
                    for sheet_df, sheet_name, _ in self.results:
                        csv_path = output_path.with_suffix("").as_posix() + f"_{self.clean_name(sheet_name)}"
                        if Path(csv_path).exists():
                            proceed = messagebox.askyesno(
                                "Overwrite?", message=csv_path + " \nalready exists. Overwrite?"
                            )
                        if proceed:
                            sheet_df.to_csv(csv_path, index=False)
                            files_written += 1
                        else:
                            proceed = True  # Reset it
                            continue
                    if files_written > 0 and not self.cancel_event.is_set():
                        messagebox.showinfo(
                            "Success!",
                            message="Images: "
                            + str(total_processed)
                            + "\nImages skipped: "
                            + str(total_skipped)
                            + "\nFiles written: "
                            + str(files_written)
                            + "\nLocated at: "
                            + output_path.parent.as_posix(),
                        )
                    else:
                        messagebox.showinfo("No output.", message="No files were written.")
                elif filetype == "JSON":  # Local export time
                    json_data = {"exported_at": datetime.now().isoformat(), "sheets": {}}
                    for sheet_df, sheet_name, _ in self.results:
                        json_data["sheets"][sheet_name] = json.loads(sheet_df.to_json(orient="records"))
                    output_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
                    if not self.cancel_event.is_set():
                        messagebox.showinfo(
                            "Success!",
                            message="Images: "
                            + str(total_processed)
                            + "\nImages skipped: "
                            + str(total_skipped)
                            + "\nOutput: "
                            + output_path.as_posix(),
                        )
                elif filetype == "Markdown":
                    files_written = 0
                    for sheet_df, sheet_name, directory in self.results:
                        md_path = Path(output_path.with_suffix("").as_posix() + f"_{self.clean_name(sheet_name)}")
                        if md_path.exists():
                            proceed = messagebox.askyesno(
                                "Overwrite?", message=f"{md_path}\nalready exists. Overwrite?"
                            )
                        if proceed:
                            md_path.write_text(
                                self._dataframe_to_txt(sheet_df, directory, hyperlinks=self.hyperlink_var.get()),
                                encoding="utf-8",
                            )
                            files_written += 1
                        else:
                            proceed = True
                            continue
                    if files_written > 0 and not self.cancel_event.is_set():
                        messagebox.showinfo(
                            "Success!",
                            message="Images: "
                            + str(total_processed)
                            + "\nImages skipped: "
                            + str(total_skipped)
                            + "\nFiles written: "
                            + str(files_written)
                            + "\nLocated at: "
                            + output_path.parent.as_posix(),
                        )
                    else:
                        messagebox.showinfo("No output.", message="No files were written.")
                self.progress_var.set(100)
                self.percentage_done.set("100%")
            else:  # Proceed is False
                messagebox.showinfo("Cancelled", message="File not overwritten. Cancelled successfully.")
                if not self.keepopen_var.get():
                    self._on_close()
            if self.collected_warnings:
                output = ""
                # Writes error messages from the dictionary collected_warnings
                for error, file in self.collected_warnings.items():
                    output += f"{error}\n"
                    if error == "Scan Error":
                        output += "These files are corrupt or non-image files, and were excluded."
                    elif error == "No Metadata":
                        output += "These files had no metadata to scan and were excluded."
                    elif error == "Directory Error":
                        output += "File/Directory couldn't be accessed."
                    elif error == "Irregular":
                        output += f"Irregular pattern (started with more than {MAX_PHOTOS_BEFORE_VIDEO} before a video)\n Please add mock files to the beginning to set correct pattern.\nFor example, if the pattern is 3 photos and 1 video, choose 3 photos and 1 video and duplicate them, naming them to be first when sorted, like DCSF0000."
                    elif error == "Hyperlink Error":
                        output += "The following sheets do not have hyperlinks."
                    elif error == "Bad Timestamp":
                        output += "The following files did not have embedded UTC offsets."
                    elif error == "Unexpected":
                        output += (
                            "Unexpected Errors - please report at https://github.com/Pianocraft1YT/MetadataExtractor/"
                        )
                    for filename in file:
                        output += f"\n{filename}\n"
                try:
                    log_path = output_path.parent / "warnings.log"
                    log_path.write_text(output, encoding="utf-8")
                    summary = f"{len(self.collected_warnings)} warning categories.\n\nFull details: {log_path.as_posix()}\n\nPlease verify any issues"
                    messagebox.showwarning("Warning(s)", message=summary)
                except OSError:
                    messagebox.showerror("Log Error", message=f"Couldn't write log file to {log_path}.\n{summary}")
            if not self.keepopen_var.get():  # Checks to close program or not
                self._on_close()
        except OSError as e:
            messagebox.showerror(
                "Error writing output", f"Is another program using {output_path.as_posix()}?\n\nError: {e}"
            )
            if not self.keepopen_var.get():
                self._on_close()
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Unexpected error", f"{e}\n\n{traceback.format_exc()}")
            if not self.keepopen_var.get():
                self._on_close()

    # Initialization function when constructed
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Metadata Extractor")
        self.frame = tk.Frame(self.root)
        self.filetype_frame = tk.Frame(self.frame)
        self.sort_methods_frame = tk.Frame(self.frame)
        self.sort_methods_label = tk.Label(self.sort_methods_frame, text="Sort Method (default filename)")
        self.execute_button = tk.Button(self.frame, command=self.check_recursive, text="Execute")
        self.cancel_button = tk.Button(self.frame, command=self.cancel, text="Cancel", state="disabled")
        self.set_directory_button = tk.Button(self.frame, command=self.set_dir, text="Set folder with images")
        self.set_output_button = tk.Button(self.frame, command=self.set_output, text="Set output folder")
        self.keepopen_var = tk.BooleanVar(value=False)
        self.keepopen_checkbox = tk.Checkbutton(self.frame, text="Keep Open", variable=self.keepopen_var)
        self.recursive_var = tk.BooleanVar(value=False)
        self.recursive_checkbox = tk.Checkbutton(
            self.frame, text="Recursive Mode", variable=self.recursive_var, command=self.recursive_input
        )
        self.utc_var = tk.BooleanVar(value=False)
        self.utc_checkbox = tk.Checkbutton(self.frame, text="Time in UTC", variable=self.utc_var)
        self.debug_var = tk.BooleanVar(value=False)
        self.debug_checkbox = tk.Checkbutton(
            self.frame, text="Debug Mode", variable=self.debug_var, command=self.debug_warning
        )
        self.filetype_var = tk.StringVar(value="Excel")
        self.sort_methods_var = tk.StringVar(value="Filename")
        self.hyperlink_var = tk.BooleanVar(value=True)
        self.hyperlink_checkbox = tk.Checkbutton(self.frame, text="Add Hyperlinks", variable=self.hyperlink_var)
        self.name_entry = tk.Entry(self.frame, width=30, foreground="gray")
        self.name_entry.insert(0, "Filename (default output.filetype)")
        self.modifier_entry = tk.Entry(self.frame, width=30, foreground="gray")
        self.modifier_entry.insert(0, "Starting index (Img # Series)")
        self.maxdepth_entry = tk.Entry(self.frame, width=20, foreground="gray")
        self.maxdepth_entry.insert(0, "Recursion Depth (#)")
        self.date_range_var = tk.BooleanVar(value=False)
        self.date_range_checkbox = tk.Checkbutton(
            self.frame, text="Date Range (Local Time)", variable=self.date_range_var, command=self.date_range
        )
        self.start_date_entry = DateEntry(self.frame, date_pattern="%Y/%m/%d", value=None)
        self.end_date_entry = DateEntry(self.frame, date_pattern="%Y/%m/%d", value=None)
        self.date_notice_label = tk.Label(self.frame, text="One date required; two dates accepted")
        self.start_date_label = tk.Label(self.frame, text="Start Date")
        self.end_date_label = tk.Label(self.frame, text="End Date")
        self.name_entry.bind("<FocusIn>", self.nameFocusIn)
        self.name_entry.bind("<FocusOut>", self.nameFocusOut)
        self.modifier_entry.bind("<FocusIn>", self.seriesFocusIn)
        self.modifier_entry.bind("<FocusOut>", self.seriesFocusOut)
        self.maxdepth_entry.bind("<FocusIn>", self.maxDepthFocusIn)
        self.maxdepth_entry.bind("<FocusOut>", self.maxDepthFocusOut)
        self.gps_var = tk.BooleanVar(value=False)
        self.gps_checkbox = tk.Checkbutton(self.frame, text="GPS", variable=self.gps_var, command=self.gps_warning)
        self.gps_warning_label = tk.Label(
            self.frame, text="Coordinates may reveal sensitive location information", foreground="gray"
        )
        self._dialog_lock = threading.Lock()
        # Extra EXIF checkboxes
        self.extra_exif_frame = tk.Frame(self.root)
        self.extra_exif_var = tk.BooleanVar(value=False)
        self.extra_exif_checkbox = tk.Checkbutton(
            self.frame, text="Extra Metadata", variable=self.extra_exif_var, command=self.extra_exif
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

        # Pack Extra Checkboxes
        self.dimensions_checkbox.pack()
        self.make_checkbox.pack()
        self.model_checkbox.pack()
        self.software_checkbox.pack()
        self.lens_model_checkbox.pack()
        self.aperture_checkbox.pack()
        self.exposure_checkbox.pack()
        self.focal_length_checkbox.pack()
        self.iso_checkbox.pack()

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
        # For sorting
        self.sort_methods = ["Filename", "Date (Oldest)", "Date (Newest)"]
        # For recursion
        self.maxdepth = 0
        # For cancel event (set by cancel(), checked in loops, cleared in check_recursive)
        self.cancel_event = threading.Event()
        # Guard so _clean_up can't fire twice through nested dialogs
        self._scan_running = False
        # For ETA
        self.time_started = None
        # For filetype resolving
        self.filetype_to_ext = {"Excel": ".xlsx", "CSV": ".csv", "JSON": ".json", "Markdown": ".md"}
        # For blocking
        self._dialog_answer = None
        self._dialog_event = threading.Event()
        # Tracking destroyed root
        self._destroyed = False
        # Progress bar widgets
        self.current_directory = tk.StringVar()
        self.scanned_count = tk.StringVar()
        self.skipped_count = tk.StringVar()
        self.percentage_done = tk.StringVar()
        self.eta = tk.StringVar()
        self.elapsed_time = tk.StringVar()
        self.progress_frame = tk.Frame(self.root)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var)
        self.directory_label = tk.Label(self.progress_frame, textvariable=self.current_directory)
        self.scanned_label = tk.Label(self.progress_frame, textvariable=self.scanned_count)
        self.percent_label = tk.Label(self.progress_frame, textvariable=self.percentage_done)
        self.skipped_label = tk.Label(self.progress_frame, textvariable=self.skipped_count)
        self.eta_label = tk.Label(self.progress_frame, textvariable=self.eta)
        self.total_files = 0
        self.elapsed_label = tk.Label(self.progress_frame, textvariable=self.elapsed_time)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._load_settings()

    # After initialization
    def run(self):
        # Pack main widgets
        self.frame.pack()
        self.set_directory_button.pack()
        self.set_output_button.pack()
        self.name_entry.pack()
        self.modifier_entry.pack()
        self.recursive_checkbox.pack()
        self.hyperlink_checkbox.pack()
        self.date_range_checkbox.pack()
        self.utc_checkbox.pack()
        self.gps_checkbox.pack()
        self.filetype_frame.pack(side="top")
        self.sort_methods_frame.pack(side="top")
        self.sort_methods_label.pack()
        for sm in self.sort_methods:
            tk.Radiobutton(self.sort_methods_frame, text=sm, variable=self.sort_methods_var, value=sm).pack(side="left")
        for ft in self.filetypes:
            tk.Radiobutton(self.filetype_frame, text=ft, variable=self.filetype_var, value=ft).pack(side="left")
        self.execute_button.pack()
        self.cancel_button.pack()
        self.keepopen_checkbox.pack()
        self.debug_checkbox.pack()
        self.extra_exif_checkbox.pack()

        # Pack progress bar
        self.progress_frame.pack()
        self.progress_bar.pack()
        self.directory_label.pack()
        self.scanned_label.pack()
        self.percent_label.pack()
        self.skipped_label.pack()
        self.eta_label.pack()
        self.elapsed_label.pack()
        self.recursive_input()
        self.extra_exif()
        self.date_range()
        self.gps_warning()
        self.root.update_idletasks()  # flush pending layout
        self.root.geometry(f"350x{self.root.winfo_reqheight()}")  # fixed width, auto height
        self.root.mainloop()


# Always runs
if __name__ == "__main__":
    app = MetadataExtractor()  # Java: MetadataExtractor app = new MetadataExtractor(); (Constructor)
    app.run()
