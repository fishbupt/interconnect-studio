"""Virtual trace table: unequal grids remain separate and unmodified."""

from bisect import bisect_right
from itertools import accumulate
from typing import Any

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.core import PlotModel

_ROOT_INDEX = QModelIndex()


class TraceTableModel(QAbstractTableModel):
    """Long-form read-only table without allocating a flattened copy of the arrays."""

    HEADERS = ("曲线", "来源", "X", "X 单位", "Y", "Y 单位")

    def __init__(
        self, plot: PlotModel, sources: dict[str, str], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.plot = plot
        self.sources = sources
        self._ends = list(accumulate(trace.n_points for trace in plot.traces))

    def rowCount(self, parent: QModelIndex = _ROOT_INDEX) -> int:  # noqa: N802
        return 0 if parent.isValid() else (self._ends[-1] if self._ends else 0)

    def columnCount(self, parent: QModelIndex = _ROOT_INDEX) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        number = bisect_right(self._ends, index.row())
        trace = self.plot.traces[number]
        row = index.row() - (self._ends[number - 1] if number else 0)
        values = (
            trace.name,
            self.sources.get(trace.source_id, trace.source_id),
            f"{float(trace.x[row]):.17g}",
            trace.x_unit,
            f"{float(trace.y[row]):.17g}",
            trace.y_unit,
        )
        return values[index.column()]

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:  # noqa: N802
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        return (
            self.HEADERS[section] if orientation is Qt.Orientation.Horizontal else str(section + 1)
        )


class TraceDataDialog(QDialog):
    """Measured samples of all current curves, with selected cells copied as TSV."""

    def __init__(
        self, plot: PlotModel, sources: dict[str, str], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("曲线数据表（原始频点）")
        self.resize(950, 560)
        self.table = QTableView(self)
        self.model = TraceTableModel(plot, sources, self)
        self.table.setModel(self.model)
        header = self.table.horizontalHeader()
        assert header is not None
        header.setStretchLastSection(True)
        self.table.setColumnWidth(0, 230)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 170)
        copy = QPushButton("复制选中单元格", self)
        copy.clicked.connect(self.copy_selection)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(copy)
        layout.addWidget(buttons)

    def copy_selection(self) -> None:
        """Copy a rectangular selection, preserving empty cells in disjoint selections."""

        indices = self.table.selectedIndexes()
        if not indices:
            return
        selected = {(index.row(), index.column()) for index in indices}
        rows = sorted({index.row() for index in indices})
        columns = range(
            min(index.column() for index in indices), max(index.column() for index in indices) + 1
        )
        text = "\n".join(
            "\t".join(
                str(self.model.data(self.model.index(row, column)))
                if (row, column) in selected
                else ""
                for column in columns
            )
            for row in rows
        )
        clipboard = QApplication.clipboard()
        assert clipboard is not None
        clipboard.setText(text)
