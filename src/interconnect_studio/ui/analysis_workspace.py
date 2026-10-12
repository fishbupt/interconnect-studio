"""PLTS-style analysis workspace with plot controls."""

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.ui.widgets.axis_range_controls import AxisRangeControls

if TYPE_CHECKING:
    from interconnect_studio.ui.main_window import MainWindow


class AnalysisWorkspace(QWidget):
    """Compose the existing analysis view, keeping file/window and Marker state intact."""

    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window)
        self.host = window
        self.setObjectName("analysisWorkspace")
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
        layout.addWidget(self.view_page, 1)
        window.plot_state_changed.connect(self.sync)
        window.view_area.current_index_changed.connect(self.axis.sync)
        self.sync()

    def sync(self) -> None:
        """Reflect the active analysis window and current plot."""

        window = self.host
        loaded = window.loaded_measurement
        self.view_stack.setCurrentWidget(window.view_area if loaded is not None else self.empty)
        for button in (self.auto_button,):
            button.setEnabled(loaded is not None)
        self.export_button.setEnabled(bool(window._files))
        self.table_button.setEnabled(bool(window.view_area.current_plot.traces))
        self.empty.setText(
            "在左侧 Data Browser 点击分析类型，重新打开当前文件的分析窗口。"
            if window._files
            else "从 File 菜单导入测量文件开始分析\n\n"
            "在左侧选择窗口与参数，点击图框选择当前图。"
        )
        self.axis.sync()
        self.host.add_trace_action.setEnabled(loaded is not None)
        self.host.file_flow.update_actions()
