"""Owned background jobs with explicit lifetime and cooperative cancellation.

``TaskRunner`` allows at most one job at a time. The job runs in a ``QThread``
and reports through signals; the UI never blocks on it. Closing the window
cancels the job and waits for the thread instead of destroying a running
``QThread`` (which would crash Qt).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore

from ..core.errors import OperationCancelled
from ..services.cancellation import check_cancelled

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float, str], None]
Operation = Callable[[threading.Event, ProgressCallback], Any]
"""A job takes a cancel event plus a progress callback and returns any payload."""


class TaskWorker(QtCore.QThread):
    """One background operation; emits exactly one terminal signal."""

    succeeded = QtCore.Signal(object)
    failed = QtCore.Signal(str)
    cancelled = QtCore.Signal()
    progress = QtCore.Signal(float, str)

    def __init__(self, operation: Operation, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self.operation = operation
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        """Request cancellation; safe to call from the UI thread."""
        self.cancel_event.set()

    def run(self) -> None:
        try:
            check_cancelled(self.cancel_event)
            result = self.operation(self.cancel_event, self.progress.emit)
            check_cancelled(self.cancel_event)
            self.succeeded.emit(result)
        except OperationCancelled:
            self.cancelled.emit()
        except Exception as exc:  # keep the UI alive and show a readable message
            logger.exception("后台任务失败")
            self.failed.emit(str(exc))


class TaskRunner(QtCore.QObject):
    """Single-slot job queue that re-emits worker signals on the UI thread."""

    succeeded = QtCore.Signal(object)
    failed = QtCore.Signal(str)
    cancelled = QtCore.Signal()
    progress = QtCore.Signal(float, str)
    busy_changed = QtCore.Signal(bool)

    def __init__(self, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self.worker: TaskWorker | None = None

    @property
    def busy(self) -> bool:
        return self.worker is not None

    def start(self, operation: Operation) -> bool:
        """Start ``operation``; returns ``False`` when a job is already running."""
        if self.busy:
            return False
        worker = TaskWorker(operation, self)
        worker.succeeded.connect(self.succeeded)
        worker.failed.connect(self.failed)
        worker.cancelled.connect(self.cancelled)
        worker.progress.connect(self.progress)
        worker.finished.connect(self._finished)
        self.worker = worker
        self.busy_changed.emit(True)
        worker.start()
        return True

    def cancel(self) -> None:
        if self.worker is not None:
            self.worker.cancel()

    @QtCore.Slot()
    def _finished(self) -> None:
        worker, self.worker = self.worker, None
        if worker is not None:
            worker.deleteLater()
        self.busy_changed.emit(False)


__all__ = ["Operation", "ProgressCallback", "TaskRunner", "TaskWorker"]
