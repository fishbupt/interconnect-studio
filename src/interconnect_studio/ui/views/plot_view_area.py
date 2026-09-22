"""Grid of plots filling the centre of the window."""

from PyQt6.QtCore import QEvent, QObject, pyqtSignal
from PyQt6.QtWidgets import QFrame, QGridLayout, QVBoxLayout, QWidget

from interconnect_studio.core import PlotModel, ViewLayout
from interconnect_studio.ui.theme import DEFAULT_THEME, Theme, palette_for
from interconnect_studio.ui.widgets import CartesianPlotWidget

_SELECTION_WIDTH = 2


class PlotViewArea(QWidget):
    """Renders a ``ViewLayout`` as a fixed grid of plots.

    One cell is always current; new traces go there. Cells are selected by
    clicking them. The grid is fixed, not a draggable splitter, so the
    layout stays serialisable and testable.
    """

    current_index_changed = pyqtSignal(int)

    def __init__(
        self,
        parent: QWidget | None = None,
        theme: Theme = DEFAULT_THEME,
        layout: ViewLayout | None = None,
    ) -> None:
        super().__init__(parent)

        self._theme = theme
        self._layout_model = layout or ViewLayout(rows=1, cols=1)
        self._current_index = 0
        self._cells: list[QFrame] = []
        self._plots: list[CartesianPlotWidget] = []

        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(2)

        self._rebuild()

    @property
    def layout_model(self) -> ViewLayout:
        """Layout currently rendered."""

        return self._layout_model

    @property
    def theme(self) -> Theme:
        """Theme currently applied."""

        return self._theme

    @property
    def current_index(self) -> int:
        """Row-major index of the selected cell."""

        return self._current_index

    @property
    def current_plot_widget(self) -> CartesianPlotWidget:
        """Plot widget of the selected cell."""

        return self._plots[self._current_index]

    @property
    def current_plot(self) -> PlotModel:
        """Plot model of the selected cell."""

        return self._layout_model.plots[self._current_index]

    def plot_widget_at(self, index: int) -> CartesianPlotWidget:
        """Plot widget of one cell, by row-major index."""

        return self._plots[index]

    def set_current_index(self, index: int) -> None:
        """Select a cell by row-major index."""

        if index < 0 or index >= len(self._plots):
            raise ValueError(f"Cell index must be in [0, {len(self._plots) - 1}], got {index}.")
        if index == self._current_index:
            return
        self._current_index = index
        self._refresh_selection()
        self.current_index_changed.emit(index)

    def set_layout_model(self, layout: ViewLayout) -> None:
        """Replace the whole layout, rebuilding the grid."""

        self._layout_model = layout
        self._current_index = min(self._current_index, layout.n_cells - 1)
        self._rebuild()

    def set_grid(self, rows: int, cols: int) -> None:
        """Resize the grid, keeping plots that still have a cell."""

        self.set_layout_model(self._layout_model.resized(rows, cols))

    def set_current_plot(self, plot: PlotModel) -> None:
        """Replace the plot model of the selected cell."""

        self.set_plot_at(self._current_index, plot)

    def set_plot_at(self, index: int, plot: PlotModel) -> None:
        """Replace the plot model of one cell."""

        row, col = divmod(index, self._layout_model.cols)
        self._layout_model = self._layout_model.with_plot(row, col, plot)
        self._plots[index].set_plot_model(plot)

    def apply_theme(self, theme: Theme) -> None:
        """Restyle every cell."""

        self._theme = theme
        for plot in self._plots:
            plot.apply_theme(theme)
        self._refresh_selection()

    def eventFilter(self, source: QObject | None, event: QEvent | None) -> bool:  # noqa: N802
        """Select the cell whose plot was clicked."""

        if event is not None and event.type() == QEvent.Type.MouseButtonPress:
            for index, plot in enumerate(self._plots):
                if source is plot or (source is not None and source.parent() is plot):
                    self.set_current_index(index)
                    break
        return super().eventFilter(source, event)

    def _rebuild(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.setParent(None)
        self._cells.clear()
        self._plots.clear()

        for index, model in enumerate(self._layout_model.plots):
            plot = CartesianPlotWidget(theme=self._theme)
            plot.set_plot_model(model)
            plot.plot_widget.installEventFilter(self)

            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.NoFrame)
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(
                _SELECTION_WIDTH,
                _SELECTION_WIDTH,
                _SELECTION_WIDTH,
                _SELECTION_WIDTH,
            )
            frame_layout.addWidget(plot)

            row, col = divmod(index, self._layout_model.cols)
            self._grid.addWidget(frame, row, col)
            self._cells.append(frame)
            self._plots.append(plot)

        self._refresh_selection()

    def _refresh_selection(self) -> None:
        palette = palette_for(self._theme)
        single_cell = len(self._cells) == 1
        for index, frame in enumerate(self._cells):
            selected = index == self._current_index and not single_cell
            color = palette.accent if selected else "transparent"
            frame.setStyleSheet(f"QFrame {{ border: {_SELECTION_WIDTH}px solid {color}; }}")
