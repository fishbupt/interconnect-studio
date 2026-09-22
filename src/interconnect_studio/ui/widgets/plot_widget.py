"""Cartesian plot widget backed by pyqtgraph."""

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from interconnect_studio.core import PlotKind, PlotModel, YAxis
from interconnect_studio.ui.theme import DEFAULT_THEME, Palette, Theme, palette_for, trace_color

_LINE_WIDTH = 2


class CartesianPlotWidget(QWidget):
    """Render a Cartesian PlotModel, with an optional second y axis.

    The right axis lives in its own view box linked to the left one on x, so
    magnitude and phase can share a plot without sharing a scale.
    """

    def __init__(self, parent: QWidget | None = None, theme: Theme = DEFAULT_THEME) -> None:
        super().__init__(parent)

        self._model = PlotModel()
        self._theme = theme

        self.plot_widget = pg.PlotWidget()
        self._plot_item = self.plot_widget.getPlotItem()
        self._plot_item.showGrid(x=True, y=True, alpha=0.25)
        self._legend = self._plot_item.addLegend(offset=(-10, 10))

        self._right_view = pg.ViewBox()
        self._plot_item.scene().addItem(self._right_view)
        self._plot_item.getAxis("right").linkToView(self._right_view)
        self._right_view.setXLink(self._plot_item)
        self._plot_item.vb.sigResized.connect(self._sync_right_view)

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
        for name in ("left", "bottom", "right"):
            axis = self._plot_item.getAxis(name)
            axis.setPen(pg.mkPen(palette.border))
            axis.setTextPen(pg.mkPen(palette.muted_text))
        self._plot_item.titleLabel.setAttr("color", palette.text)
        self._legend.setLabelTextColor(palette.text)
        self._redraw()

    def _sync_right_view(self) -> None:
        self._right_view.setGeometry(self._plot_item.vb.sceneBoundingRect())
        self._right_view.linkedViewChanged(self._plot_item.vb, self._right_view.XAxis)

    def _redraw(self) -> None:
        palette = palette_for(self._theme)
        self._plot_item.clear()
        self._right_view.clear()
        self._legend.clear()

        has_right = bool(self._model.traces_on(YAxis.RIGHT))
        self._plot_item.showAxis("right", show=has_right)

        self._apply_labels(palette, has_right)

        for index, entry in enumerate(self._model.entries):
            pen = pg.mkPen(trace_color(palette, index), width=_LINE_WIDTH)
            curve = pg.PlotDataItem(
                np.asarray(entry.trace.x, dtype=np.float64),
                np.asarray(entry.trace.y, dtype=np.float64),
                pen=pen,
                name=entry.trace.name,
            )
            if entry.y_axis is YAxis.RIGHT:
                self._right_view.addItem(curve)
                self._legend.addItem(curve, entry.trace.name)
            else:
                self._plot_item.addItem(curve)

        self._sync_right_view()

    def _apply_labels(self, palette: Palette, has_right: bool) -> None:
        # Units go through pyqtgraph's ``units`` argument rather than baked
        # into the label text, so it can scale ticks with SI prefixes
        # (100 MHz rather than 1e+08).
        label_style = {"color": palette.muted_text}
        self._plot_item.setTitle(self._model.title or None, color=palette.text)

        left_traces = self._model.traces_on(YAxis.LEFT)
        right_traces = self._model.traces_on(YAxis.RIGHT)

        self._plot_item.setLabel(
            "bottom",
            self._model.x_label,
            units=self._model.traces[0].x_unit if self._model.traces else None,
            **label_style,
        )
        self._plot_item.setLabel(
            "left",
            self._model.y_label_left,
            units=left_traces[0].y_unit if left_traces else None,
            **label_style,
        )
        if has_right:
            self._plot_item.setLabel(
                "right",
                self._model.y_label_right,
                units=right_traces[0].y_unit if right_traces else None,
                **label_style,
            )
