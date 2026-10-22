"""Base data-shaper implementation shared by product-specific shapers."""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
import os
from pathlib import Path

from data.excel_writer import ExcelWriter
from data.models import (
    MarketingTexts,
    PackageParameters,
    PriceInput,
    RowData,
)


class BaseDataShaper(ABC):
    """Base class for product-specific data shapers."""

    MAX_IMAGE_SLOTS: int = 30
    MAX_PRODUCT_NAME_CHARS: int = 254

    def __init__(self, sheet_name: str) -> None:
        """Initialize shared storage and the workbook writer."""

        self.rows: list[RowData] = []
        self.writer = ExcelWriter(sheet_name=sheet_name)

    @property
    @abstractmethod
    def technical_image_count(self) -> int:
        """Return the maximum number of technical images added to a listing."""

    @property
    def max_user_images(self) -> int:
        """Return how many user images fit beside the technical images."""

        return self.MAX_IMAGE_SLOTS - self.technical_image_count

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
        marketing_texts: MarketingTexts | None = None,
    ) -> None:
        """Append one logical product variation to the output set."""

    @staticmethod
    def resolve_image_slots(
        user_links: Sequence[str],
        technical_links: Sequence[str],
    ) -> RowData:
        """Map user and technical images into Wayfair image columns."""

        cleaned_technical_links = [
            link.strip() for link in technical_links if link and link.strip()
        ]
        # Slot 1 is the lead image, so only a user image may occupy it.
        lead_image = user_links[0] if user_links else None
        images = [lead_image, *user_links[1:], *cleaned_technical_links][
            : BaseDataShaper.MAX_IMAGE_SLOTS
        ]
        return {
            f"Image File Name or URL {index}": image
            for index, image in enumerate(images, start=1)
        }

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
    def format_product_name(title: str, sku: str) -> str:
        """Join title and SKU, trimming the title to Wayfair's name limit."""

        max_title_chars = BaseDataShaper.MAX_PRODUCT_NAME_CHARS - len(sku) - 1
        title = title.strip()
        if len(title) > max_title_chars:
            title = title[: max_title_chars + 1].rsplit(" ", maxsplit=1)[0]
            title = title[:max_title_chars].rstrip(" ,;:-")
        return f"{title} {sku}"

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

    def write_file(self, sku: str, folder: str | os.PathLike[str]) -> Path:
        """Finalize row ordering, write the workbook, and return its path."""

        self.apply_primary_variant_flags(sku)
        self.rows.sort(
            key=lambda item: (
                0 if "Peel-n-Stick" in item.get("Manufacturer Part Number", "") else 1
            )
        )
        self.rows = [self.finalize_row(row) for row in self.rows]
        output_path = self.writer.write_data(self.rows, sku, folder)
        self.rows.clear()
        return output_path
