"""Main Flet view model for the Wayfair spreadsheet generator."""

import asyncio
from collections.abc import Callable
import datetime
import os
from pathlib import Path
from typing import cast

import flet as ft

from app.builder import build_controls
from app.constants import (
    AUTOFILL_HELPER_TEXT,
    MAIN_IMAGE_CHECK_DELAY_SECONDS,
    MIN_MAIN_IMAGE_DESIGN_COVERAGE_PERCENT,
)
from app.controls import (
    build_counter_buttons,
    build_image_link_row,
    build_image_thumbnail,
    build_size_row,
)
from app.helpers import (
    contains_link,
    extract_hint_value,
    get_hint_sets,
    is_valid_url,
    SizeIssue,
    check_size,
    matching_height,
    size_presets,
)
from app.diagnostics import export_diagnostics, get_logger
from app.gemini import (
    GeminiClient,
    GeminiUserError,
    MainImageAnalysis,
    normalize_public_image_url,
)
from app.settings import settings
from app.submission import clear_errors, submit_form, validate_fields
from app.ui_ops import (
    get_size_fields,
    add_image_link,
    add_size,
    apply_i18n,
    handle_print_type_change,
    init_ui,
    remove_image_link,
    remove_size,
    reset_dynamic_controls,
    reset_form,
)
from app.validation import (
    require_dropdown,
    require_plain_text,
    require_url,
    require_value,
    validation_summary_message,
)
from app.updates import ReleaseInfo, find_available_update
from app.version import get_app_version, get_page_title
from data import DataShaperFactory
from data.pricing import PriceProvider
from i18n import get_translator

Translator = Callable[[str], str]
AnalysisKey = tuple[str, str]

logger = get_logger("ui")


def string_or_none(value: str | ft.Control | None) -> str | None:
    """Normalize Flet string-like properties that may also be typed as controls."""

    return value if isinstance(value, str) else None


