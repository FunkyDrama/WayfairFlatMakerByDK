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
SUCCESS_SNACKBAR_DURATION_MS: int = 10000

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

# Wayfair's main-image rule; the AI check only warns, it never blocks export.
MIN_MAIN_IMAGE_DESIGN_COVERAGE_PERCENT: int = 75
MAIN_IMAGE_CHECK_DELAY_SECONDS: float = 1.0
# Entered decal proportions may differ from the design's by this factor before
# a warning; covers rounding to whole inches and small AI box errors.
SIZE_PROPORTION_TOLERANCE: float = 1.15

AUTOFILL_HELPER_TEXT: str = "Press Enter to autofill."
