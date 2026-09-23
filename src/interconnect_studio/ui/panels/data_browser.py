"""Data browser panel: category -> view type -> window, as in PLTS."""

from PyQt6.QtCore import QItemSelection, QModelIndex, pyqtSignal
from PyQt6.QtWidgets import QTreeView, QVBoxLayout, QWidget

from interconnect_studio.core import DataBrowserTree, DataFile, ViewWindow
from interconnect_studio.ui.models import DataBrowserModel


class DataBrowserPanel(QWidget):
    """Navigates the PLTS-style data browser.

    Parameters and display formats are not tree nodes; they belong to the
    parameter/format panel.
    """

    current_file_changed = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.model = DataBrowserModel(parent=self)
        self.tree = QTreeView(self)
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(True)
        self.tree.setExpandsOnDoubleClick(False)

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
        self.current_file_changed.emit(self.current_file())
