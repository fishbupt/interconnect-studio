"""PLTS "Build with a Config File" dialog (File > Import > Build with Config File)."""

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.core import DataFormatError, InputValidationError
from interconnect_studio.services import ImportedNetwork, ImportService
from interconnect_studio.ui.dialogs.import_single_dialog import DUT_CONFIGURATION_TOOLTIP

_CONFIG_HELP = (
    "CSV: first row 'folder,<path>'; then one row per file: "
    "index, file name, [file ports], [DUT ports], e.g. s4p_file_2,B.s4p,[1 2 3 4],[5 6 7 8]."
)


class BuildConfigDialog(QDialog):
    """Build a DUT file from the files and port maps listed in a config CSV."""

    def __init__(self, service: ImportService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Build with a Config File")
        self._service = service
        self._imported: ImportedNetwork | None = None

        self.change_button = QPushButton("Change", self)
        self.change_button.setEnabled(False)
        self.change_button.setToolTip(DUT_CONFIGURATION_TOOLTIP)
        self.path_edit = QLineEdit(self)
        self.browse_button = QPushButton("...", self)
        self.export_button = QPushButton("Export", self)
        self.error_label = QLabel(self)
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #c0392b;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.addButton(self.export_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        configuration = QHBoxLayout()
        configuration.addWidget(QLabel("DUT Configuration", self))
        configuration.addWidget(self.change_button)
        configuration.addStretch(1)
        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(self.browse_button)
        help_label = QLabel(_CONFIG_HELP, self)
        help_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addLayout(configuration)
        layout.addWidget(QLabel("Browse for Import Build Config File", self))
        layout.addLayout(path_row)
        layout.addWidget(help_label)
        layout.addWidget(self.error_label)
        layout.addWidget(buttons)

        self.browse_button.clicked.connect(self._browse)
        self.export_button.clicked.connect(self._export)

    @property
    def imported(self) -> ImportedNetwork | None:
        """Built network after the dialog was accepted."""

        return self._imported

    def accept(self) -> None:
        """Build from the config; stay open and show why if that fails."""

        imported = self._build()
        if imported is None:
            return
        self._imported = imported
        super().accept()

    def _build(self) -> ImportedNetwork | None:
        path = self.path_edit.text().strip()
        if not path:
            self.error_label.setText("Select a build config file.")
            return None
        try:
            return self._service.build_from_config(path)
        except (DataFormatError, InputValidationError) as exc:
            self.error_label.setText(str(exc))
            return None

    def _browse(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Import Build Config File", "", "Build config (*.csv);;All Files (*)"
        )
        if file_name:
            self.path_edit.setText(file_name)
            self.error_label.clear()

    def _export(self) -> None:
        imported = self._build()
        if imported is None:
            return
        n_ports = imported.network.n_ports
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export Built File", imported.name, f"Touchstone (*.s{n_ports}p)"
        )
        if not file_name:
            return
        try:
            self._service.export_touchstone(imported.network, file_name)
        except DataFormatError as exc:
            self.error_label.setText(str(exc))
