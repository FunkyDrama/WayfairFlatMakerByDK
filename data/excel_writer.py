"""Workbook writing helpers for Wayfair templates."""

import datetime
import os
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
RowData = dict[str, Any]


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
    def write_sheet(
        ws: Worksheet,
        start_row: int,
        header_row: int,
        data: list[RowData],
    ) -> None:
        """Write rows into a worksheet using header names as keys."""

        headers = {cell.value: cell.column for cell in ws[header_row] if cell.value}

        for i, row_data in enumerate(data, start=start_row):
            for header, value in row_data.items():
                col_idx = headers.get(header)
                if col_idx is not None:
                    ws.cell(row=i, column=col_idx, value=value)

    @staticmethod
    def build_output_path(sku: str, folder: str | os.PathLike[str]) -> Path:
        """Build and create the target path for a generated workbook."""

        filename = f"{sku}_{datetime.datetime.now().strftime('%d_%m_%Y_%H_%M')}.xlsx"
        folder_path = Path(folder)
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_path / filename

    def write_data(
        self,
        new_data: list[RowData],
        sku: str,
        folder: str | os.PathLike[str],
    ) -> Path:
        """Write the main sheet into a new workbook file and return its path."""

        wb = load_workbook(self.template_filename)
        ws = wb[self.sheet_name]
        self.write_sheet(ws, self.start_row, self.header_row, new_data)
        output_path = self.build_output_path(sku, folder)
        wb.save(output_path)
        return output_path
