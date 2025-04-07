import os
import pathlib
import shutil
import time
from datetime import datetime
from typing import Optional

import piexif

from takeout_tools.image import is_piexif_supported, merge_exif
from takeout_tools.video import is_ffmpeg_supported, merge_geolocation_for_video


def get_geolocations_from_metadata(metadata: dict):
    return tuple(
        metadata['geoData'][name]
        for name in ('latitude', 'longitude', 'altitude')
    )


def modify_file_creation_time(file_path, timestamp: int):
    date = datetime.fromtimestamp(timestamp)
    t = time.mktime(date.timetuple())
    os.utime(file_path, (t, t))


def merge_exif_from_metadata(
        from_file: pathlib.Path,
        metadata: dict,
        target_file: Optional[pathlib.Path],
        target_folder: Optional[pathlib.Path],
        **options
):
    assert target_file is not None or target_folder is not None
    if target_file is None:
        target_file = target_folder.joinpath(from_file.name)

    # extract information from metadata
    timestamp = int(metadata['photoTakenTime']['timestamp'])
    latitude, longitude, altitude = get_geolocations_from_metadata(metadata)

    # format asserting
    ext_lower = str.lower(from_file.suffix)

    if is_piexif_supported(ext_lower):
        print(f'File {from_file} using piexif.')

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

    elif is_ffmpeg_supported(ext_lower):
        merge_geolocation_for_video(from_file, target_file, timestamp, latitude, longitude, altitude)

    # modify creation time
    modify_file_creation_time(target_file, timestamp)
