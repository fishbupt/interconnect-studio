"""Cartesian plot widget backed by pyqtgraph."""

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from pyqtgraph.exporters import ImageExporter

from interconnect_studio.core import PlotKind, PlotModel
from interconnect_studio.services.frequency_analysis import marker_reading
from interconnect_studio.ui.theme import DEFAULT_THEME, Palette, Theme, palette_for, trace_color

_LINE_WIDTH = 2


class CartesianPlotWidget(QWidget):
    """Render a Cartesian PlotModel.

    A plot carries one display format, so it has a single y axis. Quantities
    of different units belong in separate plots.
    """

    marker_moved = pyqtSignal(int, float)

    def __init__(self, parent: QWidget | None = None, theme: Theme = DEFAULT_THEME) -> None:
        super().__init__(parent)

        self._model = PlotModel()
        self._theme = theme
        self._line_width = _LINE_WIDTH
        self.marker_lines: dict[int, pg.InfiniteLine] = {}

        self.plot_widget = pg.PlotWidget()
        self._plot_item = self.plot_widget.getPlotItem()
        self._plot_item.showGrid(x=True, y=True, alpha=0.25)
        self._legend = self._plot_item.addLegend(offset=(-10, 10))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_widget)

        self.apply_theme(theme)

    @property
    def model(self) -> PlotModel:
        """Plot model currently rendered."""

        return self._model

    @property
    def theme(self) -> Theme:
        """Theme currently applied."""

        return self._theme

    def set_plot_model(self, model: PlotModel) -> None:
        """Replace the rendered plot model."""

        if model.kind is not PlotKind.CARTESIAN:
            raise ValueError("CartesianPlotWidget only supports Cartesian PlotModel.")
        self._model = model
        self._redraw()

    def apply_theme(self, theme: Theme) -> None:
        """Restyle the plot for a theme and redraw."""

        self._theme = theme
        palette = palette_for(theme)
        self.plot_widget.setBackground(palette.surface)
        for name in ("left", "bottom"):
            axis = self._plot_item.getAxis(name)
            axis.setPen(pg.mkPen(palette.border))
            axis.setTextPen(pg.mkPen(palette.muted_text))
        self._plot_item.titleLabel.setAttr("color", palette.text)
        self._legend.setLabelTextColor(palette.text)
        self._redraw()

    def set_line_width(self, width: int) -> None:
        """Apply the user's trace width to this plot."""

        self._line_width = width
        self._redraw()

    def _redraw(self) -> None:
        palette = palette_for(self._theme)
        self._plot_item.clear()
        self._legend.clear()
        self.marker_lines.clear()

        self._apply_labels(palette)

        for index, trace in enumerate(self._model.traces):
            pen = pg.mkPen(trace_color(palette, index), width=self._line_width)
            curve = pg.PlotDataItem(
                np.asarray(trace.x, dtype=np.float64),
                np.asarray(trace.y, dtype=np.float64),
                pen=pen,
                name=trace.name,
            )
            self._plot_item.addItem(curve)

        for marker in self._model.markers:
            trace = self._model.traces[marker.trace_index]
            color = trace_color(palette, marker.trace_index)
            reading = marker_reading(self._model, marker)
            line = pg.InfiniteLine(
                pos=reading.x,
                angle=90,
                movable=True,
                bounds=(float(trace.x[0]), float(trace.x[-1])),
                pen=pg.mkPen(color, width=1, style=Qt.PenStyle.DashLine),
                label=f"M{marker.number}",
                labelOpts={"position": 0.95, "color": color},
            )
            line.sigPositionChangeFinished.connect(
                lambda item, number=marker.number: self.marker_moved.emit(
                    number, float(item.value())
                )
            )
            self._plot_item.addItem(line, ignoreBounds=True)
            self.marker_lines[marker.number] = line
            if np.isfinite(reading.y):
                point = pg.ScatterPlotItem(
                    [reading.x], [reading.y], symbol="t", size=10, brush=color, pen=color
                )
                self._plot_item.addItem(point, ignoreBounds=True)

    def image(self, width: int = 1920) -> QImage:
        """Render axes, legend, curves and markers at the requested pixel width."""

        if not 320 <= width <= 4096:
            raise ValueError("Image width must be between 320 and 4096 pixels.")
        exporter = ImageExporter(self._plot_item)
        exporter.parameters()["width"] = width
        result = exporter.export(toBytes=True)
        if not isinstance(result, QImage) or result.isNull():
            raise ValueError("Plot image rendering failed.")
        return result

    def _apply_labels(self, palette: Palette) -> None:
        # Units go through pyqtgraph's ``units`` argument rather than baked
        # into the label text, so it can scale ticks with SI prefixes
        # (100 MHz rather than 1e+08).
        label_style = {"color": palette.muted_text}
        self._plot_item.setTitle(self._model.title or None, color=palette.text)

        first = self._model.traces[0] if self._model.traces else None
        self._plot_item.setLabel(
            "bottom",
            self._model.x_label,
            units=first.x_unit if first is not None else None,
            **label_style,
        )
        self._plot_item.setLabel(
            "left",
            self._model.y_label,
            units=first.y_unit if first is not None else None,
            **label_style,
        )
