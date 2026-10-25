"""Filesystem locations used by the application.

Everything that depends on the operating system, the current working directory
or environment variables lives here so the loader and the CLI can stay pure
functions of their arguments.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIRNAME = "bangumi-catcher"
CONFIG_FILENAME = "config.yaml"
CONFIG_ENV_VAR = "BANGUMI_CONFIG"
ENV_PREFIX = "BANGUMI_"


def user_config_path() -> Path:
    """Per-user preferences file.

    * Windows: ``%APPDATA%/bangumi-catcher/config.yaml``
    * macOS: ``~/Library/Application Support/bangumi-catcher/config.yaml``
    * Linux: ``${XDG_CONFIG_HOME:-~/.config}/bangumi-catcher/config.yaml``
    """
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return root / APP_DIRNAME / CONFIG_FILENAME


def working_dir_config_path(cwd: Path | None = None) -> Path:
    """``./config.yaml`` for the directory the program was started from."""
    return (cwd or Path.cwd()) / CONFIG_FILENAME


def repository_config_path() -> Path | None:
    """The checkout's own ``config.yaml``, or ``None`` for an installed package."""
    repository_root = Path(__file__).resolve().parents[4]
    if (repository_root / "pyproject.toml").is_file():
        return repository_root / CONFIG_FILENAME
    return None


def bundled_config_path() -> Path | None:
    """``config.yaml`` next to the package (PyInstaller onedir/onefile bundles it)."""
    candidate = Path(__file__).resolve().parents[2] / CONFIG_FILENAME
    return candidate if candidate.is_file() else None


def default_cache_dir() -> Path:
    """Default disk cache location (kept stable for backwards compatibility)."""
    return Path.home() / ".cache" / APP_DIRNAME


def config_search_paths(explicit: str | Path | None = None) -> list[Path]:
    """Ordered configuration files to merge, lowest precedence first.

    * explicit ``--config`` path (or ``BANGUMI_CONFIG``) replaces the project
      search but is still followed by environment-variable overrides;
    * otherwise the first project file found (working directory, then checkout)
      is merged with the user preferences file.
    """
    if explicit is not None:
        return [Path(explicit).expanduser()]

    env_path = os.environ.get(CONFIG_ENV_VAR)
    if env_path:
        return [Path(env_path).expanduser()]

    paths: list[Path] = []
    working = working_dir_config_path()
    repository = repository_config_path()
    bundled = bundled_config_path()
    if working.is_file():
        paths.append(working)
    elif repository is not None and repository.is_file():
        paths.append(repository)
    elif bundled is not None:
        paths.append(bundled)

    personal = user_config_path()
    if personal.is_file():
        paths.append(personal)
    return paths


__all__ = [
    "APP_DIRNAME",
    "CONFIG_ENV_VAR",
    "CONFIG_FILENAME",
    "ENV_PREFIX",
    "bundled_config_path",
    "config_search_paths",
    "default_cache_dir",
    "repository_config_path",
    "user_config_path",
    "working_dir_config_path",
]
