"""Data shaping layer for Wayfair spreadsheet export."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
from typing import Any
from collections.abc import Sequence

from data.excel_writer import ExcelWriter

RowData = dict[str, Any]
AdditionalImageRow = dict[str, str]


@dataclass(frozen=True)
class MarketingTexts:
    """Structured marketing copy for a generated item."""

    marketing_copy: str
    feature_bullet_1: str
    feature_bullet_2: str


@dataclass(frozen=True)
class PackageParameters:
    """Shipping dimensions and weight for a generated item."""

    weight: int
    height: int
    width: int
    depth: int


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
        price: float,
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
        tail_images = [*user_links[1:], *technical_links]
        secondary_slots = [
            tail_images[index] if index < len(tail_images) else None
            for index in range(4)
        ]
        additional_images = tail_images[4:]
        return [image_slot1, *secondary_slots], additional_images

    @staticmethod
    def clean_image_links(image_links: Sequence[str] | None) -> list[str]:
        """Trim and drop empty image-link values."""

        return [link.strip() for link in (image_links or []) if link and link.strip()]

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


class DecalDataShaper(BaseDataShaper):
    """Data shaper for decal listings."""

    def __init__(self) -> None:
        """Initialize decal-specific constants and templates."""

        super().__init__(
            sheet_name="3757 - Wall Stickers",
        )
        self.common_technical_images: list[str] = [
            "https://www.dropbox.com/scl/fi/p5m99jzack5fvidiwb83d/st-4x-100-2000px.jpg?rlkey=i9l7aqtztr0qvhl4fgile9r2j&st=rfddmlym&dl=0",
            "https://www.dropbox.com/scl/fi/6taulrno3kwou0wfxmo6i/st-4x-100-2000px.jpg?rlkey=1nw33ygu69dl6whdhzhl5vtqc&st=xaw5zd2u&dl=0",
            "https://www.dropbox.com/scl/fi/bwrotbl3sl3z2aztj2pgi/ev-4x-100-2000px.jpg?rlkey=rj11bqw1ssjflxoqajxofwhty&st=5dplbp6e&dl=0",
        ]
        self.color_palette_image = "https://www.dropbox.com/scl/fi/6x6nrzwu8m01vsy557elg/c-1-e-4x-100-2000px.jpg?rlkey=sna67iux3ios35q9qioifshsg&st=gcnkev3i&dl=0"
        self.colors: list[str] = [
            "Green",
            "Dark Green",
            "Lime Green",
            "Ice Blue",
            "Royal Blue",
            "Navy",
            "Mint",
            "Hot Pink",
            "Baby Pink",
            "Lilac",
            "Purple",
            "Teal",
            "Burgundy",
            "Yellow",
            "Orange",
            "Red",
            "Brown",
            "Beige",
            "Grey",
            "Matte Black",
            "Black",
            "White",
            "Metallic Gold",
            "Metallic Silver",
        ]

    def set_texts(self, keyword: str, **kwargs: str) -> MarketingTexts:
        """Build marketing copy for a decal listing."""

        marketing_copy_text = f"Are you in search of the perfect decorative solution for your walls or other smooth surfaces? Look no further than our remarkable {keyword}. These versatile vinyl stickers, also known as wall tattoos or wall vinyl, are designed to elevate your decor while serving informative purposes."
        feature_bullet_1_text = (
            f"Our {keyword} are crafted from high-quality, waterproof material."
        )
        feature_bullet_2_text = (
            f"Variety of Sizes Available: {keyword} come in multiple sizes."
        )
        return MarketingTexts(
            marketing_copy=marketing_copy_text,
            feature_bullet_1=feature_bullet_1_text,
            feature_bullet_2=feature_bullet_2_text,
        )

    def set_size_and_weight(self, height: int, width: int) -> PackageParameters:
        """Return package measurements for a decal variant."""

        if height <= 24 or width <= 24:
            return PackageParameters(weight=1, height=24, width=2, depth=2)

        if 24 < height <= 37 or 24 < width <= 37:
            return PackageParameters(weight=2, height=37, width=3, depth=3)

        if 37 < height <= 48 or 37 < width <= 48:
            return PackageParameters(weight=3, height=48, width=3, depth=3)

        return PackageParameters(weight=4, height=56, width=3, depth=3)

    def make_part_numbers(
        self,
        sku: str,
        height: int,
        width: int,
        color_choice: str = "no",
    ) -> list[str]:
        """Generate all manufacturer part numbers for a decal variation."""

        base_number = f"{sku} {width}x{height}"
        if color_choice == "yes":
            return [f"{base_number} {color}" for color in self.colors]

        return [base_number]

    def add_record(
        self,
        title: str,
        keyword: str,
        sku: str,
        image_links: Sequence[str] | None,
        height: int,
        width: int,
        price: float,
        color_choice: str | None = "no",
        personalization_choice: str | None = "No",
    ) -> None:
        """Append all export rows for a decal variation."""

        package_parameters = self.set_size_and_weight(height, width)
        texts = self.set_texts(keyword)

        cleaned_image_links = self.clean_image_links(image_links)

        technical_images = list(self.common_technical_images)
        if (color_choice or "").strip().lower() == "yes":
            technical_images.insert(0, self.color_palette_image)

        image_slots, additional_images = self.resolve_image_slots(
            cleaned_image_links, technical_images
        )

        base_number = f"{sku} {width}x{height}"
        normalized_color_choice = color_choice or "no"
        part_numbers = self.make_part_numbers(
            sku,
            height,
            width,
            normalized_color_choice,
        )
        size_label = self.format_size(width, height)

        for part_number in part_numbers:
            color_value = (
                part_number[len(base_number) + 1 :]
                if normalized_color_choice == "yes"
                else "Multicolor"
            )
            data: RowData = {
                "Brand": "Stickalz",
                "Supplier Part Number": part_number,
                "Manufacturer Part Number": part_number,
                "Product Name": f"{title} {sku}",
                "Variant Type": "Non-Primary Variant",
                "Group Reference ID": sku,
                "Variant Grouping 1": (
                    "Color" if normalized_color_choice == "yes" else "Size"
                ),
                "Variant Attribute Name On Site 1": (
                    color_value if normalized_color_choice == "yes" else size_label
                ),
                "Variant Grouping 2": (
                    "Size" if normalized_color_choice == "yes" else None
                ),
                "Variant Attribute Name On Site 2": (
                    size_label if normalized_color_choice == "yes" else None
                ),
                "Base Cost": price,
                "Marketing Copy": texts.marketing_copy,
                "Feature Bullet 1": texts.feature_bullet_1,
                "Feature Bullet 2": texts.feature_bullet_2,
                "Feature Bullet 3": "Quick installation with easy-to-follow instructions.",
                "Feature Bullet 4": "Wall decals are suitable for a wide range of surfaces, from walls and doors to windows and even cars.",
                "Feature Bullet 5": "UV protected coating ensures they never fade, preserving their allure.",
                "Minimum Order Quantity": 1,
                "Force Quantity Multiplier": 1,
                "Display Set Quantity": 1,
                "Product Weight": package_parameters.weight,
                "Ship Type": "Small Parcel",
                "Freight Class": 400,
                "Lead Time": 72,
                "Replacement Lead Time": 72,
                "Carton Weight 1": package_parameters.weight,
                "Carton Height 1": package_parameters.height,
                "Carton Width 1": package_parameters.width,
                "Carton Depth 1": package_parameters.depth,
                "Warning Required": "No",
                "Country Of Manufacturer": "United States",
                "Image File Name or URL 1": image_slots[0],
                "Image File Name or URL 2": image_slots[1],
                "Image File Name or URL 3": image_slots[2],
                "Image File Name or URL 4": image_slots[3],
                "Image File Name or URL 5": image_slots[4],
                "Product Type": "Accent",
                "Subject": "Fashion",
                "Surface Type": "Glossy",
                "Material": "Vinyl",
                "Compatible Surfaces": "Multi-Surface;Flat Surface;Glass Wall;Stainless Steel;Existing Tile;Chalkboard;Appliance;Mirror;Acrylic Panel;Laminate;Plywood Wall;Drywall;Ceramic Tile Wall;Concrete;Stone Wall",
                "Non Wall Damaging": "Yes",
                "Reusable": "No",
                "Personalization or Monogramming": personalization_choice,
                "Room Use": "Bedroom;Living Room;Nursery;Home Office;Playroom;School Classroom;Art School",
                "Holiday / Occasion": "No Holiday",
                "BPA Free": "No",
                "Licensed Product Category": "Does Not Apply",
                "Movie / Show Series Name": "Does Not Apply",
                "Durability": "Water Resistant;Fade Resistant;Heat Resistant;Stain Resistant;Tip Resistant;Waterproof;Weather Resistant",
                "Color": color_value,
                "Total Number of Pieces Included": 1,
                "Pieces Included": "Does Not Apply",
                "Uniform Packaging and Labeling Regulations (UPLR) Compliant": "Yes",
                "Canada Product Restriction": "No",
                "Reason for Restriction": "Does Not Apply",
                "Sustainability & Social Responsibility Certifications (North America Only)": "No",
                "Overall Height - Top to Bottom": height,
                "Overall Width - Side to Side": width,
                "Commercial Warranty": "Yes",
                "Commercial Warranty Length": "30 Days",
                "variant_sort_price": price,
                "variant_sort_area": width * height,
                "variant_sort_order": len(self.rows),
            }
            self.rows.append(data)

            self.additional_image_rows.extend(
                [
                    {
                        "Supplier Part Number": part_number,
                        "Image File Name or URL": image_url,
                    }
                    for image_url in additional_images
                ]
            )


class WallpaperDataShaper(BaseDataShaper):
    """Data shaper for wallpaper listings."""

    def __init__(self) -> None:
        """Initialize wallpaper-specific constants and templates."""

        super().__init__(sheet_name="6161 - Wallpaper")
        self.technical_images: list[str] = []
        self.print_type: dict[str, dict[str, str]] = {
            "Peel-n-Stick": {
                "material": "Vinyl",
                "application": "Self-Adhesive",
                "removal": "Peelable",
            },
            "Non-Woven": {
                "material": "Non-Woven",
                "application": "Non-Pasted",
                "removal": "Strippable",
            },
        }

    def set_texts(self, keyword: str, **kwargs: str) -> MarketingTexts:
        """Build marketing copy for a wallpaper listing."""

        marketing_copy_text = f"Looking for a stylish and easy way to transform your space? Our {keyword} is the perfect solution. Available in both Peel and Stick and Non-Woven options, this versatile wallpaper is designed to elevate your décor and refresh any smooth surface with minimal effort."
        bullet_1 = f"Our {keyword} is made from high-quality, durable, and waterproof material."
        bullet_2 = f"Variety of Sizes Available: {keyword} comes in multiple size options to fit your space perfectly."
        return MarketingTexts(
            marketing_copy=marketing_copy_text,
            feature_bullet_1=bullet_1,
            feature_bullet_2=bullet_2,
        )

    def set_size_and_weight(self, height: int, width: int) -> PackageParameters:
        """Return package measurements for a wallpaper variant."""

        if height <= 24 or width <= 24:
            return PackageParameters(weight=1, height=24, width=2, depth=2)
        if height <= 50 or width <= 50:
            return PackageParameters(weight=4, height=44, width=5, depth=5)
        if height <= 60 or width <= 60:
            return PackageParameters(weight=5, height=44, width=5, depth=5)
        if height <= 80 or width <= 80:
            return PackageParameters(weight=6, height=44, width=5, depth=5)
        if height <= 100 or width <= 100:
            return PackageParameters(weight=7, height=44, width=5, depth=5)
        return PackageParameters(weight=11, height=44, width=5, depth=5)

    def make_part_numbers(self, sku: str, height: int, width: int) -> list[str]:
        """Generate all manufacturer part numbers for a wallpaper variation."""

        base_number = f"{sku} {width}x{height}"
        return [f"{base_number} {material}" for material in self.print_type]

    @staticmethod
    def calculate_sq_ft(width_in_inches: float, height_in_inches: float) -> float:
        """Convert dimensions in inches to square feet."""

        width_ft = width_in_inches / 12
        height_ft = height_in_inches / 12
        square_feet = width_ft * height_ft
        return round(square_feet, 2)

    @staticmethod
    def convert_inches_to_feet(height: float) -> float:
        """Convert inches to feet with two-decimal precision."""

        return round(height / 12, 2)

    def add_record(
        self,
        title: str,
        keyword: str,
        sku: str,
        image_links: Sequence[str] | None,
        height: int,
        width: int,
        price: float,
        color_choice: str | None = None,
        personalization_choice: str | None = None,
    ) -> None:
        """Append all export rows for a wallpaper variation."""

        package_parameters = self.set_size_and_weight(height, width)
        texts = self.set_texts(keyword, title=title, sku=sku)
        part_numbers = self.make_part_numbers(sku, height, width)

        cleaned_image_links = self.clean_image_links(image_links)
        image_slots, additional_images = self.resolve_image_slots(
            cleaned_image_links, self.technical_images
        )
        size_label = self.format_size(width, height)

        for part_number in part_numbers:
            material_name = part_number.split()[-1]
            base_cost = (
                price
                if price < 20
                else (
                    price + 10
                    if self.print_type[material_name]["material"] == "Non-Woven"
                    else price
                )
            )
            data: RowData = {
                "Brand": "Stickalz",
                "Supplier Part Number": part_number,
                "Manufacturer Part Number": part_number,
                "Product Name": f"{title} {sku}",
                "Variant Type": "Non-Primary Variant",
                "Group Reference ID": sku,
                "Variant Grouping 1": "Wallpaper Material",
                "Variant Attribute Name On Site 1": material_name,
                "Variant Grouping 2": "Size",
                "Variant Attribute Name On Site 2": size_label,
                "Base Cost": base_cost,
                "Marketing Copy": texts.marketing_copy,
                "Feature Bullet 1": texts.feature_bullet_1,
                "Feature Bullet 2": texts.feature_bullet_2,
                "Feature Bullet 3": "Quick and easy installation with included step-by-step instructions.",
                "Feature Bullet 4": "Suitable for smooth surfaces such as painted walls, glass, mirrors, and doors.",
                "Feature Bullet 5": "Removable and leaves no sticky residue — ideal for renters and temporary decor.",
                "Minimum Order Quantity": 1,
                "Force Quantity Multiplier": 1,
                "Display Set Quantity": 1,
                "Product Weight": package_parameters.weight,
                "Ship Type": "Small Parcel",
                "Freight Class": 400,
                "Lead Time": 120,
                "Replacement Lead Time": 120,
                "Carton Weight 1": package_parameters.weight,
                "Carton Height 1": package_parameters.height,
                "Carton Width 1": package_parameters.width,
                "Carton Depth 1": package_parameters.depth,
                "Warning Required": "No",
                "Country Of Manufacturer": "United States",
                "Image File Name or URL 1": image_slots[0],
                "Image File Name or URL 2": image_slots[1],
                "Image File Name or URL 3": image_slots[2],
                "Image File Name or URL 4": image_slots[3],
                "Image File Name or URL 5": image_slots[4],
                "Product Type": "Wall Mural",
                "Life Stage": "All Ages",
                "Wallpaper Texture": "Smooth",
                "Finish Treatment": "Primed",
                "Wallpaper Material": self.print_type[material_name]["material"],
                "Application Type": self.print_type[material_name]["application"],
                "Match Type": "Random",
                "Removal Type": self.print_type[material_name]["removal"],
                "Paintable / Stainable": "No",
                "Supplier Intended and Approved Use": "Non Residential Use; Residential Use",
                "BPA Free": "No",
                "Movie / Show Series Name": "Does Not Apply",
                "Sports Team Name": "Does Not Apply",
                "Durability": "Mold / Mildew Resistant;Water Resistant;Fade Resistant;Heat Resistant;Non-Porous;Non-Staining",
                "Color": "Multicolor",
                "Pattern Repeat Frequency": 0,
                "Pattern Interval": 0.0,
                "Wood Species": "Does Not Apply",
                "Uniform Packaging and Labeling Regulations (UPLR) Compliant": "Yes",
                "Canada Product Restriction": "No",
                "Reason for Restriction": "Does Not Apply",
                "Sustainability & Social Responsibility Certifications (North America Only)": "No",
                "Overall Product Length - End to End": self.convert_inches_to_feet(
                    height
                ),
                "Overall Width - Side to Side": width,
                "Square Footage per Unit": self.calculate_sq_ft(width, height),
                "Overall Product Weight": package_parameters.weight,
                "Commercial Warranty": "Yes",
                "Commercial Warranty Length": "30 Days",
                "variant_sort_price": base_cost,
                "variant_sort_area": width * height,
                "variant_sort_order": len(self.rows),
            }
            self.rows.append(data)
            self.additional_image_rows.extend(
                [
                    {
                        "Supplier Part Number": part_number,
                        "Image File Name or URL": image_url,
                    }
                    for image_url in additional_images
                ]
            )


class DataShaperFactory:
    """Factory for creating product-specific data shapers."""

    @staticmethod
    def create_shaper(shaper_type: str) -> BaseDataShaper:
        """Create a data shaper for the given print type."""

        if shaper_type == "decals":
            return DecalDataShaper()
        if shaper_type == "wallpapers":
            return WallpaperDataShaper()
        raise ValueError(f"Unknown shaper type: {shaper_type}")
