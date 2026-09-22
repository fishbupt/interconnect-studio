"""Lightweight Cartesian plot widget for the first application shell."""

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFontMetrics, QPaintEvent, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget
import numpy as np

from interconnect_studio.core import PlotKind, PlotModel


class CartesianPlotWidget(QWidget):
    """Render a Cartesian PlotModel without depending on a third-party plot library."""

    _MARGIN_LEFT = 72
    _MARGIN_RIGHT = 24
    _MARGIN_TOP = 42
    _MARGIN_BOTTOM = 56

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = PlotModel()
        self.setMinimumSize(420, 280)

    @property
    def model(self) -> PlotModel:
        """Current plot model."""

        return self._model

    def set_plot_model(self, model: PlotModel) -> None:
        """Replace the displayed plot model."""

        if model.kind is not PlotKind.CARTESIAN:
            raise ValueError("CartesianPlotWidget only supports Cartesian PlotModel.")
        self._model = model
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint axes, grid, legend, and all finite trace segments."""

        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.palette().base())

        plot_rect = QRectF(
            float(self._MARGIN_LEFT),
            float(self._MARGIN_TOP),
            float(max(1, self.width() - self._MARGIN_LEFT - self._MARGIN_RIGHT)),
            float(max(1, self.height() - self._MARGIN_TOP - self._MARGIN_BOTTOM)),
        )
        self._draw_frame(painter, plot_rect)

        bounds = self._finite_bounds()
        if bounds is None:
            self._draw_empty_message(painter, plot_rect)
            return

        x_min, x_max, y_min, y_max = bounds
        self._draw_grid_and_labels(painter, plot_rect, x_min, x_max, y_min, y_max)
        self._draw_traces(painter, plot_rect, x_min, x_max, y_min, y_max)
        self._draw_legend(painter, plot_rect)

    def _finite_bounds(self) -> tuple[float, float, float, float] | None:
        if not self._model.traces:
            return None

        x_values = np.concatenate([trace.x for trace in self._model.traces])
        y_arrays = [np.asarray(trace.y, dtype=np.float64) for trace in self._model.traces]
        y_values = np.concatenate(y_arrays)
        finite_y = y_values[np.isfinite(y_values)]
        if x_values.size == 0 or finite_y.size == 0:
            return None

        x_min = float(np.min(x_values))
        x_max = float(np.max(x_values))
        y_min = float(np.min(finite_y))
        y_max = float(np.max(finite_y))
        if math.isclose(x_min, x_max):
            x_min -= 0.5
            x_max += 0.5
        if math.isclose(y_min, y_max):
            pad = max(abs(y_min) * 0.05, 1.0)
            y_min -= pad
            y_max += pad
        else:
            pad = (y_max - y_min) * 0.05
            y_min -= pad
            y_max += pad
        return x_min, x_max, y_min, y_max

    def _draw_frame(self, painter: QPainter, plot_rect: QRectF) -> None:
        painter.setPen(QPen(self.palette().mid().color(), 1.0))
        painter.drawRect(plot_rect)
        if self._model.title:
            painter.setPen(self.palette().text().color())
            painter.drawText(
                QRectF(0.0, 8.0, float(self.width()), 24.0),
                Qt.AlignmentFlag.AlignCenter,
                self._model.title,
            )

    def _draw_empty_message(self, painter: QPainter, plot_rect: QRectF) -> None:
        painter.setPen(self.palette().placeholderText().color())
        painter.drawText(
            plot_rect,
            Qt.AlignmentFlag.AlignCenter,
            "Open a .s2p file to plot S11/S21",
        )

    def _draw_grid_and_labels(
        self,
        painter: QPainter,
        plot_rect: QRectF,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        grid_pen = QPen(self.palette().midlight().color(), 1.0, Qt.PenStyle.DotLine)
        text_pen = QPen(self.palette().text().color())
        metrics = QFontMetrics(painter.font())
        for index in range(6):
            fraction = index / 5.0
            x = plot_rect.left() + fraction * plot_rect.width()
            y = plot_rect.bottom() - fraction * plot_rect.height()
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(x, plot_rect.top()), QPointF(x, plot_rect.bottom()))
            painter.drawLine(QPointF(plot_rect.left(), y), QPointF(plot_rect.right(), y))

            painter.setPen(text_pen)
            x_value = x_min + fraction * (x_max - x_min)
            y_value = y_min + fraction * (y_max - y_min)
            x_text = _format_frequency(x_value)
            y_text = f"{y_value:.3g}"
            painter.drawText(
                QRectF(x - 45.0, plot_rect.bottom() + 6.0, 90.0, 20.0),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                x_text,
            )
            painter.drawText(
                QRectF(4.0, y - 10.0, float(self._MARGIN_LEFT - 10), 20.0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                y_text,
            )

        painter.setPen(text_pen)
        x_label = self._model.x_label or "X"
        if self._model.traces and self._model.traces[0].x_unit:
            x_label = f"{x_label} ({self._model.traces[0].x_unit})"
        painter.drawText(
            QRectF(plot_rect.left(), plot_rect.bottom() + 30.0, plot_rect.width(), 20.0),
            Qt.AlignmentFlag.AlignCenter,
            x_label,
        )
        y_label = self._model.y_label or "Y"
        if self._model.traces and self._model.traces[0].y_unit:
            y_label = f"{y_label} ({self._model.traces[0].y_unit})"
        label_width = metrics.horizontalAdvance(y_label)
        painter.save()
        painter.translate(18.0, plot_rect.center().y() + label_width / 2.0)
        painter.rotate(-90.0)
        painter.drawText(QPointF(0.0, 0.0), y_label)
        painter.restore()

    def _draw_traces(
        self,
        painter: QPainter,
        plot_rect: QRectF,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        colors = (
            QColor("#1976d2"),
            QColor("#d32f2f"),
            QColor("#388e3c"),
            QColor("#7b1fa2"),
        )
        for trace_index, trace in enumerate(self._model.traces):
            y_values = np.asarray(trace.y, dtype=np.float64)
            finite = np.isfinite(trace.x) & np.isfinite(y_values)
            painter.setPen(QPen(colors[trace_index % len(colors)], 1.6))
            path = QPainterPath()
            active = False
            for x_value, y_value, is_finite in zip(trace.x, y_values, finite, strict=True):
                if not is_finite:
                    active = False
                    continue
                px = (
                    plot_rect.left()
                    + (float(x_value) - x_min) / (x_max - x_min) * plot_rect.width()
                )
                py = (
                    plot_rect.bottom()
                    - (float(y_value) - y_min) / (y_max - y_min) * plot_rect.height()
                )
                point = QPointF(px, py)
                if active:
                    path.lineTo(point)
                else:
                    path.moveTo(point)
                    active = True
            painter.drawPath(path)

    def _draw_legend(self, painter: QPainter, plot_rect: QRectF) -> None:
        colors = (
            QColor("#1976d2"),
            QColor("#d32f2f"),
            QColor("#388e3c"),
            QColor("#7b1fa2"),
        )
        x = plot_rect.right() - 130.0
        y = plot_rect.top() + 10.0
        for index, trace in enumerate(self._model.traces):
            painter.setPen(QPen(colors[index % len(colors)], 2.0))
            painter.drawLine(QPointF(x, y + 7.0), QPointF(x + 24.0, y + 7.0))
            painter.setPen(self.palette().text().color())
            painter.drawText(QPointF(x + 32.0, y + 11.0), trace.name)
            y += 20.0


def _format_frequency(value_hz: float) -> str:
    magnitude = abs(value_hz)
    if magnitude >= 1.0e9:
        return f"{value_hz / 1.0e9:.3g}G"
    if magnitude >= 1.0e6:
        return f"{value_hz / 1.0e6:.3g}M"
    if magnitude >= 1.0e3:
        return f"{value_hz / 1.0e3:.3g}k"
    return f"{value_hz:.3g}"
