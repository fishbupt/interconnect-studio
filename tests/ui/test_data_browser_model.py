import numpy as np
from PyQt6.QtCore import QModelIndex, Qt
from pytestqt.qtbot import QtBot

from interconnect_studio.core import DataFile, Group, Measurement, Network
from interconnect_studio.ui.models import DataBrowserModel
from interconnect_studio.ui.panels import DataBrowserPanel


def network() -> Network:
    return Network([1.0e9, 2.0e9], np.zeros((2, 2, 2), dtype=np.complex128), z0=50.0)


def hierarchy() -> tuple[Group, ...]:
    files = (
        DataFile(id="f1", name="dut_a.s2p", network=network()),
        DataFile(id="f2", name="dut_b.s2p", network=network()),
    )
    return (Group(name="Board A", measurements=(Measurement(name="Run 1", files=files),)),)


def display(model: DataBrowserModel, index: QModelIndex) -> str | None:
    return model.data(index, Qt.ItemDataRole.DisplayRole)


def test_empty_model_has_no_rows() -> None:
    model = DataBrowserModel()

    assert model.rowCount(QModelIndex()) == 0


def test_model_exposes_three_levels() -> None:
    model = DataBrowserModel(hierarchy())

    group_index = model.index(0, 0, QModelIndex())
    assert display(model, group_index) == "Board A"

    measurement_index = model.index(0, 0, group_index)
    assert display(model, measurement_index) == "Run 1"

    file_index = model.index(0, 0, measurement_index)
    assert display(model, file_index) == "dut_a.s2p"


def test_data_files_are_leaves() -> None:
    model = DataBrowserModel(hierarchy())
    group_index = model.index(0, 0, QModelIndex())
    measurement_index = model.index(0, 0, group_index)
    file_index = model.index(0, 0, measurement_index)

    assert model.rowCount(file_index) == 0


def test_parent_walks_back_up() -> None:
    model = DataBrowserModel(hierarchy())
    group_index = model.index(0, 0, QModelIndex())
    measurement_index = model.index(0, 0, group_index)
    file_index = model.index(0, 0, measurement_index)

    assert model.parent(file_index) == measurement_index
    assert model.parent(measurement_index) == group_index
    assert model.parent(group_index) == QModelIndex()


def test_model_shows_one_column() -> None:
    model = DataBrowserModel(hierarchy())

    assert model.columnCount(QModelIndex()) == 1


def test_data_file_at_returns_none_for_container_rows() -> None:
    model = DataBrowserModel(hierarchy())
    group_index = model.index(0, 0, QModelIndex())

    assert model.data_file_at(group_index) is None


def test_data_file_at_returns_the_leaf_payload() -> None:
    model = DataBrowserModel(hierarchy())
    group_index = model.index(0, 0, QModelIndex())
    measurement_index = model.index(0, 0, group_index)
    file_index = model.index(0, 0, measurement_index)

    data_file = model.data_file_at(file_index)
    assert data_file is not None
    assert data_file.id == "f1"


def test_index_of_data_file_finds_by_id() -> None:
    model = DataBrowserModel(hierarchy())

    index = model.index_of_data_file("f2")

    data_file = model.data_file_at(index)
    assert data_file is not None
    assert data_file.name == "dut_b.s2p"


def test_index_of_unknown_data_file_is_invalid() -> None:
    model = DataBrowserModel(hierarchy())

    assert model.index_of_data_file("missing").isValid() is False


def test_set_groups_replaces_the_tree() -> None:
    model = DataBrowserModel(hierarchy())

    model.set_groups(())

    assert model.rowCount(QModelIndex()) == 0
    assert model.groups == ()


def test_panel_selection_emits_current_file(qtbot: QtBot) -> None:
    panel = DataBrowserPanel()
    qtbot.addWidget(panel)
    panel.set_groups(hierarchy())

    with qtbot.waitSignal(panel.current_file_changed) as blocker:
        panel.select_data_file("f2")

    emitted = blocker.args[0]
    assert emitted is not None
    assert emitted.id == "f2"
    assert panel.current_file() is not None
