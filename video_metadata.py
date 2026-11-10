# Seconds from 1904-01-01 (MP4 epoch) to 1970-01-01 (Unix epoch).
MP4_EPOCH_OFFSET = 2_082_844_800

from datetime import UTC, datetime


# Finds box "target" in mp4/mov files
def _find_box(file, target, start, end):
    offset = start
    while offset + 8 <= end:
        file.seek(offset)
        header = file.read(8)
        if len(header) < 8:
            return None
        box_type = header[4:8].decode("ascii", errors="replace")
        size = int.from_bytes(header[0:4], "big")
        if size == 1:
            # 64-bit extended size in the next 8 bytes
            ext = file.read(8)
            if len(ext) < 8:
                return None
            size = int.from_bytes(ext, "big")
            header_size = 16
        elif size == 0:
            # box extends to end of parent
            size = end - offset
            header_size = 8
        else:
            header_size = 8
        if size < header_size:
            return None
        if box_type == target:
            payload_start = offset + header_size
            payload_end = offset + size
            if payload_end > end:
                return None
            return payload_start, payload_end
        offset += size


# Extracts only date + time from video metadata, if present in file's mvhd box and parseable. Output is a datetime object. It's string form is "YYYY-MM-DD HH:MM:SS+00:00" (always UTC)
def extract_video_metadata(video_path):
    try:
        video_path = video_path.as_posix()
        # rb means read bytes of file
        with open(video_path, "rb") as f:
            f.seek(0, 2)
            end = f.tell()
            moov = _find_box(f, "moov", 0, end)
            if moov is None:
                return None
            mvhd = _find_box(f, "mvhd", moov[0], moov[1])
            if mvhd is None:
                return None
            f.seek(mvhd[0])
            version_and_flags = f.read(4)
            if len(version_and_flags) < 4:
                return None
            version = version_and_flags[0]
            if version == 0:
                raw = f.read(4)
                if len(raw) < 4:
                    return None
                creation_time = int.from_bytes(raw, "big")
            elif version == 1:
                raw = f.read(8)
                if len(raw) < 8:
                    return None
                creation_time = int.from_bytes(raw, "big")
            else:
                return None
            if creation_time == 0:
                return None
            unix_time = creation_time - MP4_EPOCH_OFFSET
            if unix_time < 0:
                return None
            try:
                return datetime.fromtimestamp(unix_time, tz=UTC)
            except (ValueError, OSError, OverflowError):
                return None

    except OSError:
        return None
