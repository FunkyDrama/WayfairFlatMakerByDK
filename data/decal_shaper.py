"""Data shaper for Wayfair wall-sticker exports."""

from collections.abc import Sequence

from data.base_shaper import BaseDataShaper
from data.models import (
    MarketingTexts,
    PackageParameters,
    PriceInput,
    RowData,
    WAYFAIR_COMPLIANCE_VERIFIED_PROGRAM,
)


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
            feature_bullet_3="Quick installation with easy-to-follow instructions.",
            feature_bullet_4=(
                "Wall decals are suitable for a wide range of surfaces, from walls "
                "and doors to windows and even cars."
            ),
            feature_bullet_5=(
                "UV protected coating ensures they never fade, preserving their allure."
            ),
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
        price: PriceInput,
        color_choice: str | None = "no",
        personalization_choice: str | None = "No",
        marketing_texts: MarketingTexts | None = None,
    ) -> None:
        """Append all export rows for a decal variation."""

        package_parameters = self.set_size_and_weight(height, width)
        texts = marketing_texts or self.set_texts(keyword)

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
        base_cost = self.get_single_price(price)

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
                "Base Cost": base_cost,
                "Marketing Copy": texts.marketing_copy,
                "Feature Bullet 1": texts.feature_bullet_1,
                "Feature Bullet 2": texts.feature_bullet_2,
                "Feature Bullet 3": texts.feature_bullet_3,
                "Feature Bullet 4": texts.feature_bullet_4,
                "Feature Bullet 5": texts.feature_bullet_5,
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
                "Age Group": "All Ages",
                "Personalization or Monogramming": personalization_choice,
                "Room Use": "Bedroom;Living Room;Nursery;Home Office;Playroom;School Classroom;Art School",
                "Holiday / Occasion": "No Holiday",
                "BPA Free": "No",
                "Licensed Product Category": "Does Not Apply",
                "Movie / Show Series Name": "Does Not Apply",
                "Durability": "Water Resistant;Fade Resistant;Heat Resistant;Stain Resistant;Tip Resistant;Waterproof;Weather Resistant",
                "Adjustability Features": "Does Not Apply",
                "General Features": "Non-Wall Damaging",
                "Color": color_value,
                "Total Number of Pieces Included": 1,
                "Pieces Included": "Does Not Apply",
                WAYFAIR_COMPLIANCE_VERIFIED_PROGRAM: "No",
                "Uniform Packaging and Labeling Regulations (UPLR) Compliant": "Yes",
                "Canada Product Restriction": "No",
                "Reason for Restriction": "Does Not Apply",
                "Sustainability & Social Responsibility Certifications (North America Only)": "No",
                "Overall Height - Top to Bottom": height,
                "Overall Width - Side to Side": width,
                "Commercial Warranty": "Yes",
                "Commercial Warranty Length": "30 Days",
                "ISTA Certified": "Does Not Apply",
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
