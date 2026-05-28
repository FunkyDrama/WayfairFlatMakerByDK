"""Utility helpers shared by the UI and validation layers."""

import re
from typing import Callable
from urllib.parse import urlparse

from app.constants import (
    DECAL_SIZE_PRESETS,
    URL_PATTERN,
    WALLPAPER_SIZE_PRESETS,
)

Translator = Callable[[str], str]
HintSets = tuple[list[str], list[str]]


def get_hint_sets(
    print_type_value: str | None,
    translate: Translator,
) -> HintSets:
    """Return width and height hints for the selected print type."""

    if not print_type_value:
        return [""], [""]

    if print_type_value == "wallpapers":
        width_hints = [str(width) for width, _ in WALLPAPER_SIZE_PRESETS]
        height_hints = [str(height) for _, height in WALLPAPER_SIZE_PRESETS]
        return width_hints, height_hints

    width_hints = [str(width) for width, _ in DECAL_SIZE_PRESETS]
    height_hints = [str(height) for _, height in DECAL_SIZE_PRESETS]
    return width_hints, height_hints


def extract_hint_value(hint_text: str | None) -> str:
    """Extract the first numeric token from a hint string."""

    if not hint_text:
        return ""
    match = re.search(r"\d+(?:[.,]\d+)?", hint_text)
    return match.group(0).replace(",", ".") if match else ""


def contains_link(value: str) -> bool:
    """Return ``True`` when the text looks like it contains a URL."""

    return bool(URL_PATTERN.search(value))


def is_valid_url(value: str) -> bool:
    """Validate a URL against the schemes accepted by the form."""

    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
