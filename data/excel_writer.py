"""Workbook writing helpers for Wayfair templates.

Rows are written straight into the template's XML instead of round-tripping the
workbook through openpyxl. openpyxl rewrites the whole file (inline strings,
renumbered styles, dropped dynamic-array metadata, ``t="n"`` numbers), and
Wayfair's uploader rejects such files without an error report. Editing only the
class sheet and the shared-strings table keeps every other part byte-identical
to the template Wayfair issued.
"""

import datetime
import os
from pathlib import Path
import re
from typing import Any
from xml.etree import ElementTree
from xml.sax.saxutils import escape, quoteattr
import zipfile

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
RowData = dict[str, Any]

SPREADSHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
CELL_PATTERN = re.compile(r"<c\b[^>]*?(?:/>|>.*?</c>)", re.S)
# Characters that XML 1.0 cannot represent at all.
ILLEGAL_XML_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def column_letter(index: int) -> str:
    """Convert a 1-based column index to its Excel letters (1 -> A)."""

    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def column_index(letters: str) -> int:
    """Convert Excel column letters to a 1-based index (A -> 1)."""

    index = 0
    for char in letters:
        index = index * 26 + ord(char) - 64
    return index


def cell_column(cell_xml: str) -> int:
    """Return the column index of a ``<c>`` element."""

    match = re.search(r'\br="([A-Z]+)\d+"', cell_xml)
    if match is None:
        raise ValueError(f"Cell without a reference: {cell_xml[:80]}")
    return column_index(match.group(1))


class SharedStrings:
    """Read and append to a workbook's shared-strings table."""

    def __init__(self, xml: str) -> None:
        """Index the existing strings so repeated values reuse them."""

        self.xml = xml
        root = ElementTree.fromstring(xml)
        texts = [
            "".join(node.text or "" for node in item.iter(f"{SPREADSHEET_NS}t"))
            for item in root.findall(f"{SPREADSHEET_NS}si")
        ]
        self.texts = texts
        self.index_by_text = {text: index for index, text in enumerate(texts)}
        self.added: list[str] = []
        self.references_added = 0

    def index_of(self, text: str) -> int:
        """Return the index for ``text``, appending it when it is new."""

        self.references_added += 1
        index = self.index_by_text.get(text)
        if index is None:
            index = len(self.texts) + len(self.added)
            self.added.append(text)
            self.index_by_text[text] = index
        return index

    def to_xml(self) -> str:
        """Return the table with new strings and updated counts."""

        if not self.added and not self.references_added:
            return self.xml

        def bump(match: re.Match[str], extra: int) -> str:
            return f'{match.group(1)}="{int(match.group(2)) + extra}"'

        xml = re.sub(
            r'\b(count)="(\d+)"',
            lambda match: bump(match, self.references_added),
            self.xml,
            count=1,
        )
        xml = re.sub(
            r'\b(uniqueCount)="(\d+)"',
            lambda match: bump(match, len(self.added)),
            xml,
            count=1,
        )
        items = "".join(
            f'<si><t xml:space="preserve">{escape(text)}</t></si>'
            for text in self.added
        )
        return xml.replace("</sst>", f"{items}</sst>")


