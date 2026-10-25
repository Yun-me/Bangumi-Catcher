"""Shared fixtures and test isolation.

Every test runs offline: proxy variables and ``BANGUMI_*`` overrides are
removed, the repository/user configuration files are redirected into ``tmp_path``
and the real HTTP transport is replaced with a guard that raises. Tests that
genuinely need the network must opt in with ``@pytest.mark.network``.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from tests.factories import make_sample_collection

_PROXY_VARIABLES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    """Make configuration discovery and HTTP behaviour deterministic."""
    for name in _PROXY_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    for name in [key for key in os.environ if key.startswith("BANGUMI_")]:
        monkeypatch.delenv(name, raising=False)

    from bangumi_catcher.core.config import paths

    monkeypatch.setattr(paths, "working_dir_config_path", lambda cwd=None: tmp_path / "config.yaml")
    monkeypatch.setattr(paths, "repository_config_path", lambda: None)
    monkeypatch.setattr(paths, "user_config_path", lambda: tmp_path / "preferences.yaml")


@pytest.fixture(autouse=True)
def block_real_http(request, monkeypatch):
    """Fail loudly if a test tries to open a real HTTP connection."""
    if request.node.get_closest_marker("network"):
        return
    import httpx

    def deny(self, request):
        raise RuntimeError("tests must not use the network; inject a fake transport")

    async def deny_async(self, request):
        raise RuntimeError("tests must not use the network; inject a fake transport")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", deny)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", deny_async)


@pytest.fixture
def sample_collection():
    """Five deterministic entries covering finished/wish/watching states."""
    return make_sample_collection()


@pytest.fixture(scope="session")
def qapp():
    """One offscreen ``QApplication`` shared by all UI tests."""
    from PySide6 import QtGui, QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    if not QtGui.QFontDatabase.families():
        for name in ("msyh.ttc", "msyhbd.ttc", "segoeui.ttf", "seguisb.ttf"):
            path = Path("C:/Windows/Fonts") / name
            if path.exists():
                QtGui.QFontDatabase.addApplicationFont(str(path))
    return app
