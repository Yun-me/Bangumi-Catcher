"""后台任务 Worker —— 负责在 QThread 中执行抓取与分析。"""

from __future__ import annotations

import asyncio
import logging
import threading

from PySide6 import QtCore

from ..core.config import load_config
from ..core.exceptions import OperationCancelled
from ..services.fetch_service import fetch_and_analyze

logger = logging.getLogger(__name__)


class FetchWorker(QtCore.QObject):
    progress = QtCore.Signal(float, str)
    finished = QtCore.Signal(object, object)  # (UserCollection, AnalysisReport)
    failed = QtCore.Signal(str)

    def __init__(self, username: str, subject_type: int, force_refresh: bool):
        super().__init__()
        self.username = username
        self.subject_type = subject_type
        self.force_refresh = force_refresh
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    @QtCore.Slot()
    def run(self) -> None:
        try:
            cfg = load_config()

            def progress(frac: float, msg: str) -> None:
                if self._cancel.is_set():
                    raise OperationCancelled("已取消")
                self.progress.emit(float(frac), str(msg))

            # 抓取自身 0-1 进度映射到整体 2%~70%，分析占 70%~100%。
            def fetch_progress(frac: float, msg: str) -> None:
                progress(0.02 + 0.68 * frac, msg)

            async def _run():
                return await fetch_and_analyze(
                    cfg,
                    self.username,
                    subject_type=self.subject_type,
                    force_refresh=self.force_refresh,
                    progress=fetch_progress,
                    cancel_check=self._cancel.is_set,
                )

            progress(0.02, "连接 Bangumi API …")
            collection, report = asyncio.run(_run())
            progress(1.0, "完成")
            self.finished.emit(collection, report)
        except OperationCancelled:
            self.failed.emit("已取消")
        except Exception as e:  # noqa: BLE001
            logger.exception("抓取失败")
            self.failed.emit(str(e))
