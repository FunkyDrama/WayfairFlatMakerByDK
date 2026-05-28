"""Application-wide constants used by the Flet UI."""

import re
from re import Pattern

LanguageOption = tuple[str, str]
SizePreset = tuple[int, int]

SUPPORTED_LANGUAGES: tuple[LanguageOption, ...] = (
    ("ru", "Русский"),
    ("uk", "Українська"),
    ("en", "English"),
    ("sq", "Shqip"),
)

URL_PATTERN: Pattern[str] = re.compile(r"(?i)(https?://|www\.|dropbox\.com)")

ERROR_HIGHLIGHT_DURATION_SECONDS: int = 5
ERROR_SNACKBAR_DURATION_MS: int = 7000
SUCCESS_SNACKBAR_DURATION_MS: int = 4500

WALLPAPER_SIZE_PRESETS: tuple[SizePreset, ...] = (
    (8, 10),
    (50, 75),
    (60, 96),
    (70, 100),
    (80, 120),
    (100, 120),
    (100, 144),
    (110, 165),
    (120, 165),
)

DECAL_SIZE_PRESETS: tuple[SizePreset, ...] = (
    (10, 14),
    (22, 24),
    (35, 35),
    (55, 22),
    (75, 35),
    (95, 50),
)

MAIN_IMAGE_WARNING: str = (
    "Image Link #1 warning: the design must cover at least 75 percent of the full "
    "room/staged image."
)

AUTOFILL_HELPER_TEXT: str = "Press Enter to autofill."
