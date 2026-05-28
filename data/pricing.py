"""Price lookup and interpolation for generated product variants."""

from collections.abc import Iterable, Mapping
import csv
from dataclasses import dataclass
from io import StringIO
from urllib.error import URLError
from urllib.request import urlopen

PriceByWallpaperType = dict[str, float]
PricePointsByGroup = dict[str, list["PricePoint"]]
PricePointsByCategory = dict[str, PricePointsByGroup]

PRICE_SHEET_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1hjU8IE40wvzn52ttj7EDoHFOJhv8tUWapojFNYA5TuY/export?format=csv&gid=0"
)

WALLPAPER_TYPE_TO_PRICE_GROUP: Mapping[str, str] = {
    "Peel-n-Stick": "Peel-n-Stick/Non-Woven",
    "Non-Woven": "Peel-n-Stick/Non-Woven",
    "Peel-n-Stick: Canvas": "Peel-n-Stick: Canvas",
    "Non-Woven: Premium": "Non-Woven: Premium",
}

DECAL_COLOR_CHOICE_TO_PRICE_GROUP: Mapping[str, str] = {
    "yes": "Plottered",
    "no": "Printed",
}


class PriceSourceError(RuntimeError):
    """Raised when a price source cannot provide usable price data."""


@dataclass(frozen=True)
class PricePoint:
    """One known price for one material group and size."""

    group: str
    width: int
    height: int
    price: float

    @property
    def area(self) -> int:
        """Return the size area in square inches."""

        return self.width * self.height


