"""Grid of plots filling the centre of the window."""

from PyQt6 import sip
from PyQt6.QtCore import QEvent, QMimeData, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QDrag, QMouseEvent
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from interconnect_studio.core import PlotModel, ViewLayout
from interconnect_studio.ui.theme import DEFAULT_THEME, Theme, palette_for
from interconnect_studio.ui.widgets import CartesianPlotWidget

_SELECTION_WIDTH = 2


class PlotHandle(QLabel):
    """Small drag handle, leaving graph mouse gestures available for zoom/pan."""

    def __init__(self, index: int, parent: QWidget) -> None:
        super().__init__(parent)
        self.index = index

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:  # noqa: N802
        if event is not None and event.buttons() & Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData("application/x-interconnect-plot", str(self.index).encode())
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)
        super().mouseMoveEvent(event)


class PlotViewArea(QWidget):
    """Renders a ``ViewLayout`` as a fixed grid of plots.

    One cell is always current; new traces go there. Cells are selected by
    clicking them. The grid is fixed, not a draggable splitter, so the
    layout stays serialisable and testable.
    """

    current_index_changed = pyqtSignal(int)
    plot_range_changed = pyqtSignal()
    layout_about_to_change = pyqtSignal()
    marker_moved = pyqtSignal(int, int, float)
    reorder_requested = pyqtSignal(int, int)

    def __init__(
        self,
        parent: QWidget | None = None,
        theme: Theme = DEFAULT_THEME,
        layout: ViewLayout | None = None,
    ) -> None:
        super().__init__(parent)

        self._theme = theme
        self._line_width = 2
        self._layout_model = layout or ViewLayout(rows=1, cols=1)
        self._current_index = 0
        self._maximized = False
        self._cells: list[QFrame] = []
        self._plots: list[CartesianPlotWidget] = []

        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(8)

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
        self._refresh_visibility()
        self.current_index_changed.emit(index)

    def set_layout_model(self, layout: ViewLayout) -> None:
        """Replace the whole layout, rebuilding the grid."""

        self.layout_about_to_change.emit()
        self._layout_model = layout
        self._maximized = False
        self._current_index = min(self._current_index, layout.n_cells - 1)
        self._rebuild()

    def set_grid(self, rows: int, cols: int) -> None:
        """Resize the grid, keeping plots that still have a cell."""

        previous = self._layout_model
        selected_row, selected_col = divmod(self._current_index, previous.cols)
        histories = [plot.display_ranges() for plot in self._plots]
        ranges, auto = self.plot_ranges(), self.plot_autorange()
        self.set_layout_model(previous.resized(rows, cols))
        mapped_ranges: list[tuple[float, float, float, float] | None] = []
        mapped_auto = []
        for index, plot in enumerate(self._plots):
            row, col = divmod(index, cols)
            if row < previous.rows and col < previous.cols:
                origin = row * previous.cols + col
                plot.restore_display_ranges(histories[origin])
                mapped_ranges.append(ranges[origin])
                mapped_auto.append(auto[origin])
            else:
                mapped_ranges.append(None)
                mapped_auto.append((True, True))
        self.restore_plot_ranges(tuple(mapped_ranges), tuple(mapped_auto))
        selected = selected_row * cols + selected_col
        self.set_current_index(selected if selected_row < rows and selected_col < cols else 0)

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

    def set_line_width(self, width: int) -> None:
        """Apply trace width to current and subsequently created plots."""

        self._line_width = width
        for plot in self._plots:
            plot.set_line_width(width)

    def plot_ranges(self) -> tuple[tuple[float, float, float, float], ...]:
        """Capture the visible x/y bounds of every plot."""

        bounds: list[tuple[float, float, float, float]] = []
        for plot in self._plots:
            x_range, y_range = plot.plot_widget.getViewBox().viewRange()
            bounds.append(
                (float(x_range[0]), float(x_range[1]), float(y_range[0]), float(y_range[1]))
            )
        return tuple(bounds)

    def restore_plot_ranges(
        self,
        ranges: tuple[tuple[float, float, float, float] | None, ...],
        autorange: tuple[tuple[bool, bool], ...] = (),
    ) -> None:
        """Recall explicitly saved scales after rebuilding a layout."""

        for plot, bounds in zip(self._plots, ranges, strict=False):
            if bounds is not None:
                plot.plot_widget.setRange(xRange=bounds[:2], yRange=bounds[2:], padding=0)
        for plot, axes in zip(self._plots, autorange, strict=False):
            plot.plot_widget.getViewBox().enableAutoRange(x=axes[0], y=axes[1])

    def plot_autorange(self) -> tuple[tuple[bool, bool], ...]:
        """Remember which axes should keep following newly added data."""

        return tuple(
            (
                bool(plot.plot_widget.getViewBox().autoRangeEnabled()[0]),
                bool(plot.plot_widget.getViewBox().autoRangeEnabled()[1]),
            )
            for plot in self._plots
        )

    def toggle_maximized(self) -> None:
        """Show the active cell alone, without changing the model or its grid."""

        self._maximized = not self._maximized
        self._refresh_visibility()

    def _refresh_visibility(self) -> None:
        for index, frame in enumerate(self._cells):
            frame.setVisible(not self._maximized or index == self._current_index)
            self._grid.removeWidget(frame)
            row, col = (0, 0) if self._maximized else divmod(index, self._layout_model.cols)
            self._grid.addWidget(frame, row, col)
        for row in range(self._layout_model.rows):
            self._grid.setRowStretch(row, 1 if not self._maximized or row == 0 else 0)
        for col in range(self._layout_model.cols):
            self._grid.setColumnStretch(col, 1 if not self._maximized or col == 0 else 0)

    def eventFilter(self, source: QObject | None, event: QEvent | None) -> bool:  # noqa: N802
        """Select the cell whose plot was clicked."""

        if sip.isdeleted(self) or (source is not None and sip.isdeleted(source)):
            return False
        if event is not None:
            index = next(
                (
                    i
                    for i, frame in enumerate(self._cells)
                    if source is frame or (source is not None and source.parent() is frame)
                ),
                None,
            )
            if index is None:
                index = next(
                    (
                        i
                        for i, plot in enumerate(self._plots)
                        if source is plot or (source is not None and source.parent() is plot)
                    ),
                    None,
                )
            if index is not None:
                if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick):
                    self.set_current_index(index)
                    if event.type() == QEvent.Type.MouseButtonDblClick:
                        self.toggle_maximized()
                        return True
                if event.type() in (QEvent.Type.DragEnter, QEvent.Type.Drop):
                    from PyQt6.QtGui import QDragEnterEvent, QDropEvent

                    if isinstance(event, QDragEnterEvent | QDropEvent):
                        mime = event.mimeData()
                        if mime is not None and mime.hasFormat("application/x-interconnect-plot"):
                            event.acceptProposedAction()
                            if event.type() == QEvent.Type.Drop:
                                try:
                                    origin = int(
                                        mime.data("application/x-interconnect-plot").data()
                                    )
                                except ValueError:
                                    return True
                                self.reorder_requested.emit(origin, index)
                            return True
        return super().eventFilter(source, event)

    def _rebuild(self) -> None:
        for row in range(self._grid.rowCount()):
            self._grid.setRowStretch(row, 0)
        for col in range(self._grid.columnCount()):
            self._grid.setColumnStretch(col, 0)
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.removeEventFilter(self)
                for child in widget.findChildren(QWidget):
                    child.removeEventFilter(self)
                widget.hide()
                # Keep ownership until deferred deletion, including window teardown.
                widget.deleteLater()
        self._cells.clear()
        self._plots.clear()

        for index, model in enumerate(self._layout_model.plots):
            plot = CartesianPlotWidget(theme=self._theme)
            plot.set_line_width(self._line_width)
            plot.set_plot_model(model)
            plot.marker_moved.connect(
                lambda number, x, cell=index: self.marker_moved.emit(cell, number, x)
            )
            plot.plot_widget.installEventFilter(self)
            plot.plot_widget.getViewBox().sigRangeChangedManually.connect(
                lambda _axes: self.plot_range_changed.emit()
            )

            frame = QFrame()
            frame.setObjectName("plotCell")
            frame.setFrameShape(QFrame.Shape.NoFrame)
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(
                _SELECTION_WIDTH,
                _SELECTION_WIDTH,
                _SELECTION_WIDTH,
                _SELECTION_WIDTH,
            )
            handle = PlotHandle(index, frame)
            handle.setText(model.title or f"图 {index + 1}")
            handle.setToolTip("拖动此标题重排；双击放大或恢复")
            handle.installEventFilter(self)
            frame.setAcceptDrops(True)
            frame.installEventFilter(self)
            frame_layout.addWidget(handle)
            frame_layout.addWidget(plot)

            row, col = divmod(index, self._layout_model.cols)
            self._grid.addWidget(frame, row, col)
            self._cells.append(frame)
            self._plots.append(plot)

        self._refresh_selection()
        self._refresh_visibility()

    def _refresh_selection(self) -> None:
        palette = palette_for(self._theme)
        single_cell = len(self._cells) == 1
        for index, frame in enumerate(self._cells):
            selected = index == self._current_index and not single_cell
            color = palette.accent if selected else "transparent"
            frame.setStyleSheet(
                f"QFrame#plotCell {{ border: {_SELECTION_WIDTH}px solid {color};"
                " border-radius: 5px; }"
            )
