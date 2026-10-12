"""Multiple analysis windows, activation routing and Window menu commands."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QAction, QCloseEvent, QShowEvent
from PyQt6.QtWidgets import QMainWindow, QMdiArea, QMdiSubWindow, QMenu, QToolBar, QWidget

from interconnect_studio.ui.views import PlotViewArea

if TYPE_CHECKING:
    from interconnect_studio.ui.main_window import MainWindow
    from interconnect_studio.ui.window_session import WindowSession


WINDOW_FLAGS = (
    Qt.WindowType.WindowTitleHint
    | Qt.WindowType.WindowSystemMenuHint
    | Qt.WindowType.WindowMinMaxButtonsHint
    | Qt.WindowType.WindowCloseButtonHint
)


class FloatingAnalysisWindow(QMainWindow):
    """Owned desktop frame with native controls and an explicit dock action."""

    def __init__(self, frame: "AnalysisWindow") -> None:
        super().__init__(frame.workflow.host, Qt.WindowType.Window | WINDOW_FLAGS)
        self.frame = frame
        self.setMinimumSize(280, 220)
        toolbar = QToolBar("Window", self)
        toolbar.setMovable(False)
        dock = QAction("停靠回工作区", self)
        dock.triggered.connect(lambda: frame.workflow.toggle_floating(frame.number))
        toolbar.addAction(dock)
        self.addToolBar(toolbar)

    def closeEvent(self, event: QCloseEvent | None) -> None:  # noqa: N802
        if event is not None:
            event.ignore()
            if not self.frame.workflow.updating:
                self.frame.workflow.host.file_flow.request_close_view(self.frame.number)

    def event(self, event: QEvent | None) -> bool:
        if (
            event is not None
            and event.type() == QEvent.Type.WindowActivate
            and hasattr(self, "frame")
            and not self.isMinimized()
            and self.frame.workflow.windows.get(self.frame.number) is self.frame
            and not self.frame.workflow.updating
        ):
            self.frame.workflow.activate(self.frame.number)
        return super().event(event)


class AnalysisWindow(QMdiSubWindow):
    """Resizable analysis frame that can leave and rejoin the MDI workspace."""

    def __init__(self, number: int, workflow: "WindowWorkflow", area: PlotViewArea) -> None:
        super().__init__()
        self.number = number
        self.workflow = workflow
        self.area = area
        self.floating = False
        self.floating_host: FloatingAnalysisWindow | None = None
        self.setWindowFlags(Qt.WindowType.SubWindow | WINDOW_FLAGS)
        self.setWidget(area)
        self.setMinimumSize(280, 220)
        self.resize(720, 520)
        self.dock_action = QAction("浮动窗口", self)
        self.dock_action.triggered.connect(lambda: workflow.toggle_floating(self.number))
        menu = self.systemMenu()
        if menu is not None:
            menu.addSeparator()
            menu.addAction(self.dock_action)

    def closeEvent(self, event: QCloseEvent | None) -> None:  # noqa: N802
        if event is not None:
            event.ignore()
            if not self.workflow.updating and self.number in self.workflow.windows:
                self.workflow.host.file_flow.request_close_view(self.number)

    @property
    def surface(self) -> QWidget:
        """Visible frame on the desktop or in the MDI workspace."""

        return self.floating_host or self

    def showEvent(self, event: QShowEvent | None) -> None:  # noqa: N802
        super().showEvent(event)
        self.workflow.sync()


class WindowWorkflow:
    """Own one plot view per window; commands always target its stable window number."""

    def __init__(self, host: "MainWindow", mdi: QMdiArea) -> None:
        self.host = host
        self.mdi = mdi
        self.windows: dict[int, AnalysisWindow] = {}
        self.updating = False
        self.actions: dict[str, QAction] = {}
        self.window_actions: dict[int, QAction] = {}
        self.menu = QMenu("&Window", host)
        host.menu_bar.addMenu(self.menu)
        for key, label, callback in (
            ("cascade", "Cascade（层叠）", lambda: self.arrange("cascade")),
            ("tile", "Tile（平铺）", lambda: self.arrange("tile")),
            ("maximize", "最大化当前窗口", lambda: self.state("maximize")),
            ("minimize", "最小化当前窗口", lambda: self.state("minimize")),
            ("restore", "还原当前窗口", lambda: self.state("restore")),
            ("float", "浮动 / 停靠当前窗口", self.toggle_active_floating),
            ("close", "关闭当前窗口", self.close_active),
        ):
            action = QAction(label, host)
            action.triggered.connect(callback)
            self.menu.addAction(action)
            self.actions[key] = action
        self.actions["close"].setShortcut("Ctrl+F4")
        separator = self.menu.addSeparator()
        assert separator is not None
        self.list_separator: QAction = separator
        self.menu.aboutToShow.connect(self.sync)
        mdi.setOption(QMdiArea.AreaOption.DontMaximizeSubWindowOnActivation, True)
        mdi.subWindowActivated.connect(self._activated)
        host.plot_state_changed.connect(self.sync)
        self.sync()

    @contextmanager
    def batch(self) -> Iterator[None]:
        """Suppress activation callbacks while adding/removing/reparenting frames."""

        previous = self.updating
        self.updating = True
        try:
            yield
        finally:
            self.updating = previous

    def ensure(self, session: "WindowSession") -> PlotViewArea:
        """Create the frame lazily and render an updated session without activating it."""

        frame = self.windows.get(session.number)
        with self.batch():
            if frame is None:
                area = PlotViewArea(theme=self.host.theme)
                area.set_line_width(self.host.file_flow.preferences.line_width)
                frame = AnalysisWindow(session.number, self, area)
                self.windows[session.number] = frame
                self.mdi.addSubWindow(frame)
                area.current_index_changed.connect(
                    lambda index, number=session.number: self._cell_changed(number, index)
                )
                area.plot_range_changed.connect(
                    lambda number=session.number: self._range_changed(number)
                )
                area.marker_moved.connect(
                    lambda cell, marker, x, number=session.number: self._marker_moved(
                        number, cell, marker, x
                    )
                )
                area.reorder_requested.connect(
                    lambda origin, target, number=session.number: self._reorder(
                        number, origin, target
                    )
                )
                frame.show()
            area = frame.area
            frame.setWindowTitle(session.title)
            layout = area.layout_model
            same_layout = (
                layout.rows == session.layout.rows
                and layout.cols == session.layout.cols
                and all(a is b for a, b in zip(layout.plots, session.layout.plots, strict=False))
            )
            if not same_layout:
                area.set_layout_model(session.layout)
                for index in range(session.layout.n_cells):
                    history = (
                        session.display_ranges[index] if index < len(session.display_ranges) else {}
                    )
                    area.plot_widget_at(index).restore_display_ranges(history)
                area.restore_plot_ranges(session.plot_ranges, session.plot_autorange)
            area.set_current_index(session.current_index)
        return area

    def present(self, number: int, restore_minimized: bool = True) -> None:
        """Raise a frame, preserving normal/maximized state unless it was minimized."""

        frame = self.windows[number]
        surface = frame.surface
        with self.batch():
            if restore_minimized and surface.isMinimized():
                surface.showNormal()
            if frame.floating:
                surface.show()
                surface.raise_()
                surface.activateWindow()
            else:
                self.mdi.setActiveSubWindow(frame)
        self.sync()

    def activate(self, number: int) -> None:
        """Route mouse/native/menu activation into the same browser and command context."""

        if number not in self.host._sessions:
            return
        self.host.show_window(number)
        self.host.data_browser.select_window(number)
        self.sync()

    def _activated(self, frame: QMdiSubWindow | None) -> None:
        if not self.updating and isinstance(frame, AnalysisWindow) and not frame.isMinimized():
            self.activate(frame.number)

    def _cell_changed(self, number: int, index: int) -> None:
        if not self.updating:
            self.activate(number)
            self.host._on_cell_changed(index)

    def _range_changed(self, number: int) -> None:
        if not self.updating and number in self.host._sessions:
            owner = self.host.data_browser.browser_tree.window(number).data_file.id
            self.host.file_flow.modified(owner)

    def _marker_moved(self, number: int, cell: int, marker: int, x: float) -> None:
        self.activate(number)
        self.host.frequency_flow._dragged(cell, marker, x)

    def _reorder(self, number: int, origin: int, target: int) -> None:
        self.activate(number)
        self.host._guarded(lambda: self.host.plot_flow.reorder(origin, target))

    def capture(self) -> None:
        """Snapshot every live window, including inactive or floating windows."""

        for number, frame in self.windows.items():
            session = self.host._sessions.get(number)
            if session is None:
                continue
            area = frame.area
            loaded = (
                self.host._loaded if self.host.active_window == number else session.loaded
            ) or session.loaded
            self.host._sessions[number] = replace(
                session,
                loaded=loaded,
                layout=area.layout_model,
                current_index=area.current_index,
                plot_ranges=area.plot_ranges(),
                plot_autorange=area.plot_autorange(),
                display_ranges=tuple(
                    area.plot_widget_at(index).display_ranges()
                    for index in range(area.layout_model.n_cells)
                ),
            )

    def reconcile(self) -> None:
        """Remove closed frames and update all surviving layouts after source cleanup."""

        with self.batch():
            for number in tuple(self.windows):
                if number not in self.host._sessions:
                    self.remove(number)
            for session in self.host._sessions.values():
                self.ensure(session)
        self.sync()

    def remove(self, number: int) -> None:
        frame = self.windows.pop(number)
        with self.batch():
            frame.surface.hide()
            if frame.floating_host is not None:
                frame.floating_host.takeCentralWidget()
                frame.setWidget(frame.area)
                frame.floating_host.deleteLater()
                frame.floating_host = None
            if not frame.floating:
                self.mdi.removeSubWindow(frame)
            # Retain ownership during deferred deletion and application teardown.
            frame.setParent(self.host)
            frame.deleteLater()

    def reset(self) -> None:
        """Dispose old frames before project replacement or application shutdown."""

        with self.batch():
            for number in tuple(self.windows):
                self.remove(number)
        self.sync()

    def toggle_active_floating(self) -> None:
        number = self.host.active_window
        if number is not None:
            self.toggle_floating(number)

    def toggle_floating(self, number: int) -> None:
        """Move the existing canvas between its MDI frame and an owned desktop frame."""

        frame = self.windows[number]
        surface = frame.surface
        normal_size = surface.normalGeometry().size() if surface.isMaximized() else surface.size()
        with self.batch():
            surface.showNormal()
            if frame.floating:
                assert frame.floating_host is not None
                frame.floating_host.hide()
                frame.floating_host.takeCentralWidget()
                frame.setWidget(frame.area)
                frame.floating_host.deleteLater()
                frame.floating_host = None
                frame.floating = False
                self.mdi.addSubWindow(frame)
                frame.dock_action.setText("浮动窗口")
            else:
                position = frame.mapToGlobal(frame.rect().topLeft())
                frame.hide()
                self.mdi.removeSubWindow(frame)
                frame.setParent(self.host)
                floating = FloatingAnalysisWindow(frame)
                floating.setWindowTitle(frame.windowTitle())
                frame.setWidget(None)
                floating.setCentralWidget(frame.area)
                frame.floating_host = floating
                frame.floating = True
                floating.move(position)
                frame.dock_action.setText("停靠回工作区")
            frame.surface.resize(normal_size)
            frame.surface.show()
        self.activate(number)
        self.present(number)

    def arrange(self, kind: str) -> None:
        """Arrange all windows; floating/minimized frames rejoin the workspace first."""

        active = self.host.active_window
        with self.batch():
            for number, frame in self.windows.items():
                if frame.floating:
                    self.toggle_floating(number)
                frame.showNormal()
            if kind == "cascade":
                self.mdi.cascadeSubWindows()
            else:
                self.mdi.tileSubWindows()
        if active in self.windows:
            self.activate(active)
            self.present(active)
        self.sync()

    def state(self, kind: str) -> None:
        number = self.host.active_window
        if number is not None:
            frame = self.windows[number].surface
            with self.batch():
                if kind == "maximize":
                    frame.showMaximized()
                elif kind == "minimize":
                    frame.showMinimized()
                else:
                    frame.showNormal()
            self.sync()

    def close_active(self) -> None:
        number = self.host.active_window
        if number is not None:
            self.host.file_flow.request_close_view(number)

    def sync(self) -> None:
        """Refresh command availability, window titles and the checked active entry."""

        active = self.host.active_window
        for key, action in self.actions.items():
            action.setEnabled(
                bool(self.windows) if key in {"cascade", "tile"} else active in self.windows
            )
        for action in self.window_actions.values():
            self.menu.removeAction(action)
            action.deleteLater()
        self.window_actions.clear()
        for number, session in self.host._sessions.items():
            frame = self.windows.get(number)
            if frame is not None:
                frame.setWindowTitle(session.title)
                frame.surface.setWindowTitle(session.title)
            label = session.title.replace("&", "&&")
            action = QAction(label, self.menu)
            action.setCheckable(True)
            action.setChecked(number == active)
            action.triggered.connect(lambda _checked=False, selected=number: self._select(selected))
            self.menu.addAction(action)
            self.window_actions[number] = action
        self.list_separator.setVisible(bool(self.window_actions))

    def _select(self, number: int) -> None:
        self.activate(number)
        self.present(number)
