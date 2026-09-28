from pathlib import Path

import pytest
from PyQt6.QtWidgets import QDialogButtonBox, QFileDialog, QMessageBox
from pytestqt.qtbot import QtBot

from interconnect_studio.algorithms.mixed_mode import (
    DEFAULT_FOUR_PORT_TOPOLOGY,
    FOUR_PORT_TOPOLOGIES,
    topology_by_id,
)
from interconnect_studio.core import DutConfiguration, Line, PortGroup, quick_topology
from interconnect_studio.io import write_dut_configuration
from interconnect_studio.ui.dialogs import DutConfigurationDialog
from interconnect_studio.ui.dialogs.dut_configuration_dialog import (
    configuration_choices,
    default_configuration,
)
from interconnect_studio.ui.theme import Theme
from interconnect_studio.ui.widgets import DutConfigurationView


def test_four_port_offers_single_ended_and_every_through_wiring(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)

    names = [view.configuration.name for view in dialog.views]
    assert names[0] == "Single-Ended"
    assert [topology.name for topology in FOUR_PORT_TOPOLOGIES] == names[1:4]
    assert "4-Port SE-SE" in names


def test_two_port_offers_only_what_fits_it(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(2)
    qtbot.addWidget(dialog)

    assert [view.configuration.name for view in dialog.views] == [
        "Single-Ended",
        "2-Port SE-SE",
        "2-Port Differential Reflection",
    ]


def test_an_unusual_port_count_still_offers_single_ended(qtbot: QtBot) -> None:
    """Five ports have no presets, so the dialog is not empty by accident."""

    assert [choice.name for choice in configuration_choices(5)] == ["Single-Ended"]


def test_dialog_preselects_what_the_file_opened_as(qtbot: QtBot) -> None:
    """Opening the dialog and pressing OK must not change anything."""

    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)

    assert dialog.configuration() == default_configuration(4)
    assert dialog.configuration().topology_summary == "Diff-Diff"


def test_single_ended_is_listed_first_even_when_not_preselected(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)

    assert dialog.views[0].configuration.name == "Single-Ended"


def test_a_port_count_with_no_pair_default_opens_single_ended(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(2)
    qtbot.addWidget(dialog)

    assert dialog.configuration().name == "Single-Ended"


def test_dialog_opens_on_the_given_configuration(qtbot: QtBot) -> None:
    crossed = topology_by_id("through_1_4_2_3").dut_configuration()
    dialog = DutConfigurationDialog(4, crossed)
    qtbot.addWidget(dialog)

    assert dialog.configuration().port_group == crossed.port_group


def test_selecting_a_choice_changes_the_configuration(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)

    dialog.set_configuration(topology_by_id("through_1_3_2_4").dut_configuration())

    assert dialog.configuration().port_group.lines[0].near == (0, 1)


def test_a_named_configuration_becomes_its_own_choice(qtbot: QtBot) -> None:
    """Snapping it to the matching preset would discard the user's name."""

    renamed = DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration().renamed("My fixture")
    dialog = DutConfigurationDialog(4, renamed)
    qtbot.addWidget(dialog)

    assert dialog.configuration() == renamed
    assert dialog.views[-1].configuration.name == "My fixture"


def test_view_renders_every_preset_shape(qtbot: QtBot) -> None:
    """Reflection-only, balun and through wirings all reach paintEvent."""

    for configuration in (
        DutConfiguration.single_ended(3),
        quick_topology("2_diff_reflection"),
        quick_topology("3_diff_se"),
        DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration(),
    ):
        view = DutConfigurationView(configuration)
        qtbot.addWidget(view)
        view.resize(200, 110)
        view.grab()  # paintEvent runs here


def test_view_can_switch_configuration_and_theme(qtbot: QtBot) -> None:
    view = DutConfigurationView(DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration())
    qtbot.addWidget(view)

    view.set_configuration(topology_by_id("through_1_4_2_3").dut_configuration())
    view.apply_theme(Theme.DARK)

    assert view.configuration.port_group.lines[0].far == (3, 2)
    view.grab()


def test_view_tooltip_names_the_configuration(qtbot: QtBot) -> None:
    view = DutConfigurationView(DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration())
    qtbot.addWidget(view)

    assert DEFAULT_FOUR_PORT_TOPOLOGY.name in view.toolTip()
    assert "Diff-Diff" in view.toolTip()


def test_default_configuration_follows_plts() -> None:
    assert default_configuration(4).topology_summary == "Diff-Diff"
    assert default_configuration(2).name == "Single-Ended"


def test_reset_returns_to_what_the_file_opens_as(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)
    dialog.set_configuration(quick_topology("4_se_se"))

    dialog.reset()

    assert dialog.configuration() == default_configuration(4)


def test_save_as_then_load_restores_the_selection(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = tmp_path / "fixture.dutcfg"
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)
    dialog.set_configuration(topology_by_id("through_1_4_2_3").dut_configuration())
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(saved), ""))

    dialog.save_as()

    reopened = DutConfigurationDialog(4)
    qtbot.addWidget(reopened)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(saved), ""))

    reopened.load()

    assert reopened.configuration().port_group.lines[0].far == (3, 2)


