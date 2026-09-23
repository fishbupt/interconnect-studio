"""PLTS "Select Analysis View" dialog, shown after importing a file."""

from collections.abc import Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.core import BrowserCategory, ViewType

# Analysis views PLTS offers for imported measurement data, in its order.
ANALYSIS_VIEW_TYPES: tuple[ViewType, ...] = (
    *BrowserCategory.DATA_ANALYSIS.view_types,
    *BrowserCategory.RLCG.view_types,
)


class SelectAnalysisViewDialog(QDialog):
    """Choose the analysis view an imported file opens in.

    View types the application cannot display yet are listed but disabled.
    """

    def __init__(
        self,
        available: Iterable[ViewType],
        default: ViewType = ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Analysis View")
        enabled = frozenset(available)

        self.view_list = QListWidget(self)
        for view_type in ANALYSIS_VIEW_TYPES:
            item = QListWidgetItem(view_type.label, self.view_list)
            item.setData(Qt.ItemDataRole.UserRole, view_type)
            if view_type not in enabled:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setToolTip("Not available yet")
            if view_type is default:
                self.view_list.setCurrentItem(item)
        self.view_list.itemDoubleClicked.connect(lambda _item: self.accept())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.view_list)
        layout.addWidget(buttons)

    def selected_view_type(self) -> ViewType | None:
        """View type currently selected, if any."""

        item = self.view_list.currentItem()
        if item is None:
            return None
        view_type: ViewType = item.data(Qt.ItemDataRole.UserRole)
        return view_type
