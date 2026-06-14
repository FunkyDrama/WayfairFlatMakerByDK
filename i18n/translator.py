"""Helpers for loading gettext translators."""

import gettext
from pathlib import Path
from typing import Callable

Translator = Callable[[str], str]
DOMAIN = "app"

_cache: dict[str, Translator] = {}


def get_translator(lang: str) -> Translator:
    """Return a cached gettext translator for the requested language code."""

    if lang in _cache:
        return _cache[lang]
    locales_dir = Path(__file__).resolve().parent.parent / "locales"
    t = gettext.translation(
        DOMAIN,
        localedir=str(locales_dir),
        languages=[lang],
        fallback=True,
    )
    _cache[lang] = t.gettext
    return _cache[lang]
