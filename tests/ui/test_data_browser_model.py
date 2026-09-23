import numpy as np
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QFont, QIcon
from pytestqt.qtbot import QtBot

from interconnect_studio.core import (
    BrowserCategory,
    DataBrowserTree,
    DataFile,
    Network,
    ViewType,
)
from interconnect_studio.ui.models import DataBrowserModel
from interconnect_studio.ui.panels import DataBrowserPanel

FD_SE = ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED


def network() -> Network:
    return Network([1.0e9, 2.0e9], np.zeros((2, 2, 2), dtype=np.complex128), z0=50.0)


def data_file(file_id: str, name: str) -> DataFile:
    return DataFile(id=file_id, name=name, network=network())


def tree() -> DataBrowserTree:
    result, _ = DataBrowserTree().open(FD_SE, data_file("f1", "dut_a.s2p"))
    result, _ = result.open(FD_SE, data_file("f2", "dut_b.s2p"))
    result, _ = result.open(ViewType.TIME_DOMAIN_DIFFERENTIAL, data_file("f1", "dut_a.s2p"))
    return result


def display(model: DataBrowserModel, index: QModelIndex) -> str | None:
    return model.data(index, Qt.ItemDataRole.DisplayRole)


def children(model: DataBrowserModel, parent: QModelIndex) -> list[str | None]:
    return [display(model, model.index(row, 0, parent)) for row in range(model.rowCount(parent))]


def test_empty_model_still_lists_the_plts_catalogue() -> None:
    model = DataBrowserModel()

    assert children(model, QModelIndex()) == [
        "Data Analysis",
        "RLCG",
        "Calibration",
        "Template View",
    ]
    calibration = model.index_of_category(BrowserCategory.CALIBRATION)
    assert children(model, calibration) == ["Error Terms", "Measured Standards"]


def test_windows_sit_under_their_view_type() -> None:
    model = DataBrowserModel(tree())

    assert children(model, model.index_of_view_type(FD_SE)) == [
        "dut_a.s2p : 1",
        "dut_b.s2p : 2",
    ]
    assert children(model, model.index_of_view_type(ViewType.TIME_DOMAIN_DIFFERENTIAL)) == [
        "dut_a.s2p : 3",
    ]
    assert model.rowCount(model.index_of_view_type(ViewType.EYE_DIAGRAM_DIFFERENTIAL)) == 0


def test_windows_are_leaves() -> None:
    model = DataBrowserModel(tree())

    assert model.rowCount(model.index_of_window(1)) == 0


def test_parent_walks_back_up() -> None:
    model = DataBrowserModel(tree())
    window_index = model.index_of_window(2)
    view_index = model.index_of_view_type(FD_SE)
    category_index = model.index_of_category(BrowserCategory.DATA_ANALYSIS)

    assert model.parent(window_index) == view_index
    assert model.parent(view_index) == category_index
    assert model.parent(category_index) == QModelIndex()


def test_model_shows_one_column() -> None:
    model = DataBrowserModel(tree())

    assert model.columnCount(QModelIndex()) == 1


def test_data_file_at_returns_none_for_catalogue_rows() -> None:
    model = DataBrowserModel(tree())

    assert model.data_file_at(model.index_of_category(BrowserCategory.DATA_ANALYSIS)) is None
    assert model.data_file_at(model.index_of_view_type(FD_SE)) is None


def test_data_file_at_returns_the_window_file() -> None:
    model = DataBrowserModel(tree())

    item = model.data_file_at(model.index_of_window(2))
    assert item is not None
    assert item.id == "f2"


def test_index_of_unknown_window_is_invalid() -> None:
    model = DataBrowserModel(tree())

    assert model.index_of_window(99).isValid() is False


def test_only_windows_are_selectable() -> None:
    model = DataBrowserModel(tree())
    selectable = Qt.ItemFlag.ItemIsSelectable

    assert model.flags(model.index_of_window(1)) & selectable
    assert not model.flags(model.index_of_view_type(FD_SE)) & selectable
    assert not model.flags(model.index_of_category(BrowserCategory.DATA_ANALYSIS)) & selectable


def test_unavailable_view_types_are_greyed_out() -> None:
    model = DataBrowserModel(tree())
    enabled = Qt.ItemFlag.ItemIsEnabled
    rlcg = model.index_of_category(BrowserCategory.RLCG)
    time_domain = model.index_of_view_type(ViewType.TIME_DOMAIN_DIFFERENTIAL)

    assert model.flags(model.index_of_view_type(FD_SE)) & enabled
    assert not model.flags(time_domain) & enabled
    assert not model.flags(model.index_of_window(3)) & enabled
    assert not model.flags(rlcg) & enabled
    assert model.data(rlcg, Qt.ItemDataRole.ToolTipRole) == "Not available yet"


