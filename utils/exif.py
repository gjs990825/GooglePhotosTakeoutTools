from datetime import datetime
from decimal import Decimal

import piexif

altitude_float_digits = 2
position_float_digits = 6


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
        to_fraction_tuple(x, digits=position_float_digits)
        for x in (degrees, minutes, seconds)
    )


def make_gps_dict(altitude: float, latitude: float, longitude: float):
    return {
        piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
        piexif.GPSIFD.GPSAltitudeRef: int(altitude > 0),
        piexif.GPSIFD.GPSAltitude: to_fraction_tuple(abs(altitude), altitude_float_digits),
        piexif.GPSIFD.GPSLatitudeRef: 'N' if latitude > 0 else 'S',
        piexif.GPSIFD.GPSLatitude: to_dms_tuples(latitude),
        piexif.GPSIFD.GPSLongitudeRef: 'E' if longitude > 0 else 'W',
        piexif.GPSIFD.GPSLongitude: to_dms_tuples(longitude),
    }
