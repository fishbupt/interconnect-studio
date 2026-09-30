from pathlib import Path

import numpy as np
import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox
from pytestqt.qtbot import QtBot

from interconnect_studio.algorithms.mixed_mode import DEFAULT_FOUR_PORT_TOPOLOGY
from interconnect_studio.core import DataFormatError, Mode, ViewType
from interconnect_studio.io import ImportFileType, read_project, write_project
from interconnect_studio.services import ExportFileType, ImportedNetwork, ImportService
from interconnect_studio.ui import MainWindow
from interconnect_studio.ui.dialogs.export_dialog import ExportDialog
from interconnect_studio.ui.dialogs.file_operation_dialog import FileOperationDialog
from interconnect_studio.ui.panels.parameter_format import ParameterChoice
from interconnect_studio.ui.settings import (
    Preferences,
    SettingsStore,
    read_preferences,
    write_preferences,
)
from interconnect_studio.ui.task_runner import TaskRunner
from interconnect_studio.ui.theme import Theme

DATA = Path(__file__).parents[1] / "data"


def make_window(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def test_project_recall_keeps_multi_window_state_without_source_files(
    qtbot: QtBot, tmp_path: Path
) -> None:
    source = tmp_path / "channel.s2p"
    source.write_bytes((DATA / "touchstone/valid_2port_ri.s2p").read_bytes())
    window = make_window(qtbot)
    window.load_touchstone_file(source)
    window.set_grid(2, 2)
    window.view_area.set_current_index(3)
    window.new_plot(1, 0, "phase")
    window.plot_widget.plot_widget.setRange(xRange=(1e6, 2e6), yRange=(-180, 180), padding=0)
    window.open_view(ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED)
    window.new_plot(0, 0, "real")
    path = window.file_flow.save_project(tmp_path / "channel")
    source.unlink()
    assert not window.file_flow.dirty
    restored = make_window(qtbot)
    restored.file_flow.load_project(path)
    assert len(restored.data_browser.browser_tree.windows) == 2
    assert restored.active_window == 1
    assert restored.view_area.current_index == 0
    assert restored.view_area.layout_model.rows == 2
    assert restored.view_area.layout_model.plots[3].traces[0].name == "S21 Phase"
    bounds = restored.view_area.plot_widget_at(3).plot_widget.getViewBox().viewRange()
    np.testing.assert_allclose(bounds, [[1e6, 2e6], [-180, 180]])
    restored.show_window(2)
    assert restored.plot_widget.model.traces[0].name == "S11 Real"
    assert not restored.file_flow.dirty
    restored.load_touchstone_file(DATA / "import/three_port.s3p")
    ids = {node.data_file.id for node in restored.data_browser.browser_tree.windows}
    assert len(ids) == 2


def test_balanced_traces_and_dut_labels_survive_recall(qtbot: QtBot, tmp_path: Path) -> None:
    window = make_window(qtbot)
    network = ImportService().read(
        DATA / "import/4port.s4p",
        ImportFileType.TOUCHSTONE,
    )
    config = DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration().with_labels(
        ("TX+", "RX+", "TX-", "RX-")
    )
    window.open_imported(
        ImportedNetwork("pair", network, dut_configuration=config),
        ViewType.FREQUENCY_DOMAIN_BALANCED,
    )
    choice = ParameterChoice("SDD21", 1, 0, Mode.DIFFERENTIAL, Mode.DIFFERENTIAL)
    window.new_selected_plot(choice, "log_mag")
    before = window.plot_widget.model.traces[0].y.copy()
    path = window.file_flow.save_project(tmp_path / "pair.icproj")
    restored = make_window(qtbot)
    restored.file_flow.load_project(path)
    assert restored.loaded_measurement.dut_configuration == config
    np.testing.assert_array_equal(restored.plot_widget.model.traces[0].y, before)
    assert restored.parameter_format.is_mixed_mode


def test_bad_project_does_not_replace_current_workspace(qtbot: QtBot, tmp_path: Path) -> None:
    window = make_window(qtbot)
    window.load_touchstone_file(DATA / "touchstone/valid_2port_ri.s2p")
    before = window.loaded_measurement
    bad = tmp_path / "bad.icproj"
    bad.write_text("not a zip")
    with pytest.raises(DataFormatError):
        window.file_flow.load_project(bad)
    assert window.loaded_measurement is before
    assert window.file_flow.dirty


def test_close_all_cancel_leaves_all_windows(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    window = make_window(qtbot)
    window.load_touchstone_file(DATA / "touchstone/valid_2port_ri.s2p")
    window.load_touchstone_file(DATA / "import/three_port.s3p")
    calls = []

    def cancel(*_args: object) -> QMessageBox.StandardButton:
        calls.append(1)
        return QMessageBox.StandardButton.Cancel

    monkeypatch.setattr(QMessageBox, "question", cancel)
    window.file_flow.close_all()
    assert len(calls) == 1 and len(window.data_browser.browser_tree.windows) == 2
    monkeypatch.setattr(QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Discard)


def test_close_all_save_writes_all_files_once(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = make_window(qtbot)
    window.load_touchstone_file(DATA / "touchstone/valid_2port_ri.s2p")
    window.load_touchstone_file(DATA / "import/three_port.s3p")
    target = tmp_path / "both.icproj"
    monkeypatch.setattr(QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Save)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_args: (str(target), ""))
    window.file_flow.close_all()
    assert len(read_project(target).files) == 2
    assert not window.data_browser.browser_tree.windows
    assert not window.file_flow.dirty
    assert window.file_flow.project_path is None
    monkeypatch.setattr(QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Discard)


def test_recall_preserves_auto_scaling_for_new_traces(qtbot: QtBot, tmp_path: Path) -> None:
    window = make_window(qtbot)
    window.load_touchstone_file(DATA / "touchstone/valid_2port_ri.s2p")
    path = window.file_flow.save_project(tmp_path / "auto.icproj")
    restored = make_window(qtbot)
    restored.file_flow.load_project(path)
    assert all(restored.plot_widget.plot_widget.getViewBox().autoRangeEnabled())


def test_failed_save_keeps_dirty_workspace(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = make_window(qtbot)
    window.load_touchstone_file(DATA / "touchstone/valid_2port_ri.s2p")
    before = window.loaded_measurement
    monkeypatch.setattr(QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Save)
    monkeypatch.setattr(window.file_flow, "save_project_dialog", lambda: False)
    window.file_flow.close_all()
    assert window.loaded_measurement is before
    assert window.file_flow.dirty
    monkeypatch.setattr(QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Discard)


def test_recent_files_are_deduplicated_and_capped(tmp_path: Path) -> None:
    store = SettingsStore(QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat))
    for index in range(5):
        store.add_recent(tmp_path / f"{index}.s2p")
    store.add_recent(tmp_path / "2.s2p")
    assert [path.name for path in store.recent_files()] == ["2.s2p", "4.s2p", "3.s2p", "1.s2p"]
    store.clear_recent()
    assert store.recent_files() == ()


def test_missing_recent_file_is_removed(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = make_window(qtbot)
    missing = tmp_path / "gone.s2p"
    window.file_flow.settings.add_recent(missing)
    messages = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *_args: messages.append(_args))
    window.file_flow.open_recent(missing)
    assert window.file_flow.settings.recent_files() == ()
    assert messages and window.loaded_measurement is None


def test_recent_text_file_reopens_with_detected_delimiter(qtbot: QtBot) -> None:
    window = make_window(qtbot)
    window.file_flow.open_recent(DATA / "import/two_port_tab.txt")
    assert window.loaded_measurement.name == "two_port_tab.txt"


def test_preferences_roundtrip_and_new_window(qtbot: QtBot, tmp_path: Path) -> None:
    backend = QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat)
    store = SettingsStore(backend)
    preferences = Preferences(theme="dark", line_width=4, export_directory=str(tmp_path))
    window = MainWindow(settings=store)
    qtbot.addWidget(window)
    window.file_flow.apply_preferences(preferences)
    new = MainWindow(settings=store)
    qtbot.addWidget(new)
    assert new.theme is Theme.DARK
    assert new.file_flow.preferences.line_width == 4
    path = tmp_path / "engineering.icprefs"
    write_preferences(preferences, path)
    assert read_preferences(path) == preferences
    backend.setValue("preferences", "broken json")
    assert store.preferences() == Preferences()


def test_export_dialog_confirmation_uses_actual_suffix(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = ImportService().import_single(
        DATA / "import/2port.s2p",
        ImportFileType.TOUCHSTONE,
    )
    runner = TaskRunner()
    dialog = ExportDialog([source], runner)
    qtbot.addWidget(dialog)
    target = tmp_path / "existing.s2p"
    target.write_text("original")
    dialog.path_edit.setText(str(tmp_path / "existing.csv"))
    asked = []

    def refuse(*args: object) -> QMessageBox.StandardButton:
        asked.append(str(args[2]))
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", refuse)
    dialog._export()
    assert "existing.s2p" in asked[0]
    assert target.read_text() == "original" and dialog.exported_path is None


def test_export_browse_accepts_empty_path(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = ImportService().import_single(DATA / "import/2port.s2p", ImportFileType.TOUCHSTONE)
    dialog = ExportDialog([source], TaskRunner())
    qtbot.addWidget(dialog)
    dialog.path_edit.clear()
    selected = str(tmp_path / "channel.s2p")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_args: (selected, ""))
    dialog._browse()
    assert dialog.path_edit.text() == selected


def test_export_dialog_produces_selected_format_in_background(qtbot: QtBot, tmp_path: Path) -> None:
    from interconnect_studio.io import ImportFileType, read_touchstone2

    source = ImportService().import_single(DATA / "import/2port.s2p", ImportFileType.TOUCHSTONE)
    runner = TaskRunner()
    dialog = ExportDialog([source], runner, default_type=ExportFileType.TOUCHSTONE2)
    qtbot.addWidget(dialog)
    dialog.path_edit.setText(str(tmp_path / "channel"))
    dialog._export()
    assert dialog.result() == QDialog.DialogCode.Accepted
    result = read_touchstone2(dialog.exported_path)
    np.testing.assert_array_equal(result.s, source.network.s)
    assert runner.wait_for_done()


def test_operation_error_stays_visible_and_can_close(qtbot: QtBot) -> None:
    runner = TaskRunner()

    def fail() -> object:
        raise OSError("disk full")

    dialog = FileOperationDialog("Save", fail, runner)
    qtbot.addWidget(dialog)
    qtbot.waitUntil(lambda: bool(dialog.error))
    assert "disk full" in dialog.label.text()
    assert dialog.buttons.isEnabled()
    dialog.reject()
    assert dialog.result() == QDialog.DialogCode.Rejected
    assert runner.wait_for_done()


def test_project_replacement_cancel_preserves_old_workspace(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = make_window(qtbot)
    window.load_touchstone_file(DATA / "touchstone/valid_2port_ri.s2p")
    before = window.loaded_measurement
    path = tmp_path / "empty.icproj"
    from interconnect_studio.core import ProjectSnapshot

    write_project(ProjectSnapshot(), path)
    monkeypatch.setattr(QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Cancel)
    window.file_flow.open_recent(path)
    assert window.loaded_measurement is before
    monkeypatch.setattr(QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Discard)


def test_exit_cancel_ignores_close_event(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    from PyQt6.QtGui import QCloseEvent

    window = make_window(qtbot)
    window.load_touchstone_file(DATA / "touchstone/valid_2port_ri.s2p")
    monkeypatch.setattr(QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Cancel)
    event = QCloseEvent()
    window.closeEvent(event)
    assert not event.isAccepted()
    monkeypatch.setattr(QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Discard)