def test_save_as_supplies_the_suffix_when_the_user_omits_it(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dialog = DutConfigurationDialog(2)
    qtbot.addWidget(dialog)
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *a, **k: (str(tmp_path / "plain"), "")
    )

    dialog.save_as()

    assert (tmp_path / "plain.dutcfg").is_file()


def test_cancelling_the_file_dialog_writes_nothing(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dialog = DutConfigurationDialog(2)
    qtbot.addWidget(dialog)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))

    dialog.save_as()

    assert list(tmp_path.iterdir()) == []


def test_loading_a_custom_grouping_adds_it_as_a_choice(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hand-written grouping no preset covers must survive the round trip."""

    custom = DutConfiguration(
        name="Crossed pair",
        n_ports=4,
        port_group=PortGroup(lines=(Line(name="Pair 1", near=(2, 0), far=(3, 1)),)),
        port_labels=("A+", "B+", "A-", "B-"),
    )
    path = tmp_path / "custom.dutcfg"
    write_dut_configuration(custom, path)
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)
    before = len(dialog.views)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(path), ""))

    dialog.load()

    assert len(dialog.views) == before + 1
    assert dialog.configuration() == custom
    assert dialog.configuration().port_labels == ("A+", "B+", "A-", "B-")


def test_loading_a_different_port_count_warns_and_changes_nothing(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "two.dutcfg"
    write_dut_configuration(DutConfiguration.single_ended(2), path)
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)
    warnings: list[str] = []
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(path), ""))
    monkeypatch.setattr(
        QMessageBox, "warning", lambda parent, title, text, *a: warnings.append(text)
    )

    dialog.load()

    assert len(warnings) == 1
    assert "2-port DUT" in warnings[0]
    assert dialog.configuration() == default_configuration(4)


def test_loading_a_broken_file_warns_instead_of_raising(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "broken.dutcfg"
    path.write_text("{not json", encoding="utf-8")
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)
    warnings: list[str] = []
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(path), ""))
    monkeypatch.setattr(
        QMessageBox, "warning", lambda parent, title, text, *a: warnings.append(text)
    )

    dialog.load()

    assert "not valid JSON" in warnings[0]


def test_labels_start_at_the_defaults(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)

    assert dialog.labels.labels() == ("Port 1", "Port 2", "Port 3", "Port 4")


def test_typed_labels_reach_the_configuration(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)

    dialog.labels.set_labels(("TX+", "RX+", "TX-", "RX-"))

    assert dialog.configuration().port_labels == ("TX+", "RX+", "TX-", "RX-")
    assert dialog.configuration().logical_ports[0].label == "TX+ / TX-"


def test_labels_survive_picking_another_wiring(qtbot: QtBot) -> None:
    """Labels describe the DUT, so a different topology must not clear them."""

    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)
    dialog.labels.set_labels(("TX+", "RX+", "TX-", "RX-"))

    dialog._buttons.button(2).setChecked(True)  # a different through wiring

    assert dialog.labels.labels() == ("TX+", "RX+", "TX-", "RX-")
    assert dialog.configuration().port_labels == ("TX+", "RX+", "TX-", "RX-")


def test_adopting_a_whole_configuration_takes_its_labels(qtbot: QtBot) -> None:
    """Load and Reset replace everything, including the labels."""

    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)
    dialog.labels.set_labels(("TX+", "RX+", "TX-", "RX-"))

    dialog.set_configuration(quick_topology("4_se_se"))

    assert dialog.labels.labels() == ("Port 1", "Port 2", "Port 3", "Port 4")


def test_a_blank_label_blocks_ok_and_save(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(2)
    qtbot.addWidget(dialog)

    dialog.labels.editors[0].setText("   ")

    ok = dialog.dialog_buttons.button(QDialogButtonBox.StandardButton.Ok)
    assert ok is not None and ok.isEnabled() is False
    assert dialog.save_button.isEnabled() is False
    assert "needs a label" in dialog.error_label.text()


def test_restoring_a_label_unblocks_ok(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(2)
    qtbot.addWidget(dialog)
    dialog.labels.editors[0].setText("")

    dialog.labels.editors[0].setText("IN")

    ok = dialog.dialog_buttons.button(QDialogButtonBox.StandardButton.Ok)
    assert ok is not None and ok.isEnabled() is True
    assert dialog.error_label.text() == ""


def test_save_as_does_nothing_while_a_label_is_blank(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dialog = DutConfigurationDialog(2)
    qtbot.addWidget(dialog)
    dialog.labels.editors[0].setText("")
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *a, **k: (str(tmp_path / "x.dutcfg"), "")
    )

    dialog.save_as()

    assert list(tmp_path.iterdir()) == []


def test_reset_restores_the_default_labels(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)
    dialog.labels.set_labels(("A", "B", "C", "D"))

    dialog.reset()

    assert dialog.labels.labels() == ("Port 1", "Port 2", "Port 3", "Port 4")


def test_saved_labels_come_back_on_load(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = tmp_path / "fixture.dutcfg"
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)
    dialog.labels.set_labels(("TX+", "RX+", "TX-", "RX-"))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(saved), ""))
    dialog.save_as()

    reopened = DutConfigurationDialog(4)
    qtbot.addWidget(reopened)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(saved), ""))

    reopened.load()

    assert reopened.labels.labels() == ("TX+", "RX+", "TX-", "RX-")


def test_a_label_only_difference_is_the_same_wiring(qtbot: QtBot) -> None:
    """Otherwise every relabelled preset would pile up as a new tile."""

    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)
    before = len(dialog.views)

    dialog.set_configuration(
        DEFAULT_FOUR_PORT_TOPOLOGY.dut_configuration().with_labels(
            ("TX+", "RX+", "TX-", "RX-")
        )
    )

    assert len(dialog.views) == before
    assert dialog.labels.labels() == ("TX+", "RX+", "TX-", "RX-")


def test_logical_port_column_shows_pairing_and_polarity(qtbot: QtBot) -> None:
    """Labelling a pair is guesswork without knowing which port is which."""

    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)

    shown = [label.text() for label in dialog.labels._logical_labels]

    # Through 1-2, 3-4 pairs ports 1,3 as logical port 1 and 2,4 as port 2.
    assert shown == ["L1 +", "L2 +", "L1 −", "L2 −"]


def test_logical_port_column_follows_the_selected_wiring(qtbot: QtBot) -> None:
    dialog = DutConfigurationDialog(4)
    qtbot.addWidget(dialog)

    dialog.set_configuration(topology_by_id("through_1_3_2_4").dut_configuration())

    shown = [label.text() for label in dialog.labels._logical_labels]
    assert shown == ["L1 +", "L1 −", "L2 +", "L2 −"]
