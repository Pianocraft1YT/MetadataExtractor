# Metadata Extractor by Pianocraft1YT

Metadata Extractor is a Tkinter desktop utility for cataloging folders of camera, drone, or image media. It reads EXIF metadata from photos, uses video files as sequence delimiters, and writes a formatted Excel, CSV, JSON, or Markdown output.

It is designed for folders where files are sorted alphabetically and often follow a pattern like:

photo, photo, photo, video, photo, photo, photo, video...

The script can detect that pattern and output one row per photo+video series, using the last photo in each series as the representative file. 

Folders containing only photos are also supported and output one row per image.

Executable found here: https://github.com/Pianocraft1YT/MetadataExtractor/releases
## Features

- Extracts `DateTime` / `DateTimeOriginal` EXIF metadata from many image formats, including JPEG, HEIC, PNG, TIFF, and common RAW files.
- Skips videos for metadata extraction but uses them to detect photo/video series boundaries.
- **Full recursive scanning**: Walk deep directory trees with a configurable recursion depth. Each photo-bearing subfolder becomes its own worksheet (or its own CSV / Markdown file).
- **Live progress bar**: The UI stays completely responsive during massive scans. A background worker thread processes files while the window displays the current subfolder, scan percentage, and live processed/skipped counters.
- **Output formats**: Excel (`.xlsx`), CSV (`.csv`), JSON (`.json`), or GitHub-Flavored Markdown (`.md`), selectable via radio buttons.
- **Optional UTC conversion**: reads `OffsetTimeOriginal` and shifts timestamps to UTC when the "Time in UTC" checkbox is enabled. Photos without an offset tag are left unchanged.
- **Optional extra metadata columns** via the **Extra Metadata** checkbox: image dimensions, camera make / model, software, lens model, aperture (FNumber), exposure time, focal length, and ISO — each individually toggleable.
- **Optional GPS coordinates**: two extra columns (GPS Latitude, GPS Longitude) as signed decimal degrees with six-decimal precision. Off by default; a warning label appears when enabled, since coordinates reveal location.
- **Optional clickable hyperlinks** in Excel and Markdown output: every filename in the Files column links to the source file on disk. Unsupported in CSV and JSON.
- Optional `Img # Series` column with configurable starting index.
- **Warning log file**: If any files are skipped (missing metadata, corrupt, etc.), a `warnings.log` file is generated alongside the output with detailed error categorization.
- Simple Tkinter GUI: choose input folder, output folder, filename, recursion, timezone, hyperlinks, and execute.
- Overwrite prompts, sheet-name sanitization, and Windows-safe filename cleaning.
- Keep-open option for debugging or repeated runs.

## Output formats

| Format | Extension | Per-subfolder files | Hyperlinks |
|---|---|---|---|
| Excel | `.xlsx` | No (one workbook, one sheet per folder) | Yes |
| CSV | `.csv` | Yes | No |
| JSON | `.json` | No (one file, one dict per sheet) | No |
| Markdown | `.md` | Yes | Yes |

CSV and Markdown can't nest sheets inside a single file, so in recursive mode they produce one file per subfolder — and prompt for confirmation before running.

## Limitations

- Video metadata is not read; videos are only used as pattern markers and are not counted in the progress bar.
- The first file in a folder can be a video, but user will be prompted about it.
- If more than 5 photos appear before the first video, the pattern is treated as unpredictable and a warning is shown.
- Hyperlinks are supported in Excel and Markdown only, not CSV or JSON.
- Recursive CSV and Markdown mode produces one file per subfolder and asks for confirmation before running.
- Markdown output does not currently include frontmatter, per-column alignment, or hyperlinks outside the Files column.
- GPS altitude (`GPSAltitudeRef`, `GPSAltitude`) and `GPSDateStamp` are not extracted.

## Requirements

- Python 3.11 or newer (3.11, 3.12, 3.13, and 3.14 supported and tested)
- Pillow
- pandas
- openpyxl
- tk-date-entry
- tkinter (usually included with Python)

## Basic usage

1. Run `metadata.exe` (or `python metadata.py`).
2. Click **Set folder with images** and choose the media folder.
3. Click **Set output folder** and choose where the output should go.
4. Optionally enter a filename and starting index, and toggle **Time in UTC**, **Add Hyperlinks**, **Extra Metadata** (with its sub-checkboxes for individual EXIF fields), and **GPS Coordinates**.
5. Check **Recursive Mode** if you want to scan subfolders. A new field will appear; enter the **Recursion Depth** (e.g., `1` for immediate subfolders, `5` for deep trees).
6. Choose **Excel**, **CSV**, **JSON**, or **Markdown** output format.
7. Click **Execute**. A progress bar will track the scan.

## Building from Source

To compile the standalone Windows executable:

```
pyinstaller --onefile --windowed metadata.py
```
This program *should* run on Linux, though currently a distributable is not available.

## Video Tutorial
A video tutorial is planned for December 2026, will add when finished