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
SizeChangeHandler = Callable[[ft.Row], None]
PreviewClickHandler = Callable[[str], None]

# Small enough to sit inside the field without touching its floating label.
THUMBNAIL_SIZE = 32


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
    on_change: SizeChangeHandler,
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
    width_field.on_change = lambda e, current_row=row: on_change(current_row)
    height_field.on_change = lambda e, current_row=row: on_change(current_row)
    return row


def build_image_thumbnail(
    image_url: str | None,
    *,
    translate: Translator,
    on_open: PreviewClickHandler,
) -> ft.Container:
    """Build the small preview shown at the start of an image-link field.

    Empty links show a neutral placeholder; links that do not load show a red
    broken-image icon, so a wrong or private link is visible at a glance.
    """

    content: ft.Control
    if image_url:
        content = ft.Image(
            src=image_url,
            width=THUMBNAIL_SIZE,
            height=THUMBNAIL_SIZE,
            fit=ft.BoxFit.COVER,
            error_content=ft.Icon(
                ft.Icons.BROKEN_IMAGE_OUTLINED,
                color=ft.Colors.RED_400,
                size=20,
                tooltip=translate("The image could not be loaded. Check the link."),
            ),
        )
    else:
        content = ft.Icon(ft.Icons.IMAGE_OUTLINED, color=ft.Colors.GREY_400, size=20)
    return ft.Container(
        content=content,
        width=THUMBNAIL_SIZE,
        height=THUMBNAIL_SIZE,
        border_radius=5,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        bgcolor=ft.Colors.GREY_100,
        alignment=ft.Alignment.CENTER,
        margin=ft.Margin(left=10, right=8, top=4, bottom=4),
        tooltip=translate("Click to enlarge") if image_url else None,
        on_click=(lambda e, url=image_url: on_open(url)) if image_url else None,
        data=image_url,
    )


def build_image_link_row(
    index: int,
    *,
    translate: Translator,
    on_change: TextFieldChangeHandler,
    on_open_preview: PreviewClickHandler,
    suggest_button: ft.Control | None = None,
    suggest_progress_ring: ft.Control | None = None,
) -> ft.Row:
    """Build a single image-link row with a preview at the start of the field."""

    field = ft.TextField(
        label=f"{translate('Image Link')} #{index + 1}",
        expand=True,
        prefix_icon=build_image_thumbnail(
            None, translate=translate, on_open=on_open_preview
        ),
        on_change=on_change,
    )
    if index == 0:
        field.tooltip = translate(MAIN_IMAGE_WARNING)
    controls: list[ft.Control] = [field]
    if suggest_button is not None:
        controls.append(suggest_button)
    if suggest_progress_ring is not None:
        controls.append(suggest_progress_ring)
    return ft.Row(
        controls=controls,
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
