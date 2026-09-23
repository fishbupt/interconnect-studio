from datetime import datetime

import numpy as np
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QInputDialog
from pytestqt.qtbot import QtBot

from interconnect_studio.core import DataBrowserTree, DataFile, Network, ViewType
from interconnect_studio.ui.panels import DataBrowserPanel


def data_file(file_id: str, name: str) -> DataFile:
    network = Network(
        frequencies_hz=np.array([1.0e9]),
        s=np.zeros((1, 1, 1), dtype=np.complex128),
        z0=50.0,
    )
    return DataFile(
        id=file_id, name=name, network=network, source_path=None, imported_at=datetime(2026, 1, 1)
    )


def panel_with_window(qtbot: QtBot) -> DataBrowserPanel:
    panel = DataBrowserPanel()
    qtbot.addWidget(panel)
    tree, _ = DataBrowserTree().open(
        ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED, data_file("file-1", "dut.s1p")
    )
    panel.set_browser_tree(tree)
    return panel


def action(panel: DataBrowserPanel, object_name: str) -> QAction:
    menu = panel.window_menu(panel.browser_tree.window(1))
    found = menu.findChild(QAction, object_name)
    assert found is not None
    return found


def test_window_menu_lists_the_plts_actions(qtbot: QtBot) -> None:
    panel = panel_with_window(qtbot)

    menu = panel.window_menu(panel.browser_tree.window(1))

    assert [a.text() for a in menu.actions()] == [
        "Close View",
        "Close File",
        "Copy File Name",
        "Rename File",
        "",
        "Save Template As...",
    ]


def test_close_actions_request_the_window_and_the_file(qtbot: QtBot) -> None:
    panel = panel_with_window(qtbot)

    with qtbot.waitSignal(panel.close_view_requested) as view:
        action(panel, "close_view").trigger()
    with qtbot.waitSignal(panel.close_file_requested) as file:
        action(panel, "close_file").trigger()

    assert view.args == [1]
    assert file.args == ["file-1"]


def test_copy_file_name_puts_the_name_on_the_clipboard(qtbot: QtBot) -> None:
    panel = panel_with_window(qtbot)

    action(panel, "copy_file_name").trigger()

    clipboard = QApplication.clipboard()
    assert clipboard is not None and clipboard.text() == "dut.s1p"


def test_rename_file_asks_for_the_name(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    panel = panel_with_window(qtbot)
    monkeypatch.setattr(QInputDialog, "getText", lambda *args: (" channel ", True))

    with qtbot.waitSignal(panel.rename_file_requested) as rename:
        action(panel, "rename_file").trigger()

    assert rename.args == ["file-1", "channel"]


@pytest.mark.parametrize("answer", [("", True), ("channel", False), ("dut.s1p", True)])
def test_rename_file_does_nothing_when_cancelled_or_unchanged(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, answer: tuple[str, bool]
) -> None:
    panel = panel_with_window(qtbot)
    monkeypatch.setattr(QInputDialog, "getText", lambda *args: answer)

    with qtbot.assertNotEmitted(panel.rename_file_requested):
        action(panel, "rename_file").trigger()


def click(panel: DataBrowserPanel, view_type: ViewType) -> None:
    index = panel.model.index_of_view_type(view_type)
    viewport = panel.tree.viewport()
    assert viewport is not None
    QtBot.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=panel.tree.visualRect(index).center())


def test_clicking_an_available_view_type_requests_a_window(qtbot: QtBot) -> None:
    panel = panel_with_window(qtbot)
    panel.show()
    qtbot.waitExposed(panel)

    with qtbot.waitSignal(panel.open_view_requested) as request:
        click(panel, ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED)

    assert request.args == [ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED]


def test_clicking_an_unavailable_view_type_does_nothing(qtbot: QtBot) -> None:
    panel = panel_with_window(qtbot)
    panel.show()
    qtbot.waitExposed(panel)

    with qtbot.assertNotEmitted(panel.open_view_requested):
        click(panel, ViewType.TIME_DOMAIN_SINGLE_ENDED)
