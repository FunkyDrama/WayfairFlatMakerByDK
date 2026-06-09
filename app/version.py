"""Application version helpers."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import tomllib
from typing import Any

APP_TITLE = "Wayfair Flat Maker by Daniel K©"
PROJECT_NAME = "wayfairflatmakerbydk"
UNKNOWN_VERSION = "unknown"


def get_app_version() -> str:
    """Return the current application version from package metadata or pyproject."""

    try:
        return version(PROJECT_NAME)
    except PackageNotFoundError:
        return get_pyproject_version()


def get_pyproject_version() -> str:
    """Return the version declared in pyproject.toml when metadata is unavailable."""

    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        with pyproject_path.open("rb") as file:
            project_data: dict[str, Any] = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        return UNKNOWN_VERSION

    version_value = project_data.get("project", {}).get("version")
    return version_value if isinstance(version_value, str) else UNKNOWN_VERSION


def get_page_title() -> str:
    """Return the window title with the current application version."""

    return f"{APP_TITLE} v{get_app_version()}"
