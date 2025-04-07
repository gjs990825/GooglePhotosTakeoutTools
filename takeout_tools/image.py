import pathlib
import shutil
from copy import deepcopy
from datetime import datetime
from decimal import Decimal

import piexif

ALTITUDE_FLOAT_DIGITS = 2
POSITION_FLOAT_DIGITS = 6


def is_jpeg_ext(ext):
    return ext in ('.jpg', '.jpeg', '.jpe', '.jif', '.jfif', '.jfi')


def is_webp_ext(ext):
    return ext == '.webp'


def is_tiff_ext(ext):
    return ext in ('.tif', '.tiff')


def is_piexif_supported(ext):
    return any(checker(ext) for checker in (is_jpeg_ext, is_webp_ext, is_tiff_ext))


def set_date_exif(exif_dict, timestamp):
    date_time_str = datetime.fromtimestamp(timestamp).strftime("%Y:%m:%d %H:%M:%S")
    exif_dict['0th'][piexif.ImageIFD.DateTime] = date_time_str
    exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_time_str
    exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = date_time_str


def to_fraction_tuple(x: float, digits: int):
    return Decimal(format(x, '.{}f'.format(digits))).as_integer_ratio()


def to_dms_tuples(decimal_degree: float):
    t0 = abs(decimal_degree)
    degrees = int(t0)
    t1 = (t0 - degrees) * 60
    minutes = int(t1)
    t2 = (t1 - minutes) * 60
    seconds = round(t2, 5)

    return tuple(
        to_fraction_tuple(x, digits=POSITION_FLOAT_DIGITS)
        for x in (degrees, minutes, seconds)
    )


def make_gps_dict(altitude: float, latitude: float, longitude: float):
    return {
        piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
        piexif.GPSIFD.GPSAltitudeRef: int(altitude > 0),
        piexif.GPSIFD.GPSAltitude: to_fraction_tuple(abs(altitude), ALTITUDE_FLOAT_DIGITS),
        piexif.GPSIFD.GPSLatitudeRef: 'N' if latitude > 0 else 'S',
        piexif.GPSIFD.GPSLatitude: to_dms_tuples(latitude),
        piexif.GPSIFD.GPSLongitudeRef: 'E' if longitude > 0 else 'W',
        piexif.GPSIFD.GPSLongitude: to_dms_tuples(longitude),
    }


def merge_exif(
        exif_dict: dict,
        timestamp: int,
        latitude: float,
        longitude: float,
        altitude: float,
        prefer_original_geo_data=True,
        remove_thumbnail=True
):
    set_date_exif(exif_dict, timestamp)

    if remove_thumbnail and 'thumbnail' in exif_dict:
        del exif_dict['thumbnail']

    if altitude != 0 and latitude != 0:
        gps_dict = make_gps_dict(altitude, latitude, longitude)
        original_gps = exif_dict['GPS']

        if prefer_original_geo_data:
            gps_dict = gps_dict | original_gps
        else:
            gps_dict = original_gps | gps_dict

        exif_dict['GPS'] = gps_dict

    cp = deepcopy(exif_dict)
    for tag, contents in exif_dict.items():
        for subtag, subcontents in contents.items():
            if piexif.TAGS[tag][subtag]['type'] == piexif.TYPES.Undefined:
                cp[tag][subtag] = bytes(subcontents)
    return cp


def merge_exif_for_image(
        from_file: pathlib.Path,
        target_file: pathlib.Path,
        timestamp,
        latitude,
        longitude,
        altitude,
        **options,
):
    exif_dict = piexif.load(from_file.as_posix())
    merged_exif_dict = merge_exif(
        exif_dict,
        timestamp,
        latitude,
        longitude,
        altitude,
        **options
    )

    # copy and insert exif
    shutil.copy2(from_file, target_file)

    try:
        exif_bytes = piexif.dump(merged_exif_dict)
    except Exception as e:
        print(merged_exif_dict)
        raise e

    piexif.insert(exif_bytes, target_file.as_posix())
