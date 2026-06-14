"""Application runtime settings."""

import os
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str | None:
    candidates: list[Path] = []

    # flet build (Flutter): Flet sets this to the platform user-data dir
    flet_storage = os.environ.get("FLET_APP_STORAGE_DATA")
    if flet_storage:
        candidates.append(Path(flet_storage) / ".env")

    # flet pack (PyInstaller): bundled data extracted to _MEIPASS, fallback next to executable
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / ".env")
        candidates.append(Path(sys.executable).parent / ".env")

    # Development: project root (two levels up from this file)
    candidates.append(Path(__file__).resolve().parent.parent / ".env")

    # CWD fallback
    candidates.append(Path.cwd() / ".env")

    for path in candidates:
        try:
            if path.is_file():
                return str(path)
        except (OSError, PermissionError):
            pass

    return None


class AppSettings(BaseSettings):
    """Environment-driven application settings."""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = AppSettings()