def test_available_view_types_are_configurable() -> None:
    model = DataBrowserModel(tree(), available_view_types=ViewType)

    rlcg = model.index_of_category(BrowserCategory.RLCG)
    assert model.flags(rlcg) & Qt.ItemFlag.ItemIsEnabled
    assert model.data(rlcg, Qt.ItemDataRole.ToolTipRole) is None


def test_set_tree_replaces_the_windows() -> None:
    model = DataBrowserModel(tree())

    model.set_tree(DataBrowserTree())

    assert model.rowCount(model.index_of_view_type(FD_SE)) == 0
    assert model.rowCount(QModelIndex()) == len(BrowserCategory)
    assert model.tree == DataBrowserTree()


def test_panel_expands_view_types_with_windows(qtbot: QtBot) -> None:
    panel = DataBrowserPanel()
    qtbot.addWidget(panel)
    panel.set_browser_tree(tree())

    model = panel.model
    assert panel.tree.isExpanded(model.index_of_category(BrowserCategory.CALIBRATION))
    assert panel.tree.isExpanded(model.index_of_view_type(FD_SE))
    assert not panel.tree.isExpanded(model.index_of_view_type(ViewType.EYE_DIAGRAM_DIFFERENTIAL))


def test_panel_selection_emits_current_file(qtbot: QtBot) -> None:
    panel = DataBrowserPanel()
    qtbot.addWidget(panel)
    panel.set_browser_tree(tree())

    with qtbot.waitSignal(panel.current_file_changed) as blocker:
        panel.select_window(2)

    emitted = blocker.args[0]
    assert emitted is not None
    assert emitted.id == "f2"
    window = panel.current_window()
    assert window is not None
    assert window.number == 2


def icon_key(model: DataBrowserModel, index: QModelIndex) -> int:
    icon = model.data(index, Qt.ItemDataRole.DecorationRole)
    assert isinstance(icon, QIcon)
    assert not icon.isNull()
    return icon.cacheKey()


def test_every_row_has_an_icon() -> None:
    model = DataBrowserModel(tree())

    for category in BrowserCategory:
        icon_key(model, model.index_of_category(category))
        for view_type in category.view_types:
            icon_key(model, model.index_of_view_type(view_type))
    icon_key(model, model.index_of_window(1))


def test_categories_views_and_windows_use_different_icons() -> None:
    model = DataBrowserModel(tree())

    keys = {
        icon_key(model, model.index_of_category(BrowserCategory.DATA_ANALYSIS)),
        icon_key(model, model.index_of_view_type(FD_SE)),
        icon_key(model, model.index_of_window(1)),
    }
    assert len(keys) == 3


def test_folder_icon_opens_when_expanded() -> None:
    model = DataBrowserModel(tree())
    index = model.index_of_view_type(FD_SE)
    closed = icon_key(model, index)

    model.set_expanded(index, True)
    opened = icon_key(model, index)
    model.set_expanded(index, False)

    assert opened != closed
    assert icon_key(model, index) == closed


def test_window_rows_ignore_expansion() -> None:
    model = DataBrowserModel(tree())
    index = model.index_of_window(1)
    before = icon_key(model, index)

    model.set_expanded(index, True)

    assert icon_key(model, index) == before


def test_categories_are_bold() -> None:
    model = DataBrowserModel(tree())

    font = model.data(model.index_of_category(BrowserCategory.RLCG), Qt.ItemDataRole.FontRole)
    assert isinstance(font, QFont)
    assert font.bold()
    assert model.data(model.index_of_view_type(FD_SE), Qt.ItemDataRole.FontRole) is None


def test_panel_opens_folder_icons_of_expanded_rows(qtbot: QtBot) -> None:
    panel = DataBrowserPanel()
    qtbot.addWidget(panel)
    panel.set_browser_tree(tree())
    model = panel.model
    fd_se = model.index_of_view_type(FD_SE)
    eye = model.index_of_view_type(ViewType.EYE_DIAGRAM_DIFFERENTIAL)

    assert icon_key(model, fd_se) != icon_key(model, eye)

    panel.tree.collapse(fd_se)

    assert icon_key(model, fd_se) == icon_key(model, eye)
