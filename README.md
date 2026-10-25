# Wayfair Listing Spreadsheet Generator

Desktop app for generating Wayfair listing spreadsheets for print products such as decals and wallpapers.

The project is built with Flet, writes `.xlsx` files by filling the Wayfair template's XML directly (Python standard library only), and includes gettext-based localization for English, Russian, Ukrainian, and Albanian.

## Features

- Generate Wayfair-ready spreadsheets from a desktop form
- Support different product shaping flows for decals and wallpapers
- Use the bundled Excel template from `assets/template.xlsx`
- Switch the app language in the UI
- AI-assisted title and keyword generation via Google Gemini (optional)
- AI fills design-dependent attributes (subject, rooms, occasion, pattern, colors…) from the main image, using only the template's allowed values
- AI warns (never blocks) when the design covers less than 75% of the main image
- Hidden diagnostic log with weekly cleanup and a one-step report export
- Image previews inside each link field (broken links show a red icon; click to enlarge)
- Warns when width and height look swapped, with a one-click swap and a check before export
- Remembers the last save folder across sessions
- Price data is prefetched in the background at startup to avoid delays on first submission
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

## AI Integration (optional)

The app can suggest a listing title and keyword phrase by analyzing the first product image with Google Gemini.

To enable:

1. Create a `.env` file with your API key:

```env
GEMINI_API_KEY=your_api_key_here
```

Place it in the appropriate location:

| Mode | Location |
|------|----------|
| Development | project root (next to `main.py`) |
| `flet build` macOS | `~/Library/Application Support/com.funkydrama.wayfairflatmakerbydk/` |
| `flet build` Windows | `%APPDATA%\com.funkydrama.wayfairflatmakerbydk\` |
| `flet pack` (PyInstaller) | next to the executable |

2. Optionally override the models (defaults shown). The fallback model is used when the main model is overloaded:

```env
GEMINI_MODEL=gemini-3.5-flash
GEMINI_FALLBACK_MODEL=gemini-2.5-flash
```

When configured, a **✨ Suggest title & keywords** button appears on the form. The button is active only when the first image URL is filled and a print type is selected. Clicking it sends the image to Gemini and fills in the title and keyword fields.

Settings are loaded from the `.env` file via `app/settings.py` using `pydantic-settings`.

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
│   ├── gemini.py          # Google Gemini AI client
│   ├── settings.py        # Environment-driven app settings
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
│   └── translator.py      # gettext loader with in-memory cache
├── locales/               # .pot/.po/.mo translation catalogs
├── assets/                # Template workbook and static assets
├── main.py                # Application entry point
├── Makefile               # i18n, checks, and build helpers
└── pyproject.toml         # Dependencies, Flet config, MyPy overrides
```

## How It Works
1. The user selects a print type (decal or wallpaper).
2. Fill the app form with title, SKU, keywords, images, and sizes.
3. Optionally click **✨ Suggest title & keywords** to generate content with AI.
4. The app shapes the data for the selected print type.
5. A completed `.xlsx` file is generated into the selected folder.

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

### Releases

```bash
make release            # level chosen from commit messages since the last tag
make release BUMP=minor # or force major / minor / patch
git push origin main --follow-tags
```

`make release` runs `scripts/bump_version.py`: it raises `project.version` and `tool.flet.build_number` together, commits `chore(release): vX.Y.Z`, and creates the `vX.Y.Z` tag that triggers the build and GitHub Release. The level follows Conventional Commits: `feat:` → minor, `type!:` or `BREAKING CHANGE` → major, anything else → patch. Use `make release-dry-run` to preview.

The tag builds the Windows and macOS apps on GitHub Actions and uploads them to
the private Dropbox folder `/WayfairFlatMaker builds/vX.Y.Z` (manual runs go to
`manual-<run number>`). They are never stored as GitHub artifacts, because the
builds contain the Gemini key and artifacts of a public repository can be
downloaded by any signed-in GitHub user. The workflow needs these repository
secrets: `GEMINI_API_KEY`, `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`,
`DROPBOX_REFRESH_TOKEN` (the Dropbox app needs `files.content.write`).

Local `make build-macos` / `make build-windows` refuse to run while `.env`
contains Dropbox credentials, since `flet build` bundles `.env` into the app.

### Git Hooks

```bash
poetry run pre-commit install
```

Before each commit this runs Ruff (lint with fixes, then formatting), MyPy, basic TOML/YAML checks, and a guard that rejects changing the version without the build number (or the reverse).

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
- `[tool.flet.app.boot_screen]` and `[tool.flet.app.startup_screen]` (shown before Python starts, so their text cannot be translated)
- `[tool.flet.macos.info]`
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
- Loaded translators are cached in memory so the `.mo` file is parsed only once per language per session

If you add new UI text:

1. Update code
2. Run `make i18n-update`
3. Fill `msgstr` in each locale
4. Run `make i18n-compile`

## Dependencies

Runtime dependencies:

- [`flet[all]`](https://pypi.org/project/flet/)
- [`pillow`](https://pypi.org/project/pillow/) — shrinks images before AI analysis
- [`babel`](https://pypi.org/project/babel/)
- [`watchdog`](https://pypi.org/project/watchdog/)
- [`google-genai`](https://pypi.org/project/google-genai/) — Gemini AI SDK
- [`pydantic-settings`](https://pypi.org/project/pydantic-settings/) — `.env`-based config

Dev dependencies:

- [`ruff`](https://pypi.org/project/ruff/)
- [`mypy`](https://pypi.org/project/mypy/)

## Type Checking

Static typing is enabled and verified with:

```bash
poetry run mypy app data i18n main.py
```

`google` is configured via a MyPy override in `pyproject.toml` because type stubs are not installed for that library in this project.

## Diagnostics

The app keeps a detailed log that operators never see. It lives in the per-user
application data folder (`.../WayfairFlatMakerByDK/logs/app.log`), starts fresh
once it is a week old (the previous week is kept as `app.log.1`), and is capped
at 5 MB. API keys are masked.

To get it from an operator after a problem, ask them to click the small bug
icon next to the version number at the bottom of the window (or **Save report
for the developer** in an error dialog) and save the zip. It contains the log
plus a `system.txt` with the app version and system details.

## Notes About The Excel Template

The generated file is based on the bundled Wayfair template in `assets/template.xlsx`.

To replace it with a newer template, download a blank one from your Wayfair partner account: **Product Management → Add Products → Quick Upload**, select your brand and product categories, and download the blank template.

If some cells are protected in Excel or Google Sheets after generation, that comes from the template itself rather than from the export logic. The app writes values into the workbook but does not remove worksheet protection.

## License

This code is shared publicly with permission, but it is not provided under a traditional open-source license. Do not redistribute it commercially without prior agreement.
