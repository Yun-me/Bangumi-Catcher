#!/usr/bin/env python3
"""Repository task runner.

One entry point for humans, CI and coding agents, independent of the shell::

    python scripts/dev.py setup
    python scripts/dev.py fmt
    python scripts/dev.py check
    python scripts/dev.py test -- -k ui
    python scripts/dev.py run
    python scripts/dev.py cli -- fetch alice --format json

The script only shells out to the current interpreter, so it works on Windows,
macOS and Linux without Make, and it always prefers the ``src`` tree over an
accidentally installed copy of the package.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DEFAULT_PATHS = ["src", "tests", "scripts"]


def environment() -> dict[str, str]:
    """Environment for child processes: src on ``PYTHONPATH``, headless Qt."""
    variables = os.environ.copy()
    existing = variables.get("PYTHONPATH")
    variables["PYTHONPATH"] = str(SRC) if not existing else str(SRC) + os.pathsep + existing
    variables.setdefault("QT_QPA_PLATFORM", "offscreen")
    variables.setdefault("PYTHONIOENCODING", "utf-8")
    return variables


def run(command: list[str]) -> int:
    print("$ " + " ".join(command), flush=True)
    return subprocess.call(command, cwd=ROOT, env=environment())


def python_module(module: str, *arguments: str) -> int:
    return run([sys.executable, "-m", module, *arguments])


def _paths(arguments: list[str] | None) -> list[str]:
    return arguments or DEFAULT_PATHS


def _passthrough(arguments: list[str]) -> list[str]:
    return arguments[1:] if arguments[:1] == ["--"] else arguments


# -- tasks -----------------------------------------------------------------


def setup() -> int:
    return run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"])


def fmt(paths: list[str] | None) -> int:
    targets = _paths(paths)
    status = python_module("ruff", "format", *targets)
    return status or python_module("ruff", "check", "--fix", *targets)


def lint(paths: list[str] | None) -> int:
    return python_module("ruff", "check", *_paths(paths))


def typecheck() -> int:
    return python_module("mypy")


def test(arguments: list[str]) -> int:
    return python_module("pytest", *_passthrough(arguments))


def coverage(arguments: list[str]) -> int:
    return python_module(
        "pytest",
        "--cov=bangumi_catcher",
        "--cov-report=term-missing",
        "--cov-report=xml",
        *_passthrough(arguments),
    )


def check() -> int:
    for step in (lambda: lint(None), typecheck, lambda: test([])):
        status = step()
        if status:
            return status
    return 0


def run_app() -> int:
    return python_module("bangumi_catcher")


def run_cli(arguments: list[str]) -> int:
    return python_module("bangumi_catcher.cli", *_passthrough(arguments))


def build_package() -> int:
    return python_module("build")


def package_app(arguments: list[str]) -> int:
    return run([sys.executable, str(ROOT / "scripts" / "build.py"), *_passthrough(arguments)])


def smoke() -> int:
    checks = [
        [sys.executable, "-m", "bangumi_catcher.cli", "version"],
        [sys.executable, "-m", "bangumi_catcher.cli", "--help"],
        [sys.executable, "-c", "import bangumi_catcher.ui.main_window"],
        [sys.executable, "-c", "import bangumi_catcher.api, bangumi_catcher.reporting"],
    ]
    for command in checks:
        status = run(command)
        if status:
            return status
    return 0


def clean() -> int:
    """Remove build artefacts and caches; never touches user exports."""
    for name in (
        "build",
        "dist",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".coverage",
        "htmlcov",
        "coverage.xml",
    ):
        target = ROOT / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    for directory in ("src", "tests", "scripts"):
        for cache in (ROOT / directory).rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
    for egg_info in ROOT.glob("*.egg-info"):
        shutil.rmtree(egg_info, ignore_errors=True)
    for spec in ROOT.glob("*.spec"):
        spec.unlink()
    print("clean: done")
    return 0


TASKS = {
    "setup": "install the package in editable mode with dev extras",
    "fmt": "format and auto-fix with ruff",
    "lint": "check lint rules with ruff",
    "type": "run mypy over the Qt-free layers",
    "test": "run pytest (pass extra args after --)",
    "cov": "run pytest with a coverage report",
    "check": "lint + type + test (the definition of done)",
    "run": "launch the desktop application",
    "cli": "run the CLI (pass args after --)",
    "build": "build the sdist and wheel",
    "package": "build a PyInstaller bundle (requires .[packaging])",
    "smoke": "import smoke tests and CLI --help",
    "clean": "remove build artefacts and caches",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/dev.py",
        description="Project tasks for Bangumi Catcher.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(f"  {name:<8} {help}" for name, help in TASKS.items()),
    )
    sub = parser.add_subparsers(dest="task", required=True)

    for name in ("fmt", "lint"):
        command = sub.add_parser(name, help=TASKS[name])
        command.add_argument("paths", nargs="*", help="files or directories (default: src tests scripts)")

    for name in ("test", "cov"):
        command = sub.add_parser(name, help=TASKS[name])
        command.add_argument("arguments", nargs=argparse.REMAINDER, help="pytest arguments")

    cli = sub.add_parser("cli", help=TASKS["cli"])
    cli.add_argument("arguments", nargs=argparse.REMAINDER, help="CLI arguments")

    package = sub.add_parser("package", help=TASKS["package"])
    package.add_argument("arguments", nargs=argparse.REMAINDER, help="scripts/build.py arguments")

    for name in ("setup", "type", "check", "run", "build", "smoke", "clean"):
        sub.add_parser(name, help=TASKS[name])
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    task = arguments.task

    if task == "setup":
        return setup()
    if task == "fmt":
        return fmt(arguments.paths)
    if task == "lint":
        return lint(arguments.paths)
    if task == "type":
        return typecheck()
    if task == "test":
        return test(arguments.arguments)
    if task == "cov":
        return coverage(arguments.arguments)
    if task == "check":
        return check()
    if task == "run":
        return run_app()
    if task == "cli":
        return run_cli(arguments.arguments)
    if task == "build":
        return build_package()
    if task == "package":
        return package_app(arguments.arguments)
    if task == "smoke":
        return smoke()
    if task == "clean":
        return clean()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
