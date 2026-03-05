import datetime
import os

from openpyxl import load_workbook


class ExcelWriter:
    """Класс для записи данных в таблицу"""

    def __init__(
        self,
        template_filename: str,
        sheet_name: str,
    ) -> None:
        self.template_filename = template_filename
        self.sheet_name = sheet_name
        self.start_row: int = 6

    @staticmethod
    def _write_sheet(
        ws,
        start_row: int,
        header_row: int,
        data: list[dict],
    ) -> None:
        headers = [cell.value for cell in ws[header_row] if cell.value]

        for i, row_data in enumerate(data, start=start_row):
            for col_idx, header in enumerate(headers, start=1):
                if header in row_data:
                    ws.cell(row=i, column=col_idx, value=row_data[header])

    def write_data(self, new_data: list[dict], sku: str, folder: os.PathLike) -> None:
        """Функция для записи данных в таблицу"""
        wb = load_workbook(self.template_filename)
        ws = wb[self.sheet_name]
        self._write_sheet(ws, self.start_row, 3, new_data)

        filename = f"{sku}_{datetime.datetime.now().strftime('%d_%m_%Y_%H_%M')}.xlsx"
        if not os.path.exists(folder):
            os.makedirs(folder)
        full_path = os.path.join(folder, filename)
        wb.save(full_path)

    def write_data_with_additional_images(
        self,
        new_data: list[dict],
        additional_images_data: list[dict],
        sku: str,
        folder: os.PathLike,
    ) -> None:
        """Записывает основной лист и лист с дополнительными изображениями"""
        wb = load_workbook(self.template_filename)
        self._write_sheet(wb[self.sheet_name], self.start_row, 3, new_data)

        if additional_images_data:
            self._write_sheet(
                wb["Additional Images"],
                start_row=3,
                header_row=2,
                data=additional_images_data,
            )

        filename = f"{sku}_{datetime.datetime.now().strftime('%d_%m_%Y_%H_%M')}.xlsx"
        if not os.path.exists(folder):
            os.makedirs(folder)
        full_path = os.path.join(folder, filename)
        wb.save(full_path)
