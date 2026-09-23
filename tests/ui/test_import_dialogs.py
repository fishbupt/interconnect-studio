from pathlib import Path

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialogButtonBox, QListWidget
from pytestqt.qtbot import QtBot

from interconnect_studio.core import ViewType
from interconnect_studio.io import ImportFileType
from interconnect_studio.services import ImportService
from interconnect_studio.ui.dialogs import (
    BuildConfigDialog,
    ImportMultipleFilesDialog,
    ImportSingleFileDialog,
    SelectAnalysisViewDialog,
)

DATA_DIR = Path(__file__).parents[1] / "data" / "import"


def ok_enabled(buttons: QDialogButtonBox) -> bool:
    ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
    assert ok is not None
    return ok.isEnabled()


def select(widget: QListWidget, texts: list[str]) -> None:
    widget.clearSelection()
    for text in texts:
        items = widget.findItems(text, Qt.MatchFlag.MatchExactly)
        assert items, text
        items[0].setSelected(True)


def test_single_file_dialog_starts_without_a_file(qtbot: QtBot) -> None:
    dialog = ImportSingleFileDialog(ImportService())
    qtbot.addWidget(dialog)

    assert ok_enabled(dialog.buttons) is False
    assert dialog.range_box.isEnabled() is False
    assert dialog.change_button.isEnabled() is False


def test_single_file_dialog_types_the_file_and_shows_its_range(qtbot: QtBot) -> None:
    dialog = ImportSingleFileDialog(ImportService())
    qtbot.addWidget(dialog)

    dialog.set_path(DATA_DIR / "two_port.cti")

    assert dialog.file_type() is ImportFileType.CITIFILE
    assert dialog.configuration_label.text() == "2-port, single-ended"
    assert dialog.range_box.points_value.text() == "3"
    assert dialog.range_box.step_value.text() == "100"
    assert ok_enabled(dialog.buttons) is True


def test_single_file_dialog_imports_a_subset(qtbot: QtBot) -> None:
    dialog = ImportSingleFileDialog(ImportService())
    qtbot.addWidget(dialog)
    dialog.set_path(DATA_DIR / "three_port.s3p")

    dialog.range_box.subset_radio.setChecked(True)
    dialog.range_box.start_spin.setValue(150.0)
    assert dialog.range_box.points_value.text() == "2"
    dialog.accept()

    assert dialog.imported is not None
    np.testing.assert_allclose(dialog.imported.network.frequencies_hz, [2.0e8, 3.0e8])


def test_single_file_dialog_reset_restores_the_full_range(qtbot: QtBot) -> None:
    dialog = ImportSingleFileDialog(ImportService())
    qtbot.addWidget(dialog)
    dialog.set_path(DATA_DIR / "three_port.s3p")
    dialog.range_box.subset_radio.setChecked(True)
    dialog.range_box.stop_spin.setValue(150.0)

    dialog.range_box.reset()

    assert dialog.range_box.points_value.text() == "3"


def test_single_file_dialog_shows_read_errors(qtbot: QtBot) -> None:
    dialog = ImportSingleFileDialog(ImportService())
    qtbot.addWidget(dialog)

    dialog.set_path(DATA_DIR / "two_port_tab.txt")
    dialog.file_type_combo.setCurrentIndex(
        dialog.file_type_combo.findData(ImportFileType.TEXT_COMMA)
    )

    assert "delimiter" in dialog.error_label.text()
    assert ok_enabled(dialog.buttons) is False


def test_interpolation_is_never_offered(qtbot: QtBot) -> None:
    dialog = ImportSingleFileDialog(ImportService())
    qtbot.addWidget(dialog)
    dialog.set_path(DATA_DIR / "three_port.s3p")

    assert dialog.range_box.interpolate_check.isEnabled() is False
    assert dialog.range_box.interpolate_check.isChecked() is False


def test_select_analysis_view_defaults_to_frequency_single_ended(qtbot: QtBot) -> None:
    dialog = SelectAnalysisViewDialog({ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED})
    qtbot.addWidget(dialog)

    assert dialog.selected_view_type() is ViewType.FREQUENCY_DOMAIN_SINGLE_ENDED
    assert dialog.view_list.count() == 10
    rlcg = dialog.view_list.findItems("RLCG (W-Element)", Qt.MatchFlag.MatchExactly)[0]
    assert not rlcg.flags() & Qt.ItemFlag.ItemIsEnabled


def test_multiple_files_dialog_needs_every_parameter_mapped(qtbot: QtBot) -> None:
    dialog = ImportMultipleFilesDialog(ImportService())
    qtbot.addWidget(dialog)
    dialog.ports_spin.setValue(2)
    assert dialog.add_file(DATA_DIR / "two_port.ts")

    select(dialog.source_list, ["S21"])
    select(dialog.target_list, ["S12", "S21"])
    dialog.assign_selected()

    assert ok_enabled(dialog.buttons) is False
    item = dialog.grid.item(0, 1)
    assert item is not None and item.text() == "1:S21"


