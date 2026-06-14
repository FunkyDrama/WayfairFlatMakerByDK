"""Submission and validation flow for the form."""

import asyncio
import os
from typing import TYPE_CHECKING, cast

import flet as ft

from app.constants import (
    ERROR_HIGHLIGHT_DURATION_SECONDS,
    ERROR_SNACKBAR_DURATION_MS,
    SUCCESS_SNACKBAR_DURATION_MS,
)
from app.gemini import GeminiUserError
from data import DataShaperFactory
from data.models import MarketingTexts
from data.pricing import PriceSourceError

if TYPE_CHECKING:
    from app.flat_maker import WayfairFlatMaker


def get_size_fields(row: ft.Row) -> tuple[ft.TextField, ft.TextField]:
    """Return strongly typed controls for a size row."""

    return (
        cast(ft.TextField, row.controls[0]),
        cast(ft.TextField, row.controls[1]),
    )


def validate_fields(maker: "WayfairFlatMaker") -> bool:
    """Validate all fields and display inline errors."""

    maker.validation_error_kinds = set()
    valid = True

    valid = maker.require_dropdown(maker.print_type_dd) and valid
    valid = maker.require_plain_text(maker.title_field) and valid
    valid = maker.require_plain_text(maker.sku_field) and valid
    valid = maker.require_plain_text(maker.keyword_field) and valid

    if maker.print_type_dd.value == "decals":
        valid = (
            maker.require_segmented_value(
                maker.design_radio.value,
                maker.design_error,
                maker._("Does the design have color variations?"),
            )
            and valid
        )
        valid = (
            maker.require_segmented_value(
                maker.personalization_radio.value,
                maker.personalization_error,
                maker._(
                    "Does the design have personalization\n(e.g., text from the client)?"
                ),
            )
            and valid
        )

    if not maker.image_links_column.controls:
        valid = False
    else:
        valid = (
            maker.require_url(
                maker.get_image_field(
                    cast(ft.Row, maker.image_links_column.controls[0])
                ),
                required=True,
            )
            and valid
        )
        for control in maker.image_links_column.controls[1:]:
            image_row = cast(ft.Row, control)
            valid = (
                maker.require_url(maker.get_image_field(image_row), required=False)
                and valid
            )

    for control in maker.sizes_column.controls:
        row = cast(ft.Row, control)
        width_field, height_field = get_size_fields(row)
        valid = maker.require_value(width_field) and valid
        valid = maker.require_value(height_field) and valid

    maker.page.update()
    return valid


async def get_ai_marketing_texts(
    maker: "WayfairFlatMaker",
    title: str,
    keyword: str,
    print_type_value: str,
) -> tuple[MarketingTexts | None, str | None]:
    """Return AI-generated marketing texts plus a user-facing warning if needed."""

    if not maker.gemini_client.is_configured:
        return None, None
    try:
        texts = await asyncio.to_thread(
            maker.gemini_client.generate_marketing_texts,
            title,
            keyword,
            print_type_value,
        )
        return texts, None
    except GeminiUserError as exc:
        return None, maker._(exc.user_message)
    except Exception:
        return None, maker._(
            "AI text generation failed. Standard template text was used."
        )


async def clear_errors(maker: "WayfairFlatMaker") -> None:
    """Clear highlighted errors after a short delay."""

    maker.progress_ring.visible = False
    maker.page.update()
    await asyncio.sleep(ERROR_HIGHLIGHT_DURATION_SECONDS)

    if maker.print_type_dd.error_text:
        maker.print_type_dd.value = None
    maker.print_type_dd.error_text = None

    if maker.title_field.error:
        maker.title_field.value = ""
    maker.title_field.error = None

    if maker.sku_field.error:
        maker.sku_field.value = ""
    maker.sku_field.error = None

    if maker.keyword_field.error:
        maker.keyword_field.value = ""
    maker.keyword_field.error = None

    if maker.design_error.visible:
        maker.design_radio.value = None
    maker.set_segmented_error(maker.design_error, None)

    if maker.personalization_error.visible:
        maker.personalization_radio.value = None
    maker.set_segmented_error(maker.personalization_error, None)

    for control in maker.image_links_column.controls:
        image_row = cast(ft.Row, control)
        field = maker.get_image_field(image_row)
        if field.error:
            field.value = ""
        field.error = None

    for control in maker.sizes_column.controls:
        row = cast(ft.Row, control)
        for ctrl in row.controls:
            field = cast(ft.TextField, ctrl)
            if field.error:
                field.value = ""
            field.error = None

    maker.page.update()


