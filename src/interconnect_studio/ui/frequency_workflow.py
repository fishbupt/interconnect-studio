"""Frequency-analysis UI orchestration; measured operations live in services."""

import logging
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QMenu,
    QMessageBox,
    QScrollArea,
)

from interconnect_studio.core import InputValidationError, PlotModel
from interconnect_studio.io.atomic import atomic_destination
from interconnect_studio.services.frequency_analysis import (
    add_marker,
    compare_trace,
    export_plot_csv,
    move_marker,
    remove_marker,
    rename_trace,
    reorder_trace,
    search_marker,
    set_delta,
    step_marker,
)
from interconnect_studio.ui.dialogs.file_operation_dialog import run_file_operation
from interconnect_studio.ui.dialogs.trace_data_dialog import TraceDataDialog
from interconnect_studio.ui.panels.frequency_panel import FrequencyPanel

if TYPE_CHECKING:
    from interconnect_studio.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class FrequencyWorkflow:
    """Operate on the selected plot and preserve state through the existing session path."""

    def __init__(self, window: "MainWindow") -> None:
        self.window = window
        self.panel = FrequencyPanel(window)
        self.dock = QDockWidget("频域分析 / Marker", window)
        self.dock.setObjectName("frequency_analysis_dock")
        scroll = QScrollArea(self.dock)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.panel)
        self.dock.setWidget(scroll)
        window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock.hide()
        self.panel.requested.connect(self._request)
        self.actions: dict[str, QAction] = {}
        menu = QMenu("频域分析", window)
        window.menu_bar.addMenu(menu)
        menu.addAction(self.dock.toggleViewAction())
        for name, label in (
            ("add_marker", "添加 Marker"),
            ("compare", "跨文件曲线对比…"),
            ("table", "曲线数据表…"),
            ("csv", "导出当前图全部曲线 CSV…"),
            ("image", "导出当前图 PNG…"),
            ("copy_image", "复制当前图到剪贴板"),
            ("autoscale", "当前图自动缩放"),
            ("autoscale_all", "当前窗口全部图自动缩放"),
        ):
            action = QAction(label, window)
            action.triggered.connect(lambda _checked=False, key=name: self._request(key, None))
            menu.addAction(action)
            self.actions[name] = action
        window.plot_state_changed.connect(self.sync)
        window.view_area.marker_moved.connect(self._dragged)
        self.sync()

    def sources(self) -> dict[str, str]:
        """Names for stable source IDs, including curves overlaid from other files."""

        return {
            node.data_file.id: node.data_file.name
            for node in self.window.data_browser.browser_tree.windows
        }

    def sync(self) -> None:
        """Refresh controls when the current file, window or plot changes."""

        plot = self.window.view_area.current_plot
        self.panel.sync(plot, self.sources())
        for name, action in self.actions.items():
            action.setEnabled(
                bool(plot.traces)
                if name not in {"autoscale_all", "compare"}
                else self.window.active_window is not None
            )

    def apply(self, plot: PlotModel) -> None:
        """Apply a validated model and mark the owning engineering workspace dirty."""

        loaded = self.window.loaded_measurement
        if loaded is None:
            raise InputValidationError("请先导入文件。")
        loaded = replace(loaded, plot=plot)
        self.window._loaded = loaded
        self.window._apply(loaded)
        self.window.file_flow.modified()

    def _request(self, action: str, _payload: object) -> None:
        try:
            self._execute(action)
        except (ValueError, OSError) as exc:
            logger.warning("Frequency operation %s failed: %s", action, exc)
            QMessageBox.warning(self.window, "频域分析", str(exc))

    def _execute(self, action: str) -> None:
        plot = self.window.view_area.current_plot
        index = self.panel.trace_combo.currentIndex()
        number = self.panel.marker_combo.currentData()
        if action == "rename":
            self.apply(rename_trace(plot, index, self.panel.rename_edit.text()))
        elif action == "delete_trace":
            self.apply(plot.remove_trace(index))
        elif action in {"up", "down"}:
            destination = min(max(index + (-1 if action == "up" else 1), 0), len(plot.traces) - 1)
            self.apply(reorder_trace(plot, index, destination))
            self.panel.trace_combo.setCurrentIndex(destination)
        elif action == "add_marker":
            if index < 0:
                raise InputValidationError("请先选择一条曲线。")
            span = self.window.plot_widget.plot_widget.getViewBox().viewRange()[0]
            self.apply(add_marker(plot, index, (span[0] + span[1]) / 2))
            self.panel.marker_combo.setCurrentIndex(self.panel.marker_combo.count() - 1)
            self.dock.show()
        elif action == "move":
            self.apply(move_marker(plot, number, float(self.panel.position_edit.text())))
        elif action in {"previous", "next"}:
            self.apply(step_marker(plot, number, -1 if action == "previous" else 1))
        elif action == "delta":
            self.apply(set_delta(plot, number, self.panel.reference_combo.currentData()))
        elif action == "delete_marker":
            self.apply(remove_marker(plot, number))
        elif action in {"min", "max", "target"}:
            bounds = self.window.plot_widget.plot_widget.getViewBox().viewRange()[0]
            span = (
                (float(bounds[0]), float(bounds[1]))
                if self.panel.visible_span.isChecked()
                else None
            )
            target = float(self.panel.target_edit.text()) if action == "target" else None
            if action == "min":
                result = search_marker(plot, number, "min", span=span)
            elif action == "max":
                result = search_marker(plot, number, "max", span=span)
            else:
                result = search_marker(plot, number, "target", target=target, span=span)
            self.apply(result)
        elif action == "compare":
            self._compare_dialog()
        elif action == "table":
            TraceDataDialog(plot, self.sources(), self.window).exec()
        elif action == "csv":
            self._export_csv()
        elif action == "image":
            self._export_image()
        elif action == "copy_image":
            clipboard = QApplication.clipboard()
            assert clipboard is not None
            clipboard.setImage(self.window.plot_widget.image())
        elif action in {"autoscale", "autoscale_all"}:
            area = self.window.view_area
            indices = (
                range(area.layout_model.n_cells)
                if action == "autoscale_all"
                else (area.current_index,)
            )
            for cell in indices:
                view = area.plot_widget_at(cell).plot_widget.getViewBox()
                view.autoRange()
                view.enableAutoRange(x=True, y=True)
            self.window.file_flow.modified()

    def _dragged(self, cell: int, number: int, x: float) -> None:
        self.window.view_area.set_current_index(cell)
        try:
            self.apply(move_marker(self.window.view_area.current_plot, number, x))
        except ValueError as exc:
            logger.warning("Marker move failed: %s", exc)

    def compare_from_window(self, number: int, trace_index: int) -> None:
        """Overlay a rendered source trace; requires matching geometry and axis format."""

        self.window._store_active_session()
        session = self.window._sessions.get(number)
        if session is None:
            raise InputValidationError("来源窗口已关闭。")
        source_plot = session.layout.plots[session.current_index]
        if not 0 <= trace_index < len(source_plot.traces):
            raise InputValidationError("来源曲线已删除。")
        current = self.window.view_area.current_plot
        if current.traces and (
            current.kind != source_plot.kind or current.y_label != source_plot.y_label
        ):
            raise InputValidationError("请选择相同显示格式的曲线进行对比。")
        node = self.window.data_browser.browser_tree.window(number)
        trace = source_plot.traces[trace_index]
        source_id = trace.source_id or node.data_file.id
        source_name = self.sources().get(source_id, node.data_file.name)
        if not current.traces:
            current = replace(
                current,
                kind=source_plot.kind,
                x_label=source_plot.x_label,
                y_label=source_plot.y_label,
            )
        self.apply(compare_trace(current, trace, source_id, source_name))

    def _compare_dialog(self) -> None:
        self.window._store_active_session()
        choices: dict[str, tuple[int, int]] = {}
        for number, session in self.window._sessions.items():
            if number == self.window.active_window:
                continue
            for index, trace in enumerate(session.layout.plots[session.current_index].traces):
                choices[f"窗口 {number} · {session.loaded.name} · {index + 1}: {trace.name}"] = (
                    number,
                    index,
                )
        if not choices:
            raise InputValidationError("请先在另一个文件窗口中添加要对比的曲线。")
        label, accepted = QInputDialog.getItem(
            self.window, "跨文件对比", "选择另一窗口当前格中的曲线", list(choices), 0, False
        )
        if accepted:
            self.compare_from_window(*choices[label])

    def _destination(self, title: str, suffix: str, filters: str) -> Path | None:
        initial = Path(self.window.file_flow.preferences.export_directory) / f"plot{suffix}"
        filename, _ = QFileDialog.getSaveFileName(self.window, title, str(initial), filters)
        if not filename:
            return None
        path = Path(filename).with_suffix(suffix)
        if (
            path.exists()
            and QMessageBox.question(self.window, "覆盖文件", f"{path.name} 已存在，是否覆盖？")
            != QMessageBox.StandardButton.Yes
        ):
            return None
        return path

    def _export_csv(self) -> None:
        target = self._destination("导出曲线数据", ".csv", "CSV (*.csv)")
        if target is None:
            return
        plot, sources = self.window.view_area.current_plot, self.sources()
        run_file_operation(
            "正在导出曲线数据",
            lambda: export_plot_csv(plot, target, sources),
            self.window.tasks,
            self.window,
        )
        self.window.status_bar.showMessage(f"已导出：{target}")

    def _export_image(self) -> None:
        width, accepted = QInputDialog.getInt(
            self.window, "图片分辨率", "宽度（像素，保持图形比例）", 1920, 320, 4096, 160
        )
        if not accepted:
            return
        target = self._destination("导出曲线图片", ".png", "PNG (*.png)")
        if target is None:
            return
        image = self.window.plot_widget.image(width)

        def write() -> None:
            with atomic_destination(target) as temporary:
                if not image.save(str(temporary), "PNG"):
                    raise OSError("无法保存图片，请检查输出目录。")

        run_file_operation("正在保存图片", write, self.window.tasks, self.window)
        self.window.status_bar.showMessage(f"已导出：{target}")
