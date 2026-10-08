# Dear programmer:
# When I wrote this code, only God and I knew how it worked.
# Now, only God knows!
# 
# Therefore, if you trying to improve this,
# Please increment this counter as a warning
# For the next person:
# 
# hours_wasted_here = 41

# Coded by Pianocraft1YT
# Tutorial: https://youtu.be/ruWNKBdbYoo

#Imports
from PIL import Image, UnidentifiedImageError
import os
import sys
from pathlib import Path
import pandas as pd
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog

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
    used.clear()
    results.clear()
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
    with Image.open(Path(directory_path) / files_and_dirs[i]) as img: #Open the image in code
        exif_data = img.getexif() #Get the exif metadata
        dt = exif_data.get(306) or exif_data.get(36867) #Only extract date and time
    filename = files_and_dirs[i] #Get filename
    if dt is None:
        raise ValueError(f"No metadata found for {filename}")
    list_of_dates.append(dt) #Add to lists
    list_of_images.append(filename)
#Finds subdirectories for recursive mode
def find_directories(directory_path, final_output, modifier):
    global current_sheet_name #Used to create seperate named sheets
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
    if val.isdigit() and val != "1": #Make sure starting index is valid digit
        modifier = int(val) - 1 #We start at 1 by default, so minus 1 to not get off by one
    elif not (val == "Starting index (Img # Series)" or val == "" or val == "1"):
        #Placeholder, empty, or "1" means modifier stays 0; anything else errors
        messagebox.showerror("Numbers only.", message="Starting index must be a number.")
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
    name = name[:31] #Truncate to 31 characters max
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
        candidate = name[:31 - len(suffix)] + suffix #Truncate original name
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
    # Windows reserved names
    reserved = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }
    if name.upper() in reserved:
        name = "_" + name
    #Append .xlsx if the user didn't include it
    if not name.lower().endswith(".xlsx"):
        name += ".xlsx"
    return name
#Gets called initially, assumes irregular pattern, calls sort_and_extract() if regular
#Paths supplied by user or debug mode
def sort_and_extract_irregular(directory_path, recursive, final_output, modifier):
    global output_series
    output_series = True #If photos_before_video is less than 5.
    list_of_dates = []
    list_of_images = []
    img_series = []
    photos_before_video_updated = False
    i = 0 #Internal usage to scan files
    index = 1 #External usage for real indexing
    pattern_check = 1 #Lookahead counter for finding regular patterns/irregularities
    regular_pattern_found = False #If pattern_check found a regular pattern
    video_first = False #If a video file was scanned first
    scanned_first_set = False #If a video file was scanned first, and it is the second video found, for pattern checking catchup
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
            messagebox.showerror(
                "Video found first.",
                message="Please manually catalog the first video file, which doesn't have an image pair."
            )
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
                                if photos_before_video > 5: #Pattern not found, usually not more than 4 images + 1 video. Do not output series.
                                    output_series = False
                        else: #All photos found
                            photos_before_video_updated = True
                            photos_before_video = 0
                if (i == 0 and photos_before_video == 0) or output_series == False: #Runs if all photos, or pattern couldn't be found
                    sort_and_extract(directory_path,recursive, final_output, modifier) 
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
                            if not video_first:
                                img_series.append(str(index+modifier)) #Incorrect pattern found, images first
                            else:
                                img_series.append(str(index-1+modifier)) #Incorrect pattern found, videos first, fixing index
                            scan_image(directory_path, files_and_dirs, i, list_of_dates, list_of_images) #Scan image as one-off
                    else:
                        for r in range(photos_before_video): #End of files to scan found
                            if (i+r<len(files_and_dirs)): #Scan all remaining files
                                if files_and_dirs[i+r].lower().endswith(photo_types):
                                    scan_image(directory_path, files_and_dirs, i+r, list_of_dates, list_of_images)
                                    img_series.append(str(index+r+modifier))
                pattern_check = 1
                i += 1 #increment
                index+=1
            else: #File was a video
                if (photos_before_video_updated == False and video_first): #Runs on second video found, sets pattern
                    photos_before_video = i-1 #For Img # Series use
                    photos_before_video_updated = True #Do not update photos_before_video again
                if (photos_before_video_updated == False and i != 0): #Runs on first video found, normal images first directory
                    photos_before_video = i  #For Img # Series use
                    photos_before_video_updated = True #Do not update photos_before_video again
                if video_first and scanned_first_set == False: #To catch up on unadded series
                    scanned_first_set = True
                    img_series.append(str(i-photos_before_video+modifier) + "-" + str(i+modifier))
                    scan_image(directory_path, files_and_dirs, i-1, list_of_dates, list_of_images)
                if (i==0):
                    video_first = True #Last so all checks work correctly
                if regular_pattern_found: #Normal pattern found
                    if not video_first: #Images first mode
                        img_series.append(str(index-photos_before_video+modifier) + "-" + str(index+modifier)) #Image + video series
                    else: #Adjust by one to account for video first
                        img_series.append(str(i-photos_before_video+modifier) + "-" + str(i+modifier)) 
                    scan_image(directory_path, files_and_dirs, i-1, list_of_dates, list_of_images)
                    regular_pattern_found = False
                i += 1 #increment, essentially skipping videos
                index+=1
    except ValueError as e:
        messagebox.showerror("Metadata missing", message=str(e))
        return
    except UnidentifiedImageError as e:
        messagebox.showerror("Image couldn't be scanned.", message="Image couldn't be scanned, is it corrupt? \nError caught: " + str(e) + "\nPlease delete the specified file.")
        return
    except Exception as e:
        messagebox.showerror("An error occurred.", message="An error occurred. \nError caught: " + str(e))
        return
    fixed_date, fixed_time = fix_time(list_of_dates)
    df = create_dataframe(img_series, list_of_images, fixed_date, fixed_time, recursive, directory_path)
    if not recursive:
        create_sheet(final_output, recursive, df) #One folder only, output time