def test_multiple_files_dialog_port_mapping_keeps_original_numbering(qtbot: QtBot) -> None:
    dialog = ImportMultipleFilesDialog(ImportService())
    qtbot.addWidget(dialog)
    dialog.ports_spin.setValue(3)
    dialog.add_file(DATA_DIR / "three_port.s3p")

    dialog.port_radio.setChecked(True)
    dialog.assign_selected()
    dialog.accept()

    assert dialog.imported is not None
    np.testing.assert_allclose(
        dialog.imported.network.s,
        ImportService().read(DATA_DIR / "three_port.s3p", ImportFileType.TOUCHSTONE).s,
    )


def test_multiple_files_dialog_maps_ports_of_a_second_file(qtbot: QtBot) -> None:
    dialog = ImportMultipleFilesDialog(ImportService())
    qtbot.addWidget(dialog)
    dialog.ports_spin.setValue(3)
    dialog.add_file(DATA_DIR / "three_port.s3p")
    dialog.add_file(DATA_DIR / "two_port.ts")
    dialog.port_radio.setChecked(True)

    dialog.file_list.setCurrentRow(0)
    dialog.assign_selected()
    dialog.file_list.setCurrentRow(1)
    select(dialog.source_list, ["Port 1", "Port 2"])
    select(dialog.target_list, ["Port 3", "Port 1"])
    dialog.assign_selected()
    dialog.accept()

    assert dialog.imported is not None
    s = dialog.imported.network.s[0]
    assert (s[2, 2], s[2, 0], s[0, 2], s[0, 0]) == (11, 12, 21, 22)


def test_multiple_files_dialog_unassign_clears_a_port(qtbot: QtBot) -> None:
    dialog = ImportMultipleFilesDialog(ImportService())
    qtbot.addWidget(dialog)
    dialog.ports_spin.setValue(3)
    dialog.add_file(DATA_DIR / "three_port.s3p")
    dialog.port_radio.setChecked(True)
    dialog.assign_selected()

    select(dialog.target_list, ["Port 2"])
    dialog.unassign_selected()

    assert ok_enabled(dialog.buttons) is False
    assert dialog.grid.item(1, 0) is None
    assert dialog.grid.item(0, 0) is not None


def test_multiple_files_dialog_rejects_files_on_another_grid(qtbot: QtBot, tmp_path: Path) -> None:
    other = tmp_path / "other.s1p"
    other.write_text("# Hz S RI R 50\n1 0 0\n")
    dialog = ImportMultipleFilesDialog(ImportService())
    qtbot.addWidget(dialog)
    dialog.add_file(DATA_DIR / "three_port.s3p")

    assert dialog.add_file(other) is False
    assert "not resampled" in dialog.error_label.text()
    assert dialog.file_list.count() == 1


def test_multiple_files_dialog_remove_file_renumbers_the_rest(qtbot: QtBot) -> None:
    dialog = ImportMultipleFilesDialog(ImportService())
    qtbot.addWidget(dialog)
    dialog.ports_spin.setValue(3)
    dialog.add_file(DATA_DIR / "three_port.s3p")
    dialog.add_file(DATA_DIR / "two_port.ts")
    dialog.port_radio.setChecked(True)
    dialog.assign_selected()  # second file, ports 1-2 onto DUT ports 1-2

    dialog.file_list.setCurrentRow(0)
    dialog.remove_file_button.click()

    assert dialog.file_list.count() == 1
    assert len(dialog.assignments) == 4
    assert {item.source for item in dialog.assignments} == {0}

    dialog.file_list.setCurrentRow(0)
    dialog.remove_file_button.click()

    assert dialog.assignments == ()


def test_build_config_dialog_builds_the_listed_files(qtbot: QtBot) -> None:
    dialog = BuildConfigDialog(ImportService())
    qtbot.addWidget(dialog)

    dialog.path_edit.setText(str(DATA_DIR / "build_config.csv"))
    dialog.accept()

    assert dialog.imported is not None
    assert dialog.imported.network.n_ports == 3


def test_build_config_dialog_reports_errors(qtbot: QtBot, tmp_path: Path) -> None:
    config = tmp_path / "bad.csv"
    config.write_text("folder,.\nf1,missing.s2p,[1 2],[1 2]\n")
    dialog = BuildConfigDialog(ImportService())
    qtbot.addWidget(dialog)

    dialog.path_edit.setText(str(config))
    dialog.accept()

    assert dialog.imported is None
    assert "not found" in dialog.error_label.text()
