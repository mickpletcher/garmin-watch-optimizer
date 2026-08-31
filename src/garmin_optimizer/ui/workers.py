from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, Signal


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class Worker(QRunnable):
    def __init__(self, fn: Callable[[], object]) -> None:
        super().__init__()
        self.fn = fn
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self.fn()
        except Exception as exc:  # pragma: no cover
            self.signals.failed.emit(str(exc))
            return
        self.signals.finished.emit(result)
