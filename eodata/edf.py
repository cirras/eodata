import os
import re

from pathlib import Path
from enum import Enum, auto
from typing import List, Union

from eolib import interleave, deinterleave, swap_multiples


class EDF:
    class Kind(Enum):
        CREDITS = auto()
        CHECKSUM = auto()
        CURSE_FILTER = auto()
        JUKEBOX = auto()
        GAME_1 = auto()
        GAME_2 = auto()

    class Language(Enum):
        ENGLISH = auto()
        DUTCH = auto()
        SWEDISH = auto()
        PORTUGESE = auto()

    _id: int
    _kind: Kind
    _language: Language
    _lines: List[str]

    def __init__(self, id: int, kind: Kind, language: Language, lines: List[str]):
        self._id = id
        self._kind = kind
        self._language = language
        self._lines = lines

    @property
    def id(self) -> int:
        return self._id

    @property
    def kind(self) -> Kind:
        return self._kind

    @property
    def language(self) -> Language:
        return self._language

    @property
    def lines(self) -> List[str]:
        return self._lines

    class Reader:
        _data_directory: os.PathLike

        def __init__(self, data_directory: Union[str, os.PathLike]):
            if isinstance(data_directory, str):
                data_directory = Path(data_directory)
            self._data_directory = data_directory

        def _decode_line(self, line: str, should_swap_multiples: bool) -> str:
            data = bytearray(line.encode('cp1252'))
            deinterleave(data)
            if should_swap_multiples:
                swap_multiples(data, 7)
            return data.decode('cp1252')

        def read(self, id: int) -> 'EDF':
            path = os.path.join(self._data_directory, f'dat{id:03}.edf')

            try:
                with open(path, 'rb') as file:
                    content = file.read().decode('cp1252', 'replace')
                    lines = re.split(r'\r\n|\n|\r', content)
            except OSError:
                lines = []

            kind = _id_to_kind(id)
            language = _id_to_language(id)

            if _is_encoded(kind):
                should_swap_multiples = _should_swap_multiples(kind)
                lines = [self._decode_line(line, should_swap_multiples) for line in lines]

            return EDF(id, kind, language, lines)

    class Writer:
        _data_directory: os.PathLike

        def __init__(self, data_directory: Union[str, os.PathLike]):
            if isinstance(data_directory, str):
                data_directory = Path(data_directory)
            self._data_directory = data_directory

        def _encode_line(self, line: str, should_swap_multiples: bool) -> str:
            data = bytearray(line.encode('cp1252', 'replace'))
            if should_swap_multiples:
                swap_multiples(data, 7)
            interleave(data)
            return data.decode('cp1252')

        def write(self, edf: 'EDF') -> Path:
            lines = edf.lines

            if _is_encoded(edf.kind):
                should_swap_multiples = _should_swap_multiples(edf.kind)
                lines = [self._encode_line(line, should_swap_multiples) for line in lines]

            content = '\r\n'.join(lines)
            path = Path(self._data_directory, f'dat{edf.id:03}.edf')

            with open(path, 'wb') as file:
                file.write(content.encode('cp1252', 'replace'))

            return path


def _is_encoded(kind: EDF.Kind) -> bool:
    return kind not in [EDF.Kind.CHECKSUM, EDF.Kind.CREDITS]


def _should_swap_multiples(kind: EDF.Kind) -> bool:
    return kind != EDF.Kind.CURSE_FILTER


def _id_to_kind(id: int) -> EDF.Kind:
    match id:
        case 1:
            return EDF.Kind.CREDITS
        case 2:
            return EDF.Kind.CHECKSUM
        case 3:
            return EDF.Kind.CURSE_FILTER
        case 4:
            return EDF.Kind.JUKEBOX
        case 5 | 7 | 9 | 11:
            return EDF.Kind.GAME_1
        case 6 | 8 | 10 | 12:
            return EDF.Kind.GAME_2
        case _:
            raise ValueError(f'Unhandled data file ID: {id}')


def _id_to_language(id: int) -> EDF.Language:
    match id:
        case 1 | 2 | 3 | 4 | 5 | 6:
            return EDF.Language.ENGLISH
        case 7 | 8:
            return EDF.Language.DUTCH
        case 9 | 10:
            return EDF.Language.SWEDISH
        case 11 | 12:
            return EDF.Language.PORTUGESE
        case _:
            raise ValueError(f'Unhandled data file ID: {id}')
