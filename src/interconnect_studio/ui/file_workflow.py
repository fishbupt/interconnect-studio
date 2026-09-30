"""File menus and workspace lifecycle, composed with MainWindow."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import QByteArray
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDialog, QFileDialog, QLabel, QMenu, QMessageBox

from interconnect_studio.core import (
    DataBrowserTree,
    InputValidationError,
    PlotKind,
    ViewWindow,
)
from interconnect_studio.core.project import ProjectFile, ProjectSnapshot, ProjectWindow
from interconnect_studio.io.importing import detect_file_type
from interconnect_studio.io.project_file import PROJECT_SUFFIX, read_project, write_project
from interconnect_studio.io.touchstone import TouchstoneFrequencyUnit
from interconnect_studio.services import ImportedNetwork, LoadedTouchstonePlot
from interconnect_studio.services.export_service import ExportFileType
from interconnect_studio.ui.dialogs.export_dialog import ExportDialog
from interconnect_studio.ui.dialogs.file_operation_dialog import FileOperationDialog
from interconnect_studio.ui.dialogs.preferences_dialog import PreferencesDialog
from interconnect_studio.ui.models.data_browser_model import DEFAULT_AVAILABLE_VIEW_TYPES
from interconnect_studio.ui.settings import Preferences, SettingsStore
from interconnect_studio.ui.theme import Theme
from interconnect_studio.ui.window_session import WindowSession

if TYPE_CHECKING:
    from interconnect_studio.ui.main_window import MainWindow


class FileWorkflow:
    """Track dirty workspace state and coordinate file services with UI feedback."""

    export_action: QAction
    close_file_action: QAction
    close_all_action: QAction

    def __init__(self, window: "MainWindow", settings: SettingsStore | None = None) -> None:
        self.window = window
        self.settings = settings or SettingsStore()
        self.project_path: Path | None = None
        self.dirty = False
        self._dirty_files: set[str] = set()
        self._restoring = False
        self.status = QLabel("工程未创建", window)
        window.status_bar.addPermanentWidget(self.status)
        self.preferences = self.settings.preferences()
        self._build_menu()
        self.apply_preferences(self.preferences)
        if self.preferences.remember_layout:
            for key, restore in (
                ("geometry", window.restoreGeometry),
                ("dock_state", window.restoreState),
            ):
                value = self.settings.backend.value(key)
                if isinstance(value, QByteArray):
                    restore(value)
        self.refresh_recent()
        self.update_actions()

    def _build_menu(self) -> None:
        window = self.window
        menu = window.file_menu
        first = menu.actions()[0]
        specifications = (
            ("new_project_action", "新建工程", "Ctrl+N", self.new_project),
            ("open_project_action", "打开工程…", "Ctrl+Shift+O", self.open_project_dialog),
            ("save_project_action", "保存工程", "Ctrl+S", self.save_project_dialog),
            ("save_project_as_action", "工程另存为…", "Ctrl+Shift+S", self.save_project_as),
            ("export_action", "导出数据…", "Ctrl+E", self.export_dialog),
            ("close_file_action", "关闭当前文件", "", self.close_current_file),
            ("close_all_action", "关闭所有文件", "", self.close_all),
        )
        for attribute, text, shortcut, callback in specifications:
            action = QAction(text, window)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(callback)
            menu.insertAction(first, action)
            setattr(self, attribute, action)
        menu.insertSeparator(first)
        self.recent_menu = QMenu("最近文件", window)
        menu.addMenu(self.recent_menu)
        tools_menu = QMenu("设置", window)
        window.menu_bar.addMenu(tools_menu)
        preferences_action = QAction("常用设置…", window)
        preferences_action.triggered.connect(self.show_preferences)
        tools_menu.addAction(preferences_action)

    def modified(self, file_id: str | None = None) -> None:
        """Mark a successful data/view change; selection and global settings do not."""

        if self._restoring:
            return
        self.dirty = True
        active = self.window.active_window
        if file_id is None and active is not None:
            file_id = self.window.data_browser.browser_tree.window(active).data_file.id
        if file_id is not None:
            self._dirty_files.add(file_id)
        self.update_actions()

    def imported(self, imported: ImportedNetwork) -> None:
        """Remember successful imports, never failed or cancelled attempts."""

        if imported.source_path is not None:
            self.settings.add_recent(imported.source_path)
            self.refresh_recent()
            self.preferences = replace(
                self.preferences, import_directory=str(imported.source_path.resolve().parent)
            )
            self.settings.save_preferences(self.preferences)
        self.modified()

    def update_actions(self) -> None:
        """Keep menu availability and the project status synchronized."""

        has_data = bool(self.window.data_browser.browser_tree.windows)
        self.export_action.setEnabled(has_data)
        self.close_file_action.setEnabled(has_data)
        self.close_all_action.setEnabled(has_data)
        name = self.project_path.name if self.project_path else "未命名工程"
        self.status.setText(f"{name}{' *' if self.dirty else ''}")

    def snapshot(self) -> ProjectSnapshot:
        """Capture a Qt-free immutable snapshot before starting background IO."""

        window = self.window
        window._store_active_session()
        files: dict[str, ProjectFile] = {}
        windows: list[ProjectWindow] = []
        for node in window.data_browser.browser_tree.windows:
            session = window._sessions[node.number]
            files[node.data_file.id] = ProjectFile(node.data_file, session.loaded.dut_configuration)
            windows.append(
                ProjectWindow(
                    number=node.number,
                    file_id=node.data_file.id,
                    view_type=node.view_type,
                    layout=session.layout,
                    template=session.template,
                    plot_ranges=session.plot_ranges,
                    plot_autorange=session.plot_autorange,
                )
            )
        return ProjectSnapshot(
            files=tuple(files.values()),
            windows=tuple(windows),
            geometry=window.saveGeometry().data(),
            dock_state=window.saveState().data(),
        )

    def restore(self, snapshot: ProjectSnapshot, path: Path) -> None:
        """Apply validated state in one step; unsupported plots never replace a workspace."""

        for saved in snapshot.windows:
            if saved.view_type not in DEFAULT_AVAILABLE_VIEW_TYPES:
                raise InputValidationError(f"Unsupported project view: {saved.view_type.label}.")
            if any(plot.kind is not PlotKind.CARTESIAN for plot in saved.layout.plots):
                raise InputValidationError("This version can recall Cartesian plots only.")
        files = {item.data_file.id: item for item in snapshot.files}
        sessions: dict[int, WindowSession] = {}
        nodes: list[ViewWindow] = []
        for saved in snapshot.windows:
            item = files[saved.file_id]
            data = item.data_file
            loaded = LoadedTouchstonePlot(
                name=data.name,
                network=data.network,
                plot=saved.layout.plots[0],
                path=data.source_path,
                dut_configuration=item.dut_configuration,
            )
            sessions[saved.number] = WindowSession(
                saved.number,
                saved.view_type,
                loaded,
                saved.layout,
                template=saved.template,
                plot_ranges=saved.plot_ranges,
                plot_autorange=saved.plot_autorange,
            )
            nodes.append(ViewWindow(saved.view_type, data, saved.number, saved.template))
        tree = DataBrowserTree(tuple(nodes))
        self._restoring = True
        try:
            window = self.window
            window._active_window = None
            window._loaded = None
            window._sessions = sessions
            window.data_browser.set_browser_tree(tree)
            ids = set(files)
            window._next_file_number = 1
            while f"file-{window._next_file_number}" in ids:
                window._next_file_number += 1
            if sessions:
                first = next(iter(sessions.values()))
                window._restore_session(first)
                window.data_browser.select_window(first.number)
            else:
                window._clear_view()
            if snapshot.geometry:
                window.restoreGeometry(QByteArray(snapshot.geometry))
            if snapshot.dock_state:
                window.restoreState(QByteArray(snapshot.dock_state))
        finally:
            self._restoring = False
        self._saved(path)
        self.window._log(f"打开工程：{path}")

    def _saved(self, path: Path) -> None:
        self.project_path = path.resolve()
        self.dirty = False
        self._dirty_files.clear()
        self.settings.add_recent(self.project_path)
        self.refresh_recent()
        self.update_actions()

    def save_project(self, path: Path) -> Path:
        """Synchronous API for scripts/tests; menu actions use background IO."""

        target = path.with_suffix(PROJECT_SUFFIX)
        write_project(self.snapshot(), target)
        self._saved(target)
        return target

    def load_project(self, path: Path) -> None:
        """Synchronous validated recall API; caller owns unsaved-change handling."""

        self.restore(read_project(path), path)

    def _operation(self, title: str, work: Callable[[], object]) -> FileOperationDialog:
        operation = FileOperationDialog(title, work, self.window.tasks, self.window)
        operation.exec()
        if operation.error:
            self.window._log(f"{title}失败：{operation.error}")
        return operation

    def save_project_dialog(self) -> bool:
        """Save or request a destination; report success to unsaved-change prompts."""

        if self.project_path is None:
            return self.save_project_as()
        return self._save_to(self.project_path)

    def save_project_as(self) -> bool:
        """Choose a project path, confirming the actual suffixed destination."""

        filename, _ = QFileDialog.getSaveFileName(
            self.window,
            "工程另存为",
            str(self.project_path or Path(self.preferences.export_directory) / "工程.icproj"),
            "Project (*.icproj)",
        )
        if not filename:
            return False
        target = Path(filename).with_suffix(PROJECT_SUFFIX)
        if (
            target.exists()
            and QMessageBox.question(self.window, "覆盖工程", f"{target.name} 已存在，是否覆盖？")
            != QMessageBox.StandardButton.Yes
        ):
            return False
        return self._save_to(target)

    def _save_to(self, target: Path) -> bool:
        snapshot = self.snapshot()
        operation = self._operation("正在保存工程", lambda: write_project(snapshot, target))
        if operation.result() != QDialog.DialogCode.Accepted:
            return False
        self._saved(target)
        self.window._log(f"已保存工程：{target}")
        return True

    def confirm_discard(self) -> bool:
        """Save/Discard/Cancel for workspace replacement, closure or application exit."""

        if not self.dirty:
            return True
        answer = QMessageBox.question(
            self.window,
            "未保存的工程",
            "工程包含未保存的数据或视图修改，是否保存？",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project_dialog()
        return answer == QMessageBox.StandardButton.Discard

    def open_project_dialog(self) -> None:
        """Select a project without touching the workspace on cancel."""

        filename, _ = QFileDialog.getOpenFileName(
            self.window, "打开工程", self.preferences.import_directory, "Project (*.icproj)"
        )
        if filename:
            self.open_recent(Path(filename))

    def open_recent(self, path: Path) -> None:
        """Open a project or measurement; stale history is removed with an explanation."""

        if not path.is_file():
            self.settings.remove_recent(path)
            self.refresh_recent()
            QMessageBox.warning(self.window, "打开失败", f"文件不存在：{path}")
            return
        if path.suffix.lower() == PROJECT_SUFFIX:
            # Read/validate before offering to discard an existing workspace.
            operation = self._operation("正在读取工程", lambda: read_project(path))
            if operation.result() == QDialog.DialogCode.Accepted and self.confirm_discard():
                assert isinstance(operation.result_value, ProjectSnapshot)
                try:
                    self.restore(operation.result_value, path)
                except ValueError as exc:
                    QMessageBox.warning(self.window, "打开失败", str(exc))
        else:
            service = self.window._import_service
            operation = self._operation(
                "正在读取数据",
                lambda: service.import_single(path, detect_file_type(path)),
            )
            if operation.result() == QDialog.DialogCode.Accepted:
                assert isinstance(operation.result_value, ImportedNetwork)
                self.window.open_imported(operation.result_value)

    def refresh_recent(self) -> None:
        """Rebuild the four-entry menu with full paths in tooltips."""

        self.recent_menu.clear()
        for index, path in enumerate(self.settings.recent_files()):
            action = QAction(f"&{index + 1} {path.name}", self.window)
            self.recent_menu.addAction(action)
            action.setToolTip(str(path))
            action.triggered.connect(
                lambda _checked=False, selected=path: self.open_recent(selected)
            )
        self.recent_menu.addSeparator()
        clear = QAction("清空最近文件", self.window)
        self.recent_menu.addAction(clear)
        clear.triggered.connect(self.clear_recent)

    def clear_recent(self) -> None:
        """Clear menu history without touching measurements."""

        self.settings.clear_recent()
        self.refresh_recent()

    def new_project(self) -> None:
        """Start an empty workspace after handling unsaved changes once."""

        if not self.confirm_discard():
            return
        self.window._sessions.clear()
        self.window.data_browser.set_browser_tree(DataBrowserTree())
        self.window._clear_view()
        self.window._next_file_number = 1
        self.project_path = None
        self.dirty = False
        self._dirty_files.clear()
        self.update_actions()

    def close_all(self) -> None:
        """Batch close with a single Save/Discard/Cancel decision for all files."""

        if not self.confirm_discard():
            return
        self.window._sessions.clear()
        self.window.data_browser.set_browser_tree(DataBrowserTree())
        self.window._clear_view()
        self._dirty_files.clear()
        # End this project session; do not overwrite the saved project with
        # an empty workspace in a second exit prompt.
        self.project_path = None
        self.dirty = False
        self.update_actions()

    def request_close_file(self, file_id: str) -> None:
        """Protect unsaved data when a file is closed from the browser/menu."""

        if file_id in self._dirty_files and not self.confirm_discard():
            return
        self.window.close_file(file_id)
        self._dirty_files.discard(file_id)
        if not self.window.data_browser.browser_tree.windows:
            self.project_path = None
            self.dirty = False
        self.update_actions()

    def request_close_view(self, number: int) -> None:
        """Closing the last view of unsaved data uses the same save decision."""

        tree = self.window.data_browser.browser_tree
        file_id = tree.window(number).data_file.id
        if len(tree.windows_of_file(file_id)) == 1:
            self.request_close_file(file_id)
        else:
            self.window.close_view(number)

    def close_current_file(self) -> None:
        """Close the data file behind the current view."""

        number = self.window.active_window
        if number is not None:
            self.request_close_file(
                self.window.data_browser.browser_tree.window(number).data_file.id
            )

    def export_dialog(self) -> None:
        """Export any open data file with current-file selection first."""

        snapshot = self.snapshot()
        files = list(snapshot.files)
        number = self.window.active_window
        if number is not None:
            active_id = self.window.data_browser.browser_tree.window(number).data_file.id
            files.sort(key=lambda item: item.data_file.id != active_id)
        sources = [
            ImportedNetwork(
                item.data_file.name,
                item.data_file.network,
                item.data_file.source_path,
                item.dut_configuration,
            )
            for item in files
        ]
        dialog = ExportDialog(
            sources,
            self.window.tasks,
            self.window,
            directory=self.preferences.export_directory,
            default_type=ExportFileType(self.preferences.export_type),
            default_unit=cast(TouchstoneFrequencyUnit, self.preferences.frequency_unit),
        )
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.exported_path is not None:
            self.preferences = replace(
                self.preferences, export_directory=str(dialog.exported_path.parent)
            )
            self.settings.save_preferences(self.preferences)
            self.window._log(f"已导出：{dialog.exported_path}")

    def apply_preferences(self, preferences: Preferences) -> None:
        """Apply and persist common defaults without marking measurement data dirty."""

        self.preferences = preferences
        self.settings.save_preferences(preferences)
        self.window.set_theme(Theme(preferences.theme))
        self.window.dark_theme_action.blockSignals(True)
        self.window.dark_theme_action.setChecked(preferences.theme == Theme.DARK.value)
        self.window.dark_theme_action.blockSignals(False)
        self.window.view_area.set_line_width(preferences.line_width)

    def show_preferences(self) -> None:
        """Edit settings, applying only an accepted dialog."""

        dialog = PreferencesDialog(self.preferences, self.window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.apply_preferences(dialog.preferences())

    def persist_layout(self) -> None:
        """Save shell geometry/docks on an accepted exit."""

        if self.preferences.remember_layout:
            self.settings.backend.setValue("geometry", self.window.saveGeometry())
            self.settings.backend.setValue("dock_state", self.window.saveState())
        else:
            self.settings.backend.remove("geometry")
            self.settings.backend.remove("dock_state")
        self.settings.backend.sync()
