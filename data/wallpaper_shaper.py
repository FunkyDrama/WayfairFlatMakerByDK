"""Data shaper for Wayfair wallpaper exports."""

from collections.abc import Sequence

from data.base_shaper import BaseDataShaper
from data.models import (
    MarketingTexts,
    PackageParameters,
    PriceInput,
    RowData,
    WallpaperPrintType,
    WAYFAIR_COMPLIANCE_VERIFIED_PROGRAM,
)


class WallpaperDataShaper(BaseDataShaper):
    """Data shaper for wallpaper listings."""

    def __init__(self) -> None:
        """Initialize wallpaper-specific constants and templates."""

        super().__init__(sheet_name="6161 - Wallpaper")
        self.technical_images: list[str] = [
            "https://www.dropbox.com/scl/fi/v4cfjc5e83qgqej5w9b11/1.png?rlkey=pucx792sf969vrgu4mtlx6y5v&st=fzounq4b&dl=0",
            "https://www.dropbox.com/scl/fi/vl5iu0kz4iseu8ag7e9k4/2.png?rlkey=iuh2vzv3bb7flw91vu4fk98rg&st=mt098dai&dl=0",
            "https://www.dropbox.com/scl/fi/w3yxc7f7r07ijpjplv48u/3.png?rlkey=694xivem9zfl6ckbtgbq057ju&st=veerf94b&dl=0",
            "https://www.dropbox.com/scl/fi/8vizhx3cqz7diveargucz/4.png?rlkey=secuq9gx9g9jgsgxjwxczbpvu&st=blg4h6f7&dl=0",
            "https://www.dropbox.com/scl/fi/eb9hmlrz3trxtta4l2p08/5.png?rlkey=80ctrwkldskzkrnn5s0uu1c5n&st=zgbxv0zl&dl=0",
            "https://www.dropbox.com/scl/fi/wa5dwope9lu02ghmanmgw/6.png?rlkey=uj2m0ljjjfeblve0feyb4nddu&st=5pbk6ji0&dl=0",
            "https://www.dropbox.com/scl/fi/5apyfsr4twqmn9d8gjdf6/7.png?rlkey=tyl5gno2rv7e63cogi89r3c77&st=wcyfbgl6&dl=0",
            "https://www.dropbox.com/scl/fi/4ocir17anzy0f38jw09mw/8.png?rlkey=s652jazmlsps5ad6zj04zy700&st=8dj52o7q&dl=0",
            "https://www.dropbox.com/scl/fi/187gngfjdicnr7qobfreb/9.png?rlkey=nvayg8550qlg1d0ojsc6vzg4v&st=a42y0nn9&dl=0",
            "https://www.dropbox.com/scl/fi/1q4bxn744kemlg1h5hfgv/10.png?rlkey=qajpv744wgwgqte8f9h38d4w0&st=312qghuh&dl=0",
            "https://www.dropbox.com/scl/fi/j3tzhtllqai5d12aols6m/11.png?rlkey=y9u8keag0dhowt6qvqdep750x&st=ky1pnrl9&dl=0",
        ]
        self.print_type: dict[str, WallpaperPrintType] = {
            "Peel-n-Stick": WallpaperPrintType(
                part_number_suffix="Peel-n-Stick",
                display_name="Smooth Peel & Stick",
                material="Vinyl",
                application="Self-Adhesive",
                removal="Peelable",
            ),
            "Non-Woven": WallpaperPrintType(
                part_number_suffix="Non-Woven",
                display_name="Non-Woven Wallpaper",
                material="Non-Woven",
                application="Non-Pasted",
                removal="Strippable",
            ),
            "Peel-n-Stick: Canvas": WallpaperPrintType(
                part_number_suffix="Peel-n-Stick-Canvas",
                display_name="Luxury Canvas Texture",
                material="Vinyl",
                application="Self-Adhesive",
                removal="Peelable",
            ),
            "Non-Woven: Premium": WallpaperPrintType(
                part_number_suffix="Non-Woven-Premium",
                display_name="Premium Non-Woven",
                material="Non-Woven",
                application="Non-Pasted",
                removal="Strippable",
            ),
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

    def make_part_numbers(self, sku: str, height: int, width: int) -> dict[str, str]:
        """Map each wallpaper type to its manufacturer part number."""

        base_number = f"{sku} {width}x{height}"
        return {
            material_name: f"{base_number} {attributes.part_number_suffix}"
            for material_name, attributes in self.print_type.items()
        }

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
        price: PriceInput,
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

        for material_name, part_number in part_numbers.items():
            attributes = self.print_type[material_name]
            base_cost = self.get_material_price(price, material_name)
            data: RowData = {
                "Brand": "Stickalz",
                "Supplier Part Number": part_number,
                "Manufacturer Part Number": part_number,
                "Product Name": f"{title} {sku}",
                "Variant Type": "Non-Primary Variant",
                "Group Reference ID": sku,
                "Variant Grouping 1": "Wallpaper Material",
                "Variant Attribute Name On Site 1": attributes.display_name,
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
                "Age Group": "All Ages",
                "Pattern": "Does Not Apply",
                "Wallpaper Texture": "Smooth",
                "Material": attributes.material,
                "Finish": "Primed",
                "Application Type": attributes.application,
                "Match Type": "Random",
                "Removal Type": attributes.removal,
                "Supplier Intended and Approved Use": "Non Residential Use; Residential Use",
                "BPA Free": "No",
                "Designer": "Does Not Apply",
                "Movie / Show Series Name": "Does Not Apply",
                "Sports Team Name": "Does Not Apply",
                "Durability": "Mold / Mildew Resistant;Water Resistant;Fade Resistant;Heat Resistant;Non-Porous;Non-Staining",
                "Product Care": "Wipe clean with a damp cloth",
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
                WAYFAIR_COMPLIANCE_VERIFIED_PROGRAM: "No",
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
