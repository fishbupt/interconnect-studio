"""The shared background task runner."""

import threading

import pytest
from pytestqt.qtbot import QtBot

from interconnect_studio.ui.task_runner import TaskRunner


def test_a_result_comes_back_on_the_calling_thread(qtbot: QtBot) -> None:
    """The point of the runner: work off the GUI thread, answer on it."""

    runner = TaskRunner()
    caller = threading.get_ident()
    seen: list[tuple[object, int]] = []

    runner.submit(lambda: threading.get_ident(), lambda r: seen.append((r, threading.get_ident())))

    qtbot.waitUntil(lambda: bool(seen))
    worker_thread, delivered_on = seen[0]
    assert worker_thread != caller
    assert delivered_on == caller


def test_a_failure_becomes_a_message_not_a_crash(qtbot: QtBot) -> None:
    runner = TaskRunner()
    errors: list[str] = []

    def explode() -> object:
        raise ValueError("no reference impedance")

    runner.submit(explode, on_error=errors.append)

    qtbot.waitUntil(lambda: bool(errors))
    assert errors == ["no reference impedance"]


def test_a_failure_without_a_message_still_says_something(qtbot: QtBot) -> None:
    """An empty str(exc) would otherwise show the user a blank error."""

    runner = TaskRunner()
    errors: list[str] = []

    def explode() -> object:
        raise RuntimeError

    runner.submit(explode, on_error=errors.append)

    qtbot.waitUntil(lambda: bool(errors))
    assert errors == ["RuntimeError"]


def test_a_failing_task_does_not_stop_the_next_one(qtbot: QtBot) -> None:
    runner = TaskRunner()
    results: list[object] = []

    runner.submit(lambda: 1 / 0)
    runner.submit(lambda: "still working", results.append)

    qtbot.waitUntil(lambda: bool(results))
    assert results == ["still working"]


def test_a_cancelled_task_delivers_nothing(qtbot: QtBot) -> None:
    runner = TaskRunner()
    started = threading.Event()
    release = threading.Event()
    results: list[object] = []

    def slow() -> object:
        started.set()
        release.wait(5.0)
        return "too late"

    handle = runner.submit(slow, results.append)
    assert started.wait(5.0)
    handle.cancel()
    release.set()

    assert runner.wait_for_done() is True
    qtbot.wait(50)
    assert results == []


def test_cancel_all_disowns_everything_outstanding(qtbot: QtBot) -> None:
    runner = TaskRunner()
    release = threading.Event()
    results: list[object] = []

    for _ in range(2):
        runner.submit(lambda: release.wait(5.0), results.append)
    assert runner.pending == 2

    runner.cancel_all()
    release.set()

    assert runner.wait_for_done() is True
    qtbot.wait(50)
    assert results == []
    assert runner.pending == 0


def test_pending_falls_back_to_zero_once_reported(qtbot: QtBot) -> None:
    """Handles are held until they report, so nothing is collected early."""

    runner = TaskRunner()
    results: list[object] = []

    runner.submit(lambda: "done", results.append)

    qtbot.waitUntil(lambda: bool(results))
    qtbot.waitUntil(lambda: runner.pending == 0)


def test_tasks_run_concurrently(qtbot: QtBot) -> None:
    """One slow file must not block the next check from starting."""

    runner = TaskRunner(max_threads=2)
    both_started = threading.Barrier(2, timeout=5.0)
    results: list[object] = []

    def work() -> object:
        both_started.wait()
        return "ran"

    runner.submit(work, results.append)
    runner.submit(work, results.append)

    qtbot.waitUntil(lambda: len(results) == 2)


def test_the_traceback_reaches_the_log(
    qtbot: QtBot, caplog: pytest.LogCaptureFixture
) -> None:
    """The user sees one line; the log keeps the whole story."""

    runner = TaskRunner()
    errors: list[str] = []

    def explode() -> object:
        raise ValueError("boom")

    with caplog.at_level("ERROR"):
        runner.submit(explode, on_error=errors.append)
        qtbot.waitUntil(lambda: bool(errors))

    assert "Traceback" in caplog.text
    assert "ValueError: boom" in caplog.text