async def submit_form(
    maker: "WayfairFlatMaker",
    folder: str | os.PathLike[str],
) -> None:
    """Validate inputs, generate the spreadsheet, and report the result."""

    maker.progress_ring.visible = True
    maker.success_icon.visible = False
    maker.submit_button.disabled = True
    maker.page.update()

    await asyncio.sleep(0.1)

    generated = False
    try:
        if not validate_fields(maker):
            snack_bar = ft.SnackBar(
                ft.Text(maker.validation_summary_message()),
                duration=ERROR_SNACKBAR_DURATION_MS,
                show_close_icon=True,
                bgcolor=ft.Colors.RED_100,
            )
            maker.page.show_dialog(snack_bar)
            await clear_errors(maker)
            return

        print_type_value = maker.print_type_dd.value
        if print_type_value is None:
            raise ValueError("Print type is required before submission.")
        shaper = DataShaperFactory.create_shaper(print_type_value)

        title = maker.title_field.value
        sku = maker.sku_field.value
        keyword = maker.keyword_field.value
        image_links = [
            maker.get_image_field(cast(ft.Row, control)).value.strip()
            for control in maker.image_links_column.controls
            if (maker.get_image_field(cast(ft.Row, control)).value or "").strip()
        ]
        design_choice = maker.design_radio.value or "no"
        personalization_choice = maker.personalization_radio.value or "No"
        if maker.gemini_client.is_configured:
            maker.submit_button_text.value = maker._("Generating...")
            maker.page.update()
        marketing_texts, ai_warning = await get_ai_marketing_texts(
            maker,
            cast(str, title),
            cast(str, keyword),
            print_type_value,
        )

        for control in maker.sizes_column.controls:
            row = cast(ft.Row, control)
            width_field, height_field = get_size_fields(row)
            width = int(cast(str, width_field.value))
            height = int(cast(str, height_field.value))
            price: float | dict[str, float]
            if print_type_value == "wallpapers":
                price = maker.price_provider.get_wallpaper_prices(width, height)
            else:
                price = maker.price_provider.get_decal_price(
                    width,
                    height,
                    design_choice,
                )
            shaper.add_record(
                title=cast(str, title),
                keyword=cast(str, keyword),
                sku=cast(str, sku),
                image_links=image_links,
                height=height,
                width=width,
                price=price,
                color_choice=design_choice if print_type_value == "decals" else "no",
                personalization_choice=(
                    personalization_choice if print_type_value == "decals" else "No"
                ),
                marketing_texts=marketing_texts,
            )

        shaper.write_file(cast(str, sku), folder)

        maker.progress_ring.visible = False
        maker.success_icon.visible = True

        message = ai_warning or maker._("Spreadsheet generated")
        snack_bar = ft.SnackBar(
            ft.Text(message),
            duration=SUCCESS_SNACKBAR_DURATION_MS,
            bgcolor=ft.Colors.ORANGE_100 if ai_warning else ft.Colors.GREEN_100,
            show_close_icon=bool(ai_warning),
        )
        maker.page.show_dialog(snack_bar)
        generated = True
        maker.reset_form()
        maker.page.update()
    except PriceSourceError:
        maker.progress_ring.visible = False
        alert = ft.AlertDialog(
            title=ft.Text(
                maker._(
                    "Could not load price data. Check your internet connection and try again."
                )
            )
        )
        maker.page.show_dialog(alert)
    except Exception as ex:
        maker.progress_ring.visible = False
        alert = ft.AlertDialog(title=ft.Text(maker._("Error: %(err)s") % {"err": ex}))
        maker.page.show_dialog(alert)
    finally:
        if not generated:
            maker.progress_ring.visible = False
        maker.submit_button.disabled = False
        maker.submit_button_text.value = maker._("Generate Spreadsheet")
        maker.page.update()
