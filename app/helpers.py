"""Utility helpers shared by the UI and validation layers."""

from enum import Enum
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable
from urllib.parse import urlparse

from app.constants import (
    SizePreset,
    DECAL_SIZE_PRESETS,
    SIZE_PROPORTION_TOLERANCE,
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


def open_file(path: Path) -> None:
    """Open a file with the operating system's default application."""

    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def reveal_file(path: Path) -> None:
    """Show a file selected in Finder or Explorer, or open its folder."""

    if sys.platform == "win32":
        subprocess.Popen(["explorer", f"/select,{path}"])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path.parent)])


def size_presets(print_type_value: str | None) -> tuple[SizePreset, ...]:
    """Return the standard (width, height) sizes for a print type."""

    if print_type_value == "wallpapers":
        return WALLPAPER_SIZE_PRESETS
    if print_type_value == "decals":
        return DECAL_SIZE_PRESETS
    return ()


class SizeIssue(Enum):
    """Why an entered size looks wrong."""

    SWAPPED = "swapped"
    PROPORTIONS = "proportions"


def proportion_mismatch(ratio: float, design_ratio: float) -> float:
    """Return how many times two width/height ratios differ (1.0 = equal)."""

    return max(ratio / design_ratio, design_ratio / ratio)


def check_size(
    width: int,
    height: int,
    presets: tuple[SizePreset, ...],
    design_ratio: float | None,
) -> SizeIssue | None:
    """Return what looks wrong with a width x height size, if anything.

    With the design's proportions (from the AI image check) the size must keep
    them: if only the flipped size does, width and height were swapped;
    otherwise the proportions are off. Without them, a size that matches a
    standard preset only when flipped is the tell-tale sign of a swap.
    """

    if width <= 0 or height <= 0:
        return None
    if design_ratio:
        ratio = width / height
        if proportion_mismatch(ratio, design_ratio) <= SIZE_PROPORTION_TOLERANCE:
            return None
        if proportion_mismatch(1 / ratio, design_ratio) <= SIZE_PROPORTION_TOLERANCE:
            return SizeIssue.SWAPPED
        return SizeIssue.PROPORTIONS
    if (
        width != height
        and (height, width) in presets
        and (width, height) not in presets
    ):
        return SizeIssue.SWAPPED
    return None


def matching_height(width: int, design_ratio: float) -> int:
    """Return the whole-inch height that keeps the design's proportions."""

    return max(1, round(width / design_ratio))
