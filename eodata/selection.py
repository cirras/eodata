from dataclasses import dataclass
from typing import List

from PySide6.QtCore import QItemSelection


@dataclass
class SelectionRange:
    top: int
    left: int
    bottom: int
    right: int

    @staticmethod
    def from_item_selection(item_selection: QItemSelection) -> List['SelectionRange']:
        return list(
            map(
                lambda qt_range: SelectionRange(
                    qt_range.top(), qt_range.left(), qt_range.bottom(), qt_range.right()
                ),
                item_selection.toList(),
            )
        )


@dataclass
class ModelIndex:
    column: int
    row: int
