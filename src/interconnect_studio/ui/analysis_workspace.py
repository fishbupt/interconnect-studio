"""Engineering workspace: current-file viewer and an independent A/B comparison page."""

from typing import TYPE_CHECKING

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from interconnect_studio.ui.comparison_page import ComparisonPage
from interconnect_studio.ui.theme import Theme
from interconnect_studio.ui.widgets.axis_range_controls import AxisRangeControls

if TYPE_CHECKING:
    from interconnect_studio.ui.main_window import MainWindow


class AnalysisWorkspace(QWidget):
    """Keep the existing viewer/session path separate from temporary comparisons."""

    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window)
        self.host = window
        self.setObjectName("analysisWorkspace")
        self.title = QLabel("S 参数分析", self)
        self.title.setObjectName("pageTitle")
        description = QLabel("查看当前文件，或独立比较两份测量数据。", self)
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

        self.tabs = QTabWidget(self)
        self.view_page = QWidget(self)
        view_layout = QVBoxLayout(self.view_page)
        view_layout.setContentsMargins(8, 8, 8, 8)
        row = QHBoxLayout()
        self.compare_button = QPushButton("与另一文件比较…", self)
        self.compare_button.clicked.connect(self.open_comparison)
        self.table_button = QPushButton("当前图数据表…", self)
        self.table_button.clicked.connect(lambda: window.frequency_flow._execute("table"))
        self.export_button = QPushButton("当前文件完整数据…", self)
        self.export_button.clicked.connect(window.file_flow.export_dialog)
        self.auto_button = QPushButton("全部图 AutoScale", self)
        self.auto_button.clicked.connect(lambda: window.frequency_flow._execute("autoscale_all"))
        for button in (
            self.compare_button,
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
        self._comparison: ComparisonPage | None = None
        self._comparison_placeholder = QWidget(self)
        self.tabs.addTab(self.view_page, "文件查看")
        self.tabs.addTab(self._comparison_placeholder, "文件比较 · A / B")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(card)
        layout.addWidget(self.tabs, 1)
        self._parameter_visible = True
        self._browser_visible = True
        self._marker_visible = False
        self.tabs.currentChanged.connect(self._page_changed)
        window.plot_state_changed.connect(self.sync)
        window.view_area.current_index_changed.connect(self.axis.sync)
        self.sync()

    def viewer_dock_state(self) -> QByteArray:
        """Save the viewer's dock visibility even if comparison temporarily hides it."""

        if self.tabs.currentIndex() == 0:
            return self.host.saveState()
        docks = (
            (self.host.data_browser_dock, self._browser_visible),
            (self.host.parameter_format_dock, self._parameter_visible),
            (self.host.frequency_flow.dock, self._marker_visible),
        )
        actual = tuple(dock.isVisibleTo(self.host) for dock, _visible in docks)
        try:
            for dock, visible in docks:
                dock.setVisible(visible)
            return self.host.saveState()
        finally:
            for (dock, _visible), visible in zip(docks, actual, strict=True):
                dock.setVisible(visible)

    @property
    def comparison(self) -> ComparisonPage:
        """Create the comparison page only when it is first needed."""

        if self._comparison is None:
            self._comparison = ComparisonPage(self.host)
            self._comparison.area.set_line_width(self.host.file_flow.preferences.line_width)
            index = self.tabs.currentIndex()
            self.tabs.blockSignals(True)
            self.tabs.removeTab(1)
            self.tabs.insertTab(1, self._comparison, "文件比较 · A / B")
            self.tabs.setCurrentIndex(index)
            self.tabs.blockSignals(False)
            self._comparison_placeholder.deleteLater()
            self.sync()
        return self._comparison

    def apply_plot_preferences(self, theme: Theme, width: int) -> None:
        """Update an existing comparison page without constructing a hidden one."""

        if self._comparison is not None:
            self._comparison.area.apply_theme(theme)
            self._comparison.area.set_line_width(width)

    def sync(self) -> None:
        """Update the current-file summary without replacing a valid A/B presentation."""

        window = self.host
        files = tuple(
            {
                node.data_file.id: node.data_file
                for node in window.data_browser.browser_tree.windows
            }.values()
        )
        if self._comparison is not None:
            self._comparison.sync(files)
        loaded = window.loaded_measurement
        self.view_stack.setCurrentWidget(window.view_area if loaded is not None else self.empty)
        for button in (self.compare_button, self.export_button, self.auto_button):
            button.setEnabled(loaded is not None)
        self.table_button.setEnabled(bool(window.view_area.current_plot.traces))
        if loaded is None:
            self.summary.setText("尚未导入文件 · 支持 Touchstone / CITI")
        else:
            network = loaded.network
            self.summary.setText(
                f"{loaded.name} · {network.n_ports} 端口 · {network.n_freq} 点 · "
                f"{network.frequencies_hz[0] / 1e9:g}–"
                f"{network.frequencies_hz[-1] / 1e9:g} GHz · Z₀ {network.z0.real:g} Ω"
            )
            self.summary.setToolTip(str(loaded.path or loaded.name))
        self.axis.sync()
        viewing = self.tabs.currentIndex() == 0
        self.host.add_trace_action.setEnabled(loaded is not None and viewing)
        for action in self.host.layout_actions.values():
            action.setEnabled(viewing)
        self.host.file_flow.update_actions()
        if self.tabs.currentIndex() == 1:
            self.summary.setText("独立 A/B 视图 · 各自保留完整频率网格 · 选择文件后点击显示曲线")

    def open_comparison(self) -> None:
        """Send the currently viewed file to A; the user explicitly chooses B."""

        number = self.host.active_window
        if number is not None:
            item = self.host.data_browser.browser_tree.window(number).data_file
            self.comparison.select_a(item.id)
        self.tabs.setCurrentIndex(1)

    def _page_changed(self, index: int) -> None:
        window = self.host
        if index == 1:
            _comparison = self.comparison
            self._browser_visible = window.data_browser_dock.isVisibleTo(window)
            self._parameter_visible = window.parameter_format_dock.isVisibleTo(window)
            self._marker_visible = window.frequency_flow.dock.isVisibleTo(window)
            window.parameter_format_dock.hide()
            window.data_browser_dock.hide()
            window.frequency_flow.dock.hide()
            self.title.setText("S 参数文件比较")
        else:
            window.data_browser_dock.setVisible(self._browser_visible)
            window.parameter_format_dock.setVisible(self._parameter_visible)
            window.frequency_flow.dock.setVisible(self._marker_visible)
            self.title.setText("S 参数分析")
        self.sync()
        window.frequency_flow.sync()
        for dock in (window.data_browser_dock, window.parameter_format_dock):
            toggle = dock.toggleViewAction()
            if toggle is not None:
                toggle.setEnabled(index == 0)
