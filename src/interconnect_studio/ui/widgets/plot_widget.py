"""Cartesian plot widget backed by pyqtgraph."""

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from interconnect_studio.core import PlotKind, PlotModel
from interconnect_studio.ui.theme import DEFAULT_THEME, Palette, Theme, palette_for, trace_color

_LINE_WIDTH = 2


class CartesianPlotWidget(QWidget):
    """Render a Cartesian PlotModel.

    A plot carries one display format, so it has a single y axis. Quantities
    of different units belong in separate plots.
    """

    def __init__(self, parent: QWidget | None = None, theme: Theme = DEFAULT_THEME) -> None:
        super().__init__(parent)

        self._model = PlotModel()
        self._theme = theme

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

    def _redraw(self) -> None:
        palette = palette_for(self._theme)
        self._plot_item.clear()
        self._legend.clear()

        self._apply_labels(palette)

        for index, trace in enumerate(self._model.traces):
            pen = pg.mkPen(trace_color(palette, index), width=_LINE_WIDTH)
            curve = pg.PlotDataItem(
                np.asarray(trace.x, dtype=np.float64),
                np.asarray(trace.y, dtype=np.float64),
                pen=pen,
                name=trace.name,
            )
            self._plot_item.addItem(curve)

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
