"""TaskRunner/TaskWorker lifetime and signal contract."""

from __future__ import annotations

import threading

from bangumi_catcher.ui.workers import TaskRunner
from tests.ui.conftest import wait_until


def test_task_runner_rejects_overlapping_jobs(qapp):
    runner = TaskRunner()
    release = threading.Event()
    assert runner.start(lambda cancel, progress: release.wait(2))
    assert not runner.start(lambda cancel, progress: None)
    release.set()
    wait_until(lambda: not runner.busy)
    assert runner.start(lambda cancel, progress: 42)
    wait_until(lambda: not runner.busy)


def test_task_runner_reports_result_and_progress(qapp):
    runner = TaskRunner()
    results: list[object] = []
    progress: list[tuple[float, str]] = []
    runner.succeeded.connect(results.append)
    runner.progress.connect(lambda fraction, message: progress.append((fraction, message)))

    def operation(cancel, report):
        report(0.5, "half")
        return "done"

    assert runner.start(operation)
    wait_until(lambda: not runner.busy)
    assert results == ["done"]
    assert progress == [(0.5, "half")]


def test_task_runner_reports_failure_message(qapp):
    runner = TaskRunner()
    failures: list[str] = []
    runner.failed.connect(failures.append)

    def operation(cancel, progress):
        raise ValueError("broken input")

    assert runner.start(operation)
    wait_until(lambda: not runner.busy)
    assert failures == ["broken input"]


def test_task_runner_cancel_marks_job_cancelled(qapp):
    runner = TaskRunner()
    cancelled: list[bool] = []
    runner.cancelled.connect(lambda: cancelled.append(True))

    def operation(cancel, progress):
        cancel.wait(5)
        return "should not be delivered"

    assert runner.start(operation)
    runner.cancel()
    wait_until(lambda: not runner.busy)
    assert cancelled
