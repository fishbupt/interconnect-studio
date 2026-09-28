"""Data Integrity Check dialog.

Numerical correctness belongs to ``tests/unit/test_network_quality.py``.
These check what the dialog does with the answers: that it asks the runner
rather than the GUI thread, shows the numbers, and stays read-only.
"""

import numpy as np
from pytestqt.qtbot import QtBot

from interconnect_studio.algorithms.network import check_network
from interconnect_studio.core import Network
from interconnect_studio.ui.dialogs import DataIntegrityDialog
from interconnect_studio.ui.dialogs.data_integrity_dialog import check_summary, run_checks
from interconnect_studio.ui.task_runner import TaskRunner

FREQUENCIES = [1.0e9, 2.0e9, 3.0e9]


def two_port(s21: complex) -> Network:
    matrix = np.array([[0.0, s21], [s21, 0.0]], dtype=np.complex128)
    return Network(FREQUENCIES, np.broadcast_to(matrix, (3, 2, 2)), z0=50.0)


def open_dialog(qtbot: QtBot, network: Network) -> DataIntegrityDialog:
    dialog = DataIntegrityDialog(network, TaskRunner(), tolerance=1.0e-9)
    qtbot.addWidget(dialog)
    qtbot.waitUntil(lambda: bool(dialog.results))
    return dialog


def cell(dialog: DataIntegrityDialog, row: int, column: int) -> str:
    item = dialog.table.item(row, column)
    assert item is not None
    return item.text()


def test_a_passive_reciprocal_file_reports_both_checks(qtbot: QtBot) -> None:
    dialog = open_dialog(qtbot, two_port(0.5))

    assert [cell(dialog, row, 0) for row in range(2)] == ["Passivity", "Reciprocity"]
    assert cell(dialog, 0, 1) == "Pass"
    assert cell(dialog, 1, 1) == "Pass"


def test_an_active_file_is_reported_with_its_numbers(qtbot: QtBot) -> None:
    """The verdict alone is useless; the excess is what an engineer reads."""

    dialog = open_dialog(qtbot, two_port(2.0))

    assert cell(dialog, 0, 1) == "Outside tolerance"
    assert cell(dialog, 0, 2) == "2"
    assert cell(dialog, 0, 3) == "1 GHz"
    assert cell(dialog, 0, 4) == "3 of 3"


def test_a_small_excess_is_not_rounded_away(qtbot: QtBot) -> None:
    """A passivity excess of 3e-7 is exactly what someone opened this for."""

    dialog = open_dialog(qtbot, two_port(1.0 + 3.0e-7))

    assert cell(dialog, 0, 2).startswith("1.0000003")


def test_the_dialog_starts_before_the_answer_arrives(qtbot: QtBot) -> None:
    """Constructed, shown, and only then filled in: nothing blocks."""

    dialog = DataIntegrityDialog(two_port(0.5), TaskRunner(), tolerance=1.0e-9)
    qtbot.addWidget(dialog)

    assert dialog.results == ()
    assert dialog.status_label.text() == "Checking ..."
    qtbot.waitUntil(lambda: bool(dialog.results))


def test_closing_disowns_a_running_check(qtbot: QtBot) -> None:
    runner = TaskRunner()
    dialog = DataIntegrityDialog(two_port(0.5), runner, tolerance=1.0e-9)
    qtbot.addWidget(dialog)

    dialog.reject()

    assert runner.wait_for_done() is True
    qtbot.wait(50)
    assert dialog.results == ()


def test_a_failing_check_shows_why_rather_than_raising(qtbot: QtBot) -> None:
    runner = TaskRunner()
    dialog = DataIntegrityDialog(two_port(0.5), runner, tolerance=1.0e-9)
    qtbot.addWidget(dialog)
    dialog._on_error("singular matrix")

    assert "singular matrix" in dialog.status_label.text()


def test_the_dialog_offers_no_way_to_change_the_data(qtbot: QtBot) -> None:
    """The checks are read-only; a fix button here would invite the opposite."""

    dialog = open_dialog(qtbot, two_port(2.0))

    labels = [
        button.text().lower()
        for button in dialog.findChildren(type(dialog.status_label).__mro__[0])
        if hasattr(button, "text")
    ]
    assert not any("fix" in label or "correct" in label for label in labels)


def test_the_work_is_a_plain_callable_with_no_widget(qtbot: QtBot) -> None:
    """What the runner gets must be testable without Qt at all.

    QualityResult holds NumPy arrays, so dataclass equality is ambiguous;
    compare the fields that carry the answer.
    """

    network = two_port(0.5)

    results = run_checks(network, tolerance=1.0e-9)()
    expected = check_network(network, tolerance=1.0e-9)

    assert isinstance(results, tuple)
    assert [result.name for result in results] == [result.name for result in expected]
    for actual, wanted in zip(results, expected, strict=True):
        np.testing.assert_array_equal(actual.metric, wanted.metric)
        assert actual.passed is wanted.passed


def test_summary_names_what_failed_not_how_many(qtbot: QtBot) -> None:
    passing = check_network(two_port(0.5), tolerance=1.0e-9)
    failing = check_network(two_port(2.0), tolerance=1.0e-9)

    assert check_summary(passing) == "Data integrity: all checks passed."
    assert check_summary(failing) == "Data integrity: passivity outside tolerance."


def test_the_tolerance_note_says_it_is_provisional(qtbot: QtBot) -> None:
    """It is a number I made up; the dialog must not present it as settled."""

    dialog = open_dialog(qtbot, two_port(0.5))
    notes = [
        label.text()
        for label in dialog.findChildren(type(dialog.status_label))
        if "provisional" in label.text()
    ]

    assert notes
