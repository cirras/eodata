from dataclasses import dataclass
from types import FunctionType
from eodata.__about__ import __version__
from pathlib import Path

from copy import deepcopy
from typing import Any, Callable, Final, List, Sequence, cast

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QTabBar,
    QVBoxLayout,
    QMenuBar,
    QMenu,
    QMessageBox,
    QFileDialog,
    QAbstractItemDelegate,
    QLineEdit,
)
from PySide6.QtCore import Qt, QSettings, QItemSelection, QItemSelectionModel, QPoint
from PySide6.QtGui import QIcon, QKeySequence, QAction, QKeyEvent, QCloseEvent

from eodata.edf import EDF
from eodata.selection import ModelIndex, SelectionRange
from eodata.table import EDFTableModel, EDFTableView
from eodata.icon import application_icon


@dataclass
class SelectionMemento:
    tab_index: int
    selection_ranges: List[SelectionRange]
    current_index: ModelIndex


@dataclass
class Memento:
    edfs: List[EDF]
    undo_selection: SelectionMemento
    redo_selection: SelectionMemento


class MainWindow(QMainWindow):
    MAX_RECENT: Final[int] = 10

    _app_icon: QIcon

    _tab_bar: QTabBar
    _table: EDFTableView
    _table_model: EDFTableModel

    _open_recent_menu: QMenu
    _edit_menu: QMenu

    _save_action: QAction
    _save_as_action: QAction
    _close_folder_action: QAction
    _cut_action: QAction
    _copy_action: QAction
    _paste_action: QAction
    _insert_rows_action: QAction
    _remove_rows_action: QAction
    _undo_action: QAction
    _redo_action: QAction
    _open_recent_actions: List[QAction]

    _data_folder: Path | None
    _edfs: List[EDF]

    _mementos: List[Memento]
    _memento_position: int
    _memento_last_saved: Memento | None

    def __init__(self):
        super().__init__()

        self._app_icon = application_icon()

        self.setWindowIcon(self._app_icon)
        self.resize(1067, 750)

        self._tab_bar = QTabBar()
        self._tab_bar.addTab("Credits")
        self._tab_bar.addTab("Curse Filter")
        self._tab_bar.addTab("Jukebox")
        self._tab_bar.addTab("Game 1")
        self._tab_bar.addTab("Game 2")
        self._tab_bar.currentChanged.connect(self._tab_changed)

        self._table = EDFTableView()
        self._table.verticalHeader().setFixedWidth(30)
        self._table.horizontalHeader().setDefaultSectionSize(250)
        self._table.itemDelegate().closeEditor.connect(self._editor_closed)

        self._data_folder = None

        layout = QVBoxLayout()
        layout.addWidget(self._tab_bar)
        layout.addWidget(self._table)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        menu_bar = self._create_menu_bar()
        self.setMenuBar(menu_bar)

        self._install_context_menus()
        self._reset_mementos()
        self._update_open_recent_actions()
        self._close_data_folder()

    def _create_menu_bar(self) -> QMenuBar:
        menu_bar = QMenuBar()

        open_action = self._make_action(
            "&Open Folder...",
            shortcut=QKeySequence.StandardKey.Open,
            status_tip="Open data folder",
            triggered=self._open_data_folder,
        )

        self._open_recent_menu = QMenu("Open &Recent", self)
        self._open_recent_actions = []

        for _ in range(MainWindow.MAX_RECENT):
            action = self._make_action(visible=False, triggered=self._open_recent)
            self._open_recent_actions.append(action)

        clear_recent_action = self._make_action(
            "&Clear Recently Opened...",
            status_tip="Clear recently opened folders",
            triggered=self._clear_recent,
        )

        self._open_recent_menu.addActions(self._open_recent_actions)
        self._open_recent_menu.addSeparator()
        self._open_recent_menu.addAction(clear_recent_action)

        self._save_action = self._make_action(
            "&Save",
            shortcut=QKeySequence.StandardKey.Save,
            status_tip="Save data files",
            triggered=self._save,
        )

        self._save_as_action = self._make_action(
            "Save &As",
            shortcut=QKeySequence.StandardKey.SaveAs,
            status_tip="Save data files under a new folder",
            triggered=self._save_as,
        )

        self._close_folder_action = self._make_action(
            "&Close Folder",
            shortcut=QKeySequence.StandardKey.Close,
            status_tip="Close data folder",
            triggered=self._close_data_folder,
        )

        exit_action = self._make_action(
            "E&xit",
            shortcut=QKeySequence.StandardKey.Quit,
            status_tip="Exit the application",
            triggered=QApplication.closeAllWindows,
        )

        self._cut_action = self._make_action(
            "Cu&t",
            shortcut=QKeySequence.StandardKey.Cut,
            status_tip="Cut selected cells to the clipboard",
            triggered=self._cut,
        )

        self._copy_action = self._make_action(
            "&Copy",
            shortcut=QKeySequence.StandardKey.Copy,
            status_tip="Copy selected cells to the clipboard",
            triggered=self._copy,
        )

        self._paste_action = self._make_action(
            "&Paste",
            shortcut=QKeySequence.StandardKey.Paste,
            status_tip="Paste data from the clipboard",
            triggered=self._paste,
        )

        self._clear_action = self._make_action(
            "C&lear",
            shortcut=QKeySequence.StandardKey.Delete,
            status_tip="Clear selected cells",
            triggered=self._clear,
        )

        self._insert_rows_action = self._make_action(
            "&Insert 1 row",
            shortcuts=[QKeySequence('Ctrl+Shift++'), QKeySequence('Ctrl++')],
            status_tip="Insert rows",
            triggered=self._insert_rows,
        )

        self._remove_rows_action = self._make_action(
            "&Delete 0 rows",
            shortcut=QKeySequence('Ctrl+-'),
            status_tip="Delete rows",
            triggered=self._remove_rows,
            enabled=False,
        )

        self._undo_action = self._make_action(
            "&Undo",
            shortcut=QKeySequence.StandardKey.Undo,
            status_tip="Undo the last action",
            triggered=self._undo,
        )

        self._redo_action = self._make_action(
            "&Redo",
            shortcut=QKeySequence.StandardKey.Redo,
            status_tip="Redo the last action",
            triggered=self._redo,
        )

        about_action = self._make_action(
            "&About",
            status_tip="Show information about the application",
            triggered=self._about,
        )

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(open_action)
        file_menu.addMenu(self._open_recent_menu)
        file_menu.addSeparator()
        file_menu.addAction(self._save_action)
        file_menu.addAction(self._save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self._close_folder_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self._undo_action)
        edit_menu.addAction(self._redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self._cut_action)
        edit_menu.addAction(self._copy_action)
        edit_menu.addAction(self._paste_action)
        edit_menu.addAction(self._clear_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self._insert_rows_action)
        edit_menu.addAction(self._remove_rows_action)
        self._edit_menu = edit_menu

        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(about_action)

        return menu_bar

    def _make_action(
        self,
        text: str = '',
        *,
        status_tip: str | None = None,
        triggered: Callable[[], Any] | None = None,
        shortcut: QKeySequence | QKeySequence.StandardKey | None = None,
        shortcuts: Sequence[QKeySequence] | QKeySequence.StandardKey | None = None,
        visible: bool = True,
        enabled: bool = True,
    ) -> QAction:
        action = QAction(  # type: ignore[call-overload]
            text,
            self,
            triggered=triggered,
            visible=visible,
            enabled=enabled,
        )
        if status_tip is not None:
            action.setStatusTip(status_tip)
        if shortcut is not None:
            action.setShortcut(shortcut)
        if shortcuts is not None:
            action.setShortcuts(shortcuts)
        return action

    def _install_context_menus(self) -> None:
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._table_context_menu_requested)

        self._table.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.horizontalHeader().customContextMenuRequested.connect(
            self._table_horizontal_header_context_menu_requested
        )

        self._table.verticalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.verticalHeader().customContextMenuRequested.connect(
            self._table_vertical_header_context_menu_requested
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)
        if self._tab_bar.isEnabled():
            if event.matches(QKeySequence.StandardKey.NextChild):
                next_index = self._tab_bar.currentIndex() + 1
                if next_index >= self._tab_bar.count():
                    next_index = 0
                self._tab_bar.setCurrentIndex(next_index)
            elif event.matches(QKeySequence.StandardKey.PreviousChild):
                previous_index = self._tab_bar.currentIndex() - 1
                if previous_index < 0:
                    previous_index = self._tab_bar.count() - 1
                self._tab_bar.setCurrentIndex(previous_index)

    def _open_data_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select data directory")
        if folder and self._save_changes_prompt():
            self._load_data_folder(Path(folder))

    def _open_recent(self) -> None:
        action = self.sender()
        if action and self._save_changes_prompt():
            self._load_data_folder(Path(cast(QAction, action).data()))

    def _clear_recent(self) -> None:
        self._set_recent_list([])

    def _load_data_folder(self, path: Path) -> None:
        recent_list = self._get_recent_list()

        try:
            recent_list.remove(str(path))
            self._set_recent_list(recent_list)
        except ValueError:
            pass

        if not path.exists():
            QMessageBox.warning(
                self,
                'Endless Data Studio',
                f"{path} was not found.",
                QMessageBox.StandardButton.Ok,
            )
            return

        self._data_folder = path

        if self._update_data_folder(path):
            recent_list.insert(0, str(path))
            del recent_list[MainWindow.MAX_RECENT :]

        self._set_recent_list(recent_list)

    def _save(self) -> None:
        if self._data_folder is not None:
            self._do_save(self._data_folder)

    def _save_as(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select destination data directory")
        if folder:
            self._do_save(Path(folder))

    def _do_save(self, path: Path) -> None:
        writer = EDF.Writer(path)

        path.mkdir(parents=True, exist_ok=True)

        for i in range(12):
            edf_path = writer.write(self._edfs[i])
            if i == 0:
                # we just wrote the dat001 credits file, so now we can update the dat002 checksum
                self._update_checksum(edf_path)

        self._memento_last_saved = self._get_current_memento()
        self._update_window_modified()

    def _close_data_folder(self) -> None:
        if self._save_changes_prompt():
            self._data_folder = None
            self._update_data_folder(None)

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

    def _cut(self) -> None:
        self._record_memento(lambda: self._table.cut())

    def _copy(self) -> None:
        self._record_memento(lambda: self._table.copy())

    def _paste(self) -> None:
        self._record_memento(lambda: self._table.paste())

    def _clear(self) -> None:
        self._record_memento(lambda: self._table.clear())

    def _insert_rows(self) -> None:
        self._record_memento(lambda: self._table.insert_rows())

    def _remove_rows(self) -> None:
        self._record_memento(lambda: self._table.remove_rows())

    def _undo(self) -> None:
        if self._has_undo():
            previous_memento = self._mementos[self._memento_position]

            self._memento_position -= 1

            memento = self._mementos[self._memento_position]
            self._restore_edf_memento(memento.edfs)
            self._restore_selection_memento(previous_memento.undo_selection)

            self._update_window_modified()
            self._update_actions_enabled()

    def _redo(self) -> None:
        if self._has_redo():
            self._memento_position += 1

            memento = self._mementos[self._memento_position]
            self._restore_edf_memento(memento.edfs)
            self._restore_selection_memento(memento.redo_selection)

            self._update_window_modified()
            self._update_actions_enabled()

    def _has_undo(self) -> bool:
        return self._memento_position > 0

    def _has_redo(self) -> bool:
        return self._memento_position < len(self._mementos) - 1

    def _about(self) -> None:
        QMessageBox.about(
            self,
            "About",
            "<h3>Endless Data Studio</h3>\n"
            + f"<p style=\"text-align:center\">version {__version__}</p>",
        )

    def _update_data_folder(self, path: Path | None) -> bool:
        model: EDFTableModel | None

        try:
            self._reset_mementos()

            if path is None:
                self._edfs = []
                model = None
            else:
                reader = EDF.Reader(path)
                self._edfs = [reader.read(id) for id in range(1, 13)]
                model = EDFTableModel(self._edfs)
                self._record_memento(None)
                self._memento_last_saved = self._mementos[0]

            self._table.setModel(model)
            self._table.resizeRowsToContents()
            self._tab_bar.setCurrentIndex(0)
            self._tab_bar.setEnabled(path is not None)
            self._data_folder = path

            selection_model = self._table.selectionModel()
            if selection_model:
                selection_model.selectionChanged.connect(self._selection_changed)
        except OSError as e:
            QMessageBox.information(
                self,
                'Could not open data folder',
                f'The specified data folder could not be opened.\n{e.strerror}',
                QMessageBox.StandardButton.Ok,
            )
            return False

        self._update_window_title()
        self._update_window_modified()
        self._update_actions_enabled()
        self._update_insert_remove_actions()

        return True

    def _update_window_title(self):
        title = "Endless Data Studio"
        if self._data_folder is not None:
            display_path = str(self._data_folder.stem)
            title = f'{display_path} - {title}'
        self.setWindowTitle(f'[*]{title}')

    def _update_window_modified(self):
        self.setWindowModified(self._is_dirty())

    def _is_dirty(self) -> bool:
        return self._get_current_memento() != self._memento_last_saved

    def _update_actions_enabled(self):
        folder_open = self._data_folder is not None

        self._save_action.setEnabled(folder_open)
        self._save_as_action.setEnabled(folder_open)
        self._close_folder_action.setEnabled(folder_open)
        self._undo_action.setEnabled(self._has_undo())
        self._redo_action.setEnabled(self._has_redo())
        self._cut_action.setEnabled(folder_open)
        self._copy_action.setEnabled(folder_open)
        self._paste_action.setEnabled(folder_open)
        self._clear_action.setEnabled(folder_open)

    def _update_open_recent_actions(self):
        files = self._get_recent_list()
        recent_len = min(len(files), MainWindow.MAX_RECENT)

        for i in range(recent_len):
            self._open_recent_actions[i].setText(cast(str, files[i]).replace('&', '&&'))
            self._open_recent_actions[i].setData(files[i])
            self._open_recent_actions[i].setVisible(True)

        for i in range(recent_len, MainWindow.MAX_RECENT):
            self._open_recent_actions[i].setVisible(False)

        self._open_recent_menu.setEnabled(recent_len > 0)

    def _update_insert_remove_actions(self) -> None:
        selected_rows = self._table.selected_rows()

        if selected_rows:
            consecutive = selected_rows == list(range(min(selected_rows), max(selected_rows) + 1))
            insert_row_count = len(selected_rows) if consecutive else 0
            remove_row_count = len(selected_rows)
        else:
            insert_row_count = 1 if self._data_folder is not None else 0
            remove_row_count = 0

        self._insert_rows_action.setText(
            f"&Insert {insert_row_count} row{'' if insert_row_count == 1 else 's'}"
        )
        self._remove_rows_action.setText(
            f"&Delete {remove_row_count} row{'' if remove_row_count == 1 else 's'}"
        )
        self._insert_rows_action.setEnabled(insert_row_count != 0)
        self._remove_rows_action.setEnabled(remove_row_count != 0)

    def _tab_changed(self) -> None:
        if self._table.model():
            self._table.model().beginResetModel()
            cast(EDFTableModel, self._table.model()).kind = self._edf_kind_from_tab_index()
            self._table.model().endResetModel()
            self._table.resizeRowsToContents()
        self._update_insert_remove_actions()

    def _editor_closed(
        self,
        editor: QWidget,
        end_edit_hint: QAbstractItemDelegate.EndEditHint = QAbstractItemDelegate.EndEditHint.NoHint,
    ) -> None:
        if cast(QLineEdit, editor).isModified():
            self._record_memento(None)

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._save_changes_prompt():
            event.ignore()

    def _save_changes_prompt(self) -> bool:
        if self._is_dirty():
            button = QMessageBox.warning(
                self,
                'Endless Data Studio',
                f"Do you want to save changes to {self._data_folder}?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )

            match button:
                case QMessageBox.StandardButton.Save:
                    self._save()
                case QMessageBox.StandardButton.Discard:
                    # do nothing
                    pass
                case _:
                    return False
        return True

    def _get_current_memento(self) -> Memento | None:
        if self._memento_position == -1:
            return None
        return self._mementos[self._memento_position]

    def _reset_mementos(self) -> None:
        self._mementos = []
        self._memento_position = -1
        self._memento_last_saved = None

        self._update_actions_enabled()
        self._update_window_modified()

    def _record_memento(self, action: Callable[[], Any] | None) -> None:
        undo_selection: SelectionMemento = self._make_selection_memento()
        if action is not None:
            action()
        redo_selection: SelectionMemento = self._make_selection_memento()

        memento = Memento(deepcopy(self._edfs), undo_selection, redo_selection)

        while self._memento_position + 1 != len(self._mementos):
            self._mementos.pop()

        self._mementos.append(memento)
        self._memento_position += 1

        self._update_actions_enabled()
        self._update_window_modified()

    def _make_selection_memento(self) -> SelectionMemento:
        selection_model = self._table.selectionModel()
        q_current_index = selection_model.currentIndex()
        selection_ranges = SelectionRange.from_item_selection(selection_model.selection())
        current_index = ModelIndex(q_current_index.column(), q_current_index.row())
        return SelectionMemento(self._tab_bar.currentIndex(), selection_ranges, current_index)

    def _restore_edf_memento(self, edfs: List[EDF]) -> None:
        self._table.model().beginResetModel()
        self._edfs.clear()
        for edf in edfs:
            self._edfs.append(deepcopy(edf))
        self._table.model().endResetModel()

    def _restore_selection_memento(self, memento: SelectionMemento) -> None:
        self._tab_bar.setCurrentIndex(memento.tab_index)

        selection_model = self._table.selectionModel()
        current_index = self._table.model().index(
            memento.current_index.row, memento.current_index.column
        )

        item_selection = QItemSelection()
        for selection_range in memento.selection_ranges:
            item_selection.select(
                self._table.model().index(selection_range.top, selection_range.left),
                self._table.model().index(selection_range.bottom, selection_range.right),
            )

        selection_model.clearSelection()
        selection_model.select(item_selection, QItemSelectionModel.SelectionFlag.Select)
        selection_model.setCurrentIndex(current_index, QItemSelectionModel.SelectionFlag.Select)

    def _selection_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        self._update_insert_remove_actions()

    def _table_context_menu_requested(self, point: QPoint) -> None:
        self._edit_menu.popup(self._table.viewport().mapToGlobal(point))

    def _table_horizontal_header_context_menu_requested(self, point: QPoint) -> None:
        column: int = self._table.horizontalHeader().logicalIndexAt(point)
        selection_model = self._table.selectionModel()
        if not selection_model.isColumnSelected(column):
            self._table.selectColumn(column)
        self._edit_menu.popup(self._table.viewport().mapToGlobal(point))

    def _table_vertical_header_context_menu_requested(self, point: QPoint) -> None:
        row: int = self._table.verticalHeader().logicalIndexAt(point)
        selection_model = self._table.selectionModel()
        if not selection_model.isRowSelected(row):
            self._table.selectRow(row)
        self._edit_menu.popup(self._table.viewport().mapToGlobal(point))

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

    def _get_recent_list(self) -> List[str]:
        settings = self._get_settings()
        result = settings.value('recentList')
        return result if isinstance(result, List) else []

    def _set_recent_list(self, recent_list: List[str]) -> None:
        settings = self._get_settings()
        settings.setValue('recentList', recent_list)
        self._update_open_recent_actions()

    def _get_settings(self) -> QSettings:
        return QSettings('cirras', 'Endless Data Studio')
