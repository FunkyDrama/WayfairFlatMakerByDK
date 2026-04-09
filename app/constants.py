"""Application-wide constants used by the Flet UI."""

import re
from re import Pattern

LanguageOption = tuple[str, str]
SizePricePreset = tuple[int, int, str]

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

WALLPAPER_SIZE_PRICE_PRESETS: tuple[SizePricePreset, ...] = (
    (8, 10, "11.99"),
    (50, 75, "289.99"),
    (70, 100, "349.99"),
    (80, 120, "459.99"),
    (100, 145, "599.99"),
    (120, 165, "679.99"),
)

DECAL_SIZE_PRICE_PRESETS: tuple[SizePricePreset, ...] = (
    (16, 22, "16.99"),
    (22, 30, "27.99"),
    (35, 48, "60.99"),
    (44, 60, "79.99"),
)

MAIN_IMAGE_WARNING: str = (
    "Image Link #1 warning: the design must cover at least 75 percent of the full "
    "room/staged image."
)

AUTOFILL_HELPER_TEXT: str = "Press Enter to autofill."
