"""Application entry point."""

import flet as ft

from app.diagnostics import (
    get_logger,
    install_asyncio_exception_handler,
    setup_logging,
)
from app.settings import settings
from app.version import get_app_version

# Logging starts before the UI modules load, so their import failures are logged.
setup_logging(get_app_version(), secrets=[settings.gemini_api_key])

from app.flat_maker import WayfairFlatMaker  # noqa: E402

logger = get_logger("main")


async def main(page: ft.Page) -> None:
    """Initialize shared preferences and launch the main UI."""

    install_asyncio_exception_handler()
    prefs = ft.SharedPreferences()
    stored_lang = await prefs.get("lang")
    lang = stored_lang if isinstance(stored_lang, str) and stored_lang else "en"
    logger.info("UI starting with language %s", lang)
    WayfairFlatMaker(page, lang, prefs)


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
