import gettext
from pathlib import Path
from typing import Callable

DOMAIN = "app"


def get_translator(lang: str) -> Callable[..., str]:
    locales_dir = Path(__file__).resolve().parent.parent / "locales"
    t = gettext.translation(
        DOMAIN,
        localedir=str(locales_dir),
        languages=[lang],
        fallback=True,
    )
    return t.gettext
