# Dear programmer:
# When I wrote this code, only God and I knew how it worked.
# Now, only God knows!
# 
# Therefore, if you trying to improve this,
# Please increment this counter as a warning
# For the next person:
# 
# hours_wasted_here = 45

# Coded by Pianocraft1YT
# Tutorial: https://youtu.be/ruWNKBdbYoo
# GitHub Repo: https://github.com/Pianocraft1YT/MetadataExtractor/

#Imports
from PIL import Image, UnidentifiedImageError
import os
import sys
from pathlib import Path
import pandas as pd
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
from collections import defaultdict
import traceback

EXIF_DATETIME = 306
EXIF_DATETIME_ORIGINAL = 36867
EXIF_DATETIME_DIGITIZED = 36868
MAX_PHOTOS_BEFORE_VIDEO = 5
SHEET_NAME_MAX_CHARS = 31

#Collect warnings
collected_warnings = defaultdict(list) #Makes a list out of keys if not found in dictionary

#Cosmetic only, adds placeholder text in entry boxes
def nameFocusIn(event):
    if name_entry.get() == "Filename (default output.xlsx)":
        name_entry.delete(0, "end")
        name_entry.config(foreground="black")
def nameFocusOut(event):
    if name_entry.get() == "":
        name_entry.insert(0, "Filename (default output.xlsx)")
        name_entry.config(foreground="gray")
def seriesFocusIn(event):
    if series_entry.get() == "Starting index (Img # Series)":
        series_entry.delete(0, "end")
        series_entry.config(foreground="black")
def seriesFocusOut(event):
    if series_entry.get() == "":
        series_entry.insert(0, "Starting index (Img # Series)")
        series_entry.config(foreground="gray")

#Common video file formats to check
video_types = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv")
#Common and uncommon image formats to check
photo_types = (".jpg", ".jpeg", ".heic", ".heif", ".png", ".tiff", ".tif",
               ".dng", ".crw", ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf",
               ".sr2", ".raf", ".rw2", ".raw", ".orf", ".ori", ".pef", ".ptx",
               ".rwl", ".3fr", ".fff", ".iiq", ".mos", ".x3f", ".kdc", ".dcr",
               ".dcs", ".srw", ".mrw")
#Main directory path
directory_path = None
#Directory to output .xlsx file to
output_path = None
#For debugging only, manually set
debug = False
#To clean up any past executions
def reset():
    global total_skipped, total_processed, skipped, processed
    used.clear()
    results.clear()
    collected_warnings.clear()
    total_skipped = 0
    total_processed = 0
    skipped = 0
    processed = 0
#Gets called on set directory button press to set image directory
def set_dir():
    global directory_path
    selected = filedialog.askdirectory(title="Select a Directory")
    if selected:
        directory_path = Path(selected)
#Gets called on set output button press
def set_output():
    global output_path
    selected = filedialog.askdirectory(title="Select a Output Directory")
    if selected:
        output_path = Path(selected)
#Image metadata extractor helper function
def scan_image(directory_path, files_and_dirs, i, list_of_dates, list_of_images):
    try:
        with Image.open(Path(directory_path) / files_and_dirs[i]) as img: #open the image
            exif_data = img.getexif() #get the exif metadata
        dt = exif_data.get(EXIF_DATETIME_ORIGINAL) or exif_data.get(EXIF_DATETIME_DIGITIZED) or exif_data.get(EXIF_DATETIME) #only extract date and time
        if dt is None:
            collected_warnings["No Metadata"].append(f"[{directory_path}]\\{files_and_dirs[i]}")
            return False
    except (OSError, SyntaxError, ValueError, UnidentifiedImageError) as e:
        collected_warnings["Scan Error"].append(f"[{directory_path}]\\{files_and_dirs[i]}")
        return False
    else: #No errors
        list_of_dates.append(dt) #Add to lists
        list_of_images.append(files_and_dirs[i])
        return True
