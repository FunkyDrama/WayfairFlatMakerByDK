# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Flet desktop app (macOS/Windows) that turns a form (print type, title, SKU, keywords, image links, sizes) into a Wayfair Quick Upload `.xlsx` for wall decals or wallpapers. UI is localized (en, ru, uk, sq).

## Commands

```bash
poetry install
poetry run python main.py          # run the app (needs .env with GEMINI_API_KEY for AI features)
make check                         # ruff format + ruff check --fix + mypy .
poetry run pre-commit install      # hooks: ruff, mypy, TOML/YAML checks, version/build_number guard
make i18n-all                      # after changing UI strings: extract → update .po → compile .mo
make release [BUMP=minor]          # bump version + build_number, commit, tag; then git push origin main --follow-tags
make release-dry-run
make build-macos / build-windows   # refuse to run if .env contains DROPBOX_* (flet bundles .env into the app)
```

There is no test suite. Verify changes by running the app, and for output-file changes, by checking the generated workbook (see below).

`app/settings.py` (pydantic-settings) looks for `.env` in a different place for each run mode. If AI features are missing in a built app, check here first:

| Mode | `.env` location |
|------|-----------------|
| Development | project root (next to `main.py`) |
| `flet build` macOS | `~/Library/Application Support/com.funkydrama.wayfairflatmakerbydk/` |
| `flet build` Windows | `%APPDATA%\com.funkydrama.wayfairflatmakerbydk\` |
| `flet pack` (PyInstaller) | next to the executable |

Besides `GEMINI_API_KEY`, `.env` can override `GEMINI_MODEL` (default `gemini-3.5-flash`) and `GEMINI_FALLBACK_MODEL` (default `gemini-2.5-flash`, used when the main model is overloaded or out of quota).

## Architecture

**Entry:** `main.py` sets up logging (`app/diagnostics.py`, masks the API key) *before* importing UI modules, then constructs `WayfairFlatMaker(page, lang, prefs)`.

**UI layer (`app/`):** `flat_maker.py` holds the `WayfairFlatMaker` view-model with all controls and state. Large chunks of its behavior live in module-level functions that take the maker as their first argument (`builder.build_controls(maker)`, `ui_ops.*(maker)`, `submission.*(maker)`), importing `WayfairFlatMaker` only under `TYPE_CHECKING`. Follow this pattern rather than growing the class. `gemini.py` handles AI (title/keywords, marketing texts, design-dependent attributes, main-image coverage check) with a fallback model on overload/429. `updates.py` checks GitHub Releases for newer versions.

**Data layer (`data/`):** `DataShaperFactory.create_shaper("decals" | "wallpapers")` returns a `BaseDataShaper` subclass. Each shaper defines its Wayfair class sheet name, `CLASS_LABEL`, and `AI_ATTRIBUTES`, builds one row per size/variant, and calls `write_file()`. Prices come from a public Google Sheet CSV (`pricing.py`, prefetched at startup, interpolated by size). `template_values.py` reads the allowed answers from the template's "Valid Values" sheet so AI attributes are restricted to them (class-specific columns look like `Subject (Wall Stickers - S)`). `wayfair_rules.py` holds text rules (forbidden chars, length limits) taken from the template's validation formulas.

**Excel output (`data/excel_writer.py`), which is critical:** the writer copies `assets/template.xlsx` byte-for-byte and edits only the class sheet XML and `xl/sharedStrings.xml` (numbers with no `t` attribute, strings as `t="s"` shared strings, column default styles). **Never write output through openpyxl** (`load_workbook().save()`). Wayfair silently rejects re-serialized workbooks even when every row passes its validation. When changing output, confirm that only those two zip parts differ from the template. Product rows are 9–508; row 8 is the Default Row; column A ("Errors") shows "Validated" or the first error for each row. Those results come from LAMBDA/MAP formulas in hidden `*-WUO_ERR` sheets, which only Excel evaluates (LibreOffice can't). To check a file on macOS, drive Microsoft Excel with AppleScript:

```applescript
set f to (POSIX file "/path/to/output.xlsx") as text  -- coerce outside the tell block
tell application "Microsoft Excel"
    open workbook workbook file name f
    calculate full
    get value of range "A9" of worksheet "<class sheet name>" of active workbook
    close active workbook saving no
end tell
```

When the template changes, extract the text rules in `data/wayfair_rules.py` from those formulas again.

## Localization

Wrap UI strings with the maker's translator `_` (`i18n/translator.py`, gettext with an in-memory cache). Strings Babel can't extract from indirect call sites or constants go in `app/messages.py`. Then run `make i18n-update`, fill `msgstr` in each `locales/*/LC_MESSAGES/app.po`, and `make i18n-compile` (commit the `.mo` files). The boot/startup screen text in `pyproject.toml` can't be translated.

## Release / CI

- `project.version` and `tool.flet.build_number` in `pyproject.toml` must change together (the pre-commit hook enforces it, and `scripts/bump_version.py` does both). The bump level follows Conventional Commits (`feat:` → minor, `!`/`BREAKING CHANGE` → major, else patch).
- A `v*` tag triggers `.github/workflows/build.yml`: Windows via `flet pack` (PyInstaller), macOS via `flet build`. The builds embed the Gemini key, so they're uploaded to a private Dropbox folder and never stored as GitHub artifacts (the repo is public).