#For images-only or no Img # Series collumn
def sort_and_extract(directory_path, recursive, final_output, modifier):
    global output_series
    list_of_dates = []
    list_of_images = []
    video_first = False
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
                with Image.open(Path(directory_path) / files_and_dirs[i]) as img: #open the image
                    exif_data = img.getexif() #get the exif metadata
                    dt = exif_data.get(306) or exif_data.get(36867) #only extract date and time
                if dt is None:
                    raise ValueError(f"No metadata found for {files_and_dirs[i]}")
                filename = files_and_dirs[i] #get filename
                list_of_dates.append(dt) #add to lists
                list_of_images.append(filename)
                i += 1 #increment
            else:
                if output_series:
                    if not photos_before_video_updated: #If a video hasn't been found before
                        if (photos_before_video_updated == False and video_first):
                                photos_before_video = i-1
                        if (i != 0):
                            photos_before_video = i  #For Img # Series use
                            photos_before_video_updated = True #Do not update photos_before_video again
                        else:
                            video_first = True #Video was found first
                            messagebox.showerror("Video found first.", message="Please manually catalog the first video file, which doesn't have an image pair.")
                i += 1 #increment, essentially skipping videos
    except ValueError as e:
        messagebox.showerror("Metadata missing", message=str(e))
        return
    except UnidentifiedImageError as e:
        messagebox.showerror("Image couldn't be scanned.", message="Image couldn't be scanned, is it corrupt? \nError caught: " + str(e) + "\nPlease delete the specified file.")
        return
    except Exception as e:
        messagebox.showerror("An error occurred.", message="An error occurred. \nError caught: " + str(e))
        return
    fixed_date, fixed_time = fix_time(list_of_dates)
    img_series, final_images, final_dates, final_times = make_series(list_of_images,photos_before_video_updated,photos_before_video,fixed_date,fixed_time, modifier)
    df = create_dataframe(img_series, final_images, final_dates, final_times, recursive, directory_path)
    if not recursive:
        create_sheet(final_output, recursive, df)