#Finds subdirectories for recursive mode
def find_directories(directory_path, final_output, modifier):
    global current_sheet_name, total_processed, total_skipped, processed, skipped #Used to create seperate named sheets; processed and skipped for summary counts
    total_processed = 0
    total_skipped = 0
    name_index = 0 #For indexing over sheet_names list
    directories_found = os.listdir(directory_path) #Only one level of recursion
    directories_found.sort() # ensure consistent sheet order
    directories_to_scan = []
    sheet_names = []
    for directory in directories_found:
        current_directory = Path(directory_path.as_posix() + "/" + directory)
        if not current_directory.is_dir():
            continue
        with os.scandir(current_directory) as entries:
            has_photo = any(entry.is_file() and entry.name.lower().endswith((photo_types)) for entry in entries)
            if has_photo:
                directories_to_scan.append(current_directory)
                sheet_names.append(directory) #Just the directory name, not the full path
    for directory_path in directories_to_scan:
        current_sheet_name = sheet_names[name_index]
        name_index+=1
        sort_and_extract_irregular(directory_path, True, final_output, modifier)
        total_processed+=processed
        total_skipped+=skipped
    create_sheet(final_output, True, None)
def check_recursive(directory_path):
    global output_path
    modifier = 0 #For starting index of img_series
    if debug: #No need to set output_path every time
        output_path = Path.home() / "Downloads"
    if directory_path == None or output_path == None:
        messagebox.showerror( #If no output/directory path was set, error to allow for changes
            "Invalid path(s) specified.", message="Please set an image/video directory path OR output path.")
        return
    val = series_entry.get().strip() #Pull once, use for both checks below
    if val.isdigit() and int(val) > 0 and val != "1": #Make sure starting index is valid digit
        modifier = int(val) - 1 #We start at 1 by default, so minus 1 to not get off by one
    elif not (val == "Starting index (Img # Series)" or val == "" or val == "1"):
        #Placeholder, empty, or "1" means modifier stays 0; anything else errors
        messagebox.showerror("Numbers only.", message="Starting index must be a whole number greater than zero.")
        return
    reset() #Clear old data
    if name_entry.get() != "Filename (default output.xlsx)": #Placeholder text
        final_output = Path(output_path) / clean_name(name_entry.get()) #Clean_name to create valid names only
    else:
        final_output = Path(output_path) / "output.xlsx" #Default filename
    recursive = recursive_var.get() #Get status of recursive_checkbox
    if recursive:
        find_directories(directory_path, final_output, modifier) #Run recursive mode
    else:
        with os.scandir(directory_path) as entries:
                photo_count = sum(1 for entry in entries if entry.is_file() and entry.name.lower().endswith((photo_types)))
                if photo_count > 0:
                    sort_and_extract_irregular(directory_path, False, final_output, modifier)
                else:
                        messagebox.showerror("Empty directory", message="No files were found. Please select a valid directory")
                        return
