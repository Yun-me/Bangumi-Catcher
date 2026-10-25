"""Write-to-temporary-then-rename helper used by every exporter.

A failed or cancelled export must never truncate an existing file, so writers
only ever see a temporary sibling path. ``os.replace`` is atomic on the same
filesystem, which is why the temporary file is created next to the target.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def atomic_output(target: str | Path) -> Iterator[Path]:
    """Yield a temporary path and atomically move it to ``target`` on success."""
    destination = Path(target).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        yield temporary
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


__all__ = ["atomic_output"]
