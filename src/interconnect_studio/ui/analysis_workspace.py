"""PLTS-style analysis workspace with current-file summary and plot controls."""

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.core import ViewType
from interconnect_studio.ui.widgets.axis_range_controls import AxisRangeControls

if TYPE_CHECKING:
    from interconnect_studio.ui.main_window import MainWindow


class AnalysisWorkspace(QWidget):
    """Compose the existing analysis view, keeping file/window and Marker state intact."""

    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window)
        self.host = window
        self.setObjectName("analysisWorkspace")
        self.title = QLabel("S 参数分析", self)
        self.title.setObjectName("pageTitle")
        description = QLabel("在 Analysis View 中选择窗口，配置参数、显示格式与 Marker。", self)
        description.setObjectName("secondaryText")
        self.import_button = QPushButton("导入测量文件…", self)
        self.import_button.setObjectName("primary")
        self.import_button.clicked.connect(window.import_single_file)
        self.summary = QLabel("尚未导入文件 · 支持 Touchstone / CITI", self)
        self.summary.setObjectName("secondaryText")
        self.summary.setWordWrap(True)
        card = QWidget(self)
        card.setObjectName("summaryCard")
        card_layout = QVBoxLayout(card)
        heading = QHBoxLayout()
        heading.addWidget(self.title)
        heading.addStretch()
        heading.addWidget(self.import_button)
        card_layout.addLayout(heading)
        card_layout.addWidget(description)
        card_layout.addWidget(self.summary)
        files_row = QHBoxLayout()
        self.files = QComboBox(self)
        self.files.setMinimumContentsLength(15)
        self.files.currentIndexChanged.connect(self._select_file)
        self.view_type = QComboBox(self)
        for kind in (ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED, ViewType.FREQUENCY_DOMAIN_BALANCED):
            self.view_type.addItem(kind.label, kind)
        self.open_view_button = QPushButton("新建分析窗口", self)
        self.open_view_button.clicked.connect(
            lambda: window._guarded(lambda: window.open_view(self.view_type.currentData()))
        )
        self.close_view_button = QPushButton("关闭当前窗口", self)
        self.close_view_button.clicked.connect(
            lambda: window._guarded(
                lambda: (
                    window.close_view(window.active_window)
                    if window.active_window is not None
                    else None
                )
            )
        )
        files_row.addWidget(QLabel("当前文件", self))
        files_row.addWidget(self.files, 1)
        files_row.addWidget(self.view_type)
        files_row.addWidget(self.open_view_button)
        files_row.addWidget(self.close_view_button)
        card_layout.addLayout(files_row)

        self.view_page = QWidget(self)
        self.view_page.setObjectName("analysisView")
        view_layout = QVBoxLayout(self.view_page)
        view_layout.setContentsMargins(8, 8, 8, 8)
        row = QHBoxLayout()
        self.table_button = QPushButton("当前图数据表…", self)
        self.table_button.clicked.connect(lambda: window.frequency_flow._execute("table"))
        self.export_button = QPushButton("当前文件完整数据…", self)
        self.export_button.clicked.connect(window.file_flow.export_dialog)
        self.auto_button = QPushButton("全部图 AutoScale", self)
        self.auto_button.clicked.connect(lambda: window.frequency_flow._execute("autoscale_all"))
        for button in (
            self.table_button,
            self.export_button,
            self.auto_button,
        ):
            row.addWidget(button)
        row.addStretch()
        view_layout.addLayout(row)
        self.axis = AxisRangeControls(window.view_area, self)
        self.axis.changed.connect(window.file_flow.modified)
        view_layout.addWidget(self.axis)
        self.view_stack = QStackedWidget(self)
        self.empty = QLabel(
            "导入测量文件开始分析\n\n在左侧选择文件与参数，点击图框选择当前图。", self
        )
        self.empty.setObjectName("secondaryText")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view_stack.addWidget(self.empty)
        self.view_stack.addWidget(window.view_area)
        view_layout.addWidget(self.view_stack, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(card)
        layout.addWidget(self.view_page, 1)
        window.plot_state_changed.connect(self.sync)
        window.view_area.current_index_changed.connect(self.axis.sync)
        self.sync()

    def _select_file(self, index: int) -> None:
        file_id = self.files.itemData(index)
        if file_id is not None:
            self.host._guarded(lambda: self.host.select_data_file(file_id))

    def sync(self) -> None:
        """Reflect the active analysis window, current plot and file summary."""

        window = self.host
        loaded = window.loaded_measurement
        self.files.blockSignals(True)
        self.files.clear()
        for file_id, item in window._files.items():
            self.files.addItem(item.data_file.name, file_id)
            self.files.setItemData(
                self.files.count() - 1,
                str(item.data_file.source_path or ""),
                Qt.ItemDataRole.ToolTipRole,
            )
        self.files.setCurrentIndex(self.files.findData(window._active_file_id))
        self.files.blockSignals(False)
        self.open_view_button.setEnabled(bool(window._files))
        self.close_view_button.setEnabled(window.active_window is not None)
        self.view_stack.setCurrentWidget(window.view_area if loaded is not None else self.empty)
        for button in (self.auto_button,):
            button.setEnabled(loaded is not None)
        self.export_button.setEnabled(bool(window._files))
        self.table_button.setEnabled(bool(window.view_area.current_plot.traces))
        if loaded is None:
            selected = window._files.get(window._active_file_id or "")
            self.summary.setText(
                f"{selected.data_file.name} · 数据已保留，请新建分析窗口"
                if selected
                else "尚未导入文件 · 支持 Touchstone / CITI"
            )
        else:
            network = loaded.network
            self.summary.setText(
                f"{loaded.name} · {network.n_ports} 端口 · {network.n_freq} 点 · "
                f"{network.frequencies_hz[0] / 1e9:g}–"
                f"{network.frequencies_hz[-1] / 1e9:g} GHz · Z₀ {network.z0.real:g} Ω"
            )
            self.summary.setToolTip(str(loaded.path or loaded.name))
        self.axis.sync()
        self.host.add_trace_action.setEnabled(loaded is not None)
        self.host.file_flow.update_actions()