#For verify_name
used = set()
def verify_name(name):
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
def clean_name(name):
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
    if name.lower().endswith(".xlsx"):
        stem = name[:-5]
        ext = name[-5:]  # ".xlsx" or ".XLSX" etc.
    else:
        stem = name
        ext = ".xlsx"

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
#Gets called initially, assumes irregular pattern, calls sort_and_extract() if regular
#Paths supplied by user or debug mode
def sort_and_extract_irregular(directory_path, recursive, final_output, modifier):
    global processed, skipped
    processed = 0
    skipped = 0
    output_series = True #If photos_before_video is less than MAX_PHOTOS_BEFORE_VIDEO.
    list_of_dates = []
    list_of_images = []
    img_series = []
    photos_before_video_updated = False
    i = 0 #Internal usage to scan files
    index = 1 #External usage for real indexing
    pattern_check = 1 #Lookahead counter for finding regular patterns/irregularities
    regular_pattern_found = False #If pattern_check found a regular pattern
    initial_check = 1 #If images were first, find the pattern
    photos_before_video = 0 #Default all images
    try:
        #List all files in directory given
        all_files = os.listdir(directory_path)
        #Sorts files alphabetically, ignoring file extensions and capitalization, ignoring any non-photo or non-video files
        files_and_dirs = [f for f in all_files if f.lower().endswith((photo_types + video_types)) and os.path.isfile(os.path.join(directory_path, f))]
        files_and_dirs.sort(key=lambda x: os.path.splitext(x)[0].lower())
        # Early check: if the first file is a video, show error and return
        if files_and_dirs and files_and_dirs[0].lower().endswith(video_types):
            collected_warnings["Video First"].append(f"{directory_path}")
            return
        #Iterates through every file in the directory
        for file in files_and_dirs:
            #If file is not a video, extract metadata from the image.
            if not file.lower().endswith((video_types)):
                if i == 0: #Image found first
                    photos_before_video+=1
                    while photos_before_video_updated == False: #Find the pattern
                        if i+initial_check < len(files_and_dirs):
                            if files_and_dirs[i+initial_check].lower().endswith((photo_types)):
                                photos_before_video+=1
                                initial_check+=1
                            else:
                                photos_before_video_updated = True
                                if photos_before_video > MAX_PHOTOS_BEFORE_VIDEO: #Pattern not found, usually not more than 4 images + 1 video. Do not output series.
                                    output_series = False
                        else: #All photos found
                            photos_before_video_updated = True
                            photos_before_video = 0
                if (i == 0 and photos_before_video == 0) or output_series == False: #Runs if all photos, or pattern couldn't be found
                    sort_and_extract(directory_path,recursive, final_output, modifier, output_series) 
                    return
                if photos_before_video_updated and regular_pattern_found == False:
                    end = False #For scanning last files in a pattern
                    while pattern_check < photos_before_video:
                        if photos_before_video+i > len(files_and_dirs)-1: 
                            regular_pattern_found=True
                            end = True
                            break
                        pattern_check+=1
                    if not end: #Not nearing the end of files to scan/check yet
                        if (i+pattern_check < len(files_and_dirs) and files_and_dirs[i+pattern_check].lower().endswith((video_types))): #Verifies expected pattern
                            regular_pattern_found = True
                        else:
                            ok = scan_image(directory_path, files_and_dirs, i, list_of_dates, list_of_images) #Scan image as one-off
                            if not ok:
                                i += 1
                                index += 1 #Skipped image still consumes a series number
                                skipped += 1
                                continue
                            processed += 1
                            img_series.append(str(index+modifier)) #Incorrect pattern found, images first
                    else:
                        for r in range(photos_before_video): #End of files to scan found
                            if (i+r<len(files_and_dirs)): #Scan all remaining files
                                if files_and_dirs[i+r].lower().endswith(photo_types):
                                    ok = scan_image(directory_path, files_and_dirs, i+r, list_of_dates, list_of_images)
                                    if not ok:
                                        skipped +=1
                                        continue
                                    processed+=1
                                    img_series.append(str(index+r+modifier))
                                    
                pattern_check = 1
                i += 1 #increment
                index+=1
            else: #File was a video
                if (photos_before_video_updated == False and i != 0): #Runs on first video found, normal images first directory
                    photos_before_video = i  #For Img # Series use
                    photos_before_video_updated = True #Do not update photos_before_video again
                if regular_pattern_found: #Normal pattern found
                    ok = scan_image(directory_path, files_and_dirs, i-1, list_of_dates, list_of_images)
                    if not ok:
                        i+=1
                        index+=1
                        skipped+=1
                        regular_pattern_found = False
                        continue
                    processed +=1
                    img_series.append(str(index-photos_before_video+modifier) + "-" + str(index+modifier)) #Image + video series
                    regular_pattern_found = False
                i += 1 #increment, essentially skipping videos
                index+=1
    except (FileNotFoundError, PermissionError) as e:
        collected_warnings["Directory Error"].append(f"{directory_path}")
        return
    except OSError as e:
            collected_warnings["Scan Error"].append(f"[{directory_path}]\\{files_and_dirs[i]}")
            return
    except Exception as e:
        collected_warnings["Unexpected"].append(f"[{directory_path}]: {e}\n{traceback.format_exc()}")
        return
    fixed_date, fixed_time = fix_time(list_of_dates)
    df = create_dataframe(img_series, list_of_images, fixed_date, fixed_time, recursive, directory_path, output_series)
    if not recursive:
        create_sheet(final_output, recursive, df) #One folder only, output time
