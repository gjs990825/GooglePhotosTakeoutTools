import pathlib
import subprocess


def is_ffmpeg_supported(ext):
    return ext in ('.mp4', '.mov')


def add_geolocation_to_video(input_file, output_file, loc_iso_6709: str):
    """like this ffmpeg -i input.mp4 -map_metadata 0 -metadata location=17.641347+160.931648 -metadata location-eng=17.641347+160.931648 -c copy output.mp4"""
    # Use ffmpeg to copy existing video/audio streams and add metadata
    command = [
        'ffmpeg',
        '-i', input_file,
        '-map_metadata', '0',
        '-metadata', f'location={loc_iso_6709}',
        '-metadata', f'location-eng={loc_iso_6709}',
        '-c', 'copy',
        output_file
    ]

    # Execute the command
    result = subprocess.run(command)
    assert result.returncode == 0, f'FFmpeg execution error, code: {result.returncode}'


def to_iso6709(latitude, longitude, altitude=None):
    lat_string = f"{latitude:+08.5f}"
    lon_string = f"{longitude:+09.5f}"
    iso6709_str = f"{lat_string}{lon_string}"

    # drop altitude
    _ = altitude
    # if altitude is not None:
    #     iso6709_str += f"{altitude:+08.5f}"
    return iso6709_str


def merge_geolocation_for_video(
        from_file: pathlib.Path,
        target_file: pathlib.Path,
        timestamp,
        latitude,
        longitude,
        altitude,
):
    _ = timestamp
    add_geolocation_to_video(
        from_file,
        target_file,
        to_iso6709(latitude, longitude, altitude)
    )
