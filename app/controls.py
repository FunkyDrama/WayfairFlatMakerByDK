"""Reusable control builders for the Wayfair form."""

from collections.abc import Callable
from typing import cast

import flet as ft

from app.constants import AUTOFILL_HELPER_TEXT, MAIN_IMAGE_WARNING
from app.helpers import HintSets, Translator

RadioChangeHandler = Callable[[ft.Event[ft.RadioGroup]], None]
TextFieldChangeHandler = Callable[[ft.Event[ft.TextField]], None]
IconClickHandler = Callable[[ft.Event[ft.IconButton]], None]
SizeSubmitHandler = Callable[[ft.Event[ft.TextField], ft.Row], None]


def build_binary_radio_group(
    translate: Translator,
    *,
    yes_value: str,
    no_value: str,
    on_change: RadioChangeHandler,
) -> ft.RadioGroup:
    """Build a two-option radio group for Yes/No choices."""

    return ft.RadioGroup(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Radio(
                        label=translate("Yes"),
                        value=yes_value,
                        label_style=ft.TextStyle(size=20),
                    ),
                    margin=ft.Margin(top=0, right=20, bottom=0, left=0),
                ),
                ft.Container(
                    content=ft.Radio(
                        label=translate("No"),
                        value=no_value,
                        label_style=ft.TextStyle(size=20),
                    ),
                    margin=ft.Margin(top=0, right=0, bottom=0, left=100),
                ),
            ],
            spacing=30,
        ),
        value=None,
        on_change=on_change,
    )


def build_size_row(
    index: int,
    *,
    hint_sets: HintSets,
    translate: Translator,
    on_submit: SizeSubmitHandler,
) -> ft.Row:
    """Build a row with width and height fields."""

    width_hints, height_hints = hint_sets
    width_hint = width_hints[index % len(width_hints)]
    height_hint = height_hints[index % len(height_hints)]

    width_field = ft.TextField(
        label=translate("Width"),
        width=200,
        input_filter=ft.NumbersOnlyInputFilter(),
        hint_text=width_hint,
        helper=translate(AUTOFILL_HELPER_TEXT),
        helper_style=ft.TextStyle(size=11, color=ft.Colors.GREY_700),
    )
    height_field = ft.TextField(
        label=translate("Height"),
        width=200,
        input_filter=ft.NumbersOnlyInputFilter(),
        hint_text=height_hint,
        helper=translate(AUTOFILL_HELPER_TEXT),
        helper_style=ft.TextStyle(size=11, color=ft.Colors.GREY_700),
    )
    row = ft.Row(
        controls=[width_field, height_field],
        alignment=ft.MainAxisAlignment.CENTER,
    )
    width_field.on_submit = lambda e, current_row=row: on_submit(
        cast(ft.Event[ft.TextField], e), current_row
    )
    height_field.on_submit = lambda e, current_row=row: on_submit(
        cast(ft.Event[ft.TextField], e), current_row
    )
    return row


def build_image_link_row(
    index: int,
    *,
    translate: Translator,
    on_first_change: TextFieldChangeHandler,
) -> ft.Row:
    """Build a single image-link row."""

    field = ft.TextField(
        label=f"{translate('Image Link')} #{index + 1}",
        expand=True,
    )
    if index == 0:
        field.tooltip = translate(MAIN_IMAGE_WARNING)
        field.on_change = on_first_change
    return ft.Row(
        controls=[field],
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
    )


def build_counter_buttons(
    *,
    on_add: IconClickHandler,
    on_remove: IconClickHandler,
) -> ft.Row:
    """Build paired add/remove icon buttons."""

    add_button = ft.IconButton(icon=ft.Icons.ADD, on_click=on_add, icon_size=30)
    remove_button = ft.IconButton(
        icon=ft.Icons.REMOVE, on_click=on_remove, icon_size=30
    )
    return ft.Row(controls=[add_button, remove_button], spacing=80)
