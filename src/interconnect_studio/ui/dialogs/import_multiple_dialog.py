"""PLTS "Import Multiple Files" dialog (File > Import > Build File).

Builds one DUT file from parameters of several files. Parameters are mapped
one at a time (Individual) or a port at a time (Port); a mapping may be
changed and overwritten, and OK stays disabled until every DUT parameter has
a source. Only single-ended to single-ended mapping is available so far.
"""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.algorithms.network import (
    ParameterAssignment,
    missing_parameters,
    port_assignments,
)
from interconnect_studio.core import DataFormatError, InputValidationError
from interconnect_studio.io import ImportFileType, guess_file_type
from interconnect_studio.services import BuildSource, ImportedNetwork, ImportService
from interconnect_studio.ui.dialogs.frequency_range_box import FrequencyRangeBox
from interconnect_studio.ui.dialogs.import_single_dialog import (
    DUT_CONFIGURATION_TOOLTIP,
    data_domain_box,
    file_type_combo,
)

MAX_DUT_PORTS = 64
_NOT_YET = "Needs Mixed-Mode and DUT Configuration, which are not available yet."


def parameter_name(row: int, col: int, n_ports: int) -> str:
    """Display name of a 0-based S-parameter, e.g. S21, or S12,3 from 10 ports on."""

    if n_ports >= 10:
        return f"S{row + 1},{col + 1}"
    return f"S{row + 1}{col + 1}"


