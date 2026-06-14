"""Factories for constructing the main form controls."""

from typing import TYPE_CHECKING, Any, cast

import flet as ft

from app.constants import MAIN_IMAGE_WARNING, SUPPORTED_LANGUAGES
from app.controls import build_binary_radio_group

if TYPE_CHECKING:
    from app.flat_maker import WayfairFlatMaker


def build_controls(maker: "WayfairFlatMaker") -> None:
    """Create and attach all controls used by the form."""

    maker.lang_dd = ft.Dropdown(
        width=200,
        value=maker.lang,
        options=[
            ft.DropdownOption(key=code, text=label)
            for code, label in SUPPORTED_LANGUAGES
        ],
        on_select=cast(Any, maker.on_lang_change),
        label=maker._("Language"),
    )

    maker.personalization_radio = build_binary_radio_group(
        maker._,
        yes_value="Yes",
        no_value="No",
        on_change=maker.clear_binary_choice_errors,
    )
    maker.personalization_label = ft.Text(
        maker._("Does the design have personalization\n(e.g., text from the client)?"),
        size=20,
    )
    maker.personalization_error = ft.Text(
        "",
        color=ft.Colors.RED_700,
        size=12,
        visible=False,
    )

    maker.design_radio = build_binary_radio_group(
        maker._,
        yes_value="yes",
        no_value="no",
        on_change=maker.clear_binary_choice_errors,
    )
    maker.design_label = ft.Text(
        maker._("Does the design have color variations?"),
        size=20,
    )
    maker.design_error = ft.Text(
        "",
        color=ft.Colors.RED_700,
        size=12,
        visible=False,
    )

    maker.design_container = ft.Column(
        [maker.design_label, maker.design_radio, maker.design_error],
        visible=False,
    )
    maker.personalization_container = ft.Column(
        [
            maker.personalization_label,
            maker.personalization_radio,
            maker.personalization_error,
        ],
        visible=False,
    )
    maker.sizes_column = ft.Column(alignment=ft.MainAxisAlignment.CENTER)
    maker.buttons_row = cast(ft.Row, maker.make_size_buttons())
    maker.image_links_column = ft.Column(
        alignment=ft.MainAxisAlignment.CENTER,
        expand=True,
    )
    maker.suggest_button_text = ft.Text(maker._("✨ Suggest title & keywords"))
    maker.suggest_button = ft.ElevatedButton(
        content=maker.suggest_button_text,
        on_click=cast(Any, maker.on_suggest_title_keywords_click),
        height=50,
        disabled=True,
    )
    maker.suggest_progress_ring = ft.ProgressRing(visible=False, width=24, height=24)
    maker.main_image_note = ft.Text(
        maker._(MAIN_IMAGE_WARNING),
        color=ft.Colors.ORANGE_700,
        size=14,
        text_align=ft.TextAlign.CENTER,
        visible=True,
    )
    maker.image_buttons_row = cast(ft.Row, maker.make_image_buttons())
    maker.folder_picker = ft.FilePicker()
    maker.page.services.append(maker.folder_picker)

    maker.submit_button_text = ft.Text(maker._("Generate Spreadsheet"))
    maker.submit_button = ft.ElevatedButton(
        content=maker.submit_button_text,
        on_click=cast(Any, maker.on_submit_click),
        height=50,
    )
    maker.progress_ring = ft.ProgressRing(visible=False, width=30, height=30)
    maker.success_icon = ft.Icon(
        ft.Icons.CHECK,
        color=ft.Colors.GREEN,
        visible=False,
        size=30,
    )

    maker.submit_row = ft.Row(
        controls=[maker.submit_button, maker.progress_ring, maker.success_icon],
        alignment=ft.MainAxisAlignment.CENTER,
    )
    maker.sizes_label = ft.Text(maker._("Sizes"), size=20)
    maker.print_type_dd = ft.Dropdown(
        label=maker._("Print Type"),
        width=500,
        options=[
            ft.DropdownOption(key="decals", text=maker._("Decals")),
            ft.DropdownOption(key="wallpapers", text=maker._("Wallpapers")),
        ],
        on_select=cast(Any, maker.get_dropdown_value),
    )

    maker.title_field = ft.TextField(
        label=maker._("Listing Title"),
        width=500,
        expand=True,
        max_length=255,
    )
    maker.sku_field = ft.TextField(
        label="SKU",
        width=500,
        hint_text=maker._("e.g.: VN007"),
        expand=True,
        capitalization=ft.TextCapitalization.CHARACTERS,
    )
    maker.keyword_field = ft.TextField(
        label=maker._("Keywords"),
        width=500,
        hint_text=maker._("e.g. (in plural): Dog Wall Stickers"),
        expand=True,
    )

    maker.sizes_column.controls.append(maker.make_size_row(0))
    maker.image_links_column.controls.append(maker.make_image_link_row(0))
