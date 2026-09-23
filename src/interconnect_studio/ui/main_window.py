"""Main application window."""

from collections.abc import Callable
from datetime import datetime
from functools import partial
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QStatusBar,
    QToolBar,
    QToolButton,
    QWidget,
)

from interconnect_studio.algorithms.network import SParameterFormat
from interconnect_studio.core import (
    DataFile,
    DataFormatError,
    InputValidationError,
    PlotModel,
    ViewType,
)
from interconnect_studio.services import LoadedTouchstonePlot, TouchstonePlotService
from interconnect_studio.ui.dialogs import AddTraceDialog
from interconnect_studio.ui.panels import (
    DataBrowserPanel,
    MessageLogPanel,
    ParameterFormatPanel,
)
from interconnect_studio.ui.theme import DEFAULT_THEME, Theme, apply_theme
from interconnect_studio.ui.views import PlotViewArea
from interconnect_studio.ui.widgets import CartesianPlotWidget


class MainWindow(QMainWindow):
    """Application shell.

    The left column holds two docking areas, matching PLTS: the data browser
    above and the parameter/format panel below. The view area occupies the
    centre and is not a dock. Messages live in the status bar, with a
    collapsed panel for their history.
    """

    def __init__(
        self,
        service: TouchstonePlotService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service or TouchstonePlotService()
        self._loaded: LoadedTouchstonePlot | None = None
        self._theme = DEFAULT_THEME
        self._next_file_number = 1

        self.setWindowTitle("Interconnect Studio")
        self.resize(1200, 760)

        self.data_browser = DataBrowserPanel(self)
        self.parameter_format = ParameterFormatPanel(self)
        self.message_log = MessageLogPanel(self)
        self.view_area = PlotViewArea(theme=self._theme)

        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.parameter_format.add_trace_requested.connect(self._on_add_trace_requested)
        self.parameter_format.new_plot_requested.connect(self._on_new_plot_requested)

        self.setCentralWidget(self.view_area)
        self._build_side_docks()
        self._build_message_dock()
        self._build_actions()

        self.add_trace_action.setEnabled(False)
        self.status_bar.showMessage("Ready")

    @property
    def plot_widget(self) -> CartesianPlotWidget:
        """Plot widget of the selected cell."""

        return self.view_area.current_plot_widget

    @property
    def loaded_measurement(self) -> LoadedTouchstonePlot | None:
        """Currently loaded two-port measurement, if any."""

        return self._loaded

    def load_touchstone_file(self, path: str | Path) -> LoadedTouchstonePlot:
        """Load a .s2p file through the application service and refresh the UI."""

        loaded = self._service.load_s2p(path)
        self._loaded = loaded
        self._add_to_hierarchy(loaded)
        self._apply(loaded)
        self._log(f"Loaded: {loaded.path}")
        self._log("Default traces: S11 Log Mag, S21 Log Mag")
        self.add_trace_action.setEnabled(True)
        self.status_bar.showMessage(f"Loaded {loaded.path.name}")
        return loaded

    def add_trace(
        self,
        response_port: int,
        source_port: int,
        data_format: SParameterFormat | str,
    ) -> LoadedTouchstonePlot:
        """Add one trace to the current plot through the application service."""

        if self._loaded is None:
            raise InputValidationError("Open a .s2p file before adding a trace.")

        update = self._service.add_trace(
            self._loaded,
            response_port,
            source_port,
            data_format,
        )
        self._loaded = update.loaded
        self._apply(update.loaded)

        trace_name = update.loaded.plot.traces[-1].name
        if update.replaced_plot:
            self._log(f"Plot switched to: {trace_name}")
        else:
            self._log(f"Added trace: {trace_name}")
        self.status_bar.showMessage(trace_name)
        return update.loaded

    def show_add_trace_dialog(self) -> None:
        """Show Add Trace dialog and apply the selected trace."""

        if self._loaded is None:
            QMessageBox.information(self, "Add Trace", "Open a .s2p file first.")
            return

        dialog = AddTraceDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selection = dialog.selection()
        try:
            self.add_trace(
                selection.response_port,
                selection.source_port,
                selection.data_format,
            )
        except InputValidationError as exc:
            self._log(f"Error: {exc}")
            QMessageBox.warning(self, "Add Trace Failed", str(exc))

    def open_touchstone_dialog(self) -> None:
        """Show a file dialog and load the selected .s2p file."""

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Touchstone",
            "",
            "Touchstone 2-Port (*.s2p);;All Files (*)",
        )
        if not file_name:
            return

        try:
            self.load_touchstone_file(file_name)
        except (DataFormatError, InputValidationError) as exc:
            self._log(f"Error: {exc}")
            QMessageBox.critical(self, "Open Touchstone Failed", str(exc))

    def new_plot(
        self,
        response_port: int,
        source_port: int,
        data_format: SParameterFormat | str,
    ) -> LoadedTouchstonePlot:
        """Replace the current cell's plot with a single new trace."""

        if self._loaded is None:
            raise InputValidationError("Open a .s2p file before creating a plot.")

        cleared = LoadedTouchstonePlot(
            path=self._loaded.path,
            network=self._loaded.network,
            plot=PlotModel(),
        )
        self._loaded = cleared
        return self.add_trace(response_port, source_port, data_format)

    def _on_add_trace_requested(
        self,
        response_port: int,
        source_port: int,
        data_format: str,
    ) -> None:
        self._guarded(lambda: self.add_trace(response_port, source_port, data_format))

    def _on_new_plot_requested(
        self,
        response_port: int,
        source_port: int,
        data_format: str,
    ) -> None:
        self._guarded(lambda: self.new_plot(response_port, source_port, data_format))

    def _guarded(self, action: Callable[[], object]) -> None:
        try:
            action()
        except InputValidationError as exc:
            self._log(f"Error: {exc}")
            self.status_bar.showMessage(str(exc))

    def _add_to_hierarchy(self, loaded: LoadedTouchstonePlot) -> None:
        """Open the loaded file in a Frequency Domain (Single-Ended) window.

        That is the only view type the application can display so far; PLTS
        asks for the view type on import, which will come with the others.
        """

        data_file = DataFile(
            id=f"file-{self._next_file_number}",
            name=loaded.path.name,
            network=loaded.network,
            source_path=loaded.path,
            imported_at=datetime.now(),
        )
        self._next_file_number += 1

        tree, window = self.data_browser.browser_tree.open(
            ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED,
            data_file,
        )
        self.data_browser.set_browser_tree(tree)
        self.data_browser.select_window(window.number)

    def _apply(self, loaded: LoadedTouchstonePlot) -> None:
        self.view_area.set_current_plot(loaded.plot)
        self.parameter_format.set_summary(
            loaded.path.name,
            loaded.network.n_ports,
            loaded.network.n_freq,
            loaded.network.z0,
        )
        self.parameter_format.set_traces(tuple(trace.name for trace in loaded.plot.traces))

    def _build_side_docks(self) -> None:
        self.data_browser_dock = QDockWidget("Data Browser", self)
        self.data_browser_dock.setObjectName("data_browser_dock")
        self.data_browser_dock.setWidget(self.data_browser)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.data_browser_dock)

        self.parameter_format_dock = QDockWidget("Parameter / Format", self)
        self.parameter_format_dock.setObjectName("parameter_format_dock")
        self.parameter_format_dock.setWidget(self.parameter_format)
        self.splitDockWidget(
            self.data_browser_dock,
            self.parameter_format_dock,
            Qt.Orientation.Vertical,
        )

    def _build_message_dock(self) -> None:
        self.message_dock = QDockWidget("Messages", self)
        self.message_dock.setObjectName("message_dock")
        self.message_dock.setWidget(self.message_log)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.message_dock)
        self.message_dock.hide()

        self.messages_button = QToolButton(self)
        self.messages_button.setText("Messages")
        self.messages_button.setCheckable(True)
        self.messages_button.toggled.connect(self.message_dock.setVisible)
        self.message_dock.visibilityChanged.connect(self.messages_button.setChecked)
        self.status_bar.addPermanentWidget(self.messages_button)

    def _build_actions(self) -> None:
        file_menu = QMenu("&File", self)
        self.menu_bar.addMenu(file_menu)
        open_action = QAction("&Open Touchstone...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_touchstone_dialog)
        file_menu.addAction(open_action)

        self.add_trace_action = QAction("&Add Trace...", self)
        self.add_trace_action.setShortcut("Ctrl+T")
        self.add_trace_action.triggered.connect(self.show_add_trace_dialog)
        file_menu.addAction(self.add_trace_action)

        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = QMenu("&View", self)
        self.menu_bar.addMenu(view_menu)
        view_menu.addAction(self.data_browser_dock.toggleViewAction())
        view_menu.addAction(self.parameter_format_dock.toggleViewAction())
        view_menu.addAction(self.message_dock.toggleViewAction())

        view_menu.addSeparator()
        layout_menu = QMenu("&Layout", self)
        view_menu.addMenu(layout_menu)
        self.layout_actions: dict[tuple[int, int], QAction] = {}
        for rows, cols in ((1, 1), (1, 2), (2, 1), (2, 2)):
            action = QAction(f"{rows} x {cols}", self)
            action.setCheckable(True)
            action.setChecked((rows, cols) == (1, 1))
            action.triggered.connect(partial(self._on_layout_selected, rows, cols))
            layout_menu.addAction(action)
            self.layout_actions[(rows, cols)] = action

        view_menu.addSeparator()
        self.dark_theme_action = QAction("&Dark Theme", self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.setChecked(self._theme is Theme.DARK)
        self.dark_theme_action.toggled.connect(self._on_dark_theme_toggled)
        view_menu.addAction(self.dark_theme_action)

        toolbar = QToolBar("Main", self)
        toolbar.setObjectName("main_toolbar")
        toolbar.addAction(open_action)
        toolbar.addAction(self.add_trace_action)
        self.addToolBar(toolbar)

    def set_grid(self, rows: int, cols: int) -> None:
        """Change the view area grid, keeping plots that still have a cell."""

        self.view_area.set_grid(rows, cols)
        for size, action in self.layout_actions.items():
            action.setChecked(size == (rows, cols))
        self._log(f"Layout: {rows} x {cols}")

    @property
    def theme(self) -> Theme:
        """Theme currently applied."""

        return self._theme

    def set_theme(self, theme: Theme) -> None:
        """Switch the application theme."""

        self._theme = theme
        self.view_area.apply_theme(theme)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, theme)

    def _on_layout_selected(self, rows: int, cols: int) -> None:
        self.set_grid(rows, cols)

    def _on_dark_theme_toggled(self, checked: bool) -> None:
        self.set_theme(Theme.DARK if checked else Theme.LIGHT)

    def _log(self, message: str) -> None:
        self.message_log.append(message)
