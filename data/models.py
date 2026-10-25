"""Shared data-shaping models and type aliases."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

RowData = dict[str, Any]
PriceInput = float | Mapping[str, float]
WAYFAIR_COMPLIANCE_VETTING_PROGRAM = (
    "Wayfair Compliance Vetting Program (including Baby Safety Alliance fka JPMA) "
    "for this product category"
)


@dataclass(frozen=True)
class MarketingTexts:
    """Structured marketing copy for a generated item."""

    marketing_copy: str
    feature_bullet_1: str
    feature_bullet_2: str
    feature_bullet_3: str
    feature_bullet_4: str
    feature_bullet_5: str
    feature_bullet_6: str
    feature_bullet_7: str
    feature_bullet_8: str


@dataclass(frozen=True)
class PackageParameters:
    """Shipping dimensions and weight for a generated item."""

    weight: int
    height: int
    width: int
    depth: int


@dataclass(frozen=True)
class WallpaperPrintType:
    """Wayfair attributes for one wallpaper material variant."""

    part_number_suffix: str
    display_name: str
    material: str
    application: str
    removal: str


@dataclass(frozen=True)
class AttributeOption:
    """A listing attribute the AI may choose from the template's allowed values."""

    name: str
    allowed: tuple[str, ...]
    max_items: int
    guidance: str

    @property
    def is_multi_select(self) -> bool:
        """Return whether several values may be chosen."""

        return self.max_items > 1


# (attribute, maximum values, guidance for the AI)
AttributeSpec = tuple[str, int, str]
