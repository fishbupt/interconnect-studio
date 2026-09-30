"""Common preferences, with named import/export and restore defaults."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.services.export_service import ExportFileType
from interconnect_studio.ui.settings import Preferences, read_preferences, write_preferences
from interconnect_studio.ui.theme import Theme


class PreferencesDialog(QDialog):
    """Preferences are applied only after the user presses OK."""

    def __init__(self, preferences: Preferences, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("常用设置")
        self.theme_combo = QComboBox(self)
        self.theme_combo.addItem("浅色", Theme.LIGHT.value)
        self.theme_combo.addItem("深色", Theme.DARK.value)
        self.import_edit = QLineEdit(self)
        self.export_edit = QLineEdit(self)
        self.type_combo = QComboBox(self)
        for file_type in ExportFileType:
            self.type_combo.addItem(file_type.value, file_type.value)
        self.unit_combo = QComboBox(self)
        for unit in ("hz", "khz", "mhz", "ghz"):
            self.unit_combo.addItem(unit.upper(), unit)
        self.width_spin = QSpinBox(self)
        self.width_spin.setRange(1, 8)
        self.remember_check = QCheckBox("下次启动恢复窗口与停靠布局", self)
        form = QFormLayout()
        form.addRow("主题", self.theme_combo)
        form.addRow("默认导入目录", self._directory_row(self.import_edit))
        form.addRow("默认导出目录", self._directory_row(self.export_edit))
        form.addRow("默认导出类型", self.type_combo)
        form.addRow("默认频率单位", self.unit_combo)
        form.addRow("曲线线宽", self.width_spin)
        form.addRow(self.remember_check)
        named = QHBoxLayout()
        for text, action in (
            ("导入设置…", self._load),
            ("导出设置…", self._save),
            ("恢复默认值", lambda: self._fill(Preferences())),
        ):
            button = QPushButton(text, self)
            button.clicked.connect(action)
            named.addWidget(button)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(named)
        layout.addWidget(buttons)
        self._fill(preferences)

    def preferences(self) -> Preferences:
        """Collect the current, validated preferences."""

        return Preferences(
            theme=self.theme_combo.currentData(),
            import_directory=self.import_edit.text().strip(),
            export_directory=self.export_edit.text().strip(),
            export_type=self.type_combo.currentData(),
            frequency_unit=self.unit_combo.currentData(),
            line_width=self.width_spin.value(),
            remember_layout=self.remember_check.isChecked(),
        )

    def _fill(self, preferences: Preferences) -> None:
        for combo, value in (
            (self.theme_combo, preferences.theme),
            (self.type_combo, preferences.export_type),
            (self.unit_combo, preferences.frequency_unit),
        ):
            combo.setCurrentIndex(combo.findData(value))
        self.import_edit.setText(preferences.import_directory)
        self.export_edit.setText(preferences.export_directory)
        self.width_spin.setValue(preferences.line_width)
        self.remember_check.setChecked(preferences.remember_layout)

    def _directory_row(self, edit: QLineEdit) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(edit)
        button = QPushButton("选择…", row)

        def browse() -> None:
            directory = QFileDialog.getExistingDirectory(self, "选择目录", edit.text())
            if directory:
                edit.setText(directory)

        button.clicked.connect(browse)
        layout.addWidget(button)
        return row

    def _load(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "导入设置", "", "Preferences (*.icprefs)")
        if filename:
            try:
                self._fill(read_preferences(Path(filename)))
            except ValueError as exc:
                QMessageBox.warning(self, "导入失败", str(exc))

    def _save(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "导出设置", "", "Preferences (*.icprefs)")
        if filename:
            target = Path(filename).with_suffix(".icprefs")
            if (
                target.exists()
                and QMessageBox.question(self, "覆盖文件", f"{target.name} 已存在，是否覆盖？")
                != QMessageBox.StandardButton.Yes
            ):
                return
            try:
                write_preferences(self.preferences(), target)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "导出失败", str(exc))
