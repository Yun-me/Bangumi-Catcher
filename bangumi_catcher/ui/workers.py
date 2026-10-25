"""Owned background jobs with explicit lifetime and cooperative cancellation."""

from __future__ import annotations

import logging
import threading
from typing import Callable

from PySide6 import QtCore

from ..core.exceptions import OperationCancelled
from ..services.task_service import check_cancelled

logger = logging.getLogger(__name__)
Operation = Callable[[threading.Event, Callable[[float, str], None]], object]


class TaskWorker(QtCore.QThread):
    succeeded = QtCore.Signal(object)
    failed = QtCore.Signal(str)
    cancelled = QtCore.Signal()
    progress = QtCore.Signal(float, str)

    def __init__(self, operation: Operation, parent=None):
        super().__init__(parent)
        self.operation = operation
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        try:
            check_cancelled(self.cancel_event)
            result = self.operation(self.cancel_event, self.progress.emit)
            check_cancelled(self.cancel_event)
            self.succeeded.emit(result)
        except OperationCancelled:
            self.cancelled.emit()
        except Exception as exc:
            logger.exception("后台任务失败")
            self.failed.emit(str(exc))


class TaskRunner(QtCore.QObject):
    succeeded = QtCore.Signal(object)
    failed = QtCore.Signal(str)
    cancelled = QtCore.Signal()
    progress = QtCore.Signal(float, str)
    busy_changed = QtCore.Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: TaskWorker | None = None

    @property
    def busy(self) -> bool:
        return self.worker is not None

    def start(self, operation: Operation) -> bool:
        if self.busy:
            return False
        self.worker = TaskWorker(operation, self)
        self.worker.succeeded.connect(self.succeeded)
        self.worker.failed.connect(self.failed)
        self.worker.cancelled.connect(self.cancelled)
        self.worker.progress.connect(self.progress)
        self.worker.finished.connect(self._finished)
        self.busy_changed.emit(True)
        self.worker.start()
        return True

    def cancel(self) -> None:
        if self.worker:
            self.worker.cancel()

    @QtCore.Slot()
    def _finished(self) -> None:
        worker, self.worker = self.worker, None
        worker.deleteLater()
        self.busy_changed.emit(False)
