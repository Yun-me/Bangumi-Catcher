"""Small helpers shared by tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"


def run_python(
    code: str, *, cwd: Path | None = None, timeout: float = 120.0
) -> subprocess.CompletedProcess[str]:
    """Run ``code`` in a fresh interpreter that can import the src tree.

    Used by tests that must observe import side effects (for example, proving
    that importing the desktop does not load Matplotlib).
    """
    environment = os.environ.copy()
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = str(SOURCE_ROOT) if not existing else str(SOURCE_ROOT) + os.pathsep + existing
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(cwd or REPOSITORY_ROOT),
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def read_fixture(name: str) -> str:
    """Return the text of a file under ``tests/fixtures``."""
    return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")


__all__ = ["REPOSITORY_ROOT", "SOURCE_ROOT", "read_fixture", "run_python"]
