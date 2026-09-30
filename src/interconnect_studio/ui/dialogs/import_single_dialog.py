"""PLTS "Import a Single File" dialog (File > Import > Single File)."""

from dataclasses import replace
from pathlib import Path
from typing import Final

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.core import (
    DataFormatError,
    DutConfiguration,
    InputValidationError,
    Network,
)
from interconnect_studio.io import ImportFileType, guess_file_type
from interconnect_studio.services import ImportedNetwork, ImportService
from interconnect_studio.ui.dialogs.dut_configuration_dialog import (
    DutConfigurationDialog,
    configuration_choices,
    default_configuration,
)
from interconnect_studio.ui.dialogs.file_operation_dialog import run_file_operation
from interconnect_studio.ui.dialogs.frequency_range_box import FrequencyRangeBox
from interconnect_studio.ui.task_runner import TaskRunner

TIME_DOMAIN_TOOLTIP: Final[str] = "Time-domain import is not available yet."
DUT_CONFIGURATION_TOOLTIP: Final[str] = (
    "Choose how the ports are grouped and addressed. It changes differential "
    "maths only; the data is never remapped."
)
NO_CHOICE_TOOLTIP: Final[str] = (
    "No alternative grouping exists for this port count, so the data imports single-ended."
)


def data_domain_box(parent: QWidget) -> QGroupBox:
    """'Select Data Domain to Import' group: Freq, with Time greyed out."""

    box = QGroupBox("1. Select Data Domain to Import", parent)
    freq = QRadioButton("Freq", box)
    freq.setChecked(True)
    time = QRadioButton("Time", box)
    time.setEnabled(False)
    time.setToolTip(TIME_DOMAIN_TOOLTIP)
    row = QHBoxLayout(box)
    row.addWidget(freq)
    row.addWidget(time)
    row.addStretch(1)
    return box


def file_type_combo(parent: QWidget) -> QComboBox:
    """File Type list with the PLTS frequency-domain types."""

    combo = QComboBox(parent)
    for file_type in ImportFileType:
        combo.addItem(file_type.label, file_type)
    return combo