# Handles series construction for all folders routed to sort_and_extract
def make_series(list_of_images, photos_before_video_updated, photos_before_video, fixed_date, fixed_time, modifier):
    global output_series
    if output_series:
        i = 1 #Set i to 1 to start at image 1.
        final_images = []
        final_dates = []
        final_times = []
        img_series = []
        while i <= len(list_of_images):
            if photos_before_video_updated and photos_before_video > 0: 
                if (i % photos_before_video)==0:   #For image + video folders, only add the first image data to the final lists    
                    final_images.append(list_of_images[i-1])
                    final_dates.append(fixed_date[i-1])
                    final_times.append(fixed_time[i-1])
                    img_series.append(str(i - photos_before_video + 1 + modifier) + "-" + str(i + 1 + modifier)) #For Img # Series to correctly count the series
                i+=1
            else: #If only images were found, add all photos and increment series normally
                final_images.append(list_of_images[i-1])
                final_dates.append(fixed_date[i-1])
                final_times.append(fixed_time[i-1])
                img_series.append(str(i + modifier))
                i+=1
    else: #Don't output series collumn
        final_images = list_of_images
        final_dates = fixed_date
        final_times = fixed_time
        img_series = None
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
def create_dataframe(img_series, final_images, final_dates, final_times, recursive, directory_path):
        global output_series
        if not recursive: #Single folder mode
            if output_series:
                df = pd.DataFrame( #Create DataFrame
                    {
                        "Files": final_images,
                        "Dates": final_dates,
                        "Time": final_times,
                        "Image # Series": img_series,
                    }
                )
            else:
                df = pd.DataFrame( #Create DataFrame
                    {
                        "Files": final_images,
                        "Dates": final_dates,
                        "Time": final_times,
                    }
                )
                messagebox.showerror( #If irregular pattern starts with more than 5 images in a row, will break program, so error.
                    "An error occurred.", message="Unpredictable pattern found with directory\n" + directory_path.as_posix() + ".\nPlease add mock files to the beginning to set correct pattern." \
                    " For example, if the pattern is 3 photos and 1 video, choose 3 photos and 1 video and duplicate them, naming them to be first when sorted, like DCSF0000."
                )
            return df
        else:
            global current_sheet_name #Recursive mode
            if output_series:
                df = pd.DataFrame( #Create DataFrame
                    {
                        "Files": final_images,
                        "Dates": final_dates,
                        "Time": final_times,
                        "Image # Series": img_series,
                    }
                )
            else:
                df = pd.DataFrame( #Create DataFrame
                    {
                        "Files": final_images,
                        "Dates": final_dates,
                        "Time": final_times,
                    }
                )
                messagebox.showerror( #If irregular pattern starts with more than 5 images in a row, will break program, so error.
                    "An error occurred.", message="Unpredictable pattern found with directory\n" + directory_path.as_posix() + ".\nPlease add mock files to the beginning to set correct pattern." \
                    " For example, if the pattern is 3 photos and 1 video, choose 3 photos and 1 video and duplicate them, naming them to be first when sorted, like DCSF0000."
                )
        if final_images: #Make sure images are present.
            current_sheet_name = verify_name(current_sheet_name)
            results.append((df, current_sheet_name))

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
                if recursive:
                    #Data was found
                    with pd.ExcelWriter(output_path) as writer:
                        for df, sheet_name in results:
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    #Single folder output
                    df.to_excel(out_file, sheet_name="Output", index=False)
                messagebox.showinfo("Success!", message="Success, outputted at " + output_path.as_posix())
            else:
                messagebox.showinfo("Cancelled", message="File not overwritten. Cancelled successfully.")
            if not keepopen_var.get(): #Checks to close program or not
                root.destroy() #End program
                sys.exit()
        except Exception as e:
            messagebox.showerror( #Usually permission errors
                "An error occurred.", message="Is another program using " + output_path.as_posix() + "? Error caught: " + str(e))
            if not keepopen_var.get():
                root.destroy()
                sys.exit()
            
root = tk.Tk() #Tkinter root
frame = tk.Frame(root) #Tkinter frame window
execute_button = tk.Button(frame, command=lambda:check_recursive(directory_path), text="Execute")
#Buttons to click
set_directory_button = tk.Button(frame, command=set_dir, text="Set folder with images")
set_output_button = tk.Button(frame, command=set_output, text="Set output folder")
#Checkbox options
keepopen_var = tk.BooleanVar(value=False)  # default unchecked
keepopen_checkbox = tk.Checkbutton(frame, text="Keep open?", variable=keepopen_var)
recursive_var = tk.BooleanVar(value=False)  # default unchecked
recursive_checkbox = tk.Checkbutton(frame, text="Scan subfolders", variable=recursive_var)
#Entry options
name_entry = tk.Entry(frame, width=30, foreground="gray")
name_entry.insert(0, "Filename (default output.xlsx)")
series_entry = tk.Entry(frame, width=30, foreground="gray")
series_entry.insert(0, "Starting index (Img # Series)")
#For placeholder text
name_entry.bind("<FocusIn>", nameFocusIn)
name_entry.bind("<FocusOut>", nameFocusOut)
series_entry.bind("<FocusIn>", seriesFocusIn)
series_entry.bind("<FocusOut>", seriesFocusOut)
#Pack frame and buttons in order
frame.pack()
set_directory_button.pack()
set_output_button.pack()
name_entry.pack()
series_entry.pack()
recursive_checkbox.pack()
execute_button.pack()
keepopen_checkbox.pack()
root.geometry("240x180") #Set dimensions of window to open
root.mainloop() #Ensure window only closes by user choice