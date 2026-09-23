"""PLTS "Import a Single File" dialog (File > Import > Single File)."""

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

from interconnect_studio.core import DataFormatError, InputValidationError, Network
from interconnect_studio.io import ImportFileType, guess_file_type
from interconnect_studio.services import ImportedNetwork, ImportService
from interconnect_studio.ui.dialogs.frequency_range_box import FrequencyRangeBox

TIME_DOMAIN_TOOLTIP: Final[str] = "Time-domain import is not available yet."
DUT_CONFIGURATION_TOOLTIP: Final[str] = (
    "DUT Configuration is not available yet; data is imported as single-ended ports."
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
        self.setWindowTitle("Import a Single File")
        self._service = service
        self._network: Network | None = None
        self._imported: ImportedNetwork | None = None

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
            self._imported = self._service.import_single(
                self.path_edit.text().strip(), self.file_type(), self.range_box.frequency_range()
            )
        except (DataFormatError, InputValidationError) as exc:
            self.error_label.setText(str(exc))
            return
        super().accept()

    def _browse(self) -> None:
        filters = ";;".join(file_type.file_filter for file_type in ImportFileType)
        selected_filter = self.file_type().file_filter
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select File to Import", "", f"{filters};;All Files (*)", selected_filter
        )
        if file_name:
            self.set_path(file_name)

    def _load(self) -> None:
        path = self.path_edit.text().strip()
        self._network = None
        self.error_label.clear()
        if path:
            try:
                self._network = self._service.read(path, self.file_type())
            except (DataFormatError, InputValidationError) as exc:
                self.error_label.setText(str(exc))
        self.configuration_label.setText(
            f"{self._network.n_ports}-port, single-ended" if self._network is not None else "-"
        )
        self.range_box.set_network(self._network)
        self._refresh_ok()

    def _refresh_ok(self) -> None:
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok is not None:
            ok.setEnabled(self._network is not None and self.range_box.point_count() > 0)
