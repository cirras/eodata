from eodata.__about__ import __version__
from pathlib import Path
from typing import Any, Final, List, cast

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QTabBar,
    QTableView,
    QVBoxLayout,
    QMenuBar,
    QMessageBox,
    QFileDialog,
)
from PySide6.QtCore import Qt, QModelIndex, QAbstractTableModel
from PySide6.QtGui import QBrush, QKeySequence, QAction

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

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole):
        if value is not None and role == Qt.ItemDataRole.EditRole:
            self._edfs()[index.column()].lines[index.row()] = value
            return True
        return False

    def rowCount(self, index: QModelIndex):
        return max(map(lambda edf: len(edf.lines), self._edfs()))

    def columnCount(self, index: QModelIndex):
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


class MainWindow(QMainWindow):
    _tab_bar: QTabBar
    _table: QTableView
    _table_model: EDFTableModel
    _data_folder: Path | None
    _edfs: List[EDF]

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Endless Data Studio")
        self.resize(1067, 750)

        self._tab_bar = QTabBar()
        self._tab_bar.addTab("Credits")
        self._tab_bar.addTab("Curse Filter")
        self._tab_bar.addTab("Jukebox")
        self._tab_bar.addTab("Game 1")
        self._tab_bar.addTab("Game 2")
        self._tab_bar.currentChanged.connect(self._tab_changed)

        self._table = QTableView()
        self._table.verticalHeader().setFixedWidth(30)
        self._table.horizontalHeader().setDefaultSectionSize(250)

        layout = QVBoxLayout()
        layout.addWidget(self._tab_bar)
        layout.addWidget(self._table)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        menu_bar = self._create_menu_bar()

        self.setMenuBar(menu_bar)

    def _create_menu_bar(self) -> QMenuBar:
        menu_bar = QMenuBar()

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(
            QAction(
                "&Open Folder...",
                self,
                shortcut=QKeySequence.StandardKey.Open,
                statusTip="Open data folder",
                triggered=self._open_folder,
            )
        )
        file_menu.addSeparator()
        file_menu.addAction(
            QAction(
                "&Save",
                self,
                shortcut=QKeySequence.StandardKey.Save,
                statusTip="Save data files",
                triggered=self._save,
            )
        )
        file_menu.addAction(
            QAction(
                "Save &As",
                self,
                shortcut=QKeySequence.StandardKey.SaveAs,
                statusTip="Save data files under a new folder",
                triggered=self._save_as,
            )
        )
        file_menu.addSeparator()
        file_menu.addAction(
            QAction(
                "E&xit",
                self,
                shortcut=QKeySequence.StandardKey.Quit,
                statusTip="Exit the application",
                triggered=QApplication.closeAllWindows,
            )
        )

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(
            QAction(
                "&Undo",
                self,
                shortcut=QKeySequence.StandardKey.Undo,
                statusTip="Undo the last action",
                triggered=self._undo,
            )
        )
        edit_menu.addAction(
            QAction(
                "&Redo",
                self,
                shortcut=QKeySequence.StandardKey.Redo,
                statusTip="Redo the last action",
                triggered=self._redo,
            )
        )

        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(
            QAction(
                "&About",
                self,
                statusTip="Show information about the application",
                triggered=self._about,
            )
        )

        return menu_bar

    def _open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select data directory")
        if folder:
            self._data_folder = Path(folder)
            self._read_edfs(self._data_folder)

    def _save(self) -> None:
        if self._data_folder is not None:
            self._do_save(self._data_folder)

    def _save_as(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select destination data directory")
        if folder:
            self._do_save(Path(folder))

    def _do_save(self, path: Path) -> None:
        writer = EDF.Writer(path)

        for i in range(12):
            edf_path = writer.write(self._edfs[i])
            if i == 0:
                # we just wrote the dat001 credits file, so now we can update the dat002 checksum
                self._update_checksum(edf_path)

    def _update_checksum(self, dat001) -> None:
        file_size = dat001.stat().st_size

        aeo_count = 0
        with open(dat001, 'r') as file:
            for character in file.read():
                if character in ['a', 'A', 'e', 'E', 'o', 'O']:
                    aeo_count = aeo_count + 1

        checksum = f"DAT001.ID{{{file_size * 3013 - 11}:145:{aeo_count}:{file_size * 21}}}"

        dat002 = self._edfs[1]
        dat002.lines.clear()
        dat002.lines.append(checksum)

    def _undo(self) -> None:
        # TODO: undo/redo
        pass

    def _redo(self) -> None:
        # TODO: undo/redo
        pass

    def _about(self) -> None:
        QMessageBox.about(
            self,
            "About",
            "<h3>Endless Data Studio</h3>\n"
            + f"<p style=\"text-align:center\">version {__version__}</p>",
        )

    def _read_edfs(self, path: Path) -> EDFTableModel:
        reader = EDF.Reader(path)
        self._edfs = [reader.read(id) for id in range(1, 13)]
        self._table.setModel(EDFTableModel(self._edfs))
        self._tab_bar.setCurrentIndex(0)

    def _tab_changed(self) -> None:
        if self._table.model():
            self._table.model().beginResetModel()
            cast(EDFTableModel, self._table.model()).kind = self._edf_kind_from_tab_index()
            self._table.model().endResetModel()

    def _edf_kind_from_tab_index(self) -> EDF.Kind:
        tab_index = self._tab_bar.currentIndex()
        match tab_index:
            case 0:
                return EDF.Kind.CREDITS
            case 1:
                return EDF.Kind.CURSE_FILTER
            case 2:
                return EDF.Kind.JUKEBOX
            case 3:
                return EDF.Kind.GAME_1
            case 4:
                return EDF.Kind.GAME_2
            case _:
                raise ValueError(f'Unhandled tab index: {tab_index}')
