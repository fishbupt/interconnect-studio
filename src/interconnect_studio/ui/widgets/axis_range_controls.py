"""Finite, explicit Y-axis bounds for the selected plot."""

import math

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget
from pyqtgraph import ViewBox

from interconnect_studio.ui.views import PlotViewArea


class AxisRangeControls(QWidget):
    """Apply bounds to an existing view; its session owns persistence."""

    changed = pyqtSignal()

    def __init__(self, area: PlotViewArea, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.area = area
        self._bound_view: ViewBox | None = None
        self.minimum = QLineEdit(self)
        self.maximum = QLineEdit(self)
        for edit, placeholder in ((self.minimum, "Y 最小"), (self.maximum, "Y 最大")):
            edit.setPlaceholderText(placeholder)
            edit.setMaximumWidth(100)
        self.apply_button = QPushButton("应用 Y 范围", self)
        self.error = QLabel(self)
        self.error.setObjectName("errorText")
        self.error.setWordWrap(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for widget in (self.minimum, self.maximum, self.apply_button):
            layout.addWidget(widget)
        layout.addWidget(self.error, 1)
        self.apply_button.clicked.connect(self.apply)
        area.layout_about_to_change.connect(self.detach)

    def apply(self) -> None:
        """Reject invalid input without changing the displayed range."""

        try:
            low, high = float(self.minimum.text()), float(self.maximum.text())
            if not math.isfinite(low) or not math.isfinite(high) or low >= high:
                raise ValueError
        except ValueError:
            self.error.setText("请输入有限数值，且最小值小于最大值。")
            return
        self.error.clear()
        self.area.current_plot_widget.plot_widget.setYRange(low, high, padding=0)
        self.changed.emit()

    def detach(self) -> None:
        """Disconnect the old view before a grid rebuild destroys its widgets."""

        if self._bound_view is not None:
            try:
                self._bound_view.sigRangeChanged.disconnect(self.sync)
            except (RuntimeError, TypeError):
                pass
            self._bound_view = None

    def sync(self) -> None:
        """Reflect the selected plot's actual bounds and unit."""

        plot = self.area.current_plot
        self.setEnabled(bool(plot.traces))
        view = self.area.current_plot_widget.plot_widget.getViewBox()
        if view is not self._bound_view:
            if self._bound_view is not None:
                try:
                    self._bound_view.sigRangeChanged.disconnect(self.sync)
                except (RuntimeError, TypeError):
                    pass  # Rebuilding the grid may already have destroyed the old view.
            self._bound_view = view
            view.sigRangeChanged.connect(self.sync)
        low, high = view.viewRange()[1]
        self.minimum.setText(f"{low:.8g}")
        self.maximum.setText(f"{high:.8g}")
        unit = plot.traces[0].y_unit if plot.traces else ""
        self.apply_button.setToolTip(f"当前图 Y 轴，单位：{unit or '无量纲'}")
        self.error.clear()
