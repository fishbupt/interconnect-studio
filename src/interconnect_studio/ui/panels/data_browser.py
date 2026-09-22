"""Data browser panel: Group -> Measurement -> DataFile."""

from PyQt6.QtCore import QItemSelection, pyqtSignal
from PyQt6.QtWidgets import QTreeView, QVBoxLayout, QWidget

from interconnect_studio.core import DataFile, Group
from interconnect_studio.ui.models import DataBrowserModel


class DataBrowserPanel(QWidget):
    """Navigates the fixed three-level data hierarchy.

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

    @property
    def groups(self) -> tuple[Group, ...]:
        """Hierarchy currently shown."""

        return self.model.groups

    def set_groups(self, groups: tuple[Group, ...]) -> None:
        """Replace the hierarchy and expand it."""

        self.model.set_groups(groups)
        self.tree.expandAll()

    def current_file(self) -> DataFile | None:
        """Data file currently selected, if any."""

        return self.model.data_file_at(self.tree.currentIndex())

    def select_data_file(self, file_id: str) -> None:
        """Select a data file by id."""

        index = self.model.index_of_data_file(file_id)
        if index.isValid():
            self.tree.setCurrentIndex(index)

    def _on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        self.current_file_changed.emit(self.current_file())


DEFAULT_GROUP = "Group 1"
DEFAULT_MEASUREMENT = "Measurement 1"