class ExcelWriter:
    """Write generated data into the Excel template."""

    def __init__(self, sheet_name: str) -> None:
        """Store template metadata for subsequent writes."""

        self.template_filename = Path(ASSETS_DIR / "template.xlsx")
        self.sheet_name = sheet_name
        self.header_row: int = 5
        # Row 8 is the template's "Default Row"; product rows start below it.
        self.start_row: int = 9

    @staticmethod
    def build_output_path(sku: str, folder: str | os.PathLike[str]) -> Path:
        """Build and create the target path for a generated workbook."""

        filename = f"{sku}_{datetime.datetime.now().strftime('%d_%m_%Y_%H_%M')}.xlsx"
        folder_path = Path(folder)
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_path / filename

    def sheet_part_name(self, archive: zipfile.ZipFile) -> str:
        """Return the archive path of the worksheet named ``sheet_name``."""

        workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
        rels_xml = archive.read("xl/_rels/workbook.xml.rels").decode("utf-8")
        sheet_tag = re.search(
            rf"<sheet\b[^>]*\bname={re.escape(quoteattr(self.sheet_name))}[^>]*>",
            workbook_xml,
        )
        if sheet_tag is None:
            raise ValueError(f"Sheet not found in template: {self.sheet_name}")
        relation_id = re.search(r'\br:id="([^"]+)"', sheet_tag.group(0))
        if relation_id is None:
            raise ValueError(f"Sheet has no relationship: {self.sheet_name}")
        relation = re.search(
            rf'<Relationship\b[^>]*\bId="{re.escape(relation_id.group(1))}"[^>]*>',
            rels_xml,
        )
        if relation is None:
            raise ValueError(f"Missing relationship for sheet: {self.sheet_name}")
        target = re.search(r'\bTarget="([^"]+)"', relation.group(0))
        if target is None:
            raise ValueError(f"Relationship has no target: {self.sheet_name}")
        path = target.group(1)
        return path.lstrip("/") if path.startswith("/") else f"xl/{path}"

    def read_headers(self, sheet_xml: str, strings: SharedStrings) -> dict[str, int]:
        """Map header text in ``header_row`` to its column index."""

        row = self.find_row(sheet_xml, self.header_row)
        if row is None:
            raise ValueError(f"Header row {self.header_row} not found")
        headers: dict[str, int] = {}
        for cell in CELL_PATTERN.findall(row.group(0)):
            value = re.search(r"<v>([^<]*)</v>", cell)
            if value is None:
                continue
            text = (
                strings.texts[int(value.group(1))]
                if 't="s"' in cell
                else value.group(1)
            )
            headers.setdefault(text, cell_column(cell))
        return headers

    @staticmethod
    def find_row(sheet_xml: str, row_number: int) -> re.Match[str] | None:
        """Find a ``<row>`` element by its row number."""

        return re.search(
            rf'<row\b[^>]*\br="{row_number}"[^>]*?(?:/>|>.*?</row>)',
            sheet_xml,
            re.S,
        )

    @staticmethod
    def column_styles(sheet_xml: str) -> dict[int, str]:
        """Return each column's default style, as Excel applies to new cells."""

        styles: dict[int, str] = {}
        for col in re.findall(r"<col\b[^>]*/>", sheet_xml):
            style = re.search(r'\bstyle="(\d+)"', col)
            bounds = re.search(r'\bmin="(\d+)"[^>]*\bmax="(\d+)"', col)
            if style and bounds:
                for index in range(int(bounds.group(1)), int(bounds.group(2)) + 1):
                    styles[index] = style.group(1)
        return styles

    @staticmethod
    def build_cell(
        reference: str,
        value: Any,
        style: str | None,
        strings: SharedStrings,
    ) -> str:
        """Build a ``<c>`` element the way Excel stores the value."""

        style_attr = f' s="{style}"' if style else ""
        if isinstance(value, bool):
            raise TypeError(f"Unsupported boolean value in {reference}")
        if isinstance(value, (int, float)):
            # Excel omits t="n"; Wayfair misreads cells that carry it.
            return f'<c r="{reference}"{style_attr}><v>{value!r}</v></c>'
        text = ILLEGAL_XML_CHARS.sub("", str(value))
        index = strings.index_of(text)
        return f'<c r="{reference}"{style_attr} t="s"><v>{index}</v></c>'

    def fill_row(
        self,
        row_xml: str,
        row_number: int,
        values: dict[int, Any],
        styles: dict[int, str],
        strings: SharedStrings,
    ) -> str:
        """Merge new values into a template row, keeping its existing cells."""

        open_tag = re.match(r"<row\b[^>]*?(?=/?>)", row_xml)
        if open_tag is None:
            raise ValueError(f"Malformed row {row_number}")
        cells = {cell_column(cell): cell for cell in CELL_PATTERN.findall(row_xml)}
        for column, value in values.items():
            reference = f"{column_letter(column)}{row_number}"
            cells[column] = self.build_cell(
                reference, value, styles.get(column), strings
            )
        tag = re.sub(r'\s+spans="[^"]*"', "", open_tag.group(0))
        spans = f' spans="{min(cells)}:{max(cells)}"'
        body = "".join(cells[column] for column in sorted(cells))
        return f"{tag}{spans}>{body}</row>"

    def write_rows(
        self,
        sheet_xml: str,
        strings: SharedStrings,
        data: list[RowData],
    ) -> str:
        """Return the sheet XML with ``data`` written from ``start_row``."""

        headers = self.read_headers(sheet_xml, strings)
        styles = self.column_styles(sheet_xml)
        for row_number, row_data in enumerate(data, start=self.start_row):
            values = {
                headers[header]: value
                for header, value in row_data.items()
                if header in headers and value is not None
            }
            row = self.find_row(sheet_xml, row_number)
            if row is None:
                raise ValueError(
                    "Too many variants for one Wayfair file: the template holds "
                    f"{row_number - self.start_row} product rows."
                )
            filled = self.fill_row(row.group(0), row_number, values, styles, strings)
            sheet_xml = sheet_xml[: row.start()] + filled + sheet_xml[row.end() :]
        return sheet_xml

    def write_data(
        self,
        new_data: list[RowData],
        sku: str,
        folder: str | os.PathLike[str],
    ) -> Path:
        """Write the main sheet into a new workbook file and return its path."""

        output_path = self.build_output_path(sku, folder)
        with zipfile.ZipFile(self.template_filename) as template:
            sheet_part = self.sheet_part_name(template)
            strings = SharedStrings(
                template.read("xl/sharedStrings.xml").decode("utf-8")
            )
            sheet_xml = self.write_rows(
                template.read(sheet_part).decode("utf-8"), strings, new_data
            )
            replacements = {
                sheet_part: sheet_xml.encode("utf-8"),
                "xl/sharedStrings.xml": strings.to_xml().encode("utf-8"),
            }
            with zipfile.ZipFile(output_path, "w") as output:
                for item in template.infolist():
                    data = replacements.get(item.filename)
                    output.writestr(
                        item,
                        template.read(item) if data is None else data,
                        compress_type=item.compress_type,
                    )
        return output_path
