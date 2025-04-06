import json
import os
import pathlib
import re
from dataclasses import dataclass
from itertools import compress

from utils import get_all_files, argmax


def get_suffix_number(text):
    pattern = r'(\(\d+\))$'
    match = re.search(pattern, text.strip())

    if match:
        return int(match.group(1).removeprefix('(').removesuffix(')'))
    else:
        return None


# fuzzy match media stem name
def is_matched_stem(partial_stem, full_stem):
    if not full_stem.startswith(partial_stem):
        return False
    return len(partial_stem) / len(full_stem) >= 0.4


# use require_ext to check target extension (for example, image.jpg, image.png and image.mp4)
def is_matched_pair(media_info, metadata, require_ext=False):
    is_matched = is_matched_stem(media_info['target_stem'], metadata['target_stem'])
    if require_ext and metadata['target_ext'] != '':
        return media_info['target_ext'] == metadata['target_ext'] and is_matched
    return is_matched


# use this to handle xxx-COLLAGE.jpg
def stem_similarity(partial_stem, full_stem):
    if not full_stem.startswith(partial_stem):
        return 0.0
    return len(partial_stem) / len(full_stem)


def is_edited_version(target_stem, metadata_objs):
    """
    Warning: only for media that ends with '(1)'.
    Media file ends with '(1)': Situation 1, this file is an edited file. Situation 2, this file is a duplicated name.
    How to tell: if metadata with the same name has a version ends with '(1)', then it's a name duplicated media file.
    If the corresponding metadata file does not end with '(1)', it's an edited file.
    """
    has_matched = False
    for metadata in metadata_objs:
        if metadata['target_stem'].startswith(target_stem):
            has_matched = True
            if metadata['meta_duplicated_number'] == 1:
                return False
    assert has_matched, f'{target_stem} has no matched metadata'
    return True


@dataclass
class MediaVersion:
    ORIGINAL = 'original'
    EDITED = 'edited'


def is_media_metadata(json_obj):
    return json_obj.get('imageViews', None)


def load_metadata_dict(json_path: pathlib.Path):
    json_obj = json.load(json_path.open(encoding='utf-8'))

    json_obj['metadata_path'] = json_path

    file_stem, file_ext = os.path.splitext(json_path.name)
    json_obj['meta_duplicated_number'] = get_suffix_number(file_stem)

    json_obj['target_stem'], json_obj['target_ext'] = os.path.splitext(json_obj['title'])

    return json_obj


def make_media_infos(media_files: list[pathlib.Path], metadata_dicts: list[dict]):
    media_infos = []

    for media_file in media_files:
        media_stem, media_ext = os.path.splitext(media_file.name)

        media_info = {'target_ext': media_ext, 'media_duplicated_number': None}

        if media_stem.endswith('-edited'):  # marked edited
            media_info['version'] = MediaVersion.EDITED
            media_info['target_stem'] = media_stem.removesuffix('-edited')
        elif media_stem.endswith('-edi'):  # google had this abbreviation for 'edited', I'm in shock...
            media_info['version'] = MediaVersion.EDITED
            media_info['target_stem'] = media_stem.removesuffix('-edi')
        elif (suffix_number := get_suffix_number(media_stem)) is not None:  # has mark
            stem_no_suffix = media_stem.removesuffix(f'({suffix_number})')
            if suffix_number == 1:  # special mark
                is_edited = is_edited_version(stem_no_suffix, metadata_dicts)
                if is_edited:  # marked edited (1)
                    media_info['version'] = MediaVersion.EDITED
                else:  # marked but it's a duplicated name
                    media_info['media_duplicated_number'] = suffix_number
                    media_info['version'] = MediaVersion.ORIGINAL
            else:  # just a duplicated name
                media_info['media_duplicated_number'] = suffix_number
                media_info['version'] = MediaVersion.ORIGINAL
            media_info['target_stem'] = stem_no_suffix
        else:  # no mark
            media_info['version'] = MediaVersion.ORIGINAL
            media_info['target_stem'] = media_stem

        media_info['media_path'] = media_file
        print(media_info)
        media_infos.append(media_info)

    return media_infos


def get_single_folder(folder_path: pathlib.Path):
    all_files = get_all_files(folder_path, recursive=False)
    file_types = set([f.suffix.lower() for f in all_files])

    print(f'Found {len(all_files)} files in {folder_path}')
    print(f'File types: {file_types}')

    media_files = list(filter(lambda x: x.suffix != '.json', all_files))
    metadata_files = list(filter(lambda x: x.suffix == '.json', all_files))

    metadata_dicts = [
        d
        for f in metadata_files
        if is_media_metadata(
            d := load_metadata_dict(f)
        )
    ]
    print(f'Metadata files: {len(metadata_files)}, '
          f'media files: {len(media_files)}, '
          f'skipped json files: {len(metadata_files) - len(metadata_dicts)}')

    media_infos = make_media_infos(media_files, metadata_dicts)

    return media_infos, metadata_dicts


def pair_single_folder(folder_path: pathlib.Path, ignore_errors=False, compare_ext_name=False):
    media_infos, metadata_dicts = get_single_folder(folder_path)

    matched_lists = [[] for _ in range(len(metadata_dicts))]
    unmatched_media = []

    for media_info in media_infos:
        candidates = []
        for meta_idx, metadata in enumerate(metadata_dicts):
            if is_matched_pair(media_info, metadata, require_ext=compare_ext_name):  # matched name
                if metadata['meta_duplicated_number'] == media_info['media_duplicated_number']:
                    print(f'matched {metadata}')
                    candidates.append(meta_idx)
                else:
                    print(f'found but not matched {metadata}')

        if not candidates:  # no candidates
            print(f'{media_info["target_stem"]} has no matched metadata')
            unmatched_media.append(media_info)
        else:  # find best candidate
            similarities = [
                stem_similarity(
                    media_info['target_stem'],
                    metadata_dicts[c]['target_stem']
                )
                for c in candidates
            ]
            best_idx = argmax(similarities)
            matched_lists[candidates[best_idx]].append(media_info)
            print(candidates, similarities, best_idx)

    matched_length_list = [len(x) for x in matched_lists]
    unmatched_metadata = list(compress(media_infos, [x == 0 for x in matched_length_list]))

    print(f'Overall matched media {sum(matched_length_list)}, total media {len(media_infos)}')
    print(f'Not matched media: {unmatched_media}')
    print(f'Not matched metadata: {unmatched_metadata}')

    if not ignore_errors:
        assert sum(matched_length_list) == len(media_infos), f'Error: unmatched media: {unmatched_media}'
        assert 0 not in set(matched_length_list), f'Error: unmatched metadata: {unmatched_metadata}'

    paired = [
        (metadata, matched_media)
        for metadata, matched_media in zip(metadata_dicts, matched_lists)
    ]

    return paired, unmatched_media, unmatched_metadata
