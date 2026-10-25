"""Submission and validation flow for the form."""

import asyncio
import os
from pathlib import Path
import time
from typing import TYPE_CHECKING, cast

import flet as ft

from app.constants import (
    ERROR_HIGHLIGHT_DURATION_SECONDS,
    ERROR_SNACKBAR_DURATION_MS,
    SUCCESS_SNACKBAR_DURATION_MS,
)
from app.diagnostics import get_logger
from app.gemini import GeminiUserError
from app.helpers import open_file, reveal_file
from app.ui_ops import get_max_image_links
from data import DataShaperFactory
from data.models import MarketingTexts
from data.pricing import PriceSourceError

if TYPE_CHECKING:
    from app.flat_maker import WayfairFlatMaker

logger = get_logger("export")


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

        max_images = get_max_image_links(maker)
        for control in maker.image_links_column.controls[max_images:]:
            image_field = maker.get_image_field(cast(ft.Row, control))
            if (image_field.value or "").strip():
                maker.validation_error_kinds.add("invalid")
                image_field.error = maker._(
                    "Up to %(count)s image links are allowed for this print type."
                ) % {"count": max_images}
                valid = False

    for control in maker.sizes_column.controls:
        row = cast(ft.Row, control)
        width_field, height_field = get_size_fields(row)
        valid = maker.require_value(width_field) and valid
        valid = maker.require_value(height_field) and valid

    maker.page.update()
    return valid


def build_success_snack_bar(
    maker: "WayfairFlatMaker",
    output_path: Path,
    warnings: list[str],
) -> ft.SnackBar:
    """Build the export confirmation with shortcuts to the generated file."""

    message = maker._("Spreadsheet generated: %(file)s") % {"file": output_path.name}
    return ft.SnackBar(
        ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(message, weight=ft.FontWeight.W_500),
                        *[ft.Text(warning) for warning in warnings],
                    ],
                    spacing=2,
                    tight=True,
                    expand=True,
                ),
                ft.TextButton(
                    maker._("Open file"),
                    icon=ft.Icons.OPEN_IN_NEW,
                    on_click=lambda _: open_file(output_path),
                ),
                ft.TextButton(
                    maker._("Show in folder"),
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=lambda _: reveal_file(output_path),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        duration=SUCCESS_SNACKBAR_DURATION_MS,
        bgcolor=ft.Colors.ORANGE_100 if warnings else ft.Colors.GREEN_100,
        show_close_icon=True,
    )


async def get_ai_marketing_texts(
    maker: "WayfairFlatMaker",
    title: str,
    keyword: str,
    print_type_value: str,
    has_color_variations: bool,
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
            has_color_variations,
        )
        return texts, None
    except GeminiUserError as exc:
        logger.warning("AI marketing texts failed, using defaults: %s", exc)
        return None, maker._(exc.user_message)
    except Exception:
        logger.exception("AI marketing texts crashed, using defaults")
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
    started = time.monotonic()
    try:
        if not validate_fields(maker):
            logger.info(
                "Export blocked by validation: %s",
                sorted(maker.validation_error_kinds) or "unspecified",
            )
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
        logger.info(
            "Export started: %s, SKU %s, %s sizes, %s images, color variations %s",
            print_type_value,
            sku,
            len(maker.sizes_column.controls),
            len(image_links),
            design_choice,
        )
        if maker.gemini_client.is_configured:
            maker.submit_button_text.value = maker._("Generating...")
            maker.page.update()
        # Marketing copy and the main-image analysis run in parallel.
        (marketing_texts, ai_warning), analysis = await asyncio.gather(
            get_ai_marketing_texts(
                maker,
                cast(str, title),
                cast(str, keyword),
                print_type_value,
                print_type_value == "decals" and design_choice == "yes",
            ),
            maker.get_main_image_analysis(image_links[0], print_type_value),
        )
        warnings = [ai_warning] if ai_warning else []
        coverage_warning = maker.main_image_coverage_warning(analysis)
        if coverage_warning:
            warnings.append(coverage_warning)

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
                ai_attributes=analysis.attributes if analysis else None,
            )

        output_path = shaper.write_file(cast(str, sku), folder)
        logger.info(
            "Export finished in %.1fs: %s (AI texts %s, AI attributes %s)",
            time.monotonic() - started,
            output_path,
            "yes" if marketing_texts else "no",
            "yes" if analysis and analysis.attributes else "no",
        )

        maker.progress_ring.visible = False
        maker.success_icon.visible = True
        maker.page.show_dialog(build_success_snack_bar(maker, output_path, warnings))
        generated = True
        maker.reset_form()
        maker.page.update()
    except PriceSourceError:
        logger.warning("Export failed: price data unavailable", exc_info=True)
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
        logger.exception("Export failed")
        maker.progress_ring.visible = False
        maker.page.show_dialog(
            maker.build_error_dialog(maker._("Error: %(err)s") % {"err": ex})
        )
    finally:
        if not generated:
            maker.progress_ring.visible = False
        maker.submit_button.disabled = False
        maker.submit_button_text.value = maker._("Generate Spreadsheet")
        maker.page.update()
