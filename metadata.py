# Dear programmer:
# When I wrote this code, only God and I knew how it worked.
# Now, only God knows!
# 
# Therefore, if you trying to improve this,
# Please increment this counter as a warning
# For the next person:
# 
# hours_wasted_here = 58

# Coded by Pianocraft1YT
# Tutorial: https://youtu.be/ruWNKBdbYoo
# GitHub Repo: https://github.com/Pianocraft1YT/MetadataExtractor/

#Imports
import os
import sys
import threading
import tkinter as tk
import traceback
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

#For spreadsheet making
import openpyxl
import pandas as pd
from openpyxl.styles import Font
from PIL import Image, UnidentifiedImageError

#Constants
EXIF_DATETIME = 306
EXIF_DATETIME_ORIGINAL = 36867
EXIF_DATETIME_DIGITIZED = 36868
MAX_PHOTOS_BEFORE_VIDEO = 5
SHEET_NAME_MAX_CHARS = 31
EXIF_OFFSET_TIME_ORIGINAL = 36881

#Common video file formats to check
VIDEO_TYPES = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv")
#Common and uncommon image formats to check
PHOTO_TYPES = (".jpg", ".jpeg", ".heic", ".heif", ".png", ".tiff", ".tif",
            ".dng", ".crw", ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf",
            ".sr2", ".raf", ".rw2", ".raw", ".orf", ".ori", ".pef", ".ptx",
            ".rwl", ".3fr", ".fff", ".iiq", ".mos", ".x3f", ".kdc", ".dcr",
            ".dcs", ".srw", ".mrw")