class ImportSingleFileDialog(QDialog):
    """Import one frequency-domain file, optionally narrowed to a subset."""

    def __init__(self, service: ImportService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.initial_directory = ""
        self.runner: TaskRunner | None = None
        self.setWindowTitle("Import a Single File")
        self._service = service
        self._network: Network | None = None
        self._imported: ImportedNetwork | None = None
        self._configuration: DutConfiguration | None = None
        self._declared: DutConfiguration | None = None

        self.file_type_combo = file_type_combo(self)
        self.path_edit = QLineEdit(self)
        self.path_edit.setPlaceholderText("File to import")
        self.browse_button = QPushButton("Browse ...", self)
        self.change_button = QPushButton("Change", self)
        self.change_button.setEnabled(False)
        self.change_button.setToolTip(DUT_CONFIGURATION_TOOLTIP)
        self.configuration_label = QLabel("-", self)
        self.error_label = QLabel(self)
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #c0392b;")
        self.range_box = FrequencyRangeBox("5. Limit Data Range to Import", self)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(self.browse_button)
        configuration_row = QHBoxLayout()
        configuration_row.addWidget(self.change_button)
        configuration_row.addWidget(self.configuration_label, 1)

        form = QFormLayout()
        form.addRow("2. Select File Type:", self.file_type_combo)
        form.addRow("3. Select File to Import:", path_row)
        form.addRow("4. Configuration of Data to Import:", configuration_row)

        layout = QVBoxLayout(self)
        layout.addWidget(data_domain_box(self))
        layout.addLayout(form)
        layout.addWidget(self.range_box)
        layout.addWidget(self.error_label)
        layout.addWidget(self.buttons)

        self.change_button.clicked.connect(self._change_configuration)
        self.browse_button.clicked.connect(self._browse)
        self.path_edit.editingFinished.connect(self._load)
        self.file_type_combo.currentIndexChanged.connect(self._load)
        self.range_box.changed.connect(self._refresh_ok)
        self._refresh_ok()

    @property
    def imported(self) -> ImportedNetwork | None:
        """Imported network after the dialog was accepted."""

        return self._imported

    def file_type(self) -> ImportFileType:
        """Selected file type."""

        file_type: ImportFileType = self.file_type_combo.currentData()
        return file_type

    def set_path(self, path: str | Path) -> None:
        """Select a file, choosing its type from the name when unambiguous."""

        guessed = guess_file_type(path)
        if guessed is not None:
            self.file_type_combo.blockSignals(True)
            self.file_type_combo.setCurrentIndex(self.file_type_combo.findData(guessed))
            self.file_type_combo.blockSignals(False)
        self.path_edit.setText(str(path))
        self._load()

    def accept(self) -> None:
        """Import with the current settings; stay open and show why if that fails."""

        if self._network is None:
            return
        try:
            path = self.path_edit.text().strip()
            file_type = self.file_type()
            frequency_range = self.range_box.frequency_range()
            result = run_file_operation(
                "正在导入数据",
                lambda: self._service.import_single(path, file_type, frequency_range),
                self.runner,
                self,
            )
            assert isinstance(result, ImportedNetwork)
            imported = result
        except (DataFormatError, InputValidationError) as exc:
            self.error_label.setText(str(exc))
            return
        self._imported = replace(imported, dut_configuration=self._configuration)
        super().accept()

    def dut_configuration(self) -> DutConfiguration | None:
        """DUT configuration chosen for this import, if any."""

        return self._configuration

    def _change_configuration(self) -> None:
        if self._network is None:
            return
        dialog = DutConfigurationDialog(
            self._network.n_ports,
            self._configuration,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._configuration = dialog.configuration()
            self._refresh_configuration()

    def _browse(self) -> None:
        filters = ";;".join(file_type.file_filter for file_type in ImportFileType)
        selected_filter = self.file_type().file_filter
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Import",
            self.initial_directory,
            f"{filters};;All Files (*)",
            selected_filter,
        )
        if file_name:
            self.set_path(file_name)

    def _load(self) -> None:
        path = self.path_edit.text().strip()
        self._network = None
        self._declared = None
        self.error_label.clear()
        if path:
            try:
                file_type = self.file_type()
                result = run_file_operation(
                    "正在读取数据",
                    lambda: self._service.read_with_pairs(path, file_type),
                    self.runner,
                    self,
                )
                assert isinstance(result, tuple)
                self._network, self._declared = result
            except (DataFormatError, InputValidationError) as exc:
                self.error_label.setText(str(exc))
        self._configuration = self._default_configuration()
        # More than the plain single-ended entry means there is something to
        # choose between; with only that entry the button would open a
        # dialog offering no alternative.
        choosable = (
            self._network is not None and len(configuration_choices(self._network.n_ports)) > 1
        )
        self.change_button.setEnabled(choosable)
        self.change_button.setToolTip(DUT_CONFIGURATION_TOOLTIP if choosable else NO_CHOICE_TOOLTIP)
        self._refresh_configuration()
        self.range_box.set_network(self._network)
        self._refresh_ok()

    def _default_configuration(self) -> DutConfiguration | None:
        """What this file opens as.

        A file that stated its own pairing wins: guessing a topology over
        the file's own words would be wrong, and it is the only source here
        that actually knows. Everything else falls back to the preset the
        DUT dialog's Reset also restores.
        """

        if self._network is None:
            return None
        if self._declared is not None:
            return self._declared
        return default_configuration(self._network.n_ports)

    def _refresh_configuration(self) -> None:
        if self._network is None or self._configuration is None:
            self.configuration_label.setText("-")
            return
        configuration = self._configuration
        source = " (from file)" if configuration == self._declared else ""
        self.configuration_label.setText(
            f"{configuration.n_ports}-port, {configuration.topology_summary} "
            f"— {configuration.port_summary}{source}"
        )

    def _refresh_ok(self) -> None:
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok is not None:
            ok.setEnabled(self._network is not None and self.range_box.point_count() > 0)