#For images-only or no Img # Series collumn
def sort_and_extract(directory_path, recursive, final_output, modifier, output_series):
    global processed
    global skipped
    processed = 0
    skipped = 0
    list_of_dates = []
    list_of_images = []
    i = 0
    photos_before_video = 0
    photos_before_video_updated = False
    try:
        #List all files in directory given
        all_files = os.listdir(directory_path)
        files_and_dirs = [f for f in all_files if f.lower().endswith((photo_types + video_types)) and os.path.isfile(os.path.join(directory_path, f))]
        #Sorts files alphabetically, ignoring file extensions and capitalization
        files_and_dirs.sort(key=lambda x: os.path.splitext(x)[0].lower())
        #Iterates through every file in the directory
        while i < len(files_and_dirs):
            #If file is not a video, extract metadata from the image.
            if not files_and_dirs[i].lower().endswith((video_types)):
                ok = scan_image(directory_path, files_and_dirs, i, list_of_dates, list_of_images)
                if not ok:
                    i+=1
                    skipped+=1
                    continue
                processed+=1
            else:
                if output_series:
                    if not photos_before_video_updated: #If a video hasn't been found before
                        if (i != 0):
                            photos_before_video = i  #For Img # Series use
                            photos_before_video_updated = True #Do not update photos_before_video again
            i += 1 #increment, essentially skipping videos
    except (FileNotFoundError, PermissionError) as e:
        collected_warnings["Directory Error"].append(f"{directory_path}")
        return
    except OSError as e:
            collected_warnings["Scan Error"].append(f"[{directory_path}]\\{files_and_dirs[i]}")
            return
    except Exception as e:
        collected_warnings["Unexpected"].append(f"[{directory_path}]: {e}\n{traceback.format_exc()}")
        return
    fixed_date, fixed_time = fix_time(list_of_dates)
    img_series, final_images, final_dates, final_times = make_series(list_of_images,photos_before_video_updated,photos_before_video,fixed_date,fixed_time, modifier, output_series)
    df = create_dataframe(img_series, final_images, final_dates, final_times, recursive, directory_path, output_series)
    if not recursive:
        create_sheet(final_output, recursive, df)

# Handles series construction for all folders routed to sort_and_extract
def make_series(list_of_images, photos_before_video_updated, photos_before_video, fixed_date, fixed_time, modifier, output_series):
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

def fix_time(list_of_dates):
    fixed_time = []
    fixed_date = []
    for date in list_of_dates: #Split the exif metadata into a date list and time list (24h)
        date_str = str(date)
        if " " in date_str:
            dateslist = date_str.split(" ", maxsplit=1)
            fixed_date.append(dateslist[0])
            fixed_time.append(dateslist[1])
        else:
            fixed_date.append(date_str)
            fixed_time.append("")  # or "00:00:00" if preferred
    #Create dataframe to manipulate formatting of dates
    df = pd.DataFrame({"Dates": fixed_date})
    df["Date_Datetime"] = pd.to_datetime(df["Dates"], format="%Y:%m:%d")
    formatted_dates = df["Date_Datetime"].dt.strftime("%m/%d/%Y")
    #Turn dataframe back into list for further use
    fixed_date = formatted_dates.to_list()
    return fixed_date, fixed_time

#Variable for use with recursive directories, list of dataframes
results = []
def create_dataframe(img_series, final_images, final_dates, final_times, recursive, directory_path, output_series):
    global current_sheet_name #Recursive mode
    if final_images: #Make sure images are present.
        data = {"Files": final_images, "Dates": final_dates, "Time": final_times}
        if output_series:
            data["Img # Series"] = img_series
        else:
            collected_warnings["Irregular"].append(f"{directory_path.as_posix()}") #If irregular pattern starts with more than MAX_PHOTOS_BEFORE_VIDEO images in a row, will break program, so error. 
        if not recursive: #Single folder mode
            df = pd.DataFrame(data) #Create DataFrae
            return df
        else:
            df = pd.DataFrame(data) #Create DataFrame
            current_sheet_name = verify_name(current_sheet_name)
            results.append((df, current_sheet_name))
    else:
        return pd.DataFrame({"Files": [], "Dates": [], "Time": []})

