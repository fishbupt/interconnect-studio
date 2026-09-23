"""Main application window."""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from functools import partial
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
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
    InputValidationError,
    PlotModel,
    ViewLayout,
    ViewType,
    ViewWindow,
)
from interconnect_studio.io import ImportFileType, guess_file_type
from interconnect_studio.services import (
    ImportedNetwork,
    ImportService,
    LoadedTouchstonePlot,
    TouchstonePlotService,
)
from interconnect_studio.ui.dialogs import (
    AddTraceDialog,
    BuildConfigDialog,
    ImportMultipleFilesDialog,
    ImportSingleFileDialog,
    SelectAnalysisViewDialog,
)
from interconnect_studio.ui.models.data_browser_model import DEFAULT_AVAILABLE_VIEW_TYPES
from interconnect_studio.ui.panels import (
    DataBrowserPanel,
    MessageLogPanel,
    ParameterFormatPanel,
)
from interconnect_studio.ui.theme import DEFAULT_THEME, Theme, apply_theme
from interconnect_studio.ui.views import PlotViewArea
from interconnect_studio.ui.widgets import CartesianPlotWidget
from interconnect_studio.ui.window_session import WindowSession

APP_TITLE = "Interconnect Studio"


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
        import_service: ImportService | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service or TouchstonePlotService()
        self._import_service = import_service or ImportService()
        self._loaded: LoadedTouchstonePlot | None = None
        self._sessions: dict[int, WindowSession] = {}
        self._active_window: int | None = None
        self._theme = DEFAULT_THEME
        self._next_file_number = 1

        self.setWindowTitle(APP_TITLE)
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
        self.data_browser.current_window_changed.connect(self._on_browser_window_changed)
        self.view_area.current_index_changed.connect(self._on_cell_changed)

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
        """Network of the active window, with the plot of its selected cell."""

        return self._loaded

    @property
    def active_window(self) -> int | None:
        """Number of the window shown in the view area, if any."""

        return self._active_window

    def show_window(self, number: int) -> None:
        """Show an open window's plots, keeping the current window's for later.

        This is what selecting a window in the Data Browser does.
        """

        if number == self._active_window:
            return
        session = self._sessions.get(number)
        if session is None:
            raise InputValidationError(f"Window {number} is not open.")
        self._store_active_session()
        self._restore_session(session)
        self._log(f"Window: {session.title}")

    def load_touchstone_file(self, path: str | Path) -> LoadedTouchstonePlot:
        """Import a whole file, typed by its name, into a Frequency Domain window.

        The programmatic shortcut for Import a Single File with range "All".
        """

        file_path = Path(path)
        file_type = guess_file_type(file_path) or ImportFileType.TOUCHSTONE
        return self.open_imported(self._import_service.import_single(file_path, file_type))

    def open_imported(
        self,
        imported: ImportedNetwork,
        view_type: ViewType = ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED,
    ) -> LoadedTouchstonePlot:
        """Open an imported network in a new window of a view type and show it."""

        loaded = self._service.show_network(imported.network, imported.name, imported.source_path)
        self._store_active_session()
        window = self._add_to_hierarchy(loaded, view_type)

        # A new window starts with the grid size currently on screen, empty
        # apart from the default plot in its first cell.
        shown = self.view_area.layout_model
        layout = ViewLayout(rows=shown.rows, cols=shown.cols).with_plot(0, 0, loaded.plot)
        session = WindowSession(window.number, view_type, loaded, layout)
        self._sessions[window.number] = session
        shown_data = self._restore_session(session)
        self.data_browser.select_window(window.number)
        network = imported.network
        self._log(f"Imported: {imported.source_path or imported.name}")
        self._log(
            f"{network.n_ports} ports, {network.n_freq} points, "
            f"{network.frequencies_hz[0]:g}-{network.frequencies_hz[-1]:g} Hz"
        )
        self._log(
            "Default traces: " + ", ".join(trace.name for trace in loaded.plot.traces)
        )
        self.add_trace_action.setEnabled(True)
        self.status_bar.showMessage(f"Imported {imported.name}")
        return shown_data

    def import_single_file(self) -> None:
        """File > Import > Single File."""

        dialog = ImportSingleFileDialog(self._import_service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.imported is not None:
            self._open_with_view_selection(dialog.imported)

    def import_multiple_files(self) -> None:
        """File > Import > Multiple Files (Build a File)."""

        dialog = ImportMultipleFilesDialog(self._import_service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.imported is not None:
            self._open_with_view_selection(dialog.imported)

    def build_with_config_file(self) -> None:
        """File > Import > Build with a Config File."""

        dialog = BuildConfigDialog(self._import_service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.imported is not None:
            self._open_with_view_selection(dialog.imported)

    def _open_with_view_selection(self, imported: ImportedNetwork) -> None:
        """Ask for the analysis view, as PLTS does after an import, then open."""

        selector = SelectAnalysisViewDialog(DEFAULT_AVAILABLE_VIEW_TYPES, parent=self)
        if selector.exec() != QDialog.DialogCode.Accepted:
            return
        view_type = selector.selected_view_type()
        if view_type is None:
            return
        self.open_imported(imported, view_type)

    def add_trace(
        self,
        response_port: int,
        source_port: int,
        data_format: SParameterFormat | str,
    ) -> LoadedTouchstonePlot:
        """Add one trace to the current plot through the application service."""

        if self._loaded is None:
            raise InputValidationError("Import a file before adding a trace.")

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
            QMessageBox.information(self, "Add Trace", "Import a file first.")
            return

        dialog = AddTraceDialog(self, n_ports=self._loaded.network.n_ports)
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

    def new_plot(
        self,
        response_port: int,
        source_port: int,
        data_format: SParameterFormat | str,
    ) -> LoadedTouchstonePlot:
        """Replace the current cell's plot with a single new trace."""

        if self._loaded is None:
            raise InputValidationError("Import a file before creating a plot.")

        cleared = LoadedTouchstonePlot(
            name=self._loaded.name,
            network=self._loaded.network,
            plot=PlotModel(),
            path=self._loaded.path,
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

    def _add_to_hierarchy(
        self, loaded: LoadedTouchstonePlot, view_type: ViewType
    ) -> ViewWindow:
        """Add a window for the loaded data under its view type; does not select it."""

        data_file = DataFile(
            id=f"file-{self._next_file_number}",
            name=loaded.name,
            network=loaded.network,
            source_path=loaded.path,
            imported_at=datetime.now(),
        )
        self._next_file_number += 1

        tree, window = self.data_browser.browser_tree.open(view_type, data_file)
        self.data_browser.set_browser_tree(tree)
        return window

    def _store_active_session(self) -> None:
        """Remember what the view area shows for the active window."""

        if self._active_window is None or self._loaded is None:
            return
        session = self._sessions[self._active_window]
        self._sessions[self._active_window] = replace(
            session,
            loaded=self._loaded,
            layout=self.view_area.layout_model,
            current_index=self.view_area.current_index,
        )

    def _restore_session(self, session: WindowSession) -> LoadedTouchstonePlot:
        """Put a window's grid, selected cell and data file on screen."""

        loaded = session.loaded_for_current_cell()
        self._active_window = session.number
        self._loaded = loaded
        self.view_area.set_layout_model(session.layout)
        self.view_area.set_current_index(session.current_index)
        for size, action in self.layout_actions.items():
            action.setChecked(size == (session.layout.rows, session.layout.cols))
        network = session.loaded.network
        self.parameter_format.set_summary(
            session.loaded.name, network.n_ports, network.n_freq, network.z0
        )
        self.parameter_format.set_traces(tuple(trace.name for trace in loaded.plot.traces))
        self.setWindowTitle(f"{APP_TITLE} - [{session.title}]")
        self.add_trace_action.setEnabled(True)
        return loaded

    def _on_browser_window_changed(self, window: ViewWindow | None) -> None:
        if window is not None and window.number in self._sessions:
            self.show_window(window.number)

    def _on_cell_changed(self, index: int) -> None:
        """Point trace operations at the newly selected cell's plot."""

        if self._loaded is None:
            return
        self._loaded = replace(self._loaded, plot=self.view_area.current_plot)
        self.parameter_format.set_traces(tuple(trace.name for trace in self._loaded.plot.traces))

    def _apply(self, loaded: LoadedTouchstonePlot) -> None:
        self.view_area.set_current_plot(loaded.plot)
        self.parameter_format.set_summary(
            loaded.name,
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
        import_menu = QMenu("&Import", self)
        file_menu.addMenu(import_menu)
        self.import_single_action = QAction("&Single File...", self)
        self.import_single_action.setShortcut("Ctrl+O")
        self.import_single_action.setIconText("Import")
        self.import_single_action.triggered.connect(self.import_single_file)
        import_menu.addAction(self.import_single_action)
        self.import_multiple_action = QAction("&Multiple Files (Build a File)...", self)
        self.import_multiple_action.setIconText("Build File")
        self.import_multiple_action.triggered.connect(self.import_multiple_files)
        import_menu.addAction(self.import_multiple_action)
        self.build_config_action = QAction("Build with a &Config File...", self)
        self.build_config_action.triggered.connect(self.build_with_config_file)
        import_menu.addAction(self.build_config_action)

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
        toolbar.addAction(self.import_single_action)
        toolbar.addAction(self.import_multiple_action)
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
