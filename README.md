# Metadata Extractor by Pianocraft1YT

Metadata Extractor is a Tkinter desktop utility for cataloging folders of camera, drone, or action-cam media. It reads EXIF date/time metadata from photos, uses video files as sequence delimiters, and writes a formatted `.xlsx` workbook.

It is designed for folders where files are sorted alphabetically and often follow a pattern like:

photo, photo, photo, video, photo, photo, photo, video...

The script can detect that pattern and output one row per photo+video series, using the last photo in each series as the representative file. Folders containing only photos are also supported and output one row per image.

## Features

- Extracts `DateTime` / `DateTimeOriginal` EXIF metadata from many image formats, including JPEG, HEIC, PNG, TIFF, and common RAW files.
- Skips videos for metadata extraction but uses them to detect photo/video series boundaries.
- Supports single-folder mode or one-level subfolder recursion.
- In recursive mode, each subfolder becomes its own Excel worksheet.
- Optional `Image # Series` column with configurable starting index.
- Outputs `Files`, `Dates`, `Time`, and optional `Image # Series` columns to `.xlsx`.
- Simple Tkinter GUI: choose input folder, output folder, filename, recursion, and execute.
- Overwrite prompts, sheet-name sanitization, and Windows-safe filename cleaning.
- Keep-open option for debugging or repeated runs.

## Limitations

- Video metadata is not read; videos are only used as pattern markers.
- The first file in a folder cannot be a video.
- If more than 5 photos appear before the first video, the pattern is treated as unpredictable and a warning is shown.
- Recursive mode only scans immediate subfolders, not deeply nested trees.
- Every image must contain usable EXIF date/time metadata.
- Output is Excel `.xlsx` only.

## Requirements

- Python 3
- Pillow
- pandas
- openpyxl
- tkinter usually included with Python

## Basic usage

1. Run metadata.exe.
2. Click **Set folder with images** and choose the media folder.
3. Click **Set output folder** and choose where the `.xlsx` should go.
4. Optionally enter a filename, starting index, and check **Scan subfolders**.
5. Click **Execute**.

## Credits

Original code by Pianocraft1YT.  
Tutorial: https://youtu.be/ruWNKBdbYoo
