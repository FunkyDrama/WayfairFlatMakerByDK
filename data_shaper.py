import os
from excel_writer import ExcelWriter
from abc import ABC, abstractmethod


class BaseDataShaper(ABC):

    def __init__(self, template_filename: str, sheet_name: str):
        self.rows = []
        self.writer = ExcelWriter(
            template_filename=template_filename, sheet_name=sheet_name
        )

    @abstractmethod
    def set_texts(self, keyword: str, **kwargs): ...

    @abstractmethod
    def set_size_and_weight(self, height: int, width: int): ...

    @abstractmethod
    def add_record(
        self,
        title: str,
        keyword: str,
        sku: str,
        image_link: str,
        height: int,
        width: int,
        price: float,
        **kwargs,
    ): ...

    def write_file(self, sku: str, folder: os.PathLike) -> None:
        self.rows.sort(
            key=lambda item: (
                0 if "Peel-n-Stick" in item["Manufacturer Model Number"] else 1
            )
        )
        self.writer.write_data(self.rows, sku, folder)
        self.rows.clear()


class DecalDataShaper(BaseDataShaper):

    def __init__(self) -> None:
        super().__init__(
            template_filename="assets/decal_template.xlsx",
            sheet_name="3757 - Wall Stickers",
        )
        self.colors = [
            "White",
            "Grey",
            "Red",
            "Orange",
            "Yellow",
            "Burgundy",
            "Brown",
            "Beige",
            "Lime Green",
            "Green",
            "Dark Green",
            "Teal",
            "Mint",
            "Ice Blue",
            "Royal Blue",
            "Navy",
            "Purple",
            "Lilac",
            "Soft Pink",
            "Hot Pink",
            "Metallic Silver",
            "Metallic Gold",
        ]

    def set_texts(self, keyword: str, **kwargs) -> list[str]:
        marketing_copy_text = f"Are you in search of the perfect decorative solution for your walls or other smooth surfaces? Look no further than our remarkable {keyword}. These versatile vinyl stickers, also known as wall tattoos or wall vinyl, are designed to elevate your decor while serving informative purposes."
        feature_bullet_1_text = (
            f"Our {keyword} are crafted from high-quality, waterproof material."
        )
        feature_bullet_2_text = (
            f"Variety of Sizes Available: {keyword} come in multiple sizes."
        )
        return [marketing_copy_text, feature_bullet_1_text, feature_bullet_2_text]

    def set_size_and_weight(self, height: int, width: int) -> list[int]:
        weight_package = None
        height_package = None
        width_package = None
        depth_package = None

        if height <= 24 or width <= 24:
            weight_package = 1
            height_package = 24
            width_package = 2
            depth_package = 2

        elif 24 < height <= 37 or 24 < width <= 37:
            weight_package = 2
            height_package = 37
            width_package = 3
            depth_package = 3

        elif 37 < height <= 48 or 37 < width <= 48:
            weight_package = 3
            height_package = 48
            width_package = 3
            depth_package = 3

        elif height > 48 or width > 48:
            weight_package = 4
            height_package = 56
            width_package = 3
            depth_package = 3
        return [weight_package, height_package, width_package, depth_package]

    def make_part_numbers(
        self, sku: str, height: int, width: int, color_choice: str = "no"
    ) -> list[str]:
        """Генерирует все возможные part_number"""
        base_number = f"{sku} {width}x{height}"
        if color_choice == "yes":
            return [f"{base_number} {color}" for color in self.colors]

        return [base_number]

    def add_record(
        self,
        title: str,
        keyword: str,
        sku: str,
        image_link: str,
        height: int,
        width: int,
        price: float,
        color_choice: str = "no",
        personalization_choice: str = "No",
        second_image_link: str = None,
    ) -> None:
        """Добавляет записи для всех комбинаций цветов"""
        package_parameters = self.set_size_and_weight(height, width)
        texts = self.set_texts(keyword)

        if second_image_link:
            link2 = second_image_link
        else:
            link2 = "https://www.dropbox.com/scl/fi/cjr63aj97m7j5k9aavr9h/st-4x-100.jpg?rlkey=kv5j0uhzxwp1sy5fh422c6234&st=mmjk6rna&dl=0"

        if color_choice == "yes":
            link3 = "https://www.dropbox.com/scl/fi/627uc1b3muuerff3tk159/c-1-e-4x-100-2.jpg?rlkey=o4mfzcc652qesm3rod9tjtiq2&st=eif1qgo5&dl=0"
        else:
            link3 = "https://www.dropbox.com/scl/fi/dww9g9aythhwjru7vjp4l/ev-4x-100.jpg?rlkey=kwui3vqtkkhd51zq14g8o3my4&st=2s1y3jtt&dl=0"

        base_number = f"{sku} {width}x{height}"
        part_numbers = self.make_part_numbers(sku, height, width, color_choice)

        for part_number in part_numbers:
            color_value = (
                part_number[len(base_number) + 1 :]
                if color_choice == "yes"
                else "Multicolor"
            )
            data = {
                "Brand": "Stickalz",
                "Manufacturer Model Number": part_number,
                "Supplier Part Number": part_number,
                "Product Name": title,
                "This product is": "Decorate your home with beautiful and affordable vinyl decals for your walls. It is the newest home decor trend. It's easy to apply and really makes a room look elegant. Without much effort and cost you can decorate and style your home or any other surface. Putting up these paint-lookalike stickers, vinyl decals will completely change the way your accommodation looks.",
                "Base Cost": price,
                "Minimum Order Quantity (Per Part #)": 1,
                "Force Multiples": 1,
                "Display Set Quantity": 1,
                "Marketing Copy": texts[0],
                "Feature Bullet 1": texts[1],
                "Feature Bullet 2": texts[2],
                "Feature Bullet 3": "Quick installation with easy-to-follow instructions.",
                "Feature Bullet 4": "Wall decals are suitable for a wide range of surfaces, from walls and doors to windows and even cars.",
                "Feature Bullet 5": "UV protected coating ensures they never fade, preserving their allure.",
                "Country of Manufacture": "United States",
                "California Proposition 65 Warning Required": "No",
                "Ship Type (Small Parcel, LTL)": "Small Parcel",
                "Freight Class": 400,
                "Supplier Lead Time in Business Day Hours": 48,
                "Supplier Lead Time in Business Day Hours for Replacement Parts": 48,
                "Number of Boxes": 1,
                "Shipping Weight (Box 1)": package_parameters[0],
                "Carton Height (Box 1)": package_parameters[1],
                "Carton Width (Box 1)": package_parameters[2],
                "Carton Depth (Box 1)": package_parameters[3],
                "Image 1 File": image_link,
                "Image 2 File": link2,
                "Image 3 File": link3,
                "Individually Sellable": "Yes",
                "Product Type": "Accent",
                "Subject": "Fashion",
                "Surface Type": "Glossy",
                "Material": "Vinyl",
                "Compatible Surfaces": "Multi-Surface;Flat Surface;Glass Wall;Stainless Steel;Existing Tile;Chalkboard;Appliance;Mirror;Acrylic Panel;Laminate;Plywood Wall;Drywall;Ceramic Tile Wall;Concrete;Stone Wall",
                "Paste Included": "No",
                "Non Wall Damaging": "Yes",
                "Reusable": "No",
                "Personalization or Monogramming": personalization_choice,
                "Room Use ": "Bedroom;Living Room;Nursery;Home Office;Playroom;School Classroom;Art School",
                "Holiday / Occasion": "No Holiday",
                "Country of Origin - Additional Details": "Made in USA",
                "BPA Free": "No",
                "Licensed Product Category": "Does Not Apply",
                "Movie / Show Series Name": "Does Not Apply",
                "Character Name": "Does Not Apply",
                "Durability": "Water Resistant;Fade Resistant;Heat Resistant;Stain Resistant;Tip Resistant;Waterproof;Weather Resistant",
                "Color": color_value,
                "Total Number of Pieces Included": 1,
                "Uniform Packaging and Labeling Regulations (UPLR) Compliant": "Yes",
                "Canada Product Restriction": "No",
                "Reason for Restriction": "Does Not Apply",
                "ISO 14021 Recycled Content Standard Certified": "Does Not Apply",
                "Sustainability Assessment for Wallcovering Products - NSF/ANSI 342 - Compliant": "No",
                "Overall Height - Top to Bottom": height,
                "Overall Width - Side to Side": width,
                "Overall Product Weight": package_parameters[0],
                "Product Warranty": "Yes",
                "Warranty Length": "30 Days",
                "Full or Limited Warranty": "Full",
                "Warranty Details": "Defects Only;Failure to follow recommended care will void product warranty;Consumer misuse not covered;Satisfaction Guaranteed",
                "Commercial Warranty": "No",
            }
            self.rows.append(data)


