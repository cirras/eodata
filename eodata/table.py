import csv
import io
import re

from dataclasses import dataclass
from typing import Any, List

from PySide6.QtCore import (
    Qt,
    QEvent,
    QModelIndex,
    QAbstractTableModel,
    QItemSelectionModel,
    QItemSelection,
    QItemSelectionRange,
)
from PySide6.QtGui import QBrush, QKeySequence, QKeyEvent
from PySide6.QtWidgets import QApplication, QTableView

from eodata.edf import EDF


class EDFTableModel(QAbstractTableModel):
    _all_edfs: List[EDF]
    _kind: EDF.Kind

    def __init__(self, edfs: List[EDF]):
        super(EDFTableModel, self).__init__()
        self._all_edfs = edfs
        self._kind = EDF.Kind.CREDITS

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Vertical:
            return section

        if section < len(EDF.Language):
            return list(EDF.Language.__members__.keys())[section].lower().capitalize()

    def data(self, index: QModelIndex, role):
        edfs = self._edfs()

        if index.column() >= len(edfs):
            if role == Qt.ItemDataRole.BackgroundRole:
                return QBrush(Qt.GlobalColor.lightGray)
            return None

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return edfs[index.column()].lines[index.row()]

    def setData(
        self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole
    ):
        if isinstance(value, str) and role == Qt.ItemDataRole.EditRole:
            self._edfs()[index.column()].lines[index.row()] = sanitize_string(value)
            return True
        return False

    def insertRows(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:
        self.beginInsertRows(parent, row, row + count - 1)
        for edf in self._edfs():
            while len(edf.lines) < row:
                edf.lines.append('')
            for _ in range(count):
                edf.lines.insert(row, '')
        self.endInsertRows()

    def removeRows(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:
        self.beginRemoveRows(parent, row, row + count - 1)
        for edf in self._edfs():
            for _ in range(count):
                if len(edf.lines) < row:
                    break
                del edf.lines[row]
        self.endRemoveRows()

    def rowCount(self, parent: QModelIndex = QModelIndex()):
        if parent.isValid():
            return 0
        return max(map(lambda edf: len(edf.lines), self._edfs()))

    def columnCount(self, parent: QModelIndex = QModelIndex()):
        if parent.isValid():
            return 0
        return len(EDF.Language)

    def flags(self, index: QModelIndex):
        if index.column() >= len(self._edfs()):
            return Qt.ItemFlag.NoItemFlags

        return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

    def _edfs(self) -> List[EDF]:
        return [edf for edf in self._all_edfs if edf.kind == self._kind]

    @property
    def kind(self) -> EDF.Kind:
        return self._kind

    @kind.setter
    def kind(self, kind) -> None:
        self._kind = kind


class EDFTableView(QTableView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def event(self, event: QEvent) -> bool:
        if isinstance(event, QKeyEvent) and (
            event.matches(QKeySequence.StandardKey.NextChild)
            or event.matches(QKeySequence.StandardKey.PreviousChild)
        ):
            return False
        return super().event(event)

    def copy(self) -> None:
        if not self.selectedIndexes():
            return

        selection_model: QItemSelectionModel = self.selectionModel()
        item_selection: QItemSelection = selection_model.selection()
        selection_range: QItemSelectionRange = item_selection.first()

        csvfile = io.StringIO()
        csv_writer = csv.writer(csvfile, delimiter='\t')

        for i in range(selection_range.top(), selection_range.bottom() + 1):
            row = []

            for j in range(selection_range.left(), selection_range.right() + 1):
                cell_index: QModelIndex = self.model().index(i, j)
                if cell_index.data() is not None:
                    row.append(cell_index.data())

            csv_writer.writerow(row)

        QApplication.clipboard().setText(csvfile.getvalue())

    def cut(self) -> None:
        self.copy()
        self.clear()

    def paste(self) -> None:
        if not self.selectedIndexes():
            return

        text = QApplication.clipboard().text()
        csv_reader = csv.reader(io.StringIO(text), delimiter='\t')
        rows = list(csv_reader)

        origin_index: QModelIndex = self.selectedIndexes()[0]
        origin_row = origin_index.row()
        origin_column = origin_index.column()

        row_count = self.model().rowCount()
        end_row = origin_row + len(rows)

        if row_count < end_row:
            self.model().insertRows(row_count, end_row - row_count)

        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                cell_index: QModelIndex = self.model().index(origin_row + i, origin_column + j)
                if cell_index.isValid():
                    self.model().setData(cell_index, cell)
                    self.update(cell_index)

    def clear(self) -> None:
        if not self.selectedIndexes():
            return

        selection_model: QItemSelectionModel = self.selectionModel()
        item_selection: QItemSelection = selection_model.selection()
        selection_range: QItemSelectionRange = item_selection.first()

        for i in range(selection_range.top(), selection_range.bottom() + 1):
            for j in range(selection_range.left(), selection_range.right() + 1):
                cell_index: QModelIndex = self.model().index(i, j)
                if cell_index.data() is not None:
                    self.model().setData(cell_index, '')
                    self.update(cell_index)

    def insert_rows(self) -> None:
        selected_rows = self.selected_rows()

        if selected_rows:
            consecutive = selected_rows == list(range(min(selected_rows), max(selected_rows) + 1))
            if not consecutive:
                return
            row = selected_rows[-1] + 1
            count = len(selected_rows)
        else:
            row = 0
            count = 1

        selection_model: QItemSelectionModel = self.selectionModel()
        item_selection: QItemSelection = selection_model.selection()
        current_index = selection_model.currentIndex()

        ranges: List[SelectionRange] = item_selection_to_selection_ranges(item_selection)
        current_index = self.model().index(current_index.row() + count, current_index.column())

        self.model().insertRows(row, count)

        item_selection = QItemSelection()
        for selection_range in ranges:
            item_selection.select(
                self.model().index(selection_range.top + count, selection_range.left),
                self.model().index(selection_range.bottom + count, selection_range.right),
            )

        selection_model.clearSelection()
        selection_model.select(item_selection, QItemSelectionModel.SelectionFlag.Select)
        selection_model.setCurrentIndex(current_index, QItemSelectionModel.SelectionFlag.Select)

    def remove_rows(self) -> None:
        selected_rows = self.selected_rows()

        if not selected_rows:
            return

        selection_model: QItemSelectionModel = self.selectionModel()
        item_selection: QItemSelection = selection_model.selection()

        ranges: List[SelectionRange] = item_selection_to_selection_ranges(item_selection)
        current_index_row = selection_model.currentIndex().row()
        current_index_column = selection_model.currentIndex().column()

        consecutive = selected_rows == list(range(min(selected_rows), max(selected_rows) + 1))

        if consecutive:
            row = selected_rows[0]
            count = len(selected_rows)
            self.model().removeRows(row, count)
        else:
            for row in selected_rows:
                self.model().removeRow(row)

        selection_model.clearSelection()

        max_row = self.model().rowCount() - 1
        if max_row == -1:
            return

        item_selection = QItemSelection()
        for selection_range in ranges:
            item_selection.select(
                self.model().index(min(selection_range.top, max_row), selection_range.left),
                self.model().index(min(selection_range.bottom, max_row), selection_range.right),
            )

        selection_model.select(item_selection, QItemSelectionModel.SelectionFlag.Select)

        current_index = self.model().index(min(current_index_row, max_row), current_index_column)
        selection_model.setCurrentIndex(current_index, QItemSelectionModel.SelectionFlag.Select)

    def selected_rows(self) -> List[int]:
        result = []

        selection_model: QItemSelectionModel = self.selectionModel()
        item_selection: QItemSelection = selection_model.selection()

        for index in item_selection.indexes():
            if index.flags() & Qt.ItemFlag.ItemIsSelectable:
                result.append(index.row())

        return sorted(set(result))


def sanitize_string(value: str) -> str:
    value = lossy_convert_to_cp1252(value)
    value = collapse_newlines(value)
    return value


def lossy_convert_to_cp1252(value: str) -> str:
    return value.encode("cp1252", "replace").decode("cp1252")


def collapse_newlines(value: str) -> str:
    return re.sub(r'\r\n|\n|\r', ' ', value)


@dataclass
class SelectionRange:
    top: int
    left: int
    bottom: int
    right: int


def item_selection_to_selection_ranges(item_selection: QItemSelection) -> List[SelectionRange]:
    return list(
        map(
            lambda qt_range: SelectionRange(
                qt_range.top(), qt_range.left(), qt_range.bottom(), qt_range.right()
            ),
            item_selection.toList(),
        )
    )
