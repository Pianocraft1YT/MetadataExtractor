# Release Table and Changes:
A quaint table for release information.
Created from new tags/releases and old tags/releases from past repo.

# Full tag history — 54 tags

| Version | Date | Summary |
|---|---|---|
| v2.2.0 | 2026-02-11 | Cross-platform (Windows + Debian AMD64). Range Spreadsheet v1.0.0 bundled. |
| v2.3.0 | 2026-02-18 | Sorting files, better efficiency, common video types |
| v2.3.1 | 2026-02-18 | Code cleanup |
| v2.3.2 | 2026-02-18 | Temporary fix for irregular image+video patterns |
| v2.3.3 | 2026-02-18 | Bigger, draggable window |
| v2.4.0 | 2026-02-20 | Image + Video combinations, Image # series fixed, sorting fixed |
| v2.4.1 | 2026-02-20 | Changed size of window |
| v2.4.2 | 2026-02-20 | Fixed folders with only images, no videos |
| v2.4.3 | 2026-02-20 | Series support, sorting fix, only-image folder fix |
| v2.4.5 | 2026-07-28 | Bugfixes: video-first edge cases, `photos_before_video_present` rename |
| v2.1.2 | 2026-07-28 | Mislabeled tag from the v2.4.5 session |
| v2.5 | 2026-09-01 | Bump *(empty tag message)* |
| v2.5.1 | 2026-09-01 | Hotfix: forgot a return statement *(GitHub release body re-tells the v2.5 story)* |
| v2.5.2 | 2026-09-19 | Fix irregular pattern crash when >5 photos precede first video |
| v2.6 | 2026-09-19 | Recursive scan mode (one level deep) and photo pairing fix |
| v2.6.1 | 2026-09-19 | Sheet name sanitization and deduplication |
| v2.6.2 | 2026-09-19 | Custom output filename + `clean_name` helper |
| v2.6.3 | 2026-09-20 | Overwrite checking and keep-open toggle |
| v2.7 | 2026-09-20 | Starting index offset for Image # Series |
| **v3.0** | 2026-09-20 | **Big release:** recursive scanning, custom filename, series offset, overwrite, keep-open, sheet dedup |
| v3.0.1 | 2026-09-20 | Bump: executable + `.pyw` update *(GitHub release re-uses v3.0 notes)* |
| v3.0.2 | 2026-10-14 | `scan_image` EXIF priority chain, error handling, named constants |
| v3.0.4 | 2026-10-14 | Pytest suite (73 tests), series numbering fix, `.py`/`.pyw` unify |
| v3.1.0 | ~2026-10-19 | Bump: latest executable + info addition |
| v3.1.1 | 2026-10-19 | Refactor: `output_series` parameter instead of global |
| v3.1.2 | 2026-10-19 | Refactor: collapse DataFrame/make_series branches |
| v3.1.3 | ~2026-10-19 | Bump: return `(processed, skipped)` from scan functions |
| v3.1.4 | 2026-10-19 | CI: update a test |
| v3.2.0 | ~2026-10-19 | Bump: update `.exe` |
| v3.3.0 | 2026-10-19 | Refactor: convert module-level code into `MetadataExtractor` class |
| v3.3.1 | 2026-10-19 | Refactor: `verify_name` takes `used` set as parameter |
| v3.3.2 | 2026-10-21 | Timezone checkbox + lint cleanup |
| v3.4.0 | 2026-10-21 | UTC conversion via EXIF `OffsetTimeOriginal` |
| v3.5.0 | 2026-10-22 | Bump *(empty tag message)* |
| v3.5.1 | 2026-10-23 | CSV path bugs, extension handling, Python 3.11 compat |
| v3.6.0 | 2026-10-23 | Clickable file hyperlinks in Excel output |
| v3.7.0 | 2026-10-25 | Full recursive scanning with configurable depth |
| v3.8.0 | 2026-10-26 | Live progress bar with threaded scanning |
| v3.8.1 | 2026-10-26 | Progress bar completion, skipped-file accounting |
| v3.9.0 | 2026-10-27 | Video-first orphan handling, progress bar polish |
| v3.9.1 | 2026-10-27 | `files_and_dirs` → `media_files`, Debug Mode |
| v3.9.2 | 2026-10-27 | CI: fix tests for debug |
| v3.10.0 | 2026-10-27 | Cancellable scanning |
| v3.11.0 | 2026-10-28 | ETA, progress-bar overflow fix, test suite overhaul |
| v3.11.1 | 2026-10-29 | Thread safety, crash guards, progress accounting, extension forcing |
| v3.11.2 | 2026-10-29 | Reformat with black (no logic changes) |
| v3.12.0 | 2026-10-30 | Extra metadata columns (dimensions, make, model, software, lens) |
| v3.13.0 | 2026-10-30 | Rational EXIF columns (aperture, exposure, focal length, ISO) |
| v3.14.0 | 2026-10-30 | Date range filter (start/end, optional, local EXIF time) |
| v3.15.0 | 2026-10-31 | JSON export |
| v3.16.0 | 2026-10-31 | Settings persistence |
| v3.17.0 | 2026-11-01 | GPS coordinates (EXIF tag 34853 sub-IFD) |
| v3.18.0 | 2026-11-01 | Markdown output (GFM tables, one file per sheet) |
| v3.18.1 | 2026-11-01 | Markdown hyperlinks (`[name](<url>)` in Files column) |