def create_sheet(output_path, recursive, df): #File creation
        try:
            out_file = Path(output_path)
            #Check for empty results before prompting so the user isn't asked to overwrite for nothing
            if recursive and not results:
                messagebox.showerror("No data", message="No folders with photos were found.")
                if not keepopen_var.get():
                    root.destroy()
                    sys.exit()
                return
            proceed = True
            if output_path.exists(): #Overwrite checking
                proceed = messagebox.askyesno("Overwrite?", message=output_path.as_posix() + " \nalready exists. Overwrite?")
            if proceed:
                if collected_warnings:
                    output = ""
                    for error, file in collected_warnings.items():
                        output += f"{error}\n"
                        if error == "No Metadata":
                            output+="These files had no metadata to scan and were excluded."
                        elif error == "Scan Error":
                            output+="These files are corrupt or non-image files, and were excluded."
                        elif error == "Directory Error":
                            output+="File/Directory couldn't be accessed."
                        elif error == "Video First":
                            output+="Video File was found first. Please manually catalog"
                        elif error == "Unexpected":
                            output+= "Unexpected Errors - please report at https://github.com/Pianocraft1YT/MetadataExtractor/"
                        elif error == "Irregular":
                            output+= f"Irregular pattern (started with more than {MAX_PHOTOS_BEFORE_VIDEO} before a video. Please add mock files to the beginning to set correct pattern.\nFor example, if the pattern is 3 photos and 1 video, choose 3 photos and 1 video and duplicate them, naming them to be first when sorted, like DCSF0000."
                        for filename in file:
                            output+=f"\n{filename}"
                if recursive:
                    #Data was found
                    with pd.ExcelWriter(output_path) as writer:
                        for df, sheet_name in results:
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                    if collected_warnings:
                        messagebox.showwarning("Warning(s)", message=output)
                    messagebox.showinfo("Success!", message="Images successfully scanned: " + str(total_processed) + "\nImages skipped: " + str(total_skipped) + "\nOutput: " + output_path.as_posix())
                else:
                    #Single folder output
                    df.to_excel(out_file, sheet_name="Output", index=False)
                    if collected_warnings:
                        messagebox.showwarning("Warning(s)", message=output)
                    messagebox.showinfo("Success!", message="Images successfully scanned: " + str(processed) + "\nImages skipped: " + str(skipped) + "\nOutput: " + output_path.as_posix())
            else:
                messagebox.showinfo("Cancelled", message="File not overwritten. Cancelled successfully.")
            if not keepopen_var.get(): #Checks to close program or not
                root.destroy() #End program
                sys.exit()
        except (PermissionError, OSError) as e:
            messagebox.showerror(
                "Error writing output",
                f"Is another program using {output_path.as_posix()}?\n\nError: {e}")
            if not keepopen_var.get():
                root.destroy()
                sys.exit()
        except Exception as e:
            messagebox.showerror(
                "Unexpected error",
                f"{e}\n\n{traceback.format_exc()}")
            if not keepopen_var.get():
                root.destroy()
                sys.exit()
# Module-level widget placeholders (assigned inside main()).
# Type annotations give Pylance the widget type; the # type: ignore
# comments suppress the "None is not assignable" warning on the
# placeholder assignment. Without these, every .get() / .delete() call
# downstream shows "not a known attribute of None".
root: tk.Tk = None  # type: ignore[assignment]
frame: tk.Frame = None  # type: ignore[assignment]
execute_button: tk.Button = None  # type: ignore[assignment]
set_directory_button: tk.Button = None  # type: ignore[assignment]
set_output_button: tk.Button = None  # type: ignore[assignment]
keepopen_var: tk.BooleanVar = None  # type: ignore[assignment]
keepopen_checkbox: tk.Checkbutton = None  # type: ignore[assignment]
recursive_var: tk.BooleanVar = None  # type: ignore[assignment]
recursive_checkbox: tk.Checkbutton = None  # type: ignore[assignment]
name_entry: tk.Entry = None  # type: ignore[assignment]
series_entry: tk.Entry = None  # type: ignore[assignment]

def main():
    global root, frame, execute_button, set_directory_button, set_output_button
    global keepopen_var, keepopen_checkbox, recursive_var, recursive_checkbox
    global name_entry, series_entry

    root = tk.Tk()
    root.title("Metadata Extractor")
    frame = tk.Frame(root)
    execute_button = tk.Button(frame, command=lambda: check_recursive(directory_path), text="Execute")
    set_directory_button = tk.Button(frame, command=set_dir, text="Set folder with images")
    set_output_button = tk.Button(frame, command=set_output, text="Set output folder")
    keepopen_var = tk.BooleanVar(value=False)
    keepopen_checkbox = tk.Checkbutton(frame, text="Keep open?", variable=keepopen_var)
    recursive_var = tk.BooleanVar(value=False)
    recursive_checkbox = tk.Checkbutton(frame, text="Scan subfolders", variable=recursive_var)
    name_entry = tk.Entry(frame, width=30, foreground="gray")
    name_entry.insert(0, "Filename (default output.xlsx)")
    series_entry = tk.Entry(frame, width=30, foreground="gray")
    series_entry.insert(0, "Starting index (Img # Series)")

    name_entry.bind("<FocusIn>", nameFocusIn)
    name_entry.bind("<FocusOut>", nameFocusOut)
    series_entry.bind("<FocusIn>", seriesFocusIn)
    series_entry.bind("<FocusOut>", seriesFocusOut)

    frame.pack()
    set_directory_button.pack()
    set_output_button.pack()
    name_entry.pack()
    series_entry.pack()
    recursive_checkbox.pack()
    execute_button.pack()
    keepopen_checkbox.pack()
    root.geometry("240x180")
    root.mainloop()


if __name__ == "__main__":
    main()