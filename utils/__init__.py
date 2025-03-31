import os
from functools import reduce


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
