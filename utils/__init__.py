import os
import pathlib
import shutil
from functools import reduce

import piexif

from utils.exif import set_date_exif, make_gps_dict


def get_all_files(root: pathlib.Path, recursive=False):
    files = []
    for item in root.iterdir():
        if item.is_file():
            files.append(item)
        elif item.is_dir():
            if recursive:
                files.extend(get_all_files(item))
        else:
            raise 'Unknown type: {item}'
    return files


def argmin(a):
    return min(range(len(a)), key=a.__getitem__)


def argmax(a):
    return max(range(len(a)), key=a.__getitem__)


def remove_incompatible_characters(title):
    incompatible_characters = '%<>=:?¿*#&{}\\@!¿+|"\''
    return reduce(lambda t, c: t.replace(c, ''), incompatible_characters, title)


def get_possible_titles(title, prefer_original=False, fix_title=False):
    if fix_title:
        title = remove_incompatible_characters(title)

    if prefer_original:
        yield title

    file_name, ext = os.path.splitext(title)

    yield file_name + '-edited' + ext
    yield file_name + "(1)" + ext

    if not prefer_original:
        yield title


def merge_exif(exif_dict: dict, metadata: dict, prefer_original_geo_data=True, remove_thumbnail=True):
    timestamp = int(metadata['photoTakenTime']['timestamp'])
    set_date_exif(exif_dict, timestamp)

    if remove_thumbnail and 'thumbnail' in exif_dict:
        del exif_dict['thumbnail']

    latitude = metadata['geoData']['latitude']
    longitude = metadata['geoData']['longitude']
    altitude = metadata['geoData']['altitude']

    if altitude != 0 and latitude != 0:
        gps_dict = make_gps_dict(altitude, latitude, longitude)
        original_gps = exif_dict['GPS']

        if prefer_original_geo_data:
            exif_dict['GPS'] = gps_dict | original_gps
        else:
            exif_dict['GPS'] = original_gps | gps_dict

    return exif_dict


def merge_exif_from_metadata(from_img, metadata, target_path, **options):
    if not isinstance(from_img, str):
        from_img = str(from_img)
    exif_dict = piexif.load(from_img)
    merged_exif_dict = merge_exif(exif_dict, metadata, **options)

    shutil.copy2(from_img, target_path)

    piexif.insert(piexif.dump(merged_exif_dict), target_path)
