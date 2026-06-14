"""Shared data-shaping models and type aliases."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

RowData = dict[str, Any]
AdditionalImageRow = dict[str, str]
PriceInput = float | Mapping[str, float]
WAYFAIR_COMPLIANCE_VERIFIED_PROGRAM = (
    "Wayfair Compliance Verified Program (including Baby Safety Alliance fka JPMA) "
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
