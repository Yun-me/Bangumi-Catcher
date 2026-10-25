"""Process logging and the in-memory log buffer shown by the desktop app."""

from __future__ import annotations

import logging
import threading
from collections import deque
from pathlib import Path

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"


class LogBuffer(logging.Handler):
    """Keep the most recent log records in memory for the log viewer."""

    def __init__(self, capacity: int = 1000, level: int = logging.INFO):
        super().__init__(level=level)
        self._lines: deque[str] = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:  # pragma: no cover - logging must never raise
            self.handleError(record)
            return
        with self._lock:
            self._lines.append(message)

    @property
    def lines(self) -> list[str]:
        with self._lock:
            return list(self._lines)


log_buffer = LogBuffer()
log_buffer.setFormatter(logging.Formatter(LOG_FORMAT))


def attach_log_buffer() -> LogBuffer:
    """Attach the shared buffer to the root logger exactly once."""
    root = logging.getLogger()
    if log_buffer not in root.handlers:
        root.addHandler(log_buffer)
    return log_buffer


def configure_logging(level: str = "INFO", logfile: str | None = None) -> None:
    """Configure root logging (stderr plus an optional file).

    ``force=True`` replaces handlers installed by previous calls, so this is
    safe to call from both test code and the GUI entry point.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if logfile:
        path = Path(logfile).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, str(level).upper(), logging.INFO),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=handlers,
        force=True,
    )


__all__ = [
    "LOG_DATE_FORMAT",
    "LOG_FORMAT",
    "LogBuffer",
    "attach_log_buffer",
    "configure_logging",
    "log_buffer",
]
