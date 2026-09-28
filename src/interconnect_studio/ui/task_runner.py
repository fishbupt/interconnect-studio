"""Running slow work off the GUI thread.

``AGENTS.md`` §8 requires one shared runner rather than a thread per
feature, and requires that workers never touch widgets: they return through
signals, which Qt delivers on the thread that owns the receiver.

This lives under ``ui/`` on purpose. It is Qt plumbing, and putting it in
``services/`` would make that package depend on PyQt6, which is what keeps
the services testable without a GUI. What it *runs* is a plain callable, so
the work itself stays in Core / Algorithms / IO where it can be tested
directly.

Why it exists, concretely: a passivity check is an SVD per frequency.
A 4-port 1601-point file takes 11 ms, but a 32-port 16001-point one takes
about 4 s, and a 64-port sweep over half a minute. Those are legitimate
files, not pathological ones.
"""

import logging
import traceback
from collections.abc import Callable
from typing import Final

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

_logger: Final[logging.Logger] = logging.getLogger(__name__)


class TaskHandle(QObject):
    """One submitted task: its results, and the ability to disown them.

    ``cancel`` cannot stop work already inside NumPy. It stops the result
    being delivered, which is what a caller closing a dialog actually
    needs. The docstring says so rather than implying an interrupt.
    """

    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        """Whether the result will be discarded when it arrives."""

        return self._cancelled

    def cancel(self) -> None:
        """Stop delivering this task's result. The work still runs to completion."""

        self._cancelled = True


class _Task(QRunnable):
    """Runs one callable in the pool and reports back through a handle."""

    def __init__(self, work: Callable[[], object], handle: TaskHandle) -> None:
        super().__init__()
        self._work = work
        self._handle = handle

    def run(self) -> None:
        """Execute the work, turning any failure into a ``failed`` signal."""

        try:
            result = self._work()
        except Exception as exc:  # noqa: BLE001 - a task must not kill the pool
            # The message goes to the user; the traceback goes to the log,
            # as AGENTS.md §8 and the GUI conventions both ask.
            _logger.error("Background task failed: %s", traceback.format_exc())
            if not self._handle.cancelled:
                self._handle.failed.emit(str(exc) or exc.__class__.__name__)
            return
        if not self._handle.cancelled:
            self._handle.finished.emit(result)


class TaskRunner(QObject):
    """The one place background work is started from.

    Handles are kept alive until their task reports, so a caller may drop
    its reference without the signal vanishing mid-flight.
    """

    def __init__(self, parent: QObject | None = None, max_threads: int = 2) -> None:
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(max_threads)
        self._pending: set[TaskHandle] = set()

    def submit(
        self,
        work: Callable[[], object],
        on_result: Callable[[object], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> TaskHandle:
        """Run ``work`` in the pool and deliver its outcome on this thread.

        ``work`` takes no arguments and must not touch any widget. Returns
        a handle the caller can cancel.
        """

        handle = TaskHandle(self)
        if on_result is not None:
            handle.finished.connect(on_result)
        if on_error is not None:
            handle.failed.connect(on_error)
        handle.finished.connect(lambda _result: self._retire(handle))
        handle.failed.connect(lambda _message: self._retire(handle))

        self._pending.add(handle)
        self._pool.start(_Task(work, handle))
        return handle

    @property
    def pending(self) -> int:
        """How many tasks have not reported yet."""

        return len(self._pending)

    def cancel_all(self) -> None:
        """Disown every outstanding task. Work in flight still finishes."""

        for handle in tuple(self._pending):
            handle.cancel()
        self._pending.clear()

    def wait_for_done(self, timeout_ms: int = 30_000) -> bool:
        """Block until the pool is empty. For tests and for shutdown."""

        return self._pool.waitForDone(timeout_ms)

    def _retire(self, handle: TaskHandle) -> None:
        self._pending.discard(handle)
