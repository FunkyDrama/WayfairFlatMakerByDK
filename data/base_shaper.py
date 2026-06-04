"""Base data-shaper implementation shared by product-specific shapers."""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
import os

from data.excel_writer import ExcelWriter
from data.models import (
    AdditionalImageRow,
    MarketingTexts,
    PackageParameters,
    PriceInput,
    RowData,
)


class BaseDataShaper(ABC):
    """Base class for product-specific data shapers."""

    def __init__(self, sheet_name: str) -> None:
        """Initialize shared storage and the workbook writer."""

        self.rows: list[RowData] = []
        self.additional_image_rows: list[AdditionalImageRow] = []
        self.writer = ExcelWriter(sheet_name=sheet_name)

    @abstractmethod
    def set_texts(self, keyword: str, **kwargs: str) -> MarketingTexts:
        """Build marketing copy fields for a generated record."""

    @abstractmethod
    def set_size_and_weight(self, height: int, width: int) -> PackageParameters:
        """Return packaging metadata for the supplied size."""

    @abstractmethod
    def add_record(
        self,
        title: str,
        keyword: str,
        sku: str,
        image_links: Sequence[str] | None,
        height: int,
        width: int,
        price: PriceInput,
        color_choice: str | None = None,
        personalization_choice: str | None = None,
    ) -> None:
        """Append one logical product variation to the output set."""

    @staticmethod
    def resolve_image_slots(
        user_links: Sequence[str],
        technical_links: Sequence[str],
    ) -> tuple[list[str | None], list[str]]:
        """Map user and technical images into Wayfair image slots."""

        image_slot1 = user_links[0] if user_links else None
        cleaned_technical_links = [
            link.strip() for link in technical_links if link and link.strip()
        ]
        tail_images = [*user_links[1:], *cleaned_technical_links]
        secondary_slots = [
            tail_images[index] if index < len(tail_images) else None
            for index in range(4)
        ]
        additional_images = [image for image in tail_images[4:] if image]
        return [image_slot1, *secondary_slots], additional_images

    @staticmethod
    def clean_image_links(image_links: Sequence[str] | None) -> list[str]:
        """Trim and drop empty image-link values."""

        return [link.strip() for link in (image_links or []) if link and link.strip()]

    @staticmethod
    def get_single_price(price: PriceInput) -> float:
        """Return a scalar price and reject material-specific price maps."""

        if isinstance(price, Mapping):
            raise ValueError("A scalar price is required for this product type.")
        return price

    @staticmethod
    def get_material_price(price: PriceInput, material_name: str) -> float:
        """Return the price for one material from a scalar or material map."""

        if isinstance(price, Mapping):
            try:
                return price[material_name]
            except KeyError as exc:
                raise ValueError(
                    f"Missing price for material: {material_name}"
                ) from exc
        return price

    @staticmethod
    def format_size(width: int | float, height: int | float) -> str:
        """Format dimensions as the size label expected by Wayfair."""

        return f"{int(width)}x{int(height)} inches"

    @staticmethod
    def finalize_row(row: RowData) -> RowData:
        """Remove internal sorting keys from an export row."""

        row.pop("variant_sort_price", None)
        row.pop("variant_sort_area", None)
        row.pop("variant_sort_order", None)
        return row

    def apply_primary_variant_flags(self, sku: str) -> None:
        """Mark the cheapest variant in a group as the primary variant."""

        group_rows = [row for row in self.rows if row.get("Group Reference ID") == sku]
        if not group_rows:
            return

        primary_row = min(
            group_rows,
            key=lambda row: (
                float(row.get("variant_sort_price", float("inf"))),
                float(row.get("variant_sort_area", float("inf"))),
                int(row.get("variant_sort_order", 0)),
            ),
        )
        for row in group_rows:
            row["Variant Type"] = (
                "Primary Variant" if row is primary_row else "Non-Primary Variant"
            )

    def write_file(self, sku: str, folder: str | os.PathLike[str]) -> None:
        """Finalize row ordering and write the workbook to disk."""

        self.apply_primary_variant_flags(sku)
        self.rows.sort(
            key=lambda item: (
                0 if "Peel-n-Stick" in item.get("Manufacturer Part Number", "") else 1
            )
        )
        self.rows = [self.finalize_row(row) for row in self.rows]
        self.writer.write_data_with_additional_images(
            self.rows,
            self.additional_image_rows,
            sku,
            folder,
        )
        self.rows.clear()
        self.additional_image_rows.clear()
