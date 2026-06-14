"""UI update operations shared across the form lifecycle."""

from typing import TYPE_CHECKING, cast

import flet as ft

from app.constants import AUTOFILL_HELPER_TEXT, MAIN_IMAGE_WARNING

if TYPE_CHECKING:
    from app.flat_maker import WayfairFlatMaker


def get_size_fields(row: ft.Row) -> tuple[ft.TextField, ft.TextField]:
    """Return strongly typed controls for a size row."""

    return (
        cast(ft.TextField, row.controls[0]),
        cast(ft.TextField, row.controls[1]),
    )


def get_radio_control(group: ft.RadioGroup, index: int) -> ft.Radio:
    """Return a strongly typed radio control from a radio group row."""

    content_row = cast(ft.Row, group.content)
    container = cast(ft.Container, content_row.controls[index])
    return cast(ft.Radio, container.content)


def refresh_size_hints(maker: "WayfairFlatMaker") -> None:
    """Refresh hint text for all size rows."""

    width_hints, height_hints = maker.hint_sets()
    for index, control in enumerate(maker.sizes_column.controls):
        row = cast(ft.Row, control)
        width_field, height_field = get_size_fields(row)
        width_field.hint_text = width_hints[index % len(width_hints)]
        height_field.hint_text = height_hints[index % len(height_hints)]


def handle_print_type_change(maker: "WayfairFlatMaker") -> None:
    """Update dependent UI state after the print type changes."""

    maker.set_print_type_visibility()
    refresh_size_hints(maker)
    maker.keyword_field.hint_text = get_keyword_hint(maker)
    maker.toggle_main_image_note()
    maker.page.update()


def get_keyword_hint(maker: "WayfairFlatMaker") -> str:
    """Return the keyword example for the selected print type."""

    if maker.print_type_dd.value == "wallpapers":
        return maker._("e.g. (in plural): Dog Wallpapers")
    return maker._("e.g. (in plural): Dog Wall Stickers")


def apply_i18n(maker: "WayfairFlatMaker") -> None:
    """Re-apply all translatable labels and helper texts."""

    maker.design_label.value = maker._("Does the design have color variations?")
    maker.personalization_label.value = maker._(
        "Does the design have personalization\n(e.g., text from the client)?"
    )
    maker.sizes_label.value = maker._("Sizes")
    maker.print_type_dd.label = maker._("Print Type")
    maker.print_type_dd.options[0].text = maker._("Decals")
    maker.print_type_dd.options[1].text = maker._("Wallpapers")
    maker.title_field.label = maker._("Listing Title")
    maker.sku_field.label = "SKU"
    maker.sku_field.hint_text = maker._("e.g.: VN007")
    maker.lang_dd.label = maker._("Language")
    maker.keyword_field.label = maker._("Keywords")
    maker.keyword_field.hint_text = get_keyword_hint(maker)
    maker.suggest_button_text.value = maker._("✨ Suggest title & keywords")
    maker.main_image_note.value = maker._(MAIN_IMAGE_WARNING)
    maker.submit_button_text.value = maker._("Generate Spreadsheet")
    get_radio_control(maker.design_radio, 0).label = maker._("Yes")
    get_radio_control(maker.design_radio, 1).label = maker._("No")
    get_radio_control(maker.personalization_radio, 0).label = maker._("Yes")
    get_radio_control(maker.personalization_radio, 1).label = maker._("No")

    width_hints, height_hints = maker.hint_sets()
    for index, control in enumerate(maker.sizes_column.controls):
        row = cast(ft.Row, control)
        width_field, height_field = get_size_fields(row)
        width_field.label = maker._("Width")
        width_field.hint_text = width_hints[index % len(width_hints)]
        width_field.helper = maker._(AUTOFILL_HELPER_TEXT)
        height_field.label = maker._("Height")
        height_field.hint_text = height_hints[index % len(height_hints)]
        height_field.helper = maker._(AUTOFILL_HELPER_TEXT)

    for index, control in enumerate(maker.image_links_column.controls):
        row = cast(ft.Row, control)
        field = cast(ft.TextField, row.controls[0])
        field.label = f"{maker._('Image Link')} #{index + 1}"
        field.tooltip = maker._(MAIN_IMAGE_WARNING) if index == 0 else None
        field.on_change = maker.toggle_main_image_note if index == 0 else None
        if index == 0 and maker.suggest_button not in row.controls:
            row.controls.append(maker.suggest_button)
        if index == 0 and maker.suggest_progress_ring not in row.controls:
            row.controls.append(maker.suggest_progress_ring)

    maker.toggle_main_image_note()


