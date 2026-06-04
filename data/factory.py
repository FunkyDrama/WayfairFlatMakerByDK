"""Factory for creating product-specific data shapers."""

from data.base_shaper import BaseDataShaper
from data.decal_shaper import DecalDataShaper
from data.wallpaper_shaper import WallpaperDataShaper


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
