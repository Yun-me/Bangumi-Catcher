"""Packaging metadata guardrails.

These tests catch the classic "works from a checkout, broken after install"
failures: wrong package dir, missing template data, stale console-script target,
version drift between ``pyproject.toml`` and ``__init__.py``.
"""

from __future__ import annotations

import importlib
import sys

import pytest
import yaml

from bangumi_catcher import __version__
from tests.helpers import REPOSITORY_ROOT

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.9/3.10
    import tomli as tomllib

PYPROJECT_PATH = REPOSITORY_ROOT / "pyproject.toml"
PYPROJECT = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
PROJECT = PYPROJECT["project"]
SETUPTOOLS = PYPROJECT["tool"]["setuptools"]


def test_version_matches_package():
    assert PROJECT["version"] == __version__


def test_package_name_and_readme():
    assert PROJECT["name"] == "bangumi-catcher"
    assert PROJECT["readme"] == "README.md"
    assert (REPOSITORY_ROOT / PROJECT["readme"]).is_file()


def test_license_is_mit():
    assert "MIT" in str(PROJECT["license"])
    assert (REPOSITORY_ROOT / "LICENSE").is_file()


def test_src_layout_is_configured():
    assert SETUPTOOLS["package-dir"] == {"": "src"}
    assert (REPOSITORY_ROOT / "src" / "bangumi_catcher" / "__init__.py").is_file()
    assert not (REPOSITORY_ROOT / "bangumi_catcher").exists(), "flat package must not exist"


def test_package_data_contains_template_and_py_typed():
    package_data = SETUPTOOLS["package-data"]["bangumi_catcher"]
    assert "templates/*.j2" in package_data
    assert "py.typed" in package_data
    assert (REPOSITORY_ROOT / "src" / "bangumi_catcher" / "templates" / "report.html.j2").is_file()
    assert (REPOSITORY_ROOT / "src" / "bangumi_catcher" / "py.typed").is_file()


@pytest.mark.parametrize(("name", "target"), sorted(PROJECT["scripts"].items()))
def test_console_script_targets_are_importable(name, target):
    module_name, separator, attribute = target.partition(":")
    assert separator == ":", f"invalid console script target: {name}={target}"
    module = importlib.import_module(module_name)
    assert callable(getattr(module, attribute))


def test_console_scripts_cover_gui_and_cli():
    scripts = PROJECT["scripts"]
    assert scripts["bangumi-catcher"].startswith("bangumi_catcher.ui.app:")
    assert scripts["bangumi-catcher-cli"].startswith("bangumi_catcher.cli:")


def test_pytest_configuration_is_hermetic():
    options = PYPROJECT["tool"]["pytest"]["ini_options"]
    assert "src" in options["pythonpath"]
    assert "tests" in options["testpaths"]
    markers = " ".join(options["markers"])
    assert "network" in markers
    assert "ui" in markers


def test_dev_extras_include_tooling():
    extras = PROJECT["optional-dependencies"]["dev"]
    joined = " ".join(extras)
    for requirement in ("pytest", "pytest-cov", "ruff", "mypy", "build"):
        assert requirement in joined, f"dev extras missing {requirement}"
    assert any(requirement.startswith("tomli") for requirement in extras)


def test_packaging_extra_includes_pyinstaller():
    extras = PROJECT["optional-dependencies"]["packaging"]
    assert any(requirement.startswith("pyinstaller") for requirement in extras)


def test_python_versions_are_declared():
    assert PROJECT["requires-python"] == ">=3.9"
    classifiers = " ".join(PROJECT["classifiers"])
    assert "3.9" in classifiers
    assert "3.13" in classifiers


def test_repository_urls_are_present():
    urls = PROJECT["urls"]
    assert urls["Repository"].endswith("Bangumi-Catcher")
    assert urls["Issues"].startswith("https://")


def test_requirements_txt_is_not_used():
    assert not (REPOSITORY_ROOT / "requirements.txt").exists(), (
        "requirements.txt was replaced by pyproject.toml; keep a single source of truth"
    )


def test_task_runner_and_packaging_scripts_exist():
    for name in ("dev.py", "build.py", "launch_gui.py"):
        assert (REPOSITORY_ROOT / "scripts" / name).is_file(), name


YAML_FILES = [
    REPOSITORY_ROOT / "config.yaml",
    REPOSITORY_ROOT / ".pre-commit-config.yaml",
    REPOSITORY_ROOT / ".github" / "dependabot.yml",
    REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml",
    REPOSITORY_ROOT / ".github" / "workflows" / "release.yml",
    REPOSITORY_ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml",
    REPOSITORY_ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml",
    REPOSITORY_ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml",
]


@pytest.mark.parametrize("path", YAML_FILES, ids=lambda path: path.name)
def test_yaml_files_parse(path):
    assert yaml.safe_load(path.read_text(encoding="utf-8")) is not None


def test_ci_workflow_runs_quality_and_tests():
    workflow = yaml.safe_load(
        (REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )
    jobs = workflow["jobs"]
    assert {"quality", "test", "package"} <= set(jobs)
    test_steps = " ".join(str(step) for step in jobs["test"]["steps"])
    assert "pytest" in test_steps


def test_build_script_uses_src_paths():
    script = (REPOSITORY_ROOT / "scripts" / "build.py").read_text(encoding="utf-8")
    assert "--paths" in script
    assert "templates" in script
    assert "launch_gui.py" in script


def test_python_version_floor_matches_runtime_support():
    # Guard against accidentally using a 3.10+ syntax in a way this test can catch
    # at the metadata level; the real compatibility check runs in CI on 3.9.
    assert sys.version_info >= (3, 9)
