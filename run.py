"""Development entry point: ``python run.py``.

Adds ``src/`` to ``sys.path`` so the desktop can be launched from a checkout
without installing the package first. The canonical entry point remains
``python -m bangumi_catcher`` after ``pip install -e .``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from bangumi_catcher.ui.app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
