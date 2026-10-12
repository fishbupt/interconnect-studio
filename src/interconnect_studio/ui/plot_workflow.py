"""Plot commands and menu bindings composed with the existing analysis view."""

from dataclasses import replace
from typing import TYPE_CHECKING

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QInputDialog, QMenu

from interconnect_studio.core import InputValidationError, PlotKind, PlotModel, ViewLayout
from interconnect_studio.services.plot_layout import (
    LayoutEdit,
    delete_plot,
    insert_plot,
    move_plot,
    renamed_plot,
)

if TYPE_CHECKING:
    from interconnect_studio.ui.main_window import MainWindow


class PlotWorkflow:
    """Remap view state with whole plots; marker indices remain inside their plot."""

    def __init__(self, window: "MainWindow") -> None:
        self.window = window
        self.actions: dict[str, QAction] = {}
        menu = QMenu("图管理", window)
        window.menu_bar.addMenu(menu)
        for key, label, callback in (
            ("new", "新增空图", self.new_empty),
            ("replace", "替换为当前参数", self.replace_selected),
            ("copy", "复制到新图", self.copy),
            ("rename", "重命名图…", self.rename_dialog),
            ("delete", "删除当前图", self.delete),
            ("clear", "清空全部图", self.clear),
            ("previous", "向前移动", lambda: self.move(-1)),
            ("next", "向后移动", lambda: self.move(1)),
            ("maximize", "放大当前图 / 恢复", lambda: window.view_area.toggle_maximized()),
        ):
            action = QAction(label, window)
            action.triggered.connect(lambda _checked=False, call=callback: window._guarded(call))
            menu.addAction(action)
            self.actions[key] = action
        window.plot_state_changed.connect(self.sync)
        self.sync()

    def sync(self) -> None:
        area = self.window.view_area
        for action in self.actions.values():
            action.setEnabled(self.window.active_window is not None)
        self.actions["previous"].setEnabled(
            self.window.active_window is not None and area.current_index > 0
        )
        self.actions["next"].setEnabled(
            self.window.active_window is not None
            and area.current_index < area.layout_model.n_cells - 1
        )

    def apply(self, edit: LayoutEdit) -> None:
        """Commit a validated edit and keep scales attached to their original plots."""

        window = self.window
        if window.active_window is None:
            raise InputValidationError("Open an analysis window before editing plots.")
        if any(plot.kind is not PlotKind.CARTESIAN for plot in edit.layout.plots):
            raise InputValidationError("This version can display Cartesian plots only.")
        window._store_active_session()
        session = window._sessions[window.active_window]
        ranges = tuple(session.plot_ranges[i] if i is not None else None for i in edit.origins)
        auto = tuple(
            session.plot_autorange[i] if i is not None else (True, True) for i in edit.origins
        )
        histories = tuple(session.display_ranges[i] if i is not None else {} for i in edit.origins)
        session = replace(
            session,
            layout=edit.layout,
            current_index=edit.current_index,
            plot_ranges=ranges,
            plot_autorange=auto,
            display_ranges=histories,
        )
        window._restore_session(session)
        window.file_flow.modified()

    def insert(self, plot: PlotModel) -> None:
        area = self.window.view_area
        self.apply(insert_plot(area.layout_model, area.current_index, plot))

    def new_empty(self) -> None:
        """Named empty plots are real collection members, unlike spare grid cells."""

        self.insert(PlotModel(title="新图"))

    def delete(self) -> None:
        area = self.window.view_area
        self.apply(delete_plot(area.layout_model, area.current_index))

    def clear(self) -> None:
        area = self.window.view_area
        layout = ViewLayout(area.layout_model.rows, area.layout_model.cols)
        self.apply(LayoutEdit(layout, 0, (None,) * layout.n_cells))

    def copy(self) -> None:
        area = self.window.view_area
        plot = replace(area.current_plot)
        edit = insert_plot(area.layout_model, area.current_index, plot)
        # Copy scale and display history as well as traces and markers.
        origins = list(edit.origins)
        origins[edit.current_index] = area.current_index
        self.apply(replace(edit, origins=tuple(origins)))

    def rename(self, title: str) -> None:
        area = self.window.view_area
        plot = renamed_plot(area.current_plot, title)
        row, col = divmod(area.current_index, area.layout_model.cols)
        layout = area.layout_model.with_plot(row, col, plot)
        self.apply(LayoutEdit(layout, area.current_index, tuple(range(layout.n_cells))))

    def rename_dialog(self) -> None:
        name, accepted = QInputDialog.getText(
            self.window,
            "重命名图",
            "图名（1–22 字符）",
            text=self.window.view_area.current_plot.title,
        )
        if accepted:
            self.rename(name)

    def move(self, offset: int) -> None:
        area = self.window.view_area
        self.apply(move_plot(area.layout_model, area.current_index, area.current_index + offset))

    def reorder(self, source: int, destination: int) -> None:
        self.window._guarded(
            lambda: self.apply(move_plot(self.window.view_area.layout_model, source, destination))
        )

    def replace_selected(self) -> None:
        """Replace explicitly; compute the requested parameter before changing the view."""

        window = self.window
        choice = window.parameter_format.selected_choice()
        fmt = window.parameter_format.selected_format()
        if choice is None or fmt is None or window.loaded_measurement is None:
            raise InputValidationError("Select a parameter and format first.")
        empty = replace(window.loaded_measurement, plot=PlotModel())
        if choice.is_mixed_mode:
            assert choice.response_mode is not None and choice.source_mode is not None
            update = window._service.add_mixed_mode_trace(
                empty,
                choice.response_mode,
                choice.source_mode,
                choice.response_port,
                choice.source_port,
                fmt,
            )
        else:
            update = window._service.add_trace(empty, choice.response_port, choice.source_port, fmt)
        window._after_trace_update(update)
