import flet as ft

from app import WayfairFlatMaker


async def main(page: ft.Page) -> None:
    """Главная функция, которая запускает приложение"""
    prefs = ft.SharedPreferences()
    page.services.append(prefs)
    stored_lang = await prefs.get("lang")
    lang = stored_lang or "en"
    WayfairFlatMaker(page, lang, prefs)


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
