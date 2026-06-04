# Wayfair Listing Spreadsheet Generator

Desktop app for generating Wayfair listing spreadsheets for print products such as decals and wallpapers.

The project is built with Flet, writes `.xlsx` files with `openpyxl`, and includes gettext-based localization for English, Russian, Ukrainian, and Albanian.

## Features

- Generate Wayfair-ready spreadsheets from a desktop form
- Support different product shaping flows for decals and wallpapers
- Use the bundled Excel template from `assets/template.xlsx`
- Switch the app language in the UI
- Manage translations with Babel and Makefile helpers
- Run linting and static type checks with Ruff and MyPy
- Build desktop bundles for macOS and Windows with Flet

## Requirements

- Python 3.12+
- [Poetry](https://python-poetry.org/)
- For macOS builds: full Xcode installation, not only Command Line Tools
- For Windows builds from macOS/Linux: Flet/Flutter build prerequisites as required by the target platform

## Installation

```bash
git clone https://github.com/FunkyDrama/WayfairFlatMakerByDK.git
cd WayfairFlatMakerByDK
poetry install
```

## Run The App

```bash
poetry run python main.py
```

## Project Structure

```text
.
├── app/
│   ├── __init__.py
│   ├── flat_maker.py      # Main UI/view-model class
│   ├── builder.py         # Control construction
│   ├── controls.py        # Reusable Flet control builders
│   ├── ui_ops.py          # UI update helpers
│   ├── submission.py      # Validation and submit flow
│   ├── validation.py      # Validation helpers
│   ├── helpers.py         # Shared utility helpers
│   ├── constants.py       # UI and preset constants
│   └── messages.py        # Translation anchor strings for Babel
├── data/
│   ├── data_shaper.py     # Compatibility exports for shapers
│   ├── base_shaper.py     # Shared shaper behavior
│   ├── decal_shaper.py    # Decal-specific data shaping
│   ├── wallpaper_shaper.py # Wallpaper-specific data shaping
│   ├── factory.py         # Shaper factory
│   ├── models.py          # Shared shaper models and types
│   ├── pricing.py         # Google Sheet price lookup and interpolation
│   └── excel_writer.py    # Excel template writer
├── i18n/
│   ├── babel.cfg          # Babel extraction config
│   └── translator.py      # gettext loader
├── locales/               # .pot/.po/.mo translation catalogs
├── assets/                # Template workbook and static assets
├── main.py                # Application entry point
├── Makefile               # i18n, checks, and build helpers
└── pyproject.toml         # Dependencies, Flet config, MyPy overrides
```

## How It Works
1. The user selects a print type (decal or wallpaper).
2. Fill the app form with title, SKU, keywords, images, and sizes.
3. The app shapes the data for the selected print type.
4. A completed `.xlsx` file is generated into the selected folder.

Wayfair path:
`Product Management -> Add Products -> Standard -> Quick Upload`

## Makefile Commands

### Localization

```bash
make i18n-extract
make i18n-update
make i18n-compile
make i18n-init LANG=de
make i18n-all
```

What they do:

- `i18n-extract`: extract translatable strings into `locales/app.pot`
- `i18n-update`: update existing catalogs from the template
- `i18n-compile`: compile `.po` files into `.mo`
- `i18n-init LANG=de`: create a new locale scaffold
- `i18n-all`: update and compile in one run

### Quality Checks

```bash
make check
```

This runs:

- `poetry run ruff format`
- `poetry run ruff check --fix`
- `poetry run mypy --check-untyped-defs .`

### Builds

```bash
make build-macos
make build-windows
make build-windows-onefile
```

Notes:

- `build-macos` runs `poetry run flet build macos`
- `build-windows` runs `poetry run flet build windows`
- `build-windows-onefile` runs `flet pack` with bundled `assets` and `locales`

## Flet Build Configuration

Build metadata is defined in `pyproject.toml` under:

- `[tool.flet]`
- `[tool.flet.app]`
- `[tool.flet.app.startup_screen]`
- `[tool.flet.macos]`
- `[tool.flet.windows]`

Equivalent direct commands:

```bash
poetry run flet build macos
poetry run flet build windows
```

## Localization Notes

- Runtime translations are loaded from `locales/<lang>/LC_MESSAGES/app.mo`
- Source catalogs live in `locales/<lang>/LC_MESSAGES/app.po`
- `app/messages.py` intentionally keeps strings that Babel would not reliably extract from indirect call sites or constants

If you add new UI text:

1. Update code
2. Run `make i18n-update`
3. Fill `msgstr` in each locale
4. Run `make i18n-compile`

## Dependencies

Runtime dependencies:

- [`flet[all]`](https://pypi.org/project/flet/)
- [`openpyxl`](https://pypi.org/project/openpyxl/)
- [`babel`](https://pypi.org/project/babel/)
- [`watchdog`](https://pypi.org/project/watchdog/)

Dev dependencies:

- [`ruff`](https://pypi.org/project/ruff/)
- [`mypy`](https://pypi.org/project/mypy/)

## Type Checking

Static typing is enabled and verified with:

```bash
poetry run mypy app data i18n main.py
```

`openpyxl` is configured via a MyPy override in `pyproject.toml` because type stubs are not installed for that library in this project.

## Notes About The Excel Template

The generated file is based on the bundled Wayfair template in `assets/template.xlsx`.

If some cells are protected in Excel or Google Sheets after generation, that comes from the template itself rather than from the export logic. The app writes values into the workbook but does not remove worksheet protection.

## License

This code is shared publicly with permission, but it is not provided under a traditional open-source license. Do not redistribute it commercially without prior agreement.
