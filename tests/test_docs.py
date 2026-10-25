"""Documentation guardrails.

If a document is moved, renamed or deleted, these tests fail before readers (or
agents) follow a stale link. They also keep the version in the changelog in sync
with the package.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

import pytest

from bangumi_catcher import __version__
from tests.helpers import REPOSITORY_ROOT

DOCS = REPOSITORY_ROOT / "docs"
MARKDOWN_FILES = sorted(
    [
        REPOSITORY_ROOT / name
        for name in ("README.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "CHANGELOG.md")
    ]
    + list(DOCS.rglob("*.md"))
)

REQUIRED_FILES = [
    REPOSITORY_ROOT / "README.md",
    REPOSITORY_ROOT / "AGENTS.md",
    REPOSITORY_ROOT / "CLAUDE.md",
    REPOSITORY_ROOT / "CONTRIBUTING.md",
    REPOSITORY_ROOT / "CHANGELOG.md",
    REPOSITORY_ROOT / "LICENSE",
    DOCS / "README.md",
    DOCS / "architecture.md",
    DOCS / "development.md",
    DOCS / "testing.md",
    DOCS / "conventions.md",
    DOCS / "data-model.md",
    DOCS / "configuration.md",
    DOCS / "packaging.md",
    DOCS / "migration-4.0.md",
    DOCS / "playbooks" / "README.md",
    DOCS / "playbooks" / "add-chart.md",
    DOCS / "playbooks" / "add-export-format.md",
    DOCS / "playbooks" / "add-config-option.md",
    DOCS / "playbooks" / "debug-fetch.md",
    DOCS / "adr" / "README.md",
    DOCS / "adr" / "0001-layered-architecture.md",
    DOCS / "adr" / "0002-src-layout-and-agent-docs.md",
    DOCS / "adr" / "0003-offline-first-testing.md",
    DOCS / "adr" / "0004-charts-and-reporting-split.md",
    REPOSITORY_ROOT / "docs" / "assets" / "screenshots" / "overview.png",
    REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml",
    REPOSITORY_ROOT / ".github" / "workflows" / "release.yml",
    REPOSITORY_ROOT / ".pre-commit-config.yaml",
    REPOSITORY_ROOT / "Makefile",
    REPOSITORY_ROOT / "scripts" / "dev.py",
]

LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _relative_links(markdown: Path) -> list[str]:
    links: list[str] = []
    for raw in LINK_PATTERN.findall(markdown.read_text(encoding="utf-8")):
        target = raw.strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        target = target.split(' "', 1)[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path_part = unquote(target.split("#", 1)[0])
        if path_part:
            links.append(path_part)
    return links


@pytest.mark.parametrize("path", REQUIRED_FILES, ids=lambda path: str(path.relative_to(REPOSITORY_ROOT)))
def test_required_files_exist(path):
    assert path.is_file(), f"missing required file: {path}"


@pytest.mark.parametrize("markdown", MARKDOWN_FILES, ids=lambda path: str(path.relative_to(REPOSITORY_ROOT)))
def test_relative_markdown_links_resolve(markdown):
    for target in _relative_links(markdown):
        resolved = (markdown.parent / target).resolve()
        assert resolved.exists(), f"{markdown.relative_to(REPOSITORY_ROOT)} -> {target}"


def test_docs_index_covers_main_topics():
    text = (DOCS / "README.md").read_text(encoding="utf-8")
    for target in (
        "architecture.md",
        "development.md",
        "testing.md",
        "conventions.md",
        "data-model.md",
        "configuration.md",
        "packaging.md",
        "migration-4.0.md",
        "playbooks/README.md",
        "adr/README.md",
    ):
        assert f"]({target})" in text, f"docs/README.md does not link {target}"


def test_adr_index_links_every_adr():
    index = (DOCS / "adr" / "README.md").read_text(encoding="utf-8")
    for adr in (DOCS / "adr").glob("[0-9]*.md"):
        assert f"]({adr.name})" in index, f"ADR index does not link {adr.name}"


def test_playbook_index_links_every_playbook():
    index = (DOCS / "playbooks" / "README.md").read_text(encoding="utf-8")
    for playbook in (DOCS / "playbooks").glob("*.md"):
        if playbook.name == "README.md":
            continue
        assert f"]({playbook.name})" in index, f"playbook index does not link {playbook.name}"


def test_changelog_contains_current_version():
    changelog = (REPOSITORY_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{__version__}]" in changelog


def test_agents_mentions_definition_of_done_and_key_files():
    text = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for needle in (
        "scripts/dev.py check",
        "tests/fakes.py",
        "docs/architecture.md",
        "tests/architecture/test_layers.py",
        "只读",
    ):
        assert needle in text, f"AGENTS.md lost key reference: {needle}"


def test_readme_points_to_agent_and_contributor_docs():
    text = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
    for needle in ("AGENTS.md", "docs/README.md", "CONTRIBUTING.md", "docs/assets/screenshots/overview.png"):
        assert needle in text, f"README.md does not reference {needle}"


def test_readme_declares_current_version_family():
    text = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
    assert __version__.split(".")[0] in text


def test_screenshots_exist():
    for name in ("overview.png", "library.png", "dark.png", "charts.png", "settings.png"):
        path = DOCS / "assets" / "screenshots" / name
        assert path.is_file() and path.stat().st_size > 0, path
