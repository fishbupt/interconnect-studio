"""Data browser panel: Group -> Measurement -> DataFile."""

from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

DEFAULT_GROUP = "Group 1"
DEFAULT_MEASUREMENT = "Measurement 1"


class DataBrowserPanel(QWidget):
    """Navigates the fixed three-level data hierarchy.

    Parameters and display formats are not tree nodes; they belong to the
    parameter/format panel.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)

    def clear(self) -> None:
        """Remove every node."""

        self.tree.clear()

    def show_data_file(
        self,
        file_name: str,
        group: str = DEFAULT_GROUP,
        measurement: str = DEFAULT_MEASUREMENT,
    ) -> None:
        """Show a single data file under the given group and measurement."""

        self.tree.clear()
        group_item = QTreeWidgetItem([group])
        measurement_item = QTreeWidgetItem([measurement])
        measurement_item.addChild(QTreeWidgetItem([file_name]))
        group_item.addChild(measurement_item)
        self.tree.addTopLevelItem(group_item)
        self.tree.expandAll()
