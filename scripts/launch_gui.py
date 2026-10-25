"""PyInstaller entry point.

Kept separate from ``run.py`` so the frozen build never needs the repository on
``sys.path``; ``scripts/build.py`` passes ``--paths src`` to the analysis.
"""

from __future__ import annotations

from bangumi_catcher.ui.app import main

if __name__ == "__main__":
    raise SystemExit(main())
