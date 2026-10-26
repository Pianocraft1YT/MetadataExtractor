# Metadata Extractor by Pianocraft1YT

Metadata Extractor is a Tkinter desktop utility for cataloging folders of camera, drone, or action-cam media. It reads EXIF date/time metadata from photos, uses video files as sequence delimiters, and writes a formatted Excel or CSV workbook.

It is designed for folders where files are sorted alphabetically and often follow a pattern like:

photo, photo, photo, video, photo, photo, photo, video...

The script can detect that pattern and output one row per photo+video series, using the last photo in each series as the representative file. Folders containing only photos are also supported and output one row per image.

## Features

- Extracts `DateTime` / `DateTimeOriginal` EXIF metadata from many image formats, including JPEG, HEIC, PNG, TIFF, and common RAW files.
- Skips videos for metadata extraction but uses them to detect photo/video series boundaries.
- **Full recursive scanning**: Walk deep directory trees with a configurable recursion depth. Each photo-bearing subfolder becomes its own worksheet (or CSV file).
- **Live progress bar**: The UI stays completely responsive during massive scans. A background worker thread processes files while the window displays the current subfolder, scan percentage, and live processed/skipped counters.
- Output formats: Excel (`.xlsx`) or CSV (`.csv`), selectable via radio buttons.
- Optional UTC conversion: reads `OffsetTimeOriginal` and shifts timestamps to UTC when the "Time in UTC" checkbox is enabled. Photos without an offset tag are left unchanged.
- Optional clickable hyperlinks in the Excel output: every filename in the Files column links to the source file on disk. Off in CSV mode (unsupported).
- Optional `Image # Series` column with configurable starting index.
- **Warning log file**: If any files are skipped (missing metadata, corrupt, etc.), a `warnings.log` file is generated alongside the output with detailed error categorization.
- Simple Tkinter GUI: choose input folder, output folder, filename, recursion, timezone, hyperlinks, and execute.
- Overwrite prompts, sheet-name sanitization, and Windows-safe filename cleaning.
- Keep-open option for debugging or repeated runs.

## Limitations

- Video metadata is not read; videos are only used as pattern markers and are not counted in the progress bar.
- The first file in a folder cannot be a video.
- If more than 5 photos appear before the first video, the pattern is treated as unpredictable and a warning is shown.
- Hyperlinks are Excel-only.
- Recursive CSV mode produces one file per subfolder and asks for confirmation before running.
- Every image must contain usable EXIF date/time metadata.

## Requirements

- Python 3.11 or newer (3.11, 3.12, and 3.13 supported and tested)
- Pillow
- pandas
- openpyxl
- tkinter (usually included with Python)

## Basic usage

1. Run `metadata.exe` (or `python metadata.py`).
2. Click **Set folder with images** and choose the media folder.
3. Click **Set output folder** and choose where the output should go.
4. Optionally enter a filename, starting index, and toggle **Time in UTC** or **Add Hyperlinks**.
5. Check **Recursive Mode** if you want to scan subfolders. A new field will appear; enter the **Recursion Depth** (e.g., `1` for immediate subfolders, `5` for deep trees).
6. Choose **Excel** or **CSV** output format.
7. Click **Execute**. A progress bar will track the scan.

## Building from Source

To compile the standalone Windows executable:

pyinstaller --onefile --windowed metadata.py
