"""Allowed answers read from the Wayfair template's "Valid Values" sheet."""

import functools
import re
from xml.etree import ElementTree
import zipfile

from data.excel_writer import (
    ASSETS_DIR,
    CELL_PATTERN,
    ExcelWriter,
    SharedStrings,
    cell_column,
)

VALID_VALUES_SHEET = "Valid Values"


@functools.cache
def valid_values() -> dict[str, tuple[str, ...]]:
    """Map each Valid Values column header to the answers listed under it."""

    with zipfile.ZipFile(ASSETS_DIR / "template.xlsx") as template:
        strings = SharedStrings(template.read("xl/sharedStrings.xml").decode("utf-8"))
        sheet_xml = template.read(
            ExcelWriter(VALID_VALUES_SHEET).sheet_part_name(template)
        ).decode("utf-8")

    columns: dict[int, list[str]] = {}
    for row in re.findall(r"<row\b.*?</row>", sheet_xml, re.S):
        for cell in CELL_PATTERN.findall(row):
            value = re.search(r"<v>([^<]*)</v>", cell)
            if value is None:
                continue
            text = (
                strings.texts[int(value.group(1))]
                if 't="s"' in cell
                else ElementTree.fromstring(cell).findtext("{*}v", "")
            )
            columns.setdefault(cell_column(cell), []).append(text)
    return {values[0]: tuple(values[1:]) for values in columns.values() if values}


def allowed_values(attribute: str, class_label: str) -> tuple[str, ...]:
    """Return the answers for ``attribute``, preferring the class-specific list.

    Class-specific columns are headed like ``Subject (Wall Stickers - S)``.
    """

    values = valid_values()
    return values.get(f"{attribute} ({class_label})") or values.get(attribute, ())
