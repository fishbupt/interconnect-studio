"""Main application window."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QDialog,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from interconnect_studio.algorithms.network import SParameterFormat
from interconnect_studio.core import DataFormatError, InputValidationError
from interconnect_studio.services import LoadedTouchstonePlot, TouchstonePlotService
from interconnect_studio.ui.dialogs import AddTraceDialog
from interconnect_studio.ui.widgets import CartesianPlotWidget


class MainWindow(QMainWindow):
    """First Interconnect Studio application shell."""

    def __init__(
        self,
        service: TouchstonePlotService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service or TouchstonePlotService()
        self._loaded: LoadedTouchstonePlot | None = None

        self.setWindowTitle("Interconnect Studio")
        self.resize(1200, 760)

        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabel("Project")
        self.plot_widget = CartesianPlotWidget()
        self.property_panel = QWidget()
        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.file_value = QLabel("-")
        self.ports_value = QLabel("-")
        self.points_value = QLabel("-")
        self.z0_value = QLabel("-")

        self._build_property_panel()
        self._build_central_layout()
        self._build_log_dock()
        self._build_actions()
        self.add_trace_action.setEnabled(False)
        self.status_bar.showMessage("Ready")

    @property
    def loaded_measurement(self) -> LoadedTouchstonePlot | None:
        """Currently loaded two-port measurement, if any."""

        return self._loaded

    def load_touchstone_file(self, path: str | Path) -> LoadedTouchstonePlot:
        """Load a .s2p file through the application service and refresh the UI."""

        loaded = self._service.load_s2p(path)
        self._loaded = loaded
        self.plot_widget.set_plot_model(loaded.plot)
        self._update_project_tree(loaded)
        self._update_properties(loaded)
        self._append_log(f"Loaded: {loaded.path}")
        self._append_log("Default traces: S11 Log Mag, S21 Log Mag")
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
        self.plot_widget.set_plot_model(update.loaded.plot)
        self._update_project_tree(update.loaded)

        trace_name = update.loaded.plot.traces[-1].name
        if update.replaced_plot:
            self._append_log(f"Plot switched to: {trace_name}")
        else:
            self._append_log(f"Added trace: {trace_name}")
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
            self._append_log(f"Error: {exc}")
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
            self._append_log(f"Error: {exc}")
            QMessageBox.critical(self, "Open Touchstone Failed", str(exc))

    def _build_property_panel(self) -> None:
        layout = QFormLayout(self.property_panel)
        layout.addRow("File", self.file_value)
        layout.addRow("Ports", self.ports_value)
        layout.addRow("Points", self.points_value)
        layout.addRow("Z0", self.z0_value)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

    def _build_central_layout(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.project_tree)
        splitter.addWidget(self.plot_widget)
        splitter.addWidget(self.property_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([220, 760, 220])
        self.setCentralWidget(splitter)

    def _build_log_dock(self) -> None:
        dock = QDockWidget("Log", self)
        dock.setObjectName("log_dock")
        dock.setWidget(self.log_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        dock.resize(dock.width(), 150)

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

        toolbar = QToolBar("Main", self)
        toolbar.setObjectName("main_toolbar")
        toolbar.addAction(open_action)
        toolbar.addAction(self.add_trace_action)
        self.addToolBar(toolbar)

    def _update_project_tree(self, loaded: LoadedTouchstonePlot) -> None:
        self.project_tree.clear()
        root = QTreeWidgetItem([loaded.path.name])
        for trace in loaded.plot.traces:
            root.addChild(QTreeWidgetItem([trace.name]))
        self.project_tree.addTopLevelItem(root)
        root.setExpanded(True)

    def _update_properties(self, loaded: LoadedTouchstonePlot) -> None:
        self.file_value.setText(loaded.path.name)
        self.ports_value.setText(str(loaded.network.n_ports))
        self.points_value.setText(str(loaded.network.n_freq))
        self.z0_value.setText(f"{loaded.network.z0.real:g} Ω")

    def _append_log(self, message: str) -> None:
        self.log_panel.append(message)
