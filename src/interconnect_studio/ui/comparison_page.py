"""Independent A/B file overlays sharing imported data with the viewer."""

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.algorithms.network import SParameterFormat
from interconnect_studio.algorithms.network.traces import format_display_name
from interconnect_studio.core import DataFile, ViewLayout
from interconnect_studio.io.atomic import atomic_destination
from interconnect_studio.services.comparison_view_service import comparison_layout
from interconnect_studio.services.frequency_analysis import export_plot_csv, renamed_trace
from interconnect_studio.ui.dialogs.file_operation_dialog import run_file_operation
from interconnect_studio.ui.dialogs.trace_data_dialog import TraceDataDialog
from interconnect_studio.ui.views import PlotViewArea
from interconnect_studio.ui.widgets.axis_range_controls import AxisRangeControls

if TYPE_CHECKING:
    from interconnect_studio.ui.main_window import MainWindow


class ComparisonPage(QWidget):
    """Transient A/B presentation; never edits the viewer or the project file format."""

    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window)
        self.host = window
        self.files: dict[str, DataFile] = {}
        self._ranges: dict[tuple[str, str], tuple[tuple[float, float, float, float], ...]] = {}
        self._rendered_key: tuple[str, str] | None = None
        self._rendered_sources: tuple[str, str] | None = None
        self.area = PlotViewArea(theme=window.theme)
        self.a_combo = QComboBox(self)
        self.b_combo = QComboBox(self)
        self.swap_button = QPushButton("交换 A / B", self)
        self.parameter_combo = QComboBox(self)
        self.format_combo = QComboBox(self)
        for fmt in (
            SParameterFormat.LOG_MAG,
            SParameterFormat.LINEAR_MAG,
            SParameterFormat.PHASE,
            SParameterFormat.UNWRAPPED_PHASE,
            SParameterFormat.REAL,
            SParameterFormat.IMAGINARY,
        ):
            self.format_combo.addItem(format_display_name(fmt), fmt.value)
        stored = window.file_flow.settings.backend.value("comparison_format", "log_mag")
        self.format_combo.setCurrentIndex(max(0, self.format_combo.findData(stored)))
        self.compare_button = QPushButton("显示 A / B 曲线", self)
        self.compare_button.setObjectName("primary")
        self.note = QLabel("选择 A、B 两个文件，保留各自频率点，蓝色实线 A / 橙色虚线 B。", self)
        self.note.setObjectName("secondaryText")
        self.note.setWordWrap(True)
        self.summary = QLabel(self)
        self.summary.setWordWrap(True)
        self.summary.setObjectName("secondaryText")
        self.table_button = QPushButton("当前图数据表…", self)
        self.csv_button = QPushButton("当前图原始曲线 CSV…", self)
        self.image_button = QPushButton("当前图图片 PNG…", self)
        self.auto_button = QPushButton("当前图 AutoScale", self)
        self.auto_all_button = QPushButton("全部图 AutoScale", self)
        self.axis = AxisRangeControls(self.area, self)

        config = QWidget(self)
        config.setObjectName("configPanel")
        config_layout = QVBoxLayout(config)
        config_layout.setContentsMargins(12, 12, 12, 12)
        inputs = QGroupBox("比较输入", config)
        form = QFormLayout(inputs)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form.addRow("A · 蓝色实线", self.a_combo)
        form.addRow("B · 橙色虚线", self.b_combo)
        form.addRow(self.swap_button)
        for label, combo in (("参数", self.parameter_combo), ("格式", self.format_combo)):
            row = QWidget(inputs)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(QLabel(label, row))
            row_layout.addWidget(combo, 1)
            form.addRow(row)
        form.addRow(self.compare_button)
        config_layout.addWidget(inputs)
        config_layout.addWidget(self.note)
        config_layout.addWidget(self.summary)
        config_layout.addStretch()
        for button in (self.table_button, self.csv_button, self.image_button):
            config_layout.addWidget(button)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(config)
        scroll.setMinimumWidth(220)
        main = QWidget(self)
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(8, 8, 8, 8)
        scales = QHBoxLayout()
        scales.addWidget(self.auto_button)
        scales.addWidget(self.auto_all_button)
        scales.addStretch()
        main_layout.addLayout(scales)
        main_layout.addWidget(self.axis)
        main_layout.addWidget(self.area, 1)
        self.splitter: QSplitter = QSplitter(self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(scroll)
        self.splitter.addWidget(main)
        self.splitter.setSizes([250, 800])
        self.splitter.setStretchFactor(1, 1)
        stored_splitter = window.file_flow.settings.backend.value("comparison_splitter")
        if window.file_flow.preferences.remember_layout and isinstance(stored_splitter, QByteArray):
            self.splitter.restoreState(stored_splitter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)

        self.a_combo.currentIndexChanged.connect(self._inputs_changed)
        self.b_combo.currentIndexChanged.connect(self._inputs_changed)
        self.parameter_combo.currentIndexChanged.connect(self._invalidate)
        self.format_combo.currentIndexChanged.connect(self._invalidate)
        self.swap_button.clicked.connect(self.swap)
        self.compare_button.clicked.connect(self.show_comparison)
        self.auto_button.clicked.connect(lambda: self.autoscale(False))
        self.auto_all_button.clicked.connect(lambda: self.autoscale(True))
        self.table_button.clicked.connect(self.table)
        self.csv_button.clicked.connect(lambda: self.export("csv"))
        self.image_button.clicked.connect(lambda: self.export("png"))
        self.area.current_index_changed.connect(self.axis.sync)
        self._inputs_changed()

    def sync(self, files: tuple[DataFile, ...]) -> None:
        """Keep selections and valid overlays when unrelated files change."""

        updated = {item.id: item for item in files}
        selected = (self.a_combo.currentData(), self.b_combo.currentData())
        invalidate = any(
            source
            and (
                source not in updated
                or source not in self.files
                or updated[source].network is not self.files[source].network
            )
            for source in selected
        )
        self.files = updated
        for combo, source in zip((self.a_combo, self.b_combo), selected, strict=True):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("请选择文件", None)
            for item in files:
                combo.addItem(f"{item.name} [{item.id}]", item.id)
                combo.setItemData(
                    combo.count() - 1,
                    f"{item.name} [{item.id}]\n{item.source_path or item.name}",
                    Qt.ItemDataRole.ToolTipRole,
                )
            combo.setCurrentIndex(max(0, combo.findData(source)))
            combo.blockSignals(False)
        if invalidate:
            self._inputs_changed()
        else:
            if self._rendered_sources is not None:
                roles = dict(zip(self._rendered_sources, ("A", "B"), strict=True))
                names = {key: f"{role} · {updated[key].name}" for key, role in roles.items()}
                for index, plot in enumerate(self.area.layout_model.plots):
                    traces = tuple(
                        renamed_trace(trace, names[trace.source_id])
                        if trace.name != names[trace.source_id]
                        else trace
                        for trace in plot.traces
                    )
                    if any(a is not b for a, b in zip(traces, plot.traces, strict=True)):
                        self.area.set_plot_at(index, replace(plot, traces=traces))
            self._update_enabled()

    def select_a(self, file_id: str) -> None:
        """Send the current viewer object to A without silently choosing B."""

        self.a_combo.setCurrentIndex(max(0, self.a_combo.findData(file_id)))
        if self.b_combo.currentData() == file_id:
            self.b_combo.setCurrentIndex(0)

    def swap(self) -> None:
        """Exchange sources while keeping the physical parameter and display mode."""

        a, b = self.a_combo.currentData(), self.b_combo.currentData()
        for combo, source in ((self.a_combo, b), (self.b_combo, a)):
            combo.blockSignals(True)
            combo.setCurrentIndex(max(0, combo.findData(source)))
            combo.blockSignals(False)
        self._inputs_changed()

    def _inputs_changed(self) -> None:
        self._invalidate()
        previous = self.parameter_combo.currentData()
        inputs = [
            self.files[key]
            for key in (self.a_combo.currentData(), self.b_combo.currentData())
            if key in self.files
        ]
        n_ports = min((item.network.n_ports for item in inputs), default=0)
        self.parameter_combo.blockSignals(True)
        self.parameter_combo.clear()
        if n_ports >= 2:
            self.parameter_combo.addItem("端口 1/2 · 2×2", None)
        for response in range(n_ports):
            for source in range(n_ports):
                self.parameter_combo.addItem(f"S{response + 1}{source + 1}", (response, source))
        self.parameter_combo.setCurrentIndex(max(0, self.parameter_combo.findData(previous)))
        self.parameter_combo.blockSignals(False)
        self._update_enabled()

    def _remember_ranges(self) -> None:
        if self._rendered_key is not None:
            self._ranges[self._rendered_key] = self.area.plot_ranges()

    def _invalidate(self) -> None:
        self._remember_ranges()
        self._rendered_key = None
        self._rendered_sources = None
        self.area.set_layout_model(ViewLayout(rows=1, cols=1))
        self.summary.clear()
        self.note.setText("输入或显示格式已改变，请显示 A / B 曲线。原始频率网格不插值。")
        self.axis.sync()
        self._update_enabled()

    def _update_enabled(self) -> None:
        a, b = self.a_combo.currentData(), self.b_combo.currentData()
        ready = a in self.files and b in self.files and a != b
        self.compare_button.setEnabled(ready)
        if a in self.files and a == b:
            self.note.setText("请选择两个不同的文件。")
        self.swap_button.setEnabled(ready)
        valid = self._rendered_sources is not None
        for control in (
            self.table_button,
            self.csv_button,
            self.image_button,
            self.auto_button,
            self.auto_all_button,
        ):
            control.setEnabled(valid)
        workspace = getattr(self.host, "workspace", None)
        if workspace is not None and workspace._comparison is self:
            self.host.frequency_flow.sync()

    def show_comparison(self) -> None:
        """Build immutable curves off the UI thread behind the shared busy dialog."""

        a = self.files.get(self.a_combo.currentData())
        b = self.files.get(self.b_combo.currentData())
        if a is None or b is None or a.id == b.id:
            self.note.setText("请选择两个不同的文件。")
            return
        self._remember_ranges()
        fmt = SParameterFormat(self.format_combo.currentData())
        parameter = self.parameter_combo.currentData()
        key = (fmt.value, str(parameter))
        try:
            layout = cast(
                ViewLayout,
                run_file_operation(
                    "正在准备比较曲线",
                    lambda: comparison_layout(a, b, fmt, parameter),
                    self.host.tasks,
                    self.host,
                ),
            )
        except (ValueError, OSError) as exc:
            self._invalidate()
            self.note.setText(str(exc))
            return
        self.area.set_layout_model(layout)
        for cell in range(layout.n_cells):
            self.area.plot_widget_at(cell).set_comparison_sources((a.id, b.id))
        if key in self._ranges:
            self.area.restore_plot_ranges(self._ranges[key])
        self._rendered_key = key
        self._rendered_sources = (a.id, b.id)
        self.note.setText("A 蓝色实线 / B 橙色虚线。各自完整原始网格；未匹配或插值。")
        self.summary.setText(
            "\n".join(
                f"{role}: {item.network.n_ports} 端口 · {item.network.n_freq} 点\n"
                f"{item.network.frequencies_hz[0] / 1e9:g}–"
                f"{item.network.frequencies_hz[-1] / 1e9:g} GHz · Z₀ {item.network.z0.real:g} Ω"
                for role, item in (("A", a), ("B", b))
            )
        )
        self.axis.sync()
        self._update_enabled()

    def autoscale(self, all_plots: bool) -> None:
        """Reset bounds for the selected plot or all current comparison plots."""

        indices = range(self.area.layout_model.n_cells) if all_plots else (self.area.current_index,)
        for index in indices:
            view = self.area.plot_widget_at(index).plot_widget.getViewBox()
            view.autoRange()
            view.enableAutoRange(x=True, y=True)
        self.axis.sync()

    def table(self) -> None:
        """Show the selected comparison plot's original point table."""

        TraceDataDialog(self.area.current_plot, self._source_names(), self.host).exec()

    def _source_names(self) -> dict[str, str]:
        return {key: f"{item.name} [{key}]" for key, item in self.files.items()}

    def export(self, kind: str) -> None:
        """Export only the valid comparison plot, distinct from full network export."""

        if self._rendered_sources is None:
            return
        name, _ = QFileDialog.getSaveFileName(
            self.host, "导出当前比较图", f"comparison.{kind}", f"{kind.upper()} (*.{kind})"
        )
        if not name:
            return
        target = Path(name).with_suffix(f".{kind}")
        if (
            target.exists()
            and QMessageBox.question(self.host, "覆盖文件", f"{target.name} 已存在，是否覆盖？")
            != QMessageBox.StandardButton.Yes
        ):
            return
        plot, names = self.area.current_plot, self._source_names()
        image = self.area.current_plot_widget.image() if kind == "png" else None

        def write() -> None:
            if image is None:
                export_plot_csv(plot, target, names)
            else:
                with atomic_destination(target) as temporary:
                    if not image.save(str(temporary), "PNG"):
                        raise OSError("图片保存失败，请检查输出目录。")

        try:
            run_file_operation("正在导出比较图", write, self.host.tasks, self.host)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self.host, "导出失败", str(exc))
            return
        self.host.status_bar.showMessage(f"已导出：{target}")