class PriceProvider:
    """Fetch and calculate product prices from external source data."""

    def __init__(self, sheet_csv_url: str = PRICE_SHEET_CSV_URL) -> None:
        """Store external source settings and initialize the in-memory cache."""

        self.sheet_csv_url = sheet_csv_url
        self.points_by_category: PricePointsByCategory | None = None

    def get_wallpaper_prices(self, width: int, height: int) -> PriceByWallpaperType:
        """Return calculated prices for every wallpaper material variant."""

        points_by_group = self.get_wallpaper_points_by_group()
        prices: PriceByWallpaperType = {}
        for material_name, group_name in WALLPAPER_TYPE_TO_PRICE_GROUP.items():
            group_points = points_by_group.get(group_name, [])
            prices[material_name] = self.interpolate_price(group_points, width, height)
        return prices

    def get_decal_price(
        self,
        width: int,
        height: int,
        color_choice: str,
    ) -> float:
        """Return the decal price for plottered or printed decal variants."""

        group_name = DECAL_COLOR_CHOICE_TO_PRICE_GROUP.get(
            color_choice.strip().lower(),
            "Printed",
        )
        points_by_group = self.get_decal_points_by_group()
        return self.interpolate_price(
            points_by_group.get(group_name, []), width, height
        )

    def get_wallpaper_points_by_group(self) -> PricePointsByGroup:
        """Return cached wallpaper price points, fetching the sheet on first use."""

        points_by_group = self.get_points_by_category().get("Wallpapers", {})
        self.validate_required_groups(
            points_by_group,
            set(WALLPAPER_TYPE_TO_PRICE_GROUP.values()),
            "Wallpaper",
        )
        return points_by_group

    def get_decal_points_by_group(self) -> PricePointsByGroup:
        """Return cached decal price points, fetching the sheet on first use."""

        points_by_group = self.get_points_by_category().get("Decals", {})
        self.validate_required_groups(
            points_by_group,
            set(DECAL_COLOR_CHOICE_TO_PRICE_GROUP.values()),
            "Decal",
        )
        return points_by_group

    def get_points_by_category(self) -> PricePointsByCategory:
        """Return cached price points grouped by category and material group."""

        if self.points_by_category is None:
            csv_text = self.fetch_sheet_csv()
            self.points_by_category = self.parse_price_points(csv_text)
        return self.points_by_category

    def fetch_sheet_csv(self) -> str:
        """Fetch the Google Sheet CSV export used as the price source."""

        try:
            with urlopen(self.sheet_csv_url, timeout=12) as response:
                return response.read().decode("utf-8-sig")
        except (OSError, URLError) as exc:
            raise PriceSourceError("Could not load prices from Google Sheets.") from exc

    @staticmethod
    def parse_price_points(csv_text: str) -> PricePointsByCategory:
        """Parse grouped price rows from the source CSV."""

        points_by_category: PricePointsByCategory = {}
        current_category = ""
        current_group = ""

        for row in csv.DictReader(StringIO(csv_text)):
            current_category = row.get("Category", "").strip() or current_category
            current_group = row.get("Type / Material", "").strip() or current_group
            if not current_category or not current_group:
                continue

            width_text = row.get("Width", "").strip()
            height_text = row.get("Length", "").strip()
            price_text = row.get("Base cost", "").strip()
            if not width_text or not height_text or not price_text:
                continue

            try:
                point = PricePoint(
                    group=current_group,
                    width=int(float(width_text)),
                    height=int(float(height_text)),
                    price=PriceProvider.parse_currency(price_text),
                )
            except ValueError:
                continue

            category_points = points_by_category.setdefault(current_category, {})
            category_points.setdefault(current_group, []).append(point)

        return points_by_category

    @staticmethod
    def parse_wallpaper_points(csv_text: str) -> PricePointsByGroup:
        """Parse wallpaper price rows from the source CSV."""

        points_by_group = PriceProvider.parse_price_points(csv_text).get(
            "Wallpapers",
            {},
        )
        PriceProvider.validate_required_groups(
            points_by_group,
            set(WALLPAPER_TYPE_TO_PRICE_GROUP.values()),
            "Wallpaper",
        )
        return points_by_group

    @staticmethod
    def validate_required_groups(
        points_by_group: PricePointsByGroup,
        required_groups: set[str],
        source_name: str,
    ) -> None:
        """Ensure a parsed price source contains all required groups."""

        missing_groups = {
            group_name
            for group_name in required_groups
            if not points_by_group.get(group_name)
        }
        if missing_groups:
            missing_text = ", ".join(sorted(missing_groups))
            raise PriceSourceError(
                f"{source_name} price table is missing required groups: {missing_text}."
            )

    @staticmethod
    def parse_currency(value: str) -> float:
        """Convert a sheet currency cell to a float."""

        normalized = value.replace("$", "").replace(",", "").strip()
        return float(normalized)

    @staticmethod
    def round_interpolated_price(price: float) -> float:
        """Return an interpolated price with a .99 ending."""

        return float(int(price) + 0.99)

    @staticmethod
    def interpolate_price(
        points: Iterable[PricePoint],
        width: int,
        height: int,
    ) -> float:
        """Return exact or area-interpolated price for a requested size."""

        known_points = sorted(points, key=lambda point: point.area)
        if not known_points:
            raise PriceSourceError("Price table has no usable price rows.")

        requested_dimensions = sorted((width, height))
        for point in known_points:
            if requested_dimensions == sorted((point.width, point.height)):
                return round(point.price, 2)

        area_prices = [(point.area, point.price) for point in known_points]

        target_area = width * height
        if target_area <= area_prices[0][0]:
            return round(area_prices[0][1], 2)
        if target_area >= area_prices[-1][0]:
            return round(area_prices[-1][1], 2)

        previous_area, previous_price = area_prices[0]
        for next_area, next_price in area_prices[1:]:
            if target_area <= next_area:
                area_delta = next_area - previous_area
                if area_delta == 0:
                    price = (previous_price + next_price) / 2
                    return PriceProvider.round_interpolated_price(price)
                position = (target_area - previous_area) / area_delta
                price = previous_price + (next_price - previous_price) * position
                return PriceProvider.round_interpolated_price(price)
            previous_area, previous_price = next_area, next_price

        return round(area_prices[-1][1], 2)