class MetadataExtractor:

    #Cosmetic only, adds placeholder text in entry boxes
    def nameFocusIn(self, event):
        if self.name_entry.get() == "Filename (default output.filetype)":
            self.name_entry.delete(0, "end")
            self.name_entry.config(foreground="black")
    def nameFocusOut(self, event):
        if self.name_entry.get() == "":
            self.name_entry.insert(0, "Filename (default output.filetype)")
            self.name_entry.config(foreground="gray")
    def seriesFocusIn(self, event):
        if self.series_entry.get() == "Starting index (Img # Series)":
            self.series_entry.delete(0, "end")
            self.series_entry.config(foreground="black")
    def seriesFocusOut(self, event):
        if self.series_entry.get() == "":
            self.series_entry.insert(0, "Starting index (Img # Series)")
            self.series_entry.config(foreground="gray")
    def maxDepthFocusIn(self, event):
        if self.maxdepth_entry.get() == "Recursion Depth (#)":
            self.maxdepth_entry.delete(0, "end")
            self.maxdepth_entry.config(foreground="black")
    def maxDepthFocusOut(self, event):
        if self.maxdepth_entry.get() == "":
            self.maxdepth_entry.insert(0, "Recursion Depth (#)")
            self.maxdepth_entry.config(foreground="gray")
    # Show recursive_input entry box when recursive is checked
    def recursive_input(self):
        if self.recursive_var.get():
            self.maxdepth_entry.pack(before=self.hyperlink_checkbox)
        else:
            self.maxdepth_entry.pack_forget()

    # For debug_checkbox warning
    def debug_warning(self):
        if self.debug_var.get():
            self.debug_var.set(messagebox.askokcancel("Debug selected", message="Debug mode has been enabled.\nThis means that output directory is Path.home()/Downloads/output.filetype.\nSeries will always output regardles of irregularity.\n\nPlease disable if this was an accident."))

    # Helpers for progress bar
    def get_total_files(self, max_depth):
        file_count = 0
        for _, _, files in self.walk_to_depth(self.directory_path, max_depth): # HAve _ for unused
            file_count += sum(1 for entry in files if entry.lower().endswith(PHOTO_TYPES))
        return file_count
    # Updates the progress bar
    def update_progress(self, processed, skipped, current_dir):
        self.scanned_count.set(f"Scanned: {processed} / {self.total_files}")
        self.skipped_count.set(f"Skipped: {skipped}")
        if self.total_files > 0: # No divide-by-zero errors
            self.percentage_done.set(f"{round(((processed + skipped) / self.total_files) * 100, 1)}%")
            self.progress_var.set(round(((processed + skipped) / self.total_files) * 100, 1))
        else:
            self.percentage_done.set("0%")
            self.progress_var.set(0)
        self.current_directory.set(str(current_dir)[-30:]) #Truncate to not be too long, last 30 characters
    # Runs the threaded versions of the scan(s)
    def _run_scan_threaded(self, recursive, final_output, modifier):
        total_scanned, total_skipped = 0, 0
        try:
            if recursive:
                total_scanned, total_skipped = self.find_directories(self.directory_path, final_output, modifier, defer_create_sheet=True, progress_callback=lambda p, s, d: self.root.after(0, lambda p=p, s=s, d=d: self.update_progress(p, s, d))) #Run recursive mode
            else:
                total_scanned, total_skipped = self.sort_and_extract_irregular(self.directory_path, recursive, final_output, modifier, defer_create_sheet=True, progress_callback=lambda p, s, d: self.root.after(0, lambda p=p, s=s, d=d: self.update_progress(p, s, d)))
        finally:
            self.root.after(0, self._clean_up, final_output, recursive, total_scanned, total_skipped)
    def _clean_up(self, final_output, recursive, processed, skipped):
        self.execute_button.config(state="normal")
        self.create_sheet(final_output, recursive, processed, skipped)

    #To clean up any past executions
    def reset(self, recursive):
        self.used = set()
        self.results.clear()
        self.collected_warnings.clear()
        self.current_sheet_name = "Sheet"
        self.current_directory.set("")
        if recursive:
            self.total_files = self.get_total_files(self.maxdepth)
        else:
            with os.scandir(self.directory_path) as entries:
                self.total_files = sum(1 for entry in entries if entry.is_file() and entry.name.lower().endswith(PHOTO_TYPES))
        self.scanned_count.set(f"Scanned: 0 / {self.total_files}")
        self.skipped_count.set("Skipped: 0")
        self.percentage_done.set("0%")
        self.progress_var.set(0)
    # Core Functions

    #Gets called on set directory button press to set image directory
    def set_dir(self):
        selected = filedialog.askdirectory(title="Select a Directory")
        if selected:
            self.directory_path = Path(selected)

    #Gets called on set output button press
    def set_output(self):
        selected = filedialog.askdirectory(title="Select a Output Directory")
        if selected:
            self.output_path = Path(selected)

    #Image metadata extractor helper function
    def scan_image(self, directory_path, media_files, i, list_of_dates, list_of_images, list_of_offsets):
        offset = None
        try:
            with Image.open(Path(directory_path) / media_files[i]) as img: #open the image
                exif_data = img.getexif() #get the exif metadata
            dt = exif_data.get(EXIF_DATETIME_ORIGINAL) or exif_data.get(EXIF_DATETIME_DIGITIZED) or exif_data.get(EXIF_DATETIME) #only extract date and time
            if dt is None:
                self.collected_warnings["No Metadata"].append(f"[{directory_path}]\\{media_files[i]}")
                return False
            if self.timezone_var.get():
                offset = exif_data.get(EXIF_OFFSET_TIME_ORIGINAL)
        except (OSError, SyntaxError, ValueError, UnidentifiedImageError):
            self.collected_warnings["Scan Error"].append(f"[{directory_path}]\\{media_files[i]}")
            return False
        else: #No errors
            list_of_dates.append(dt) #Add to lists
            list_of_images.append(media_files[i])
            list_of_offsets.append(offset)
            return True

    #Hyperlink feature 
    def add_hyperlinks(self, excel_file):
        try:
            wb = openpyxl.load_workbook(excel_file)
            for df, sheet_name, directory in self.results:
                if not directory:
                    continue
                try:
                    ws = wb[sheet_name]
                    for cell in ws["A"][1:]:
                        if cell.value:
                            cell.hyperlink = (directory / cell.value).as_posix()
                            cell.font = Font(color="0563C1", underline="single")
                except Exception as e:  # noqa: BLE001
                    self.collected_warnings["Hyperlink Error"].append(sheet_name + f"\nError: {e}")
            wb.save(excel_file)
        except Exception as e:  # noqa: BLE001
            self.collected_warnings["Hyperlink Error"].append(f"Hyperlinks could not be added. \nError: {e}")

    #Finds subdirectories for recursive mode
    def find_directories(self, directory_path, final_output, modifier, progress_callback = None, defer_create_sheet=False):
        directories_to_scan = []
        sheet_names = []
        total_skipped = 0
        total_processed = 0
        for dirpath, dirs, files in self.walk_to_depth(directory_path, self.maxdepth): #Only one level of recursion
            if not any(f.lower().endswith(PHOTO_TYPES) for f in files):
                continue 
            dirpath = Path(dirpath)
            directories_to_scan.append(dirpath)
            rel = Path(os.path.relpath(dirpath, directory_path))
            sheet_name = "_".join(rel.parts)
            if len(sheet_name) > SHEET_NAME_MAX_CHARS:
                sheet_name = sheet_name[-SHEET_NAME_MAX_CHARS:]
            sheet_names.append(sheet_name)
        for path, sheet_name in zip(directories_to_scan, sheet_names):
            self.current_sheet_name = sheet_name

            if progress_callback:
                _base_p = total_processed
                _base_s = total_skipped
                wrapped_cb = lambda p, s, d, base_p=_base_p, base_s=_base_s: progress_callback(base_p + p, base_s + s, d)
            else:
                wrapped_cb = None

            p, s = self.sort_and_extract_irregular(
                path, True, final_output, modifier,
                progress_callback=wrapped_cb,
                defer_create_sheet=defer_create_sheet,
            )
            total_processed += p
            total_skipped += s
        if not defer_create_sheet:
            self.create_sheet(final_output, True, total_processed, total_skipped)
        return total_processed, total_skipped

    # Helper to find directories one-by-one to max_depth
    def walk_to_depth(self, root_dir, max_depth):
        # Normalize the path and count baseline separators
        root_dir = os.path.abspath(str(root_dir))
        baseline_depth = len(Path(root_dir).parts)

        for dirpath, dirs, files in os.walk(root_dir, topdown=True):
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(dirpath, d))]
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"System Volume Information", "$RECYCLE.BIN"}]
            dirs.sort()
            yield dirpath, dirs, files
            
            # Calculate current depth relative to root_dir
            current_depth = len(Path(dirpath).parts) - baseline_depth
            
            # If we have reached the max depth, clear 'dirs' in-place 
            # so os.walk won't dig any deeper
            if current_depth >= max_depth:
                del dirs[:]  # or dirs.clear()

    # Initial function; runs on "Execute" button press
    def check_recursive(self):
        proceed = True #For CSV not having hyperlinks
        modifier = 0 #For starting index of img_series
        filetype = self.filetype_var.get() #CSV or Excel
        recursive = self.recursive_var.get() #Get status of recursive_checkbox
        if self.debug_var.get(): #No need to set output_path every time on debug mode
            self.output_path = Path.home() / "Downloads"
        if self.directory_path is None or self.output_path is None: #Validating paths
            messagebox.showerror( #If no output/directory path was set, error to allow for changes
                "Invalid path(s) specified.", message="Please set an image/video directory path OR output path.")
            return
        val = self.series_entry.get().strip() #Modifier for Img # Series
        if val.isdigit() and int(val) > 0 and val != "1": #Make sure starting index is valid digit
            modifier = int(val) - 1 #We start at 1 by default, so minus 1 to not get off by one
        elif not (val == "Starting index (Img # Series)" or val == "" or val == "1"): #Placeholder, empty, or "1" means modifier stays 0; anything else errors
            messagebox.showerror("Numbers only.", message="Starting index must be a whole number greater than zero.")
            return
        if recursive: #Get maxdepth entry
            val = self.maxdepth_entry.get().strip()
            if val.isdigit() and int(val) > 0: #Make sure starting index is valid digit
                self.maxdepth = int(val) #We start at 1 by default
            elif not (val == "Recursion Depth (#)" or val == ""): #Placeholder or empty is rejected.
                messagebox.showerror("Numbers only.", message="Recursion Depth must be a whole number greater than zero.")
                return
        if filetype == "CSV" and self.hyperlink_var.get(): #CSV doesn't have hyperlinks, ask if they want to continue or change options
            proceed = messagebox.askyesno("Hyperlinks Unsupported.", message="Hyperlinks are unsupported with CSV. Please select Excel for hyperlinks. Proceed without?")
        if proceed:
            self.reset(recursive) #Clear old data
            if self.name_entry.get() != "Filename (default output.filetype)": #Placeholder text
                final_output = Path(self.output_path) / self.clean_name(self.name_entry.get()) #Clean_name to create valid names only
            else:
                ext = "csv" if filetype == "CSV" else "xlsx" #File extension for final output path
                final_output = Path(self.output_path) / f"output.{ext}" #Default filename
                # final_output = Path(self.output_path) / f"output.{filetype.lower() if filetype.lower() == "csv" else "xlsx"}"  #Doesn't work on Python 3.11
            self.execute_button.config(state="disabled") #Disable "Execute" button so everything doesn't break
            if filetype == "Excel":
                if recursive:
                    threading.Thread(target=self._run_scan_threaded, args=(True, final_output, modifier), daemon=True).start()
                else:
                    with os.scandir(self.directory_path) as entries:
                        photo_count = sum(1 for entry in entries if entry.is_file() and entry.name.lower().endswith(PHOTO_TYPES))
                        if photo_count > 0:
                           threading.Thread(target=self._run_scan_threaded, args=(False, final_output, modifier), daemon=True).start()
                        else:
                            messagebox.showerror("Empty directory", message="No files were found. Please select a valid directory")
                            return
            else: #Prompt for multiple CSV files output
                if recursive:
                    ok = messagebox.askyesno("Multiple CSV Files", message="Recursive mode on CSV output will create multiple CSVs, one for each valid folder. Proceed?")
                    if ok: threading.Thread(target=self._run_scan_threaded, args=(True, final_output, modifier), daemon=True).start()
                    else: return
                else: 
                    with os.scandir(self.directory_path) as entries:
                        photo_count = sum(1 for entry in entries if entry.is_file() and entry.name.lower().endswith(PHOTO_TYPES))
                        if photo_count > 0:
                            threading.Thread(target=self._run_scan_threaded, args=(False, final_output, modifier), daemon=True).start()
                        else:
                            messagebox.showerror("Empty directory", message="No files were found. Please select a valid directory")
                            return

    #For Sheet Names
    def verify_name(self, name, used):
        illegal_chars = ("[", "]", ":", "*", "?", "/", "\\") #Can't be in a sheet name
        for c in illegal_chars:
            name = name.replace(c, "_") #Replace any instances with "_"
        name = name[:SHEET_NAME_MAX_CHARS] #Truncate to SHEET_NAME_MAX_CHARS (31) characters max
        # Excel restrictions: apostrophes at start/end, reserved name "History"
        if name.startswith("'") or name.endswith("'"):
            name = name.strip("'")
        if name.lower() == "history":
            name = "History_"
        if len(name) < 1: #If no name, make default "Sheet"
            name = "Sheet"
        if name.lower() not in used: #Check if used already, duplicate sheet names not allowed
            used.add(name.lower())
            return name
        f = 2
        while True: #Name was used already
            suffix = "_" + str(f) #Infinitely try increasing _X numbers, from 2
            candidate = name[:SHEET_NAME_MAX_CHARS - len(suffix)] + suffix #Truncate original name
            if candidate.lower() not in used:
                used.add(candidate.lower())
                return candidate
            f += 1

    #For filenames
    def clean_name(self, name):
        #Windows-illegal filename characters
        illegal_chars = ("<", ">", ":", "\"", "/", "\\", "|", "?", "*")
        for c in illegal_chars:
            name = name.replace(c, "_")
        #Trim whitespace and trailing dots (Windows strips trailing dots silently)
        name = name.strip().rstrip(".")
        #Fall back if the user typed only illegal chars or spaces
        if len(name) < 1:
            name = "output"

        # Split extension once so reserved-name and length checks see the stem.
        # Preserve the case of the extension as typed by the user.
        suffix = Path(name).suffix.lower()
        if suffix in (".xlsx", ".csv"):
            stem = name[:-len(suffix)]
            ext = name[-len(suffix):]
        else:
            stem = name
            ext = ".xlsx" if self.filetype_var.get() == "Excel" else ".csv"

        # Windows reserved names — check the stem, not the full name
        reserved = {
            "CON", "PRN", "AUX", "NUL",
            "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
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

    #Gets called as first scan function, assumes irregular pattern, calls sort_and_extract() if photos_before_video > MAX_PHOTOS_BEFORE_VIDEO or all photos, no videos
    #Paths supplied by user or debug mode
    def sort_and_extract_irregular(self, directory_path, recursive, final_output, modifier, progress_callback=None, defer_create_sheet=False):
        processed = 0 #Processed this turn
        skipped = 0 #Skipped this turn
        output_series = True #If photos_before_video is less than MAX_PHOTOS_BEFORE_VIDEO.
        list_of_dates = []
        list_of_images = []
        list_of_offsets = []
        img_series = []
        photos_before_video_updated = False
        i = 0 #Internal usage to scan files
        index = 1 #External usage for "real" index
        pattern_check = 1 #Lookahead counter for finding regular patterns/irregularities
        regular_pattern_found = False #If a regular pattern from pattern_check and photos_before_video found
        initial_check = 1 #Finding pattern initially
        photos_before_video = 0 #Default all images
        try:
            #List all files in directory given
            all_files = os.listdir(directory_path)
            #Sorts files alphabetically, ignoring file extensions and capitalization, ignoring any non-photo or non-video files
            media_files = [f for f in all_files if f.lower().endswith(PHOTO_TYPES + VIDEO_TYPES) and os.path.isfile(os.path.join(directory_path, f))]
            media_files.sort(key=lambda x: os.path.splitext(x)[0].lower())
            # Initial check: if the first file is a video
            first_video_orphan = False #Default not an orphaned video
            if media_files and media_files[0].lower().endswith(VIDEO_TYPES):
                first_video_orphan = messagebox.askyesno("Video First", message=f"Video was found first in {directory_path}. Is it an orphan? (Please check)")
                if first_video_orphan:
                    media_files = media_files[1:] # Chop off orphan
            #Iterates through every file in the directory
            for file in media_files:
                #If file is not a video, extract metadata from the image.
                if not file.lower().endswith(VIDEO_TYPES):
                    if i == 0: #Image found first
                        photos_before_video+=1
                        while photos_before_video_updated == False: #Find the pattern
                            if i+initial_check < len(media_files):
                                if media_files[i+initial_check].lower().endswith(PHOTO_TYPES): #Keep incrementing until video is found
                                    photos_before_video+=1
                                    initial_check+=1
                                else: #Video was detected
                                    photos_before_video_updated = True
                                    if photos_before_video > MAX_PHOTOS_BEFORE_VIDEO and not self.debug_var.get(): #Pattern not found, usually not more than 5 images + 1 video. Do not output series.
                                        output_series = False
                            else: #All photos found
                                photos_before_video_updated = True
                                photos_before_video = 0
                    if (i == 0 and photos_before_video == 0) or output_series == False: #Runs if all photos, or pattern couldn't be found
                        return self.sort_and_extract(directory_path, recursive, final_output, modifier, output_series, progress_callback=progress_callback, defer_create_sheet=defer_create_sheet) 
                    if photos_before_video_updated and regular_pattern_found == False: #No pattern found yet, or is in between sets
                        end = False #For scanning last files in a pattern
                        while pattern_check < photos_before_video:
                            if photos_before_video+i > len(media_files)-1: 
                                regular_pattern_found=True
                                end = True
                                break
                            pattern_check+=1
                        if not end: #Not nearing the end of files to scan/check yet
                            if (i+pattern_check < len(media_files) and media_files[i+pattern_check].lower().endswith(VIDEO_TYPES)): #Verifies expected pattern
                                regular_pattern_found = True
                            else: #Not regular pattern
                                ok = self.scan_image(directory_path, media_files, i, list_of_dates, list_of_images, list_of_offsets) #Scan image as one-off
                                if not ok:
                                    i += 1
                                    index += 1 #Skipped image still consumes a series number
                                    skipped += 1
                                    if progress_callback:
                                        progress_callback(processed, skipped, directory_path)
                                    continue
                                processed += 1 #Scan went ok
                                img_series.append(str(index+modifier)) #Incorrect pattern found, images first
                                if progress_callback:
                                    progress_callback(processed, skipped, directory_path)
                        else: #Nearing end of directory listing
                            for r in range(photos_before_video): #End of files to scan found
                                if (i+r<len(media_files)) and media_files[i+r].lower().endswith(PHOTO_TYPES): #Scan all remaining files
                                    ok = self.scan_image(directory_path, media_files, i+r, list_of_dates, list_of_images, list_of_offsets)
                                    if not ok:
                                        skipped +=1
                                        if progress_callback:
                                            progress_callback(processed, skipped, directory_path)
                                        continue
                                    processed+=1
                                    img_series.append(str(index+r+modifier))
                                    if progress_callback:
                                        progress_callback(processed, skipped, directory_path)
                    # Always increment                     
                    pattern_check = 1 #Reset checks
                    i += 1 #increment
                    index+=1
                else: #File was a video
                    # If the first file was a video (not orphan), count the photos after it to set the pattern
                    if (i == 0 and not first_video_orphan): #First video is part of series, so it is video, photos_before_video photos, then start of next block with video.
                        while photos_before_video_updated == False: #Find the pattern
                            if i+initial_check < len(media_files):
                                if media_files[i+initial_check].lower().endswith(PHOTO_TYPES):
                                    photos_before_video += 1
                                    initial_check += 1
                                else:
                                    photos_before_video_updated = True
                                    if photos_before_video > MAX_PHOTOS_BEFORE_VIDEO and not self.debug_var.get():
                                        output_series = False
                            else:
                                photos_before_video_updated = True
                                photos_before_video = 0
                    # Standard pattern found logic otherwise
                    if regular_pattern_found: 
                        ok = self.scan_image(directory_path, media_files, i-1, list_of_dates, list_of_images, list_of_offsets)
                        if not ok:
                            i+=1
                            index+=1
                            skipped+=1
                            regular_pattern_found = False
                            continue
                        processed +=1
                        img_series.append(str(index-photos_before_video+modifier) + "-" + str(index+modifier)) #Image + video series
                        if progress_callback:
                            progress_callback(processed, skipped, directory_path)
                        regular_pattern_found = False
                    i += 1 #increment, essentially skipping videos
                    index+=1
        except (FileNotFoundError, PermissionError):
            self.collected_warnings["Directory Error"].append(f"{directory_path}")
            skipped_count = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES))
            return 0, skipped_count
        except OSError:
                self.collected_warnings["Scan Error"].append(f"[{directory_path}]\\{media_files[i]}")
                skipped_count = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES))
                return 0, skipped_count
        except Exception as e:  # noqa: BLE001
            self.collected_warnings["Unexpected"].append(f"[{directory_path}]: {e}\n{traceback.format_exc()}")
            skipped_count = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES))
            return 0, skipped_count
        fixed_date, fixed_time = self.fix_time(list_of_dates, list_of_offsets)
        self.create_dataframe(img_series, list_of_images, fixed_date, fixed_time, directory_path, output_series)
        if not recursive and not defer_create_sheet:
            self.create_sheet(final_output, recursive, processed, skipped) #One folder only, output time
        return processed, skipped #For tallying total processed and skipped

    #For images-only or no Img # Series collumn
    def sort_and_extract(self, directory_path, recursive, final_output, modifier, output_series, progress_callback = None, defer_create_sheet=False):
        processed = 0
        skipped = 0
        list_of_dates = []
        list_of_images = []
        list_of_offsets = []
        i = 0
        photos_before_video = 0
        photos_before_video_updated = False
        try:
            #List all files in directory given
            all_files = os.listdir(directory_path)
            media_files = [f for f in all_files if f.lower().endswith(PHOTO_TYPES + VIDEO_TYPES) and os.path.isfile(os.path.join(directory_path, f))]
            #Sorts files alphabetically, ignoring file extensions and capitalization
            media_files.sort(key=lambda x: os.path.splitext(x)[0].lower())
            #Iterates through every file in the directory
            while i < len(media_files):
                #If file is not a video, extract metadata from the image.
                if not media_files[i].lower().endswith(VIDEO_TYPES):
                    ok = self.scan_image(directory_path, media_files, i, list_of_dates, list_of_images, list_of_offsets)
                    if not ok:
                        i+=1
                        skipped+=1
                        if progress_callback:
                            progress_callback(processed, skipped, directory_path)
                        continue
                    processed+=1
                    if progress_callback:
                        progress_callback(processed, skipped, directory_path)
                else:
                    if output_series and not photos_before_video_updated and i != 0: #If a video hasn't been found before:
                        photos_before_video = i  #For Img # Series use
                        photos_before_video_updated = True #Do not update photos_before_video again
                i += 1 #increment, essentially skipping videos
        except (FileNotFoundError, PermissionError):
            self.collected_warnings["Directory Error"].append(f"{directory_path}")
            skipped_count = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES))
            return 0, skipped_count
        except OSError:
                self.collected_warnings["Scan Error"].append(f"[{directory_path}]\\{media_files[i]}")
                skipped_count = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES))
                return 0, skipped_count
        except Exception as e:  # noqa: BLE001
            self.collected_warnings["Unexpected"].append(f"[{directory_path}]: {e}\n{traceback.format_exc()}")
            skipped_count = sum(1 for f in media_files if f.lower().endswith(PHOTO_TYPES))
            return 0, skipped_count

        fixed_date, fixed_time = self.fix_time(list_of_dates, list_of_offsets)
        img_series, final_images, final_dates, final_times = self.make_series(list_of_images,photos_before_video_updated,photos_before_video,fixed_date,fixed_time, modifier, output_series)
        self.create_dataframe(img_series, final_images, final_dates, final_times, directory_path, output_series)
        if not recursive and not defer_create_sheet: #Single folder mode
            self.create_sheet(final_output, recursive, processed, skipped)
        return processed, skipped #Recursive mode

    # Handles series construction for all folders routed to sort_and_extract
    def make_series(self, list_of_images, photos_before_video_updated, photos_before_video, fixed_date, fixed_time, modifier, output_series):
        if not output_series:
            return None, list_of_images, fixed_date, fixed_time
        i = 1 #Set i to 1 to start at image 1.
        img_series = []
        final_images = []
        final_dates = []
        final_times = []
        while i <= len(list_of_images):
            if photos_before_video_updated and photos_before_video > 0: 
                if (i % photos_before_video)==0:   #For image + video folders, only add the last image data to the final lists    
                    final_images.append(list_of_images[i-1])
                    final_dates.append(fixed_date[i-1])
                    final_times.append(fixed_time[i-1])
                    # Each group consumes N photos + 1 video. group is 0-indexed.
                    group = (i // photos_before_video) - 1
                    start = i - photos_before_video + 1 + group + modifier
                    end   = i + 1 + group + modifier
                    img_series.append(f"{start}-{end}")
                i+=1
            else: #If only images were found, add all photos and increment series normally
                final_images.append(list_of_images[i-1])
                final_dates.append(fixed_date[i-1])
                final_times.append(fixed_time[i-1])
                img_series.append(str(i + modifier))
                i+=1
        return img_series, final_images, final_dates, final_times

    #Handles time and date formatting, along with UTC offsets
    def fix_time(self, list_of_dates, list_of_offsets):
        #Input format: "YYYY:MM:DD HH:MM:SS"
        fixed_time = []
        fixed_date = []
        check_timezone = self.timezone_var.get()
        for offset_index, date in enumerate(list_of_dates): #Split the EXIF metadata into a date list and time list (24h)
            date_str = str(date)
            if " " in date_str:
                try:
                    dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    fixed_date.append(date_str)
                    fixed_time.append("")
                    continue
                if check_timezone:
                    offset = list_of_offsets[offset_index]
                    if offset:
                        offset = offset.split(":") #Format is +-XX:00 so turn into +-XX
                        hours = offset[0]
                        minutes = int(offset[1])
                        sign = hours[0:1]
                        hours = int(hours[1:])
                        if sign == "+":
                            dt-=timedelta(hours=hours, minutes=minutes)
                        else: 
                            dt+=timedelta(hours=hours, minutes=minutes)
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

    #Creates dataframes for create_sheet to use
    def create_dataframe(self, img_series, final_images, final_dates, final_times, directory_path, output_series):
        if final_images: #Make sure images are present.
            data = {"Files": final_images, "Dates": final_dates, "Time": final_times}
            if output_series:
                data["Img # Series"] = img_series #Add on img_series
            else:
                self.collected_warnings["Irregular"].append(f"{directory_path.as_posix()}") #If irregular pattern starts with more than MAX_PHOTOS_BEFORE_VIDEO images in a row, will break program, so error. 
            df = pd.DataFrame(data) #Create DataFrame
            current_sheet_name = self.verify_name(self.current_sheet_name, self.used)
            self.results.append((df, current_sheet_name, directory_path))
        else:
            # No files are present
            empty_df = pd.DataFrame({"Files": [], "Dates": [], "Time": []})
            current_sheet_name = self.verify_name(self.current_sheet_name, self.used)
            self.results.append((empty_df, current_sheet_name, None))

    #Makes CSVs or Excel files
    def create_sheet(self, output_path, recursive, total_processed, total_skipped): #File creation
            try:
                #Check for empty results before prompting so the user isn't asked to overwrite for nothing
                if recursive and not self.results:
                    messagebox.showerror("No data", message="No folders with photos were found.")
                    if not self.keepopen_var.get():
                        self.root.destroy()
                        sys.exit()
                    return
                filetype = self.filetype_var.get()
                proceed = True
                if filetype == "Excel" and output_path.exists():
                    proceed = messagebox.askyesno("Overwrite?", message=output_path.as_posix() + " \nalready exists. Overwrite?")
                if proceed:
                    #Data was found
                    if filetype == "Excel":
                        with pd.ExcelWriter(output_path) as writer: #Opens ExcelWriter and closes automatically
                            for sheet_df, sheet_name, directory in self.results:
                                sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
                        if self.hyperlink_var.get():
                            self.add_hyperlinks(output_path.as_posix())
                        messagebox.showinfo("Success!", message="Images successfully scanned: " + str(total_processed) + "\nImages skipped: " + str(total_skipped) + "\nOutput: " + output_path.as_posix())
                    else: #CSV mode
                        for sheet_df, sheet_name, directory in self.results:
                            csv_path = output_path.as_posix()[0:-4] + f"_{self.clean_name(sheet_name)}"
                            if Path(csv_path).exists():
                                proceed = messagebox.askyesno("Overwrite?", message=csv_path + " \nalready exists. Overwrite?")
                            if proceed:
                                sheet_df.to_csv(csv_path, index=False)
                            else: proceed = True; continue
                        messagebox.showinfo("Success!", message="Images successfully scanned: " + str(total_processed) + "\nImages skipped: " + str(total_skipped) + "\nFiles located at: " + output_path.parent.as_posix())
                    if self.collected_warnings:
                        output = ""
                        #Writes error messages from the dictionary collected_warnings
                        for error, file in self.collected_warnings.items():
                            output += f"{error}\n"
                            if error == "No Metadata":
                                output+="These files had no metadata to scan and were excluded."
                            elif error == "Scan Error":
                                output+="These files are corrupt or non-image files, and were excluded."
                            elif error == "Directory Error":
                                output+="File/Directory couldn't be accessed."
                            # elif error == "Video First": #Unused error message
                            #     output+="Video File was found first. Please manually catalog, delete video, and re-run."
                            elif error == "Irregular":
                                output+= f"Irregular pattern (started with more than {MAX_PHOTOS_BEFORE_VIDEO} before a video. Please add mock files to the beginning to set correct pattern.\nFor example, if the pattern is 3 photos and 1 video, choose 3 photos and 1 video and duplicate them, naming them to be first when sorted, like DCSF0000."
                            elif error == "Hyperlink Error":
                                output += "The following sheets do not have hyperlinks."
                            elif error == "Unexpected":
                                output+= "Unexpected Errors - please report at https://github.com/Pianocraft1YT/MetadataExtractor/"
                            for filename in file:
                                output+=f"\n{filename}\n"
                    if self.collected_warnings:
                        log_path = output_path.parent / "warnings.log"
                        log_path.write_text(output, encoding="utf-8")
                        summary = f"{len(self.collected_warnings)} warning categories.\n\nFull details: {log_path.as_posix()}\n\nPlease verify any issues"
                        messagebox.showwarning("Warning(s)", message=summary)
                else:
                    messagebox.showinfo("Cancelled", message="File not overwritten. Cancelled successfully.")
                if not self.keepopen_var.get(): #Checks to close program or not
                    self.root.destroy() #End program
                    sys.exit()
            except (PermissionError, OSError) as e:
                messagebox.showerror(
                    "Error writing output",
                    f"Is another program using {output_path.as_posix()}?\n\nError: {e}")
                if not self.keepopen_var.get():
                    self.root.destroy()
                    sys.exit()
            except Exception as e:  # noqa: BLE001
                messagebox.showerror(
                    "Unexpected error",
                    f"{e}\n\n{traceback.format_exc()}")
                if not self.keepopen_var.get():
                    self.root.destroy()
                    sys.exit()

    #Initialization function when constructed
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Metadata Extractor")
        self.frame = tk.Frame(self.root)
        self.filetype_frame = tk.Frame(self.frame)
        self.execute_button = tk.Button(self.frame, command=self.check_recursive, text="Execute")
        self.set_directory_button = tk.Button(self.frame, command=self.set_dir, text="Set folder with images")
        self.set_output_button = tk.Button(self.frame, command=self.set_output, text="Set output folder")
        self.keepopen_var = tk.BooleanVar(value=False)
        self.keepopen_checkbox = tk.Checkbutton(self.frame, text="Keep Open", variable=self.keepopen_var)
        self.recursive_var = tk.BooleanVar(value=False)
        self.recursive_checkbox = tk.Checkbutton(self.frame, text="Recursive Mode", variable=self.recursive_var, command=self.recursive_input)
        self.timezone_var = tk.BooleanVar(value=False)
        self.timezone_checkbox = tk.Checkbutton(self.frame, text="Time in UTC", variable=self.timezone_var)
        self.debug_var = tk.BooleanVar(value=False)
        self.debug_checkbox = tk.Checkbutton(self.frame, text="Debug Mode", variable=self.debug_var, command=self.debug_warning)
        self.filetype_var = tk.StringVar(value="Excel")
        self.hyperlink_var = tk.BooleanVar(value=True)
        self.hyperlink_checkbox = tk.Checkbutton(self.frame, text="Add Hyperlinks", variable=self.hyperlink_var)
        self.name_entry = tk.Entry(self.frame, width=30, foreground="gray")
        self.name_entry.insert(0, "Filename (default output.filetype)")
        self.series_entry = tk.Entry(self.frame, width=30, foreground="gray")
        self.series_entry.insert(0, "Starting index (Img # Series)")
        self.maxdepth_entry = tk.Entry(self.frame, width=20, foreground="gray")
        self.maxdepth_entry.insert(0, "Recursion Depth (#)")

        self.name_entry.bind("<FocusIn>", self.nameFocusIn)
        self.name_entry.bind("<FocusOut>", self.nameFocusOut)
        self.series_entry.bind("<FocusIn>", self.seriesFocusIn)
        self.series_entry.bind("<FocusOut>", self.seriesFocusOut)
        self.maxdepth_entry.bind("<FocusIn>", self.maxDepthFocusIn)
        self.maxdepth_entry.bind("<FocusOut>", self.maxDepthFocusOut)

        #Set default sheet name
        self.current_sheet_name = "Sheet"
        #Collect warnings
        self.collected_warnings = defaultdict(list) #Makes a list out of keys if not found in dictionary
        #Main directory path
        self.directory_path = None
        #Directory to output .xlsx file to
        self.output_path = None
        #For verify_name
        self.used = set()
        #Variable for use with recursive directories, list of dataframes
        self.results = []
        #For output filetypes
        self.filetypes = ["Excel", "CSV"]
        #For recursion
        self.maxdepth = 1

        #Progress bar widgets
        self.current_directory = tk.StringVar()
        self.scanned_count = tk.StringVar()
        self.skipped_count = tk.StringVar()
        self.percentage_done = tk.StringVar()
        self.progress_frame = tk.Frame(self.root)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var)
        self.directory_label = tk.Label(self.progress_frame, textvariable=self.current_directory)
        self.scanned_label = tk.Label(self.progress_frame, textvariable=self.scanned_count)
        self.percent_label = tk.Label(self.progress_frame, textvariable=self.percentage_done)
        self.skipped_label = tk.Label(self.progress_frame, textvariable=self.skipped_count)
        self.total_files = 0

    #After initialization
    def run(self):
        #Pack main widgets
        self.frame.pack()
        self.set_directory_button.pack()
        self.set_output_button.pack()
        self.name_entry.pack()
        self.series_entry.pack()
        self.recursive_checkbox.pack()
        self.hyperlink_checkbox.pack()
        self.timezone_checkbox.pack()
        self.filetype_frame.pack(side="top")
        for ft in self.filetypes:
            tk.Radiobutton(self.filetype_frame, text=ft, variable=self.filetype_var, value=ft).pack(side="left")
        self.execute_button.pack()
        self.keepopen_checkbox.pack()
        self.debug_checkbox.pack()

        #Pack progress bar
        self.progress_frame.pack()
        self.progress_bar.pack()
        self.directory_label.pack()
        self.scanned_label.pack()
        self.percent_label.pack()
        self.skipped_label.pack()
        self.root.geometry("300x380")
        self.root.mainloop()

#Always runs
if __name__ == "__main__":
    app = MetadataExtractor() #Java: MetadataExtractor app = new MetadataExtractor(); (Constructor)
    app.run()