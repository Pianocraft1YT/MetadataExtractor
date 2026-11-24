from PIL import Image
from PIL.TiffImagePlugin import IFDRational

img = Image.new("RGB", (148, 196), color="blue")
exif = Image.Exif()

# --- IFD0 (Main Image / Camera / Author) ---
exif[270] = "Test photo with full EXIF"          # ImageDescription
exif[271] = "Canon"                              # Make
exif[272] = "Canon EOS R5"                       # Model
exif[274] = 6                                    # Orientation (Rotated 90° CW)
exif[282] = IFDRational(72, 1)                   # XResolution
exif[283] = IFDRational(72, 1)                   # YResolution
exif[296] = 2                                    # ResolutionUnit (Inches)
exif[305] = "Extractor of Metadata"              # Software
exif[306] = "2024:12:02 02:02:02"                # DateTime (ModifyDate)
exif[315] = "Extractor Test"                     # Artist
exif[33432] = "Public Domain"                    # Copyright

# --- 0x8769 (Exif Sub-IFD: Dates, Offsets, Exposure, Lens, Settings) ---
exif[0x8769] = {
    33434: IFDRational(1, 500),                  # ExposureTime (1/500)
    33437: IFDRational(28, 10),                  # FNumber (f/2.8)
    34850: 3,                                    # ExposureProgram (Aperture-priority)
    34855: 400,                                  # ISOSpeedRatings
    36864: b"0232",                              # ExifVersion (2.32)
    36867: "2024:12:01 01:01:01",                # DateTimeOriginal
    36868: "2024:12:01 01:02:01",                # DateTimeDigitized
    36880: "+02:00",                             # OffsetTime
    36881: "+02:00",                             # OffsetTimeOriginal
    36882: "+02:00",                             # OffsetTimeDigitized
    37377: IFDRational(8965784, 1000000),        # ShutterSpeedValue (APEX)
    37378: IFDRational(2970854, 1000000),        # ApertureValue (APEX)
    37379: IFDRational(-97, 10),                 # BrightnessValue
    37380: IFDRational(-3, 10),                  # ExposureBiasValue (-0.3 EV)
    37381: IFDRational(14, 10),                  # MaxApertureValue
    37382: IFDRational(125, 10),                 # SubjectDistance (12.5 m)
    37383: 5,                                    # MeteringMode (Pattern)
    37384: 1,                                    # LightSource (Daylight)
    37385: 16,                                   # Flash (Off, Did not fire)
    37386: IFDRational(50, 1),                   # FocalLength (50mm)
    37510: b"ASCII\x00\x00\x00u found me",       # UserComment
    37520: "68",                                 # SubSecTime
    37521: "68",                                 # SubSecTimeOriginal
    37522: "68",                                 # SubSecTimeDigitized
    40961: 1,                                    # ColorSpace (sRGB)
    40962: 148,                                  # PixelXDimension (ExifImageWidth)
    40963: 196,                                  # PixelYDimension (ExifImageHeight)
    41986: 0,                                    # ExposureMode (Auto)
    41987: 0,                                    # WhiteBalance (Auto)
    41988: IFDRational(1, 1),                    # DigitalZoomRatio
    41989: 50,                                   # FocalLengthIn35mmFilm
    41990: 0,                                    # SceneCaptureType (Standard)
    41991: 0,                                    # GainControl (None)
    41992: 0,                                    # Contrast (Normal)
    41993: 0,                                    # Saturation (Normal)
    41994: 0,                                    # Sharpness (Normal)
    42033: "000000001",                          # BodySerialNumber
    42035: "Canon",                              # LensMake
    42036: "RF 50mm F1.2L USM",                  # LensModel
    42037: "100000002",                          # LensSerialNumber
}

# --- 0x8825 (GPS IFD) ---
exif[0x8825] = {
    1: "N",                                      # GPSLatitudeRef
    2: (IFDRational(48, 1), IFDRational(51, 1), IFDRational(24, 1)),  # GPSLatitude
    3: "E",                                      # GPSLongitudeRef
    4: (IFDRational(2, 1), IFDRational(21, 1), IFDRational(7, 1)),    # GPSLongitude
    5: 0,                                        # GPSAltitudeRef (0 = above sea level)
    6: IFDRational(1245, 10),                    # GPSAltitude (124.5 m)
    7: (IFDRational(1, 1), IFDRational(1, 1), IFDRational(1, 1)),     # GPSTimeStamp
    12: "K",                                     # GPSSpeedRef (km/h)
    13: IFDRational(305, 10),                    # GPSSpeed
    16: "T",                                     # GPSImgDirectionRef (True north)
    17: IFDRational(122, 10),                    # GPSImgDirection
    23: "T",                                     # GPSDestBearingRef (True north)
    24: IFDRational(1426, 10),                   # GPSDestBearing
    29: "2024:12:01",                            # GPSDateStamp
}

out_path = "kitchen_sink_exif.jpg"
img.save(out_path, format="JPEG", exif=exif, quality=85)

# Verify round-trip
with Image.open(out_path) as check:
    read_exif = check.getexif()
    print("IFD0 count:", len(read_exif))
    print("0x8769 count:", len(read_exif.get_ifd(0x8769)))
    print("0x8825 count:", len(read_exif.get_ifd(0x8825)))