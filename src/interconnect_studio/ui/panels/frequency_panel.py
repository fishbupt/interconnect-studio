"""Trace controls and measured-point marker readouts for the current plot."""

import math

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.core import PlotModel
from interconnect_studio.services.frequency_analysis import marker_reading


def reading_text(value: float | None) -> str:
    """Format a readout without pretending an undefined delta is a number."""

    if value is None or math.isnan(value):
        return "—"
    return f"{value:.10g}"


class FrequencyPanel(QWidget):
    """Persistent controls; each action is handled by the workflow/service layer."""

    requested = pyqtSignal(str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._plot = PlotModel()
        self.trace_combo = QComboBox(self)
        self.rename_edit = QLineEdit(self)
        self.source_label = QLabel(self)
        self.source_label.setWordWrap(True)
        self.marker_combo = QComboBox(self)
        for key, action in (("Left", "previous"), ("Right", "next")):
            shortcut = QShortcut(key, self.marker_combo)
            shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
            shortcut.activated.connect(lambda key=action: self.requested.emit(key, None))
        self.position_edit = QLineEdit(self)
        self.position_edit.setPlaceholderText("频率 / Hz")
        self.reference_combo = QComboBox(self)
        self.target_edit = QLineEdit(self)
        self.target_edit.setPlaceholderText("目标 Y（曲线单位）")
        self.visible_span = QCheckBox("只搜索当前可见频段", self)
        self.readout = QLabel(self)
        self.readout.setWordWrap(True)
        layout = QVBoxLayout(self)
        trace_box = QGroupBox("曲线管理", self)
        form = QFormLayout(trace_box)
        form.addRow("当前曲线", self.trace_combo)
        form.addRow("来源", self.source_label)
        form.addRow("名称", self.rename_edit)
        form.addRow(self._buttons(("重命名", "rename"), ("删除", "delete_trace")))
        form.addRow(self._buttons(("向前", "up"), ("向后", "down")))
        form.addRow(self._buttons(("跨文件对比…", "compare"), ("数据表…", "table")))
        layout.addWidget(trace_box)
        marker_box = QGroupBox("Marker", self)
        form = QFormLayout(marker_box)
        form.addRow(self._buttons(("添加 Marker", "add_marker")))
        form.addRow("当前 Marker", self.marker_combo)
        form.addRow("位置（Hz）", self.position_edit)
        form.addRow(self._buttons(("设置位置", "move"), ("前一点", "previous"), ("后一点", "next")))
        form.addRow("Delta 参考", self.reference_combo)
        form.addRow(self._buttons(("应用参考", "delta"), ("删除 Marker", "delete_marker")))
        form.addRow(self.visible_span)
        form.addRow(self._buttons(("Min", "min"), ("Max", "max")))
        form.addRow("目标 Y", self.target_edit)
        form.addRow(self._buttons(("查找最近目标值", "target")))
        form.addRow(self.readout)
        layout.addWidget(marker_box)
        layout.addStretch()
        self.trace_combo.currentIndexChanged.connect(self._trace_selected)
        self.marker_combo.currentIndexChanged.connect(self._marker_selected)
        self.position_edit.returnPressed.connect(lambda: self.requested.emit("move", None))
        self.rename_edit.returnPressed.connect(lambda: self.requested.emit("rename", None))
        self.sync(PlotModel(), {})

    def _buttons(self, *specs: tuple[str, str]) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        for text, action in specs:
            button = QPushButton(text, row)
            button.clicked.connect(
                lambda _checked=False, key=action: self.requested.emit(key, None)
            )
            layout.addWidget(button)
        return row

    def sync(self, plot: PlotModel, sources: dict[str, str]) -> None:
        """Show a new plot while retaining selection within the same plot when possible."""

        self._plot = plot
        self._sources = sources
        trace_index = max(self.trace_combo.currentIndex(), 0)
        number = self.marker_combo.currentData()
        self.trace_combo.blockSignals(True)
        self.trace_combo.clear()
        self.trace_combo.addItems([trace.name for trace in plot.traces])
        self.trace_combo.setCurrentIndex(min(trace_index, len(plot.traces) - 1))
        self.trace_combo.blockSignals(False)
        self.marker_combo.blockSignals(True)
        self.marker_combo.clear()
        for marker in plot.markers:
            self.marker_combo.addItem(
                f"M{marker.number} · {plot.traces[marker.trace_index].name}", marker.number
            )
        index = self.marker_combo.findData(number)
        self.marker_combo.setCurrentIndex(index if index >= 0 else len(plot.markers) - 1)
        self.marker_combo.blockSignals(False)
        self._trace_selected()
        self._marker_selected()

    def _trace_selected(self) -> None:
        index = self.trace_combo.currentIndex()
        if index < 0:
            self.rename_edit.clear()
            self.source_label.clear()
            return
        trace = self._plot.traces[index]
        self.rename_edit.setText(trace.name)
        self.source_label.setText(self._sources.get(trace.source_id, trace.source_id or "当前文件"))

    def _marker_selected(self) -> None:
        number = self.marker_combo.currentData()
        marker = next((m for m in self._plot.markers if m.number == number), None)
        self.reference_combo.clear()
        self.reference_combo.addItem("绝对读数", None)
        for reference in self._plot.markers:
            if reference.number != number and reference.reference_id is None:
                self.reference_combo.addItem(f"M{reference.number}", reference.number)
        if marker is None:
            self.position_edit.clear()
            self.readout.setText("添加 Marker 后可搜索、逐点移动或拖动图中的竖线。")
            return
        self.reference_combo.setCurrentIndex(
            max(0, self.reference_combo.findData(marker.reference_id))
        )
        self.position_edit.setText(f"{marker.x:.17g}")
        trace = self._plot.traces[marker.trace_index]
        reading = marker_reading(self._plot, marker)
        text = (
            f"M{marker.number}: X = {reading_text(reading.x)} {trace.x_unit}\n"
            f"Y = {reading_text(reading.y)} {trace.y_unit}"
        )
        if marker.reference_id is not None:
            text += (
                f"\nΔX = {reading_text(reading.delta_x)} {trace.x_unit}\n"
                f"ΔY = {reading_text(reading.delta_y)} {trace.y_unit}"
            )
        self.readout.setText(text)
