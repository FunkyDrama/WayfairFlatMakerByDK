"""Application runtime settings."""

import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file_path() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller / flet pack: look next to the executable
        return Path(sys.executable).parent / ".env"
    # Development: project root (two levels up from this file)
    return Path(__file__).resolve().parent.parent / ".env"


class AppSettings(BaseSettings):
    """Environment-driven application settings."""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(
        env_file=str(_env_file_path()),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = AppSettings()
