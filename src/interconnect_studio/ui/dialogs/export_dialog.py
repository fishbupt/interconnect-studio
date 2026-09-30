"""Unified frequency-domain export dialog."""

from collections.abc import Sequence
from pathlib import Path
from typing import cast

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.core import InputValidationError
from interconnect_studio.io.touchstone import TouchstoneFormat, TouchstoneFrequencyUnit
from interconnect_studio.services.export_service import ExportFileType, ExportOptions, ExportService
from interconnect_studio.services.import_service import ImportedNetwork
from interconnect_studio.ui.dialogs.file_operation_dialog import FileOperationDialog
from interconnect_studio.ui.dialogs.frequency_range_box import FrequencyRangeBox
from interconnect_studio.ui.task_runner import TaskRunner


class ExportDialog(QDialog):
    """Choose an open data file, format, range, port order and destination."""

    def __init__(
        self,
        sources: Sequence[ImportedNetwork],
        runner: TaskRunner,
        parent: QWidget | None = None,
        *,
        directory: str = "",
        default_type: ExportFileType = ExportFileType.TOUCHSTONE,
        default_unit: TouchstoneFrequencyUnit = "hz",
        service: ExportService | None = None,
    ) -> None:
        super().__init__(parent)
        if not sources:
            raise InputValidationError("Import a file before exporting.")
        self.setWindowTitle("导出数据")
        self.resize(520, 540)
        self._sources = tuple(sources)
        self._runner = runner
        self._service = service or ExportService()
        self._directory = directory
        self.exported_path: Path | None = None
        self.source_combo = QComboBox(self)
        self.source_combo.addItems([source.name for source in sources])
        self.type_combo = QComboBox(self)
        for file_type in ExportFileType:
            self.type_combo.addItem(file_type.value, file_type.value)
        self.type_combo.setCurrentIndex(self.type_combo.findData(default_type.value))
        self.format_combo = QComboBox(self)
        for data_format in ("ri", "ma", "db"):
            self.format_combo.addItem(data_format.upper(), data_format)
        self.unit_combo = QComboBox(self)
        for unit in ("hz", "khz", "mhz", "ghz"):
            self.unit_combo.addItem(unit.upper(), unit)
        self.unit_combo.setCurrentIndex(self.unit_combo.findData(default_unit))
        self.port_order_edit = QLineEdit(self)
        self.port_order_edit.setToolTip("输出端口 → 原端口；填写完整排列，例如 3,1,4,2。")
        self.convert_check = QCheckBox("明确转换参考阻抗到 50 Ω（CITIfile）", self)
        self.reference_label = QLabel(self)
        self.path_edit = QLineEdit(self)
        browse = QPushButton("选择输出文件…", self)
        browse.clicked.connect(self._browse)
        form = QFormLayout()
        form.addRow("数据文件", self.source_combo)
        form.addRow("文件类型", self.type_combo)
        form.addRow("数值格式", self.format_combo)
        form.addRow("频率单位", self.unit_combo)
        form.addRow("端口顺序（1-based）", self.port_order_edit)
        form.addRow(self.reference_label)
        form.addRow(self.convert_check)
        form.addRow("输出路径", self.path_edit)
        form.addRow(browse)
        self.range_box = FrequencyRangeBox("导出频率范围（保留测量点）", self)
        note = QLabel("导出完整单端 S 矩阵。修改格式、频率范围或端口顺序不会改动原数据。", self)
        note.setWordWrap(True)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.buttons.accepted.connect(self._export)
        self.buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.range_box)
        layout.addWidget(note)
        layout.addWidget(self.buttons)
        self.source_combo.currentIndexChanged.connect(self._source_changed)
        self.type_combo.currentIndexChanged.connect(self._type_changed)
        self._source_changed()

    def options(self) -> ExportOptions:
        """Validate the form and build an explicit service configuration."""

        try:
            order = tuple(
                int(value.strip()) - 1 for value in self.port_order_edit.text().split(",")
            )
        except ValueError as exc:
            raise InputValidationError("端口顺序必须为逗号分隔的整数。") from exc
        return ExportOptions(
            file_type=ExportFileType(self.type_combo.currentData()),
            data_format=cast(TouchstoneFormat, self.format_combo.currentData()),
            frequency_unit=cast(TouchstoneFrequencyUnit, self.unit_combo.currentData()),
            frequency_range=self.range_box.frequency_range(),
            port_order=order,
            renormalize_to_50=self.convert_check.isChecked(),
        )

    def _source_changed(self) -> None:
        source = self._sources[self.source_combo.currentIndex()]
        self.range_box.set_network(source.network)
        self.port_order_edit.setText(
            ",".join(str(index + 1) for index in range(source.network.n_ports))
        )
        self.reference_label.setText(f"原始参考阻抗：{source.network.z0} Ω")
        self.path_edit.setText(str(Path(self._directory) / (Path(source.name).stem + "_export")))
        self._type_changed()

    def _type_changed(self) -> None:
        file_type = ExportFileType(self.type_combo.currentData())
        self.format_combo.setEnabled(
            file_type in {ExportFileType.TOUCHSTONE, ExportFileType.TOUCHSTONE2}
        )
        self.unit_combo.setEnabled(file_type is not ExportFileType.CITIFILE)
        self.convert_check.setVisible(file_type is ExportFileType.CITIFILE)
        if file_type is not ExportFileType.CITIFILE:
            self.convert_check.setChecked(False)

    def _target(self) -> Path:
        source = self._sources[self.source_combo.currentIndex()]
        text = self.path_edit.text().strip()
        if not text:
            raise InputValidationError("请选择输出路径。")
        return self._service.destination(
            text, source.network.n_ports, ExportFileType(self.type_combo.currentData())
        )

    def _browse(self) -> None:
        initial = str(self._target()) if self.path_edit.text().strip() else self._directory
        path, _ = QFileDialog.getSaveFileName(self, "选择输出文件", initial)
        if path:
            self.path_edit.setText(path)

    def _export(self) -> None:
        try:
            options = self.options()
            target = self._target()
        except ValueError as exc:
            QMessageBox.warning(self, "导出失败", str(exc))
            return
        if (
            target.exists()
            and QMessageBox.question(self, "覆盖文件", f"{target.name} 已存在，是否覆盖？")
            != QMessageBox.StandardButton.Yes
        ):
            return
        network = self._sources[self.source_combo.currentIndex()].network
        operation = FileOperationDialog(
            "正在导出数据",
            lambda: self._service.export(network, target, options),
            self._runner,
            self,
        )
        if operation.exec() == QDialog.DialogCode.Accepted:
            assert isinstance(operation.result_value, Path)
            self.exported_path = operation.result_value
            self.accept()
