"""Helpers for loading gettext translators."""

import gettext
from pathlib import Path
from typing import Callable

Translator = Callable[[str], str]
DOMAIN = "app"


def get_translator(lang: str) -> Translator:
    """Return a gettext translator for the requested language code."""

    locales_dir = Path(__file__).resolve().parent.parent / "locales"
    t = gettext.translation(
        DOMAIN,
        localedir=str(locales_dir),
        languages=[lang],
        fallback=True,
    )
    return t.gettext