class WayfairFlatMaker:
    """Coordinate application state, UI callbacks, and form actions."""

    page: ft.Page
    lang: str
    prefs: ft.SharedPreferences
    _: Translator
    validation_error_kinds: set[str]
    lang_dd: ft.Dropdown
    personalization_radio: ft.RadioGroup
    personalization_label: ft.Text
    personalization_error: ft.Text
    design_radio: ft.RadioGroup
    design_label: ft.Text
    design_error: ft.Text
    design_container: ft.Column
    personalization_container: ft.Column
    sizes_column: ft.Column
    buttons_row: ft.Row
    image_links_column: ft.Column
    suggest_button_text: ft.Text
    suggest_button: ft.Button
    suggest_progress_ring: ft.ProgressRing
    main_image_note: ft.Text
    main_image_check: ft.Text
    report_button: ft.IconButton
    image_buttons_row: ft.Row
    folder_picker: ft.FilePicker
    submit_button_text: ft.Text
    submit_button: ft.Button
    progress_ring: ft.ProgressRing
    success_icon: ft.Icon
    submit_row: ft.Row
    sizes_label: ft.Text
    print_type_dd: ft.Dropdown
    title_field: ft.TextField
    sku_field: ft.TextField
    keyword_field: ft.TextField
    price_provider: PriceProvider
    gemini_client: GeminiClient
    url_launcher: ft.UrlLauncher

    def __init__(self, page: ft.Page, lang: str, prefs: ft.SharedPreferences) -> None:
        """Initialize the page, translator, and top-level controls."""

        self.page = page
        self.configure_page()
        self.lang = lang
        self.prefs = prefs
        self._ = get_translator(lang=self.lang)
        self.validation_error_kinds: set[str] = set()
        self.price_provider = PriceProvider()
        self.gemini_client = GeminiClient()
        # Services register themselves on creation; keep a reference so they stay.
        self.url_launcher = ft.UrlLauncher()
        # One analysis per (image URL, print type), shared by the background check
        # and the export so the same image is never analysed twice.
        self.image_analyses: dict[
            AnalysisKey, asyncio.Task[MainImageAnalysis | None]
        ] = {}
        self._image_check_generation = 0

        self.build_controls()
        self.init_ui()
        self.page.run_task(self._prefetch_prices)
        self.page.run_task(self._check_for_updates)

    async def _prefetch_prices(self) -> None:
        """Warm the price cache in the background so the first submit is instant."""

        try:
            await asyncio.to_thread(self.price_provider.get_points_by_category)
            logger.info("Price data prefetched")
        except Exception:
            logger.warning("Price prefetch failed", exc_info=True)

    async def _check_for_updates(self) -> None:
        """Offer a newer GitHub release unless the user skipped that version."""

        try:
            release = await asyncio.to_thread(find_available_update, get_app_version())
            if release is None:
                logger.info("No newer release found")
                return
            if await self.prefs.get("skipped_update_version") == release.version:
                logger.info("Release %s was skipped by the user", release.version)
                return
        except Exception:
            logger.warning("Update check failed", exc_info=True)
            return
        logger.info("Offering update to %s", release.version)
        self.page.show_dialog(self.build_update_dialog(release))

    def build_update_dialog(self, release: ReleaseInfo) -> ft.AlertDialog:
        """Build the dialog that announces a newer application version."""

        async def open_instructions(e: ft.Event[ft.Button]) -> None:
            self.page.pop_dialog()
            await self.url_launcher.launch_url(release.page_url)

        async def skip_version(e: ft.Event[ft.TextButton]) -> None:
            self.page.pop_dialog()
            await self.prefs.set("skipped_update_version", release.version)

        def later(e: ft.Event[ft.TextButton]) -> None:
            self.page.pop_dialog()

        return ft.AlertDialog(
            title=ft.Text(self._("Update available")),
            content=ft.Text(
                self._(
                    "Version %(new)s is available. You are using version %(current)s."
                )
                % {"new": release.version, "current": get_app_version()}
            ),
            actions=[
                ft.TextButton(self._("Skip this version"), on_click=skip_version),
                ft.TextButton(self._("Later"), on_click=later),
                ft.FilledButton(
                    self._("How to update"),
                    icon=ft.Icons.OPEN_IN_NEW,
                    on_click=open_instructions,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    async def save_diagnostics(self) -> None:
        """Ask where to save the diagnostics zip, then write it."""

        file_name = (
            f"WayfairFlatMaker-report-{datetime.datetime.now():%Y-%m-%d_%H-%M}.zip"
        )
        path = await self.folder_picker.save_file(
            dialog_title=self._("Save report for the developer"),
            file_name=file_name,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["zip"],
        )
        if not path:
            return
        extra = {
            "Language": self.lang,
            "AI model": settings.gemini_model,
            "AI fallback model": settings.gemini_fallback_model,
            "AI configured": str(self.gemini_client.is_configured),
        }
        try:
            saved = await asyncio.to_thread(
                export_diagnostics, Path(path), get_app_version(), extra
            )
        except OSError:
            logger.exception("Could not save diagnostics report")
            self.page.show_dialog(
                ft.SnackBar(
                    ft.Text(self._("Could not save the report.")),
                    bgcolor=ft.Colors.RED_100,
                    show_close_icon=True,
                )
            )
            return
        self.page.show_dialog(
            ft.SnackBar(
                ft.Text(self._("Report saved: %(file)s") % {"file": saved.name}),
                bgcolor=ft.Colors.GREEN_100,
            )
        )

    def build_error_dialog(self, message: str) -> ft.AlertDialog:
        """Build an error dialog that can save a report for the developer."""

        async def save_report(e: ft.Event[ft.TextButton]) -> None:
            self.page.pop_dialog()
            await self.save_diagnostics()

        def close(e: ft.Event[ft.TextButton]) -> None:
            self.page.pop_dialog()

        return ft.AlertDialog(
            title=ft.Text(message),
            actions=[
                ft.TextButton(
                    self._("Save report for the developer"),
                    icon=ft.Icons.BUG_REPORT_OUTLINED,
                    on_click=save_report,
                ),
                ft.TextButton("OK", on_click=close),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    async def get_main_image_analysis(
        self, image_url: str, print_type: str
    ) -> MainImageAnalysis | None:
        """Return the AI analysis of the main image, or ``None`` if unavailable."""

        if not self.gemini_client.is_configured:
            return None
        key = (image_url, print_type)
        task = self.image_analyses.get(key)
        if task is None:
            task = asyncio.ensure_future(self._analyse_main_image(*key))
            self.image_analyses[key] = task
        return await asyncio.shield(task)

    async def _analyse_main_image(
        self, image_url: str, print_type: str
    ) -> MainImageAnalysis | None:
        """Run the AI analysis; failures only cost the AI suggestions."""

        # Color is offered too; the shaper ignores it for color-variation decals.
        options = DataShaperFactory.create_shaper(print_type).ai_attribute_options(
            has_color_variations=False
        )
        try:
            return await asyncio.to_thread(
                self.gemini_client.analyze_main_image, image_url, print_type, options
            )
        except Exception:
            logger.warning("Main image analysis failed", exc_info=True)
            self.image_analyses.pop((image_url, print_type), None)
            return None

    def main_image_coverage_warning(
        self, analysis: MainImageAnalysis | None
    ) -> str | None:
        """Return a warning when the design covers too little of the main image."""

        if analysis is None or analysis.design_coverage_percent is None:
            return None
        if analysis.design_coverage_percent >= MIN_MAIN_IMAGE_DESIGN_COVERAGE_PERCENT:
            return None
        return self._(
            "AI check: the design covers only about %(percent)s%% of the main image, "
            "but at least %(required)s%% is required. Consider a closer image. "
            "You can still continue."
        ) % {
            "percent": analysis.design_coverage_percent,
            "required": MIN_MAIN_IMAGE_DESIGN_COVERAGE_PERCENT,
        }

    def schedule_main_image_check(self) -> None:
        """Re-check the main image shortly after the link or print type changes."""

        self._image_check_generation += 1
        self.page.run_task(self._check_main_image, self._image_check_generation)

    async def _check_main_image(self, generation: int) -> None:
        """Analyse the main image in the background and show the result."""

        # Wait for typing to stop; a newer change supersedes this check.
        await asyncio.sleep(MAIN_IMAGE_CHECK_DELAY_SECONDS)
        if generation != self._image_check_generation:
            return
        image_url = self.first_image_url()
        print_type = self.print_type_dd.value
        if not (
            image_url
            and self.is_valid_url(image_url)
            and print_type
            and self.gemini_client.is_configured
        ):
            self.show_main_image_check(None, checking=False)
            return

        self.show_main_image_check(None, checking=True)
        analysis = await self.get_main_image_analysis(image_url, print_type)
        if generation == self._image_check_generation:
            self.show_main_image_check(analysis, checking=False)

    def show_main_image_check(
        self, analysis: MainImageAnalysis | None, *, checking: bool
    ) -> None:
        """Render the main-image check status under the image links."""

        # A new orientation may confirm or clear size warnings.
        self.check_all_size_rows()

        warning = self.main_image_coverage_warning(analysis)
        if checking:
            self.main_image_check.value = self._("AI is checking the main image...")
            self.main_image_check.color = ft.Colors.GREY_600
        elif warning:
            self.main_image_check.value = warning
            self.main_image_check.color = ft.Colors.ORANGE_800
        elif analysis is not None and analysis.design_coverage_percent is not None:
            self.main_image_check.value = self._("AI check: the main image looks good.")
            self.main_image_check.color = ft.Colors.GREEN_700
        else:
            self.main_image_check.value = ""
        self.main_image_check.visible = bool(self.main_image_check.value)
        self.page.update()

    def current_design_ratio(self) -> float | None:
        """Return the analysed decal design's width/height ratio, if known.

        Wallpaper murals are cropped to the wall, so only decals have fixed
        proportions that the entered size must keep.
        """

        if self.print_type_dd.value != "decals":
            return None
        task = self.image_analyses.get((self.first_image_url(), "decals"))
        if task is None or not task.done() or task.cancelled():
            return None
        analysis = task.result()
        return analysis.design_aspect_ratio if analysis else None

    @staticmethod
    def size_row_values(row: ft.Row) -> tuple[int, int] | None:
        """Return a size row's (width, height), or ``None`` if incomplete."""

        width_field, height_field = get_size_fields(row)
        try:
            return int(width_field.value or ""), int(height_field.value or "")
        except ValueError:
            return None

    def size_row_issue(self, row: ft.Row) -> SizeIssue | None:
        """Return what looks wrong with a size row, if anything."""

        values = self.size_row_values(row)
        if values is None:
            return None
        return check_size(
            *values, size_presets(self.print_type_dd.value), self.current_design_ratio()
        )

    def corrected_size(self, row: ft.Row, issue: SizeIssue) -> tuple[int, int]:
        """Return the size a problem row would get after fixing it."""

        values = self.size_row_values(row)
        assert values is not None
        width, height = values
        design_ratio = self.current_design_ratio()
        if issue is SizeIssue.SWAPPED or design_ratio is None:
            return height, width
        return width, matching_height(width, design_ratio)

    def check_size_row(self, row: ft.Row, *, update: bool = True) -> None:
        """Show or clear the size warning and its one-click fix."""

        width_field, height_field = get_size_fields(row)
        issue = self.size_row_issue(row)
        if issue is None:
            width_field.helper = self._(AUTOFILL_HELPER_TEXT)
            width_field.helper_style = ft.TextStyle(size=11, color=ft.Colors.GREY_700)
            height_field.suffix_icon = None
        else:
            # Short enough for one line, so both fields of the row stay level.
            width_field.helper = (
                self._("Width/height swapped?")
                if issue is SizeIssue.SWAPPED
                else self._("Proportions off?")
            )
            width_field.helper_style = ft.TextStyle(
                size=11, color=ft.Colors.ORANGE_800, weight=ft.FontWeight.W_500
            )
            fixed_width, fixed_height = self.corrected_size(row, issue)
            height_field.suffix_icon = ft.IconButton(
                icon=(
                    ft.Icons.SWAP_HORIZ
                    if issue is SizeIssue.SWAPPED
                    else ft.Icons.AUTO_FIX_HIGH
                ),
                icon_color=ft.Colors.ORANGE_800,
                tooltip=(
                    self._("Swap width and height")
                    if issue is SizeIssue.SWAPPED
                    else self._("Use %(size)s to keep the design's proportions")
                    % {"size": f"{fixed_width}x{fixed_height}"}
                ),
                on_click=lambda e, current_row=row: self.fix_size_row(current_row),
            )
        if update:
            self.page.update()

    def check_all_size_rows(self) -> None:
        """Re-check every size row without redrawing the page."""

        for control in self.sizes_column.controls:
            self.check_size_row(cast(ft.Row, control), update=False)

    def fix_size_row(self, row: ft.Row, *, update: bool = True) -> None:
        """Swap the values, or set the height that keeps the proportions."""

        issue = self.size_row_issue(row)
        if issue is None:
            return
        width_field, height_field = get_size_fields(row)
        fixed_width, fixed_height = self.corrected_size(row, issue)
        logger.info(
            "Size %sx%s fixed to %sx%s (%s)",
            width_field.value,
            height_field.value,
            fixed_width,
            fixed_height,
            issue.value,
        )
        width_field.value, height_field.value = str(fixed_width), str(fixed_height)
        self.check_size_row(row, update=update)

    def problem_size_rows(self) -> list[tuple[ft.Row, SizeIssue]]:
        """Return the size rows that look wrong, with the reason."""

        problems = []
        for control in self.sizes_column.controls:
            row = cast(ft.Row, control)
            issue = self.size_row_issue(row)
            if issue is not None:
                problems.append((row, issue))
        return problems

    async def confirm_problem_sizes(
        self, problems: list[tuple[ft.Row, SizeIssue]]
    ) -> str:
        """Ask what to do with suspicious sizes: "fix", "keep" or "cancel"."""

        answer: asyncio.Future[str] = asyncio.get_running_loop().create_future()

        def choose(choice: str) -> None:
            if not answer.done():
                answer.set_result(choice)
            self.page.pop_dialog()

        changes = "\n".join(
            "{}x{} → {}x{}".format(
                *(self.size_row_values(row) or ("?", "?")),
                *self.corrected_size(row, issue),
            )
            for row, issue in problems
        )
        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(self._("Check the sizes")),
                content=ft.Column(
                    [
                        ft.Text(
                            self._(
                                "These sizes do not match the design: width and "
                                "height look swapped or the proportions differ. "
                                "Width is the horizontal side. Suggested fixes:"
                            )
                        ),
                        ft.Text(changes, weight=ft.FontWeight.W_500),
                    ],
                    tight=True,
                ),
                actions=[
                    ft.TextButton(
                        self._("Cancel"), on_click=lambda e: choose("cancel")
                    ),
                    ft.TextButton(
                        self._("Keep as entered"), on_click=lambda e: choose("keep")
                    ),
                    ft.FilledButton(
                        self._("Fix and continue"),
                        icon=ft.Icons.AUTO_FIX_HIGH,
                        on_click=lambda e: choose("fix"),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
                on_dismiss=lambda e: choose("cancel"),
            )
        )
        choice = await answer
        logger.info("Problem sizes %s: user chose %s", changes.split("\n"), choice)
        return choice

    def on_image_link_change(self, e: ft.Event[ft.TextField]) -> None:
        """Refresh the link's preview, and the main-image checks for link #1."""

        self.refresh_image_preview(e.control)
        if self.image_links_column.controls and e.control is self.get_image_field(
            cast(ft.Row, self.image_links_column.controls[0])
        ):
            self.toggle_main_image_note(e)
        else:
            self.page.update()

    def refresh_image_preview(self, field: ft.TextField) -> None:
        """Point the field's thumbnail at its link, or show the placeholder."""

        value = (field.value or "").strip()
        image_url = normalize_public_image_url(value) if is_valid_url(value) else None
        current = field.prefix_icon
        if isinstance(current, ft.Container) and current.data == image_url:
            return
        field.prefix_icon = build_image_thumbnail(
            image_url, translate=self._, on_open=self.open_image_preview
        )

    def open_image_preview(self, image_url: str) -> None:
        """Show an image link at a comfortable size."""

        self.page.show_dialog(
            ft.AlertDialog(
                content=ft.Image(
                    src=image_url,
                    width=640,
                    height=480,
                    fit=ft.BoxFit.CONTAIN,
                    error_content=ft.Text(
                        self._("The image could not be loaded. Check the link.")
                    ),
                ),
                actions=[
                    ft.TextButton("OK", on_click=lambda e: self.page.pop_dialog())
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def first_image_url(self) -> str:
        """Return the trimmed main image link, or an empty string."""

        if not self.image_links_column.controls:
            return ""
        field = self.get_image_field(cast(ft.Row, self.image_links_column.controls[0]))
        return (field.value or "").strip()

    def configure_page(self) -> None:
        """Apply static window and page settings."""

        self.page.window.maximized = True
        self.page.title = get_page_title()
        self.page.scroll = ft.ScrollMode.ALWAYS
        self.page.window.resizable = True

    def build_controls(self) -> None:
        """Create all interactive controls used by the form."""

        build_controls(self)

    def hint_sets(self) -> tuple[list[str], list[str]]:
        """Return hint sets for the currently selected print type."""

        return get_hint_sets(self.print_type_dd.value, self._)

    def make_size_row(self, index: int) -> ft.Row:
        """Create a single size row."""

        return build_size_row(
            index,
            hint_sets=self.hint_sets(),
            translate=self._,
            on_submit=self.on_size_field_commit,
            on_change=self.check_size_row,
        )

    @staticmethod
    def extract_hint_value(hint_text: str | None) -> str:
        """Extract a numeric value from a hint string."""

        return extract_hint_value(hint_text)

    async def focus_next_size_field(
        self, current_row: ft.Row, current_control: ft.TextField
    ) -> None:
        """Move focus to the next size field after an Enter key submission."""

        try:
            row_index = self.sizes_column.controls.index(current_row)
            control_index = current_row.controls.index(current_control)
        except ValueError:
            return

        next_control: ft.TextField | None = None
        if control_index < len(current_row.controls) - 1:
            next_control = cast(ft.TextField, current_row.controls[control_index + 1])
        elif row_index < len(self.sizes_column.controls) - 1:
            next_row = cast(ft.Row, self.sizes_column.controls[row_index + 1])
            next_control = cast(ft.TextField, next_row.controls[0])

        if next_control is not None:
            await next_control.focus()

    def on_size_field_commit(self, e: ft.Event[ft.TextField], row: ft.Row) -> None:
        """Handle Enter on a size row by autofilling and moving focus."""

        changed = False
        control = e.control
        if not (control.value or "").strip():
            hint_value = self.extract_hint_value(control.hint_text)
            if hint_value:
                control.value = hint_value
                changed = True

        self.page.run_task(self.focus_next_size_field, row, control)

        if changed:
            self.page.update()

    def make_image_link_row(self, index: int) -> ft.Row:
        """Create a single image-link row."""

        return build_image_link_row(
            index,
            translate=self._,
            on_change=self.on_image_link_change,
            on_open_preview=self.open_image_preview,
            suggest_button=self.suggest_button if index == 0 else None,
            suggest_progress_ring=self.suggest_progress_ring if index == 0 else None,
        )

    @staticmethod
    def get_image_field(image_row: ft.Row) -> ft.TextField:
        """Return the only field stored inside an image-link row."""

        return cast(ft.TextField, image_row.controls[0])

    @staticmethod
    def contains_link(value: str) -> bool:
        """Return ``True`` when the provided text contains a link."""

        return contains_link(value)

    @staticmethod
    def is_valid_url(value: str) -> bool:
        """Return ``True`` when the provided value is a valid HTTP(S) URL."""

        return is_valid_url(value)

    def set_print_type_visibility(self) -> None:
        """Toggle decal-only sections based on the selected print type."""

        is_decals = self.print_type_dd.value == "decals"
        self.design_container.visible = is_decals
        self.personalization_container.visible = is_decals

    def toggle_main_image_note(self, e: ft.Event[ft.TextField] | None = None) -> None:
        """Show the main-image warning and gate the Suggest button on the first image URL."""

        has_url = bool(self.first_image_url())
        has_print_type = bool(self.print_type_dd.value)
        self.main_image_note.visible = not has_url
        self.suggest_button.disabled = not has_url or not has_print_type
        self.schedule_main_image_check()
        if e is not None:
            self.page.update()

    async def on_suggest_title_keywords_click(
        self,
        e: ft.Event[ft.Button],
    ) -> None:
        """Generate title and keywords from the main image URL."""

        first_image_url = self.first_image_url()

        if not first_image_url or not self.is_valid_url(first_image_url):
            self.page.show_dialog(
                ft.SnackBar(
                    ft.Text(
                        self._("Enter a valid URL for %(field)s.")
                        % {"field": f"{self._('Image Link')} #1"}
                    ),
                    bgcolor=ft.Colors.RED_100,
                    show_close_icon=True,
                )
            )
            return

        self.suggest_button.disabled = True
        self.suggest_progress_ring.visible = True
        self.suggest_button_text.value = self._("Generating...")
        self.page.update()
        logger.info("Title suggestion requested for %s", self.print_type_dd.value)
        try:
            suggestion = await asyncio.to_thread(
                self.gemini_client.suggest_title_keywords,
                first_image_url,
                self.print_type_dd.value,
            )
            logger.info("Title suggestion ready: %s", suggestion.title)
            self.title_field.value = suggestion.title
            self.keyword_field.value = suggestion.keyword
            self.page.show_dialog(
                ft.SnackBar(
                    ft.Text(self._("Title and keywords generated")),
                    bgcolor=ft.Colors.GREEN_100,
                )
            )
        except GeminiUserError as exc:
            logger.warning("Title suggestion failed: %s", exc)
            self.page.show_dialog(
                ft.AlertDialog(title=ft.Text(self._(exc.user_message)))
            )
        except Exception:
            logger.exception("Title suggestion crashed")
            self.page.show_dialog(
                self.build_error_dialog(
                    self._(
                        "AI could not generate a title and keywords. Try again or fill them manually."
                    )
                )
            )
        finally:
            self.suggest_button.disabled = False
            self.suggest_progress_ring.visible = False
            self.suggest_button_text.value = self._("✨ Suggest title & keywords")
            self.page.update()

    def set_segmented_error(self, control: ft.Text, message: str | None) -> None:
        """Apply or clear an error message for a binary-choice helper text."""

        control.value = message or ""
        control.visible = bool(message)

    def clear_binary_choice_errors(
        self, e: ft.Event[ft.RadioGroup] | None = None
    ) -> None:
        """Clear inline errors for the binary radio groups."""

        self.set_segmented_error(self.design_error, None)
        self.set_segmented_error(self.personalization_error, None)

    def require_segmented_value(
        self,
        value: str | None,
        error_control: ft.Text,
        field_name: str,
    ) -> bool:
        """Require a Yes/No value for a radio group."""

        if value is None:
            self.validation_error_kinds.add("missing")
            self.set_segmented_error(
                error_control,
                self._("Please choose Yes or No for %(field)s.")
                % {"field": field_name},
            )
            return False
        self.set_segmented_error(error_control, None)
        return True

    def first_validation_message(self) -> str | None:
        """Return the first currently visible validation error, if any."""

        candidates: list[str | None] = [
            string_or_none(self.print_type_dd.error_text),
            string_or_none(self.title_field.error),
            string_or_none(self.sku_field.error),
            string_or_none(self.keyword_field.error),
            string_or_none(self.design_error.value)
            if self.design_error.visible
            else None,
            string_or_none(self.personalization_error.value)
            if self.personalization_error.visible
            else None,
        ]
        for control in self.image_links_column.controls:
            image_row = cast(ft.Row, control)
            candidates.append(string_or_none(self.get_image_field(image_row).error))
        for control in self.sizes_column.controls:
            row = cast(ft.Row, control)
            for ctrl in row.controls:
                candidates.append(string_or_none(cast(ft.TextField, ctrl).error))
        for message in candidates:
            if message:
                return message
        return None

    def validation_summary_message(self) -> str:
        """Build a short summary message for the validation snackbar."""

        return validation_summary_message(self.validation_error_kinds, self._)

    def get_dropdown_value(self, e: ft.Event[ft.Dropdown]) -> None:
        """Handle print-type dropdown changes."""

        handle_print_type_change(self)

    async def on_lang_change(self, e: ft.Event[ft.Dropdown]) -> None:
        """Persist language selection and refresh translated UI labels."""

        self.lang = cast(str, e.control.value)
        logger.info("Language changed to %s", self.lang)
        await self.prefs.set("lang", self.lang)
        self._ = get_translator(self.lang)
        self.apply_i18n()
        self.page.update()
        # Re-render the main-image check in the new language (uses the cache).
        self.schedule_main_image_check()

    def apply_i18n(self) -> None:
        """Re-apply translated labels across the form."""

        apply_i18n(self)

    def add_size(self, e: ft.Event[ft.IconButton]) -> None:
        """Append one size row."""

        add_size(self)

    def remove_size(self, e: ft.Event[ft.IconButton]) -> None:
        """Remove the last size row."""

        remove_size(self)

    def make_size_buttons(self) -> ft.Control:
        """Build add/remove buttons for size rows."""

        return build_counter_buttons(on_add=self.add_size, on_remove=self.remove_size)

    def add_image_link(self, e: ft.Event[ft.IconButton]) -> None:
        """Append one image-link row."""

        add_image_link(self)

    def remove_image_link(self, e: ft.Event[ft.IconButton]) -> None:
        """Remove the last image-link row."""

        remove_image_link(self)

    def make_image_buttons(self) -> ft.Control:
        """Build add/remove buttons for image-link rows."""

        return build_counter_buttons(
            on_add=self.add_image_link, on_remove=self.remove_image_link
        )

    async def on_submit_click(self, e: ft.Event[ft.Button]) -> None:
        """Open folder picker and trigger spreadsheet generation."""

        self.submit_button.disabled = True
        self.page.update()

        problems = self.problem_size_rows()
        if problems:
            choice = await self.confirm_problem_sizes(problems)
            if choice == "cancel":
                self.submit_button.disabled = False
                self.page.update()
                return
            if choice == "fix":
                for row, _issue in problems:
                    self.fix_size_row(row, update=False)
                self.page.update()

        last_folder = await self.prefs.get("last_folder")
        directory_path = await self.folder_picker.get_directory_path(
            dialog_title=self._("Choose a folder to save the file"),
            initial_directory=last_folder if isinstance(last_folder, str) else None,
        )
        if directory_path:
            await self.prefs.set("last_folder", directory_path)
            await self.submit_form(directory_path)
            return

        self.submit_button.disabled = False
        self.page.update()

    def require_value(self, control: ft.TextField) -> bool:
        """Validate that a text field is not empty."""

        return require_value(control, self.validation_error_kinds, self._)

    def require_plain_text(self, control: ft.TextField) -> bool:
        """Validate that a text field is not empty and contains no links."""

        return require_plain_text(
            control,
            self.validation_error_kinds,
            self._,
            contains_link=self.contains_link,
        )

    def require_dropdown(self, control: ft.Dropdown) -> bool:
        """Validate that a dropdown has a selected value."""

        return require_dropdown(control, self.validation_error_kinds, self._)

    def require_url(self, control: ft.TextField, *, required: bool) -> bool:
        """Validate a URL field with optional emptiness support."""

        return require_url(
            control,
            self.validation_error_kinds,
            self._,
            required=required,
            is_valid_url=self.is_valid_url,
        )

    def reset_dynamic_controls(self) -> None:
        """Clear values for dynamic rows without changing their count."""

        reset_dynamic_controls(self)

    def reset_form(self) -> None:
        """Reset the entire form state."""

        reset_form(self)

    def validate_fields(self) -> bool:
        """Run form validation and return ``True`` when valid."""

        return validate_fields(self)

    async def clear_errors(self) -> None:
        """Clear highlighted validation errors after a delay."""

        await clear_errors(self)

    async def submit_form(self, folder: str | os.PathLike[str]) -> None:
        """Generate the spreadsheet into the selected folder."""

        await submit_form(self, folder)

    def init_ui(self) -> None:
        """Render the top-level application layout."""

        init_ui(self)
