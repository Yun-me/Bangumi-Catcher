"""PySide6 desktop layer.

Importing this package has no side effects; the application is created by
:func:`bangumi_catcher.ui.app.main`. The layer may import any other package,
but nothing outside ``ui`` and ``cli`` may import it — see
``tests/architecture/test_layers.py``.
"""

from __future__ import annotations

__all__: list[str] = []