class WallpaperDataShaper(BaseDataShaper):

    def __init__(self) -> None:
        super().__init__(
            template_filename="assets/wallpaper_template.xlsx",
            sheet_name="6161 - Wallpaper",
        )
        self.print_type = {
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

    def set_texts(self, keyword: str, **kwargs) -> list[str]:
        title = kwargs.get("title")
        sku = kwargs.get("sku")
        titles = [f"{title} ({t}) {sku}" for t in self.print_type.keys()]
        marketing_copy_text = f"Looking for a stylish and easy way to transform your space? Our {keyword} is the perfect solution. Available in both Peel and Stick and Non-Woven options, this versatile wallpaper is designed to elevate your décor and refresh any smooth surface with minimal effort."
        bullit_1 = f"Our {keyword} is made from high-quality, durable, and waterproof material."
        bullit_2 = f"Variety of Sizes Available: {keyword} comes in multiple size options to fit your space perfectly."
        return [titles, marketing_copy_text, bullit_1, bullit_2]

    def set_size_and_weight(self, height: int, width: int) -> list[int]:
        weight_package = None
        height_package = 44
        width_package = 5
        depth_package = 5

        if height <= 24 or width <= 24:
            weight_package = 1
            height_package = 24
            width_package = 2
            depth_package = 2

        elif height <= 50 or width <= 50:
            weight_package = 4

        elif height <= 60 or width <= 60:
            weight_package = 5

        elif height <= 80 or width <= 80:
            weight_package = 6

        elif height <= 100 or width <= 100:
            weight_package = 7

        elif height <= 120 or width <= 120:
            weight_package = 11

        return [weight_package, height_package, width_package, depth_package]

    def make_part_numbers(self, sku: str, height: int, width: int) -> list[str]:
        """Генерирует все возможные part_number"""
        base_number = f"{sku} {width}x{height}"
        return [f"{base_number} {material}" for material in self.print_type.keys()]

    @staticmethod
    def calculate_sq_ft(width_in_inches: float, height_in_inches: float) -> float:
        width_ft = width_in_inches / 12
        height_ft = height_in_inches / 12
        square_feet = width_ft * height_ft
        return round(square_feet, 1)

    def add_record(
        self,
        title: str,
        keyword: str,
        sku: str,
        image_link: str,
        height: int,
        width: int,
        price: float,
        second_image_link: str = None,
        **kwargs,
    ) -> None:
        """Добавляет записи для всех комбинаций цветов"""
        package_parameters = self.set_size_and_weight(height, width)
        texts = self.set_texts(keyword, title=title, sku=sku)
        part_numbers = self.make_part_numbers(sku, height, width)

        for part_number in part_numbers:

            data = {
                "Brand": "Stickalz",
                "Manufacturer Model Number": part_number,
                "Supplier Part Number": part_number,
                "Product Name": f"{title} ({part_number.split()[-1]}) {sku}",
                "This product is": """Transform your space effortlessly with our premium wallpaper, available in both Peel and Stick and Non-Woven options. Whether you're decorating a living room, nursery, office, or hallway, these high-quality wall murals bring personality and depth to any interior. Easy to install and remove, our wallpapers are perfect for renters and homeowners alike.
                Crafted with vivid colors and detailed designs, they create a stunning focal point in minutes — no professional help needed. Whether you choose the self-adhesive peel and stick version for a mess-free setup, or the traditional non-woven paper for a classic application, you’ll enjoy a smooth finish that elevates your walls.
                Bring art, nature, fantasy, or modern minimalism into your home — without the mess of paint or the cost of renovations.""",
                "Base Cost": (
                    price
                    if price < 10
                    else (
                        price + 10
                        if self.print_type[part_number.split(" ")[-1]]["material"]
                        == "Non-Woven"
                        else price
                    )
                ),
                "Minimum Order Quantity (Per Part #)": 1,
                "Force Multiples": 1,
                "Display Set Quantity": 1,
                "Marketing Copy": texts[1],
                "Feature Bullet 1": texts[2],
                "Feature Bullet 2": texts[3],
                "Feature Bullet 3": "Quick and easy installation with included step-by-step instructions.",
                "Feature Bullet 4": "Suitable for smooth surfaces such as painted walls, glass, mirrors, and doors.",
                "Feature Bullet 5": "UV-protected and fade-resistant coating ensures long-lasting color vibrancy.",
                "Feature Bullet 6": "Removable and leaves no sticky residue — ideal for renters and temporary décor.",
                "Feature Bullet 7": "Adds personality and atmosphere to any space — from kids' rooms to living areas and offices.",
                "Country of Manufacture": "United States",
                "California Proposition 65 Warning Required": "No",
                "Ship Type (Small Parcel, LTL)": "Small Parcel",
                "Freight Class": 400,
                "Supplier Lead Time in Business Day Hours": 96,
                "Supplier Lead Time in Business Day Hours for Replacement Parts": 96,
                "Number of Boxes": 1,
                "Shipping Weight (Box 1)": package_parameters[0],
                "Carton Height (Box 1)": package_parameters[1],
                "Carton Width (Box 1)": package_parameters[2],
                "Carton Depth (Box 1)": package_parameters[3],
                "Image 1 File": image_link,
                "Image 2 File": second_image_link,
                "Individually Sellable": "Yes",
                "Product Type": "Wall Mural",
                "Life Stage": "All Ages",
                "Wallpaper Texture": "Smooth",
                "Finish Treatment": "Primed",
                "Wallpaper Material": self.print_type[part_number.split(" ")[-1]][
                    "material"
                ],
                "Application Type": self.print_type[part_number.split(" ")[-1]][
                    "application"
                ],
                "Match Type": "Random",
                "Removal Type": self.print_type[part_number.split(" ")[-1]]["removal"],
                "Paintable / Stainable": "No",
                "Supplier Intended and Approved Use": "Non Residential Use; Residential Use",
                "BPA Free": "No",
                "Made to Order": "Yes",
                "Licensed Product Category": "Does Not Apply",
                "Movie / Show Series Name": "Does Not Apply",
                "Character Name": "Does Not Apply",
                "Sports Team Name": "Does Not Apply",
                "Durability": "Mold / Mildew Resistant;Water Resistant;Fade Resistant;Heat Resistant;Non-Porous;Non-Staining",
                "Color": "Multicolor",
                "Pattern Repeat Frequency": 0,
                "Pattern Interval": 0.0,
                "Wood Species": "Does Not Apply",
                "Uniform Packaging and Labeling Regulations (UPLR) Compliant": "Yes",
                "Canada Product Restriction": "No",
                "Reason for Restriction": "Does Not Apply",
                "ISO 14021 Recycled Content Standard Certified": "Does Not Apply",
                "Overall Product Length - End to End": height,
                "Overall Width - Side to Side": width,
                "Square Footage per Unit": self.calculate_sq_ft(width, height),
                "Overall Product Weight": package_parameters[0],
                "Commercial Warranty": "Yes",
                "Commercial Warranty Length": "30 Days",
                "Product Warranty": "Yes",
                "Warranty Length": "30 Days",
                "Full or Limited Warranty": "Full",
                "Warranty Details": "Defects Only;Failure to follow recommended care will void product warranty;Consumer misuse not covered;Satisfaction Guaranteed",
            }
            self.rows.append(data)


class DataShaperFactory:

    @staticmethod
    def create_shaper(shaper_type: str) -> BaseDataShaper:
        if shaper_type == "decals":
            return DecalDataShaper()
        elif shaper_type == "wallpapers":
            return WallpaperDataShaper()
        else:
            raise ValueError(f"Неизвестный тип шейпера: {shaper_type}")
