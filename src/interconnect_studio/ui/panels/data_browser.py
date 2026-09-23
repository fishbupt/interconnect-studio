"""Data browser panel: category -> view type -> window, as in PLTS."""

from collections.abc import Callable

from PyQt6.QtCore import QItemSelection, QModelIndex, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QInputDialog,
    QLineEdit,
    QMenu,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.core import DataBrowserTree, DataFile, ViewTemplate, ViewWindow
from interconnect_studio.ui.models import DataBrowserModel


class DataBrowserPanel(QWidget):
    """Navigates the PLTS-style data browser.

    Parameters and display formats are not tree nodes; they belong to the
    parameter/format panel.

    Right-clicking a window offers the PLTS window menu. The panel only asks
    for the operation; the owner of the open windows carries it out:
    ``close_view_requested(window number)``, ``close_file_requested(file id)``
    and ``rename_file_requested(file id, new name)``. Copy File Name is
    handled here, as it changes nothing.

    Clicking an available view type asks for a new window of that type for
    the active data file: ``open_view_requested(view type)``; clicking a
    saved template asks for the active file laid out with it:
    ``open_template_requested(template)``. The window menu's Save Template
    As asks for ``save_template_requested(window number, template name)``.
    """

    current_file_changed = pyqtSignal(object)
    current_window_changed = pyqtSignal(object)
    close_view_requested = pyqtSignal(int)
    close_file_requested = pyqtSignal(str)
    rename_file_requested = pyqtSignal(str, str)
    open_view_requested = pyqtSignal(object)
    open_template_requested = pyqtSignal(object)
    save_template_requested = pyqtSignal(int, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.model = DataBrowserModel(parent=self)
        self.tree = QTreeView(self)
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(True)
        self.tree.setExpandsOnDoubleClick(False)
        self.tree.expanded.connect(lambda index: self.model.set_expanded(index, True))
        self.tree.collapsed.connect(lambda index: self.model.set_expanded(index, False))
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu_requested)
        self.tree.clicked.connect(self._on_clicked)

        selection = self.tree.selectionModel()
        if selection is not None:
            selection.selectionChanged.connect(self._on_selection_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)
        self._expand_open_windows()

    @property
    def browser_tree(self) -> DataBrowserTree:
        """Hierarchy currently shown."""

        return self.model.tree

    def set_browser_tree(self, tree: DataBrowserTree) -> None:
        """Replace the open windows, keeping every one of them visible."""

        self.model.set_tree(tree)
        self._expand_open_windows()

    def set_templates(self, templates: tuple[ViewTemplate, ...]) -> None:
        """List saved templates under Template View."""

        self.model.set_templates(templates)
        self._expand_open_windows()

    def current_window(self) -> ViewWindow | None:
        """Window currently selected, if any."""

        return self.model.window_at(self.tree.currentIndex())

    def current_file(self) -> DataFile | None:
        """Data file of the window currently selected, if any."""

        return self.model.data_file_at(self.tree.currentIndex())

    def select_window(self, number: int) -> None:
        """Select a window by its number."""

        index = self.model.index_of_window(number)
        if index.isValid():
            self.tree.setCurrentIndex(index)

    def _expand_open_windows(self) -> None:
        """Expand categories, and the view types that hold windows.

        PLTS shows empty view types collapsed and the ones with open windows
        expanded, so the open windows are always visible.
        """

        root = QModelIndex()
        for category_row in range(self.model.rowCount(root)):
            category_index = self.model.index(category_row, 0, root)
            self.tree.expand(category_index)
            for view_row in range(self.model.rowCount(category_index)):
                view_index = self.model.index(view_row, 0, category_index)
                if self.model.rowCount(view_index) > 0:
                    self.tree.expand(view_index)

    def _on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        self.current_window_changed.emit(self.current_window())
        self.current_file_changed.emit(self.current_file())

    def window_menu(self, window: ViewWindow) -> QMenu:
        """Build the right-click menu of one window, as in PLTS."""

        menu = QMenu(self)
        actions: tuple[tuple[str, str, Callable[[], None]], ...] = (
            ("close_view", "Close View", lambda: self.close_view_requested.emit(window.number)),
            (
                "close_file",
                "Close File",
                lambda: self.close_file_requested.emit(window.data_file.id),
            ),
            ("copy_file_name", "Copy File Name", lambda: self.copy_file_name(window)),
            ("rename_file", "Rename File", lambda: self.ask_rename_file(window)),
            ("save_template_as", "Save Template As...", lambda: self.ask_save_template(window)),
        )
        for object_name, text, slot in actions:
            if object_name == "save_template_as":
                menu.addSeparator()
            action = QAction(text, menu)
            action.setObjectName(object_name)
            action.triggered.connect(slot)
            menu.addAction(action)
        return menu

    def copy_file_name(self, window: ViewWindow) -> None:
        """Put the window's data file name on the clipboard."""

        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(window.data_file.name)

    def ask_rename_file(self, window: ViewWindow) -> None:
        """Ask for a new data file name and request the rename."""

        name, accepted = QInputDialog.getText(
            self,
            "Rename File",
            "File name:",
            QLineEdit.EchoMode.Normal,
            window.data_file.name,
        )
        name = name.strip()
        if accepted and name and name != window.data_file.name:
            self.rename_file_requested.emit(window.data_file.id, name)

    def ask_save_template(self, window: ViewWindow) -> None:
        """Ask for a template name and request saving the window as it."""

        name, accepted = QInputDialog.getText(
            self,
            "Save Template As",
            "Template name:",
            QLineEdit.EchoMode.Normal,
            window.template,
        )
        name = name.strip()
        if accepted and name:
            self.save_template_requested.emit(window.number, name)

    def _on_clicked(self, index: QModelIndex) -> None:
        view_type = self.model.view_type_at(index)
        if view_type is not None and self.model.is_available(view_type):
            self.open_view_requested.emit(view_type)
        template = self.model.template_at(index)
        if template is not None and self.model.is_available(template.view_type):
            self.open_template_requested.emit(template)

    def _on_context_menu_requested(self, position: QPoint) -> None:
        window = self.model.window_at(self.tree.indexAt(position))
        if window is None:
            return
        viewport = self.tree.viewport()
        if viewport is None:
            return
        self.window_menu(window).exec(viewport.mapToGlobal(position))
