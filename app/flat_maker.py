"""Main Flet view model for the Wayfair spreadsheet generator."""

import asyncio
import os
from collections.abc import Callable
from typing import cast

import flet as ft

from app.builder import build_controls
from app.controls import build_counter_buttons, build_image_link_row, build_size_row
from app.helpers import contains_link, extract_hint_value, get_hint_sets, is_valid_url
from app.gemini import GeminiClient, GeminiUserError
from app.submission import clear_errors, submit_form, validate_fields
from app.ui_ops import (
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
from app.version import get_page_title
from data.pricing import PriceProvider
from i18n import get_translator

Translator = Callable[[str], str]


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
    suggest_button: ft.ElevatedButton
    suggest_progress_ring: ft.ProgressRing
    main_image_note: ft.Text
    image_buttons_row: ft.Row
    folder_picker: ft.FilePicker
    submit_button_text: ft.Text
    submit_button: ft.ElevatedButton
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

        self.build_controls()
        self.init_ui()
        self.page.run_task(self._prefetch_prices)

    async def _prefetch_prices(self) -> None:
        """Warm the price cache in the background so the first submit is instant."""

        try:
            await asyncio.to_thread(self.price_provider.get_points_by_category)
        except Exception:
            pass

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
            on_first_change=self.toggle_main_image_note,
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

        first_link_value = ""
        if self.image_links_column.controls:
            first_link_value = (
                self.get_image_field(
                    cast(ft.Row, self.image_links_column.controls[0])
                ).value
                or ""
            ).strip()
        has_url = bool(first_link_value)
        has_print_type = bool(self.print_type_dd.value)
        self.main_image_note.visible = not has_url
        self.suggest_button.disabled = not has_url or not has_print_type
        if e is not None:
            self.page.update()

    async def on_suggest_title_keywords_click(
        self,
        e: ft.Event[ft.Button],
    ) -> None:
        """Generate title and keywords from the main image URL."""

        first_image_url = ""
        if self.image_links_column.controls:
            first_image_url = (
                self.get_image_field(
                    cast(ft.Row, self.image_links_column.controls[0])
                ).value
                or ""
            ).strip()

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
        try:
            suggestion = await asyncio.to_thread(
                self.gemini_client.suggest_title_keywords,
                first_image_url,
                self.print_type_dd.value,
            )
            self.title_field.value = suggestion.title
            self.keyword_field.value = suggestion.keyword
            self.page.show_dialog(
                ft.SnackBar(
                    ft.Text(self._("Title and keywords generated")),
                    bgcolor=ft.Colors.GREEN_100,
                )
            )
        except GeminiUserError as exc:
            self.page.show_dialog(
                ft.AlertDialog(title=ft.Text(self._(exc.user_message)))
            )
        except Exception:
            self.page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text(
                        self._(
                            "AI could not generate a title and keywords. Try again or fill them manually."
                        )
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
        await self.prefs.set("lang", self.lang)
        self._ = get_translator(self.lang)
        self.apply_i18n()
        self.page.update()

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

        last_folder = await self.prefs.get("last_folder")
        directory_path = await self.folder_picker.get_directory_path(
            dialog_title=self._("Choose a folder to save the file"),
            initial_directory=last_folder,
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