def add_size(maker: "WayfairFlatMaker") -> None:
    """Append a new size row."""

    maker.sizes_column.controls.append(
        maker.make_size_row(len(maker.sizes_column.controls))
    )
    maker.page.update()


def remove_size(maker: "WayfairFlatMaker") -> None:
    """Remove the last size row while keeping at least one row."""

    if len(maker.sizes_column.controls) > 1:
        maker.sizes_column.controls.pop()
        maker.page.update()


def add_image_link(maker: "WayfairFlatMaker") -> None:
    """Append a new image-link row."""

    maker.image_links_column.controls.append(
        maker.make_image_link_row(len(maker.image_links_column.controls))
    )
    maker.toggle_main_image_note()
    maker.page.update()


def remove_image_link(maker: "WayfairFlatMaker") -> None:
    """Remove the last image-link row while keeping at least one row."""

    if len(maker.image_links_column.controls) > 1:
        maker.image_links_column.controls.pop()
        maker.toggle_main_image_note()
        maker.page.update()


def reset_dynamic_controls(maker: "WayfairFlatMaker") -> None:
    """Clear dynamic rows without changing their current count."""

    for control in maker.sizes_column.controls:
        row = cast(ft.Row, control)
        for ctrl in row.controls:
            field = cast(ft.TextField, ctrl)
            field.value = ""
            field.error = None
    for control in maker.image_links_column.controls:
        image_row = cast(ft.Row, control)
        field = maker.get_image_field(image_row)
        field.value = ""
        field.error = None

    refresh_size_hints(maker)

    for index, control in enumerate(maker.image_links_column.controls):
        image_row = cast(ft.Row, control)
        field = maker.get_image_field(image_row)
        field.label = f"{maker._('Image Link')} #{index + 1}"
        field.tooltip = maker._(MAIN_IMAGE_WARNING) if index == 0 else None
        field.on_change = maker.toggle_main_image_note if index == 0 else None
        if index == 0 and maker.suggest_button not in image_row.controls:
            image_row.controls.append(maker.suggest_button)
        if index == 0 and maker.suggest_progress_ring not in image_row.controls:
            image_row.controls.append(maker.suggest_progress_ring)


def reset_form(maker: "WayfairFlatMaker") -> None:
    """Reset the entire form to its initial state."""

    maker.print_type_dd.value = None
    maker.print_type_dd.error_text = None
    maker.title_field.value = ""
    maker.title_field.error = None
    maker.sku_field.value = ""
    maker.sku_field.error = None
    maker.keyword_field.value = ""
    maker.keyword_field.error = None
    maker.design_radio.value = None
    maker.personalization_radio.value = None
    maker.set_segmented_error(maker.design_error, None)
    maker.set_segmented_error(maker.personalization_error, None)
    reset_dynamic_controls(maker)
    maker.set_print_type_visibility()
    maker.toggle_main_image_note()


def init_ui(maker: "WayfairFlatMaker") -> None:
    """Render the top-level page layout."""

    maker.page.add(
        ft.Row(
            controls=[ft.Image(src="logo.png", fit=ft.BoxFit.FIT_HEIGHT, height=70)],
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        ft.Row(controls=[maker.lang_dd], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row(controls=[maker.print_type_dd], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row(controls=[maker.title_field], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row(controls=[maker.sku_field], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row(controls=[maker.keyword_field], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row(
            controls=[ft.Container(content=maker.image_links_column, expand=True)],
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        ft.Row(controls=[maker.main_image_note], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row(
            controls=[maker.image_buttons_row], alignment=ft.MainAxisAlignment.CENTER
        ),
        ft.Row(
            controls=[maker.design_container], alignment=ft.MainAxisAlignment.CENTER
        ),
        ft.Divider(),
        ft.Row(
            controls=[maker.personalization_container],
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        ft.Divider(),
        ft.Row(controls=[maker.sizes_label], alignment=ft.MainAxisAlignment.CENTER),
        maker.sizes_column,
        ft.Row(controls=[maker.buttons_row], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(),
        ft.Row(controls=[maker.submit_row], alignment=ft.MainAxisAlignment.CENTER),
    )
