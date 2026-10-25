"""Executable architecture rules.

The import graph is derived from the AST, so the rules are checked without
importing (and therefore without loading Qt or Matplotlib). The dependency
direction is documented in ``docs/architecture.md``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.helpers import REPOSITORY_ROOT, run_python

PACKAGE_ROOT = REPOSITORY_ROOT / "src" / "bangumi_catcher"
LAYERS = ("core", "api", "charts", "reporting", "services", "ui", "cli")

# layer -> first-party layers it may import (besides the root package & itself)
ALLOWED_LAYER_IMPORTS = {
    "core": {"core"},
    "api": {"api", "core"},
    "charts": {"charts", "core"},
    "reporting": {"reporting", "charts", "core"},
    "services": {"services", "reporting", "api", "core"},
    "ui": {"ui", "services", "reporting", "charts", "api", "core"},
    "cli": {"cli", "ui", "services", "reporting", "charts", "api", "core"},
}

NO_UI_OR_PLOTTING = {
    "PySide6",
    "matplotlib",
    "bangumi_catcher.ui",
    "bangumi_catcher.cli",
    "bangumi_catcher.charts",
}
NO_HTTP_STACK = {"httpx", "diskcache", "bangumi_catcher.api"}
NO_QT = {"PySide6", "bangumi_catcher.ui", "bangumi_catcher.cli"}


def _module_name(path: Path) -> str:
    relative = path.relative_to(PACKAGE_ROOT)
    parts = list(relative.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]
    return ".".join(["bangumi_catcher", *parts])


def _package_of(module: str, is_package: bool) -> str:
    return module if is_package else module.rpartition(".")[0]


def _resolve_relative(module: str, is_package: bool, level: int, target: str | None) -> str:
    package_parts = _package_of(module, is_package).split(".")
    base = package_parts[: len(package_parts) - (level - 1)]
    if target:
        base = [*base, *target.split(".")]
    return ".".join(base)


def _module_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    module = _module_name(path)
    is_package = path.name == "__init__.py"
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                imports.add(_resolve_relative(module, is_package, node.level, node.module))
            elif node.module:
                imports.add(node.module)
    return imports


def _top_level_imports(path: Path) -> set[str]:
    """Imports executed at module import time (function-level imports excluded)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    module = _module_name(path)
    is_package = path.name == "__init__.py"
    imports: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                imports.add(_resolve_relative(module, is_package, node.level, node.module))
            elif node.module:
                imports.add(node.module)
    return imports


def _layer(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) < 2 or parts[0] != "bangumi_catcher":
        return None
    return parts[1] if parts[1] in LAYERS else "shared"


def _modules(layer: str | None = None) -> list[Path]:
    root = PACKAGE_ROOT if layer is None else PACKAGE_ROOT / layer
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _matches(import_name: str, prefixes: set[str]) -> bool:
    return any(import_name == prefix or import_name.startswith(prefix + ".") for prefix in prefixes)


@pytest.mark.parametrize(
    "path", [p for p in _modules() if _layer(_module_name(p)) == "core"], ids=lambda p: _module_name(p)
)
def test_core_is_framework_free(path):
    imports = _module_imports(path)
    assert not any(_matches(name, NO_UI_OR_PLOTTING) for name in imports), imports
    assert not any(_matches(name, NO_HTTP_STACK) for name in imports), imports


@pytest.mark.parametrize("path", list(_modules("api")), ids=lambda p: _module_name(p))
def test_api_has_no_ui_or_plotting(path):
    imports = _module_imports(path)
    assert not any(_matches(name, NO_UI_OR_PLOTTING) for name in imports), imports


@pytest.mark.parametrize("path", list(_modules("charts")), ids=lambda p: _module_name(p))
def test_charts_depend_only_on_core_and_matplotlib(path):
    imports = _module_imports(path)
    assert not any(_matches(name, NO_HTTP_STACK | NO_QT) for name in imports), imports


@pytest.mark.parametrize("path", list(_modules("reporting")), ids=lambda p: _module_name(p))
def test_reporting_has_no_http_or_qt(path):
    imports = _module_imports(path)
    assert not any(_matches(name, NO_HTTP_STACK | NO_QT) for name in imports), imports


@pytest.mark.parametrize("path", list(_modules("services")), ids=lambda p: _module_name(p))
def test_services_are_headless(path):
    imports = _module_imports(path)
    assert not any(_matches(name, NO_QT) for name in imports), imports
    assert not any(_matches(name, {"matplotlib"}) for name in imports), imports


@pytest.mark.parametrize("path", list(_modules()), ids=lambda p: _module_name(p))
def test_import_direction_follows_layers(path):
    current = _layer(_module_name(path))
    if current not in ALLOWED_LAYER_IMPORTS:
        return
    allowed = ALLOWED_LAYER_IMPORTS[current] | {"shared", "root"}
    for target in _module_imports(path):
        target_layer = _layer(target)
        if target_layer in LAYERS or target_layer == "shared":
            assert target_layer in allowed, f"{_module_name(path)} -> {target}"


@pytest.mark.parametrize("path", list(_modules("ui")), ids=lambda p: _module_name(p))
def test_ui_imports_plotting_lazily(path):
    top_level = _top_level_imports(path)
    forbidden = {"matplotlib", "bangumi_catcher.charts.render", "bangumi_catcher.charts.builders"}
    assert not any(_matches(name, forbidden) for name in top_level), top_level


def test_cli_imports_qt_lazily():
    top_level = _top_level_imports(PACKAGE_ROOT / "cli" / "main.py")
    assert not any(_matches(name, {"PySide6", "bangumi_catcher.ui"}) for name in top_level)


def test_desktop_startup_does_not_load_matplotlib():
    result = run_python(
        "import sys; import bangumi_catcher.ui.app, bangumi_catcher.ui.main_window; "
        "assert 'matplotlib' not in sys.modules, sorted(sys.modules)"
    )
    assert result.returncode == 0, result.stderr


def test_chart_catalog_does_not_load_matplotlib():
    result = run_python(
        "import sys; from bangumi_catcher.charts.catalog import CHART_TITLES; "
        "assert 'matplotlib' not in sys.modules"
    )
    assert result.returncode == 0, result.stderr


def test_first_party_imports_never_reach_tests_or_scripts():
    for path in _modules():
        for name in _module_imports(path):
            assert not name.startswith(("tests", "scripts")), f"{_module_name(path)} -> {name}"