class ImportMultipleFilesDialog(QDialog):
    """Map parameters or ports of several files onto one DUT network."""

    def __init__(self, service: ImportService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import Multiple Files")
        self._service = service
        self._sources: list[BuildSource] = []
        self._assignments: dict[tuple[int, int], ParameterAssignment] = {}
        self._imported: ImportedNetwork | None = None

        self.ports_spin = QSpinBox(self)
        self.ports_spin.setRange(1, MAX_DUT_PORTS)
        self.ports_spin.setValue(4)
        self.change_button = QPushButton("Change", self)
        self.change_button.setEnabled(False)
        self.change_button.setToolTip(DUT_CONFIGURATION_TOOLTIP)
        self.file_type_combo = file_type_combo(self)
        self.browse_button = QPushButton("Browse ...", self)
        self.remove_file_button = QPushButton("Remove", self)
        self.file_list = QListWidget(self)
        self.file_list.setMaximumHeight(80)
        self.name_edit = QLineEdit(self)
        self.individual_radio = QRadioButton("Individual", self)
        self.port_radio = QRadioButton("Port", self)
        self.individual_radio.setChecked(True)

        self.source_list = QListWidget(self)
        self.source_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.target_list = QListWidget(self)
        self.target_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.assign_button = QPushButton(">>", self)
        self.unassign_button = QPushButton("<<", self)
        self.grid = QTableWidget(self)
        self.grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.range_box = FrequencyRangeBox("7. Limit Data Range to Import", self)
        self.error_label = QLabel(self)
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #c0392b;")

        self.export_button = QPushButton("Export", self)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.buttons.addButton(self.export_button, QDialogButtonBox.ButtonRole.ActionRole)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(data_domain_box(self))
        layout.addLayout(self._file_section())
        layout.addWidget(self._mapping_section())
        layout.addWidget(self.range_box)
        layout.addWidget(self.error_label)
        layout.addWidget(self.buttons)

        self.ports_spin.valueChanged.connect(self._on_port_count_changed)
        self.browse_button.clicked.connect(self._browse)
        self.remove_file_button.clicked.connect(self._remove_file)
        self.file_list.currentRowChanged.connect(self._refresh_source_list)
        self.individual_radio.toggled.connect(self._refresh_lists)
        self.assign_button.clicked.connect(self.assign_selected)
        self.unassign_button.clicked.connect(self.unassign_selected)
        self.export_button.clicked.connect(self._export)
        self.range_box.changed.connect(self._refresh_buttons)
        self._refresh_lists()

    @property
    def imported(self) -> ImportedNetwork | None:
        """Built network after the dialog was accepted."""

        return self._imported

    @property
    def n_ports(self) -> int:
        """DUT port count."""

        return self.ports_spin.value()

    @property
    def assignments(self) -> tuple[ParameterAssignment, ...]:
        """Current mapping, in row-major DUT parameter order."""

        return tuple(self._assignments[key] for key in sorted(self._assignments))

    def add_file(self, path: str | Path) -> bool:
        """Read a file and append it to the source files; False if it fails."""

        file_path = Path(path)
        file_type = guess_file_type(file_path) or self._file_type()
        try:
            network = self._service.read(file_path, file_type)
        except (DataFormatError, InputValidationError) as exc:
            self.error_label.setText(str(exc))
            return False
        if self._sources:
            reference = self._sources[0].network
            if network.n_freq != reference.n_freq or network.z0 != reference.z0:
                self.error_label.setText(
                    f"{file_path.name} does not share the frequency points and reference "
                    "impedance of the first file; files are not resampled."
                )
                return False
        self.error_label.clear()
        self._sources.append(BuildSource(path=file_path, network=network))
        self.file_list.addItem(f"{len(self._sources)}: {file_path.name}")
        self.file_list.setCurrentRow(len(self._sources) - 1)
        if len(self._sources) == 1:
            self.name_edit.setText(f"{file_path.stem}_build.s{self.n_ports}p")
            self.range_box.set_network(network)
        self._refresh_buttons()
        return True

    def assign_selected(self) -> None:
        """'>>': map the selected file parameter(s) / port(s) to the selected DUT ones."""

        source = self.file_list.currentRow()
        if source < 0:
            return
        try:
            if self.individual_radio.isChecked():
                new = self._individual(
                    source, _parameters(self.source_list), _parameters(self.target_list)
                )
            else:
                new = self._by_port(source, _ports(self.source_list), _ports(self.target_list))
        except InputValidationError as exc:
            self.error_label.setText(str(exc))
            return
        self.error_label.clear()
        for item in new:
            self._assignments[(item.row, item.col)] = item
        self._refresh_grid()

    def unassign_selected(self) -> None:
        """'<<': clear the selected DUT parameters, or every parameter of the selected ports."""

        if self.individual_radio.isChecked():
            for target in _parameters(self.target_list):
                self._assignments.pop(target, None)
        else:
            ports = set(_ports(self.target_list))
            for key in list(self._assignments):
                if key[0] in ports or key[1] in ports:
                    del self._assignments[key]
        self._refresh_grid()

    def accept(self) -> None:
        """Build the network; stay open and show why if that fails."""

        imported = self._build()
        if imported is None:
            return
        self._imported = imported
        super().accept()

    def _individual(
        self,
        source: int,
        sources: list[tuple[int, int]],
        targets: list[tuple[int, int]],
    ) -> list[ParameterAssignment]:
        if len(sources) != 1:
            raise InputValidationError("Select one file parameter to map.")
        if not targets:
            raise InputValidationError("Select one or more DUT parameters.")
        source_row, source_col = sources[0]
        return [
            ParameterAssignment(row, col, source, source_row, source_col) for row, col in targets
        ]

    def _by_port(
        self, source: int, source_ports: list[int], target_ports: list[int]
    ) -> list[ParameterAssignment]:
        if not source_ports and not target_ports:
            # PLTS: select Port and press >> to keep the file's own port numbering.
            count = min(self._sources[source].network.n_ports, self.n_ports)
            source_ports = target_ports = list(range(count))
        if len(source_ports) != len(target_ports):
            raise InputValidationError(
                "Select as many DUT ports as file ports; they are paired in order."
            )
        return list(port_assignments(source, source_ports, target_ports))

    def _build(self) -> ImportedNetwork | None:
        name = self.name_edit.text().strip() or f"build.s{self.n_ports}p"
        try:
            return self._service.build(
                self._sources,
                self.n_ports,
                self.assignments,
                name,
                self.range_box.frequency_range(),
            )
        except (DataFormatError, InputValidationError) as exc:
            self.error_label.setText(str(exc))
            return None

    def _export(self) -> None:
        imported = self._build()
        if imported is None:
            return
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export Built File", imported.name, f"Touchstone (*.s{self.n_ports}p)"
        )
        if not file_name:
            return
        try:
            self._service.export_touchstone(imported.network, file_name)
        except DataFormatError as exc:
            self.error_label.setText(str(exc))

    def _browse(self) -> None:
        file_type = self._file_type()
        file_names, _ = QFileDialog.getOpenFileNames(
            self, "Select Files to Import", "", f"{file_type.file_filter};;All Files (*)"
        )
        for file_name in file_names:
            self.add_file(file_name)

    def _remove_file(self) -> None:
        row = self.file_list.currentRow()
        if row < 0:
            return
        del self._sources[row]
        # Assignments refer to sources by index: drop this file's, shift later ones.
        kept: dict[tuple[int, int], ParameterAssignment] = {}
        for key, item in self._assignments.items():
            if item.source == row:
                continue
            source = item.source - 1 if item.source > row else item.source
            kept[key] = ParameterAssignment(
                item.row, item.col, source, item.source_row, item.source_col
            )
        self._assignments = kept
        self.file_list.clear()
        for index, entry in enumerate(self._sources, start=1):
            self.file_list.addItem(f"{index}: {entry.path.name}")
        self.range_box.set_network(self._sources[0].network if self._sources else None)
        self._refresh_lists()

    def _on_port_count_changed(self, n_ports: int) -> None:
        self._assignments = {
            key: item
            for key, item in self._assignments.items()
            if item.row < n_ports and item.col < n_ports
        }
        stem = self.name_edit.text().rsplit(".s", 1)[0]
        if stem:
            self.name_edit.setText(f"{stem}.s{n_ports}p")
        self._refresh_lists()

    def _refresh_lists(self) -> None:
        self._refresh_source_list()
        self.target_list.clear()
        for value, text in self._choices(self.n_ports):
            self._add_item(self.target_list, value, text)
        self._refresh_grid()

    def _refresh_source_list(self) -> None:
        self.source_list.clear()
        row = self.file_list.currentRow()
        if 0 <= row < len(self._sources):
            for value, text in self._choices(self._sources[row].network.n_ports):
                self._add_item(self.source_list, value, text)
        self.source_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
            if self.individual_radio.isChecked()
            else QAbstractItemView.SelectionMode.ExtendedSelection
        )

    def _choices(self, n_ports: int) -> list[tuple[object, str]]:
        if self.individual_radio.isChecked():
            return [
                ((row, col), parameter_name(row, col, n_ports))
                for row in range(n_ports)
                for col in range(n_ports)
            ]
        return [(port, f"Port {port + 1}") for port in range(n_ports)]

    def _refresh_grid(self) -> None:
        n_ports = self.n_ports
        self.grid.clear()
        self.grid.setRowCount(n_ports)
        self.grid.setColumnCount(n_ports)
        labels = [str(port) for port in range(1, n_ports + 1)]
        self.grid.setHorizontalHeaderLabels(labels)
        self.grid.setVerticalHeaderLabels(labels)
        for (row, col), item in self._assignments.items():
            source_name = parameter_name(
                item.source_row, item.source_col, self._sources[item.source].network.n_ports
            )
            cell = QTableWidgetItem(f"{item.source + 1}:{source_name}")
            cell.setToolTip(
                f"DUT {parameter_name(row, col, n_ports)} <- file {item.source + 1} {source_name}"
            )
            self.grid.setItem(row, col, cell)
        self.grid.resizeColumnsToContents()
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        missing = missing_parameters(self.n_ports, self._assignments.values())
        ready = bool(self._sources) and not missing and self.range_box.point_count() > 0
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok is not None:
            ok.setEnabled(ready)
        self.export_button.setEnabled(ready)
        self.remove_file_button.setEnabled(bool(self._sources))

    def _file_type(self) -> ImportFileType:
        file_type: ImportFileType = self.file_type_combo.currentData()
        return file_type

    def _file_section(self) -> QFormLayout:
        configuration = QHBoxLayout()
        configuration.addWidget(self.change_button)
        configuration.addWidget(QLabel("DUT ports", self))
        configuration.addWidget(self.ports_spin)
        configuration.addStretch(1)
        files = QGridLayout()
        files.addWidget(self.file_list, 0, 0, 2, 1)
        files.addWidget(self.browse_button, 0, 1)
        files.addWidget(self.remove_file_button, 1, 1)
        mapping = QHBoxLayout()
        mapping.addWidget(self.individual_radio)
        mapping.addWidget(self.port_radio)
        mapping.addStretch(1)

        form = QFormLayout()
        form.addRow("2. Configuration of Data to Import:", configuration)
        form.addRow("3. Select File Type:", self.file_type_combo)
        form.addRow("4. Select File to Import:", files)
        form.addRow("5. Choose Parameter Mapping:", mapping)
        form.addRow("Name of built file:", self.name_edit)
        return form

    def _mapping_section(self) -> QGroupBox:
        box = QGroupBox(
            "6. Select one file parameter to map to one or more selected DUT parameters", self
        )
        kinds = QHBoxLayout()
        single = QRadioButton("Single Ended", box)
        single.setChecked(True)
        kinds.addWidget(single)
        for text in ("Differential", "Single Ended to Differential"):
            radio = QRadioButton(text, box)
            radio.setEnabled(False)
            radio.setToolTip(_NOT_YET)
            kinds.addWidget(radio)
        kinds.addStretch(1)

        arrows = QVBoxLayout()
        arrows.addStretch(1)
        arrows.addWidget(self.assign_button)
        arrows.addWidget(self.unassign_button)
        arrows.addStretch(1)

        lists = QGridLayout()
        lists.addWidget(QLabel("File Parameters", box), 0, 0)
        lists.addWidget(QLabel("DUT Parameters", box), 0, 1)
        lists.addWidget(QLabel("DUT S-parameter sources (file:parameter)", box), 0, 3)
        lists.addWidget(self.source_list, 1, 0)
        lists.addWidget(self.target_list, 1, 1)
        lists.addLayout(arrows, 1, 2)
        lists.addWidget(self.grid, 1, 3)
        lists.setColumnStretch(3, 1)

        layout = QVBoxLayout(box)
        layout.addLayout(kinds)
        layout.addLayout(lists)
        return box

    @staticmethod
    def _add_item(widget: QListWidget, value: object, text: str) -> None:
        item = QListWidgetItem(text, widget)
        item.setData(Qt.ItemDataRole.UserRole, value)


def _parameters(widget: QListWidget) -> list[tuple[int, int]]:
    """Selected 0-based (row, col) parameters of a list, in list order."""

    values = []
    for row in range(widget.count()):
        item = widget.item(row)
        if item is None or not item.isSelected():
            continue
        value = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(value, tuple) and len(value) == 2:
            values.append((int(value[0]), int(value[1])))
    return values


def _ports(widget: QListWidget) -> list[int]:
    """Selected 0-based ports of a list, in the order they were selected."""

    return [
        int(value)
        for item in widget.selectedItems()
        if isinstance(value := item.data(Qt.ItemDataRole.UserRole), int)
    ]

