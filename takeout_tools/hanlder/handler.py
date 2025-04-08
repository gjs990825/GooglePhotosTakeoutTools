import pathlib
import shutil
from abc import abstractmethod, ABC, ABCMeta
from typing import Optional

from takeout_tools.utils import get_geolocations_from_metadata, modify_file_creation_time


class MediaHandlerMeta(ABCMeta):
    """Metaclass to register subclasses automatically."""
    _registry = []
    fallback = None

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        if cls.__name__ == 'MediaHandler':
            return
        if cls.__name__ == 'FallbackHandler':
            MediaHandlerMeta.fallback = cls
            return
        MediaHandlerMeta._registry.append(cls)

    @classmethod
    def list_handlers(cls):
        return MediaHandlerMeta._registry


class MediaHandler(ABC, metaclass=MediaHandlerMeta):
    @classmethod
    def handler_for_extension(cls, ext: str, allow_fallback=False):
        ext = ext.lower()
        for handler in cls.list_handlers():
            if handler.supports(ext):
                return handler
        if allow_fallback and cls.fallback is not None:
            return cls.fallback
        raise ValueError(f'No handler found for extension {ext}')

    @staticmethod
    def handler_for_media(media_info: dict, allow_fallback=False):
        from_file = media_info['media_path']
        return MediaHandler.handler_for_extension(from_file.suffix, allow_fallback)

    @staticmethod
    @abstractmethod
    def supports(extension: str) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def merge_metadata_for_media(
            from_file: pathlib.Path,
            target_file: pathlib.Path,
            timestamp: int,
            latitude: float,
            longitude: float,
            altitude: float,
            **options,
    ) -> pathlib.Path:
        pass

    @classmethod
    def merge_from_metadata(
            cls,
            media_info: dict,
            metadata: dict,
            target_file: Optional[pathlib.Path] = None,
            target_folder: Optional[pathlib.Path] = None,
            **options
    ) -> None:
        assert target_file is not None or target_folder is not None

        from_file = media_info['media_path']

        if target_file is None:
            target_file = target_folder.joinpath(from_file.name)

        # extract information from metadata
        timestamp = int(metadata['photoTakenTime']['timestamp'])
        latitude, longitude, altitude = get_geolocations_from_metadata(metadata)

        # format asserting
        ext_lower = str.lower(from_file.suffix)
        assert cls.supports(ext_lower), f'{ext_lower} is not supported'

        target_file = cls.merge_metadata_for_media(
            from_file,
            target_file,
            timestamp,
            latitude,
            longitude,
            altitude,
            **options
        )

        # modify creation time
        modify_file_creation_time(target_file, timestamp)


class FallbackHandler(MediaHandler):
    @staticmethod
    def supports(extension: str) -> bool:
        return True

    @staticmethod
    def merge_metadata_for_media(
            from_file: pathlib.Path,
            target_file: pathlib.Path,
            timestamp: int,
            latitude: float,
            longitude: float,
            altitude: float,
            **options
    ) -> pathlib.Path:
        # just copy it
        shutil.copy2(from_file, target_file)
        return target_file
