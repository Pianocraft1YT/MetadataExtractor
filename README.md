# Metadata Extractor by Pianocraft1YT
![Image of Metadata Extractor App](image.png)
---
Metadata Extractor is a Tkinter desktop utility for cataloging folders of camera, drone, or action-cam media. It extracts EXIF metadata from photos and `mvhd` creation timestamps from `.mp4`/`.mov` videos, groups captures into bursts by timestamp proximity, and exports formatted Excel, CSV, JSON, or Markdown reports.

Folders of photos and videos are clustered chronologically using a configurable **Photo grouping cutoff** (default `2` seconds). By default, videos contribute timestamps and series slots without producing output rows; enabling **Create Video Rows** (Advanced mode) includes timestamped videos directly in the exported tables. Photos or videos without timestamps are handled cleanly without aborting the folder.

Executable found here: https://github.com/Pianocraft1YT/MetadataExtractor/releases

Release History/Roadmap found here: https://github.com/Pianocraft1YT/MetadataExtractor/blob/main/ReleaseNotes.md

## Features

- **EXIF & sub-IFD extraction**: Reads `DateTimeOriginal`, `DateTimeDigitized`, and `DateTime` (across IFD0 and the Exif sub-IFD) from JPEG, PNG, TIFF, and more, plus optional `.heic`/`.heif` support when `pillow-heif` is installed.
- **Timestamp-proximity burst grouping**: Groups photos and `.mp4`/`.mov` videos captured within a configurable **Photo grouping cutoff** (default `2.0` seconds; `0` groups identical timestamps) and assigns shared `Img # Series` labels (e.g. `1-3`) with an optional custom starting index.
- **Basic and Advanced modes**: Launches in a streamlined **Basic** view for everyday scans and expands **Advanced** controls (Debug Mode, Create Video Rows, Starting index, Sort Method, Date Range, Hidden Files, Time in UTC, GPS, Extra Metadata) on demand.
- **Create Video Rows (Advanced)**: Opt-in toggle that emits output rows for timestamped `.mp4`/`.mov` videos (including video-only bursts and folders) with `File Size` and optional video `Dimensions` (when `hachoir` is installed).
- **Full recursive scanning**: Walk directory trees up to a configurable **Recursion Depth**. Each media-bearing subfolder becomes its own worksheet (Excel/JSON) or its own CSV/Markdown file.
- **Sorting & date filtering (Advanced)**: Sort rows by `Timestamp` (default), `Date (Oldest)`, or `Date (Newest)` (keeping bursts intact), and optionally filter media by Start/End local dates with an **Include undateable files** toggle.
- **Live progress bar & cancellation**: Threaded scanning with single-open photo/video caching, live scanned/skipped counters, current subfolder display, ETA, elapsed time, and a **Cancel** button.
- **Formatted output formats**: Excel (`.xlsx` with frozen header row, bold headers, AutoFilter, auto-fitted column widths, XML control-character scrubbing, and formula-injection neutralization), CSV (`.csv`), JSON (`.json`), and GitHub-Flavored Markdown (`.md`).
- **Optional UTC conversion (Advanced)**: Pairs each matched EXIF datetime with its corresponding `OffsetTime*` tag and shifts timestamps to UTC before burst clustering and formatting.
- **Optional extra metadata columns (Advanced)** via **Extra Metadata**: `Image Dimensions`, `File Size`, `Camera Make`, `Camera Model`, `Software`, `Lens Model`, `FNumber / Aperture`, `Exposure Time`, `Focal Length`, and `ISO` — each individually toggleable.
- **Optional GPS coordinates (Advanced)**: `GPS Latitude` and `GPS Longitude` from the GPS IFD as signed decimal degrees (6-decimal precision), with an on-screen privacy notice when enabled.
- **Clickable hyperlinks**: Links filenames in the `Files` column to the files on disk in Excel (`file:///` URIs) and Markdown (`[name](<url>)`). Unsupported in CSV and JSON.
- **Path visibility, auto-open, & `warnings.log` viewer**: Displays truncated `Source:` and `Output:` paths in the main window, optionally opens the output folder on completion (**Auto-Open Output Folder**), and provides a **View warnings.log** button whenever warnings are written.
- **Persistent settings**: Saves UI options and folder selections to `~/.metadata-extractor/settings.json` (Debug Mode is never persisted).

## Output formats

| Format | Extension | Per-subfolder files | Hyperlinks |
|---|---|---|---|
| Excel | `.xlsx` | No (one workbook, one sheet per folder) | Yes |
| CSV | `.csv` | Yes | No |
| JSON | `.json` | No (one file, one dict per sheet) | No |
| Markdown | `.md` | Yes | Yes |

CSV and Markdown can't nest multiple sheets inside a single file, so in recursive mode they produce one file per subfolder — and prompt for confirmation before running.

## Limitations

- **Video containers & timestamps**: `mvhd` timestamp extraction supports `.mp4` and `.mov` containers; `.mkv`, `.avi`, `.webm`, and `.wmv` cannot contribute timestamps (logged under `"Unsupported Video Format"`), and video timestamps are read as naive wall-clock time.
- **Dateless videos**: Even with **Create Video Rows** enabled, videos without a readable `mvhd` timestamp do not produce output rows.
- **Optional dependencies**: `.heic`/`.heif` decoding requires `pillow-heif` (without it, HEIC/HEIF files are skipped with `"HEIC/HEIF requires pillow-heif"` in `warnings.log`). Video dimensions in **Create Video Rows** require `hachoir`.
- **Camera RAW formats**: Common RAW extensions are listed in `PHOTO_TYPES`, but no dedicated RAW EXIF reader/decoder is bundled beyond what Pillow opens natively.
- **Hyperlinks**: Supported in Excel and Markdown only, not CSV or JSON.
- **Markdown & GPS scope**: Markdown output does not include frontmatter, per-column alignment, or hyperlinks outside the `Files` column. GPS altitude (`GPSAltitudeRef`, `GPSAltitude`) and `GPSDateStamp` are not extracted.

## Requirements

- Python 3.11 or newer (3.11, 3.12, 3.13, and 3.14 supported and tested)
- Pillow
- pandas
- openpyxl
- tk-date-entry
- tkinter (usually included with Python)
- **Optional**: `pillow-heif` (for `.heic`/`.heif` support), `hachoir` (for video dimensions when **Create Video Rows** is enabled)

## Basic usage

1. Run `metadata.exe` (or `python metadata.py`).
2. Click **Set folder with images** and choose the media folder, then click **Set output folder** and choose where exports should be saved.
3. Optionally adjust **Photo grouping cutoff (default 2 seconds)**, enter a custom filename, or check **Add Hyperlinks**, **Keep Open After Scan**, and **Auto-Open Output Folder**.
4. Check **Recursive Mode** if you want to scan subfolders, and enter a **Recursion Depth** (defaults to `1` if left unset).
5. Switch to **Advanced** if you want **Debug Mode**, **Create Video Rows**, custom **Starting index**, **Sort Method**, **Date Range (Local Time)**, **Include Hidden Files**, **Time in UTC**, **GPS**, or **Extra Metadata** columns.
6. Choose **Excel**, **CSV**, **JSON**, or **Markdown** output format.
7. Click **Execute**. A live progress bar tracks the scan; if any warnings are logged, click **View warnings.log** afterward to inspect them.

## Building from Source

To compile the standalone Windows executable:

```
pyinstaller --onefile --windowed metadata.py
```
This program runs cross-platform on Windows, macOS, and Linux (though prebuilt binaries are currently published for Windows).

## Video Tutorial
A video tutorial is planned for December 2026, will add when finished