import os
import time
import flet as ft
from data_shaper import DataShaperFactory
from i18n import get_translator


class WayfairFlatMaker:
    """Главный класс для формирования графического интерфейса"""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.page.window.maximized = True
        self.page.title = "Wayfair Flat Maker by Daniel K"
        self.page.scroll = ft.ScrollMode.ALWAYS
        self.page.window.resizable = True
        lang_selected = self.page.client_storage.get("lang")
        self.lang = lang_selected or "en"
        self._ = get_translator(lang=self.lang)

        self.lang_dd = ft.Dropdown(
            width=200,
            value=self.lang,
            options=[
                ft.dropdown.Option("ru", "Русский"),
                ft.dropdown.Option("en", "English"),
            ],
            on_change=self.on_lang_change,
            label=self._("Language"),
        )
        self.personalization_radio = ft.RadioGroup(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Radio(
                            label=self._("Yes"),
                            value="Yes",
                            label_style=ft.TextStyle(size=20),
                        ),
                        margin=ft.Margin(top=0, right=20, bottom=0, left=0),
                    ),
                    ft.Container(
                        content=ft.Radio(
                            label=self._("No"),
                            value="No",
                            label_style=ft.TextStyle(size=20),
                        ),
                        margin=ft.Margin(top=0, right=0, bottom=0, left=100),
                    ),
                ],
                spacing=30,
            ),
            value="No",
        )
        self.personalization_label = ft.Text(
            self._(
                "Does the design have personalization\n(e.g., text from the client)?"
            ),
            size=20,
        )
        self.design_radio = ft.RadioGroup(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Radio(
                            label=self._("Yes"),
                            value="yes",
                            label_style=ft.TextStyle(size=20),
                        ),
                        margin=ft.Margin(top=0, right=20, bottom=0, left=0),
                    ),
                    ft.Container(
                        content=ft.Radio(
                            label=self._("No"),
                            value="no",
                            label_style=ft.TextStyle(size=20),
                        ),
                        margin=ft.Margin(top=0, right=0, bottom=0, left=100),
                    ),
                ],
                spacing=30,
            ),
            value="no",
        )
        self.design_label = ft.Text(
            self._("Does the design have color variations?"), size=20
        )
        self.design_container = ft.Column([self.design_label, self.design_radio])
        self.personalization_container = ft.Column(
            [self.personalization_label, self.personalization_radio]
        )
        self.sizes_column = ft.Column(alignment=ft.MainAxisAlignment.CENTER)
        self.buttons_row = self.make_size_buttons()
        self.folder_picker = ft.FilePicker(on_result=self.folder_picker_result)
        self.page.overlay.append(self.folder_picker)
        self.submit_button = ft.ElevatedButton(
            self._("Generate Spreadsheet"),
            on_click=lambda e: self.folder_picker.get_directory_path(
                dialog_title=self._("Choose a folder to save the file"),
            ),
            height=50,
        )
        self.progress_ring = ft.ProgressRing(visible=False, width=30, height=30)
        self.success_icon = ft.Icon(
            ft.Icons.CHECK, color=ft.Colors.GREEN, visible=False, size=30
        )

        self.submit_row = ft.Row(
            controls=[self.submit_button, self.progress_ring, self.success_icon],
            alignment=ft.MainAxisAlignment.CENTER,
        )
        self.size_price_label = ft.Text(self._("Sizes and prices"), size=20)
        self.print_type_dd = ft.Dropdown(
            label=self._("Print Type"),
            width=500,
            options=[
                ft.DropdownOption(text=self._("Decals"), key="decals"),
                ft.DropdownOption(text=self._("Wallpapers"), key="wallpapers"),
            ],
            on_change=self.get_dropdown_value,
        )

        self.title_field = ft.TextField(
            label=self._("Listing Title"),
            width=500,
            expand=True,
            max_length=255,
        )

        self.sku_field = ft.TextField(
            label="SKU",
            width=500,
            hint_text=self._("e.g.: VN007"),
            expand=True,
            capitalization=ft.TextCapitalization.CHARACTERS,
        )
        self.keyword_field = ft.TextField(
            label=self._("Keywords"),
            width=500,
            hint_text=self._("e.g. (in plural): Dog Wall Stickers"),
            expand=True,
        )
        self.main_image_link_field = ft.TextField(
            label=self._("Main Image Link"),
            width=500,
            expand=True,
        )

        self.second_image_link_field = ft.TextField(
            label=self._("Secondary Image Link"),
            width=500,
            expand=True,
            helper_text=self._(
                "If there is no second image of the design, leave it blank."
            ),
        )
        self.init_ui()

    def get_dropdown_value(self, e: ft.ControlEvent) -> None:
        """Получение значения из выпадающего меню. Необходимо для класса-фабрики и обновления интерфейса"""
        if self.print_type_dd.value == "wallpapers":
            self.design_container.visible = False
            self.personalization_container.visible = False
        if self.print_type_dd.value == "decals":
            self.design_container.visible = True
            self.personalization_container.visible = True
        self.page.update()

    def on_lang_change(self, e: ft.ControlEvent) -> None:
        self.lang = e.control.value
        self.page.client_storage.set("lang", self.lang)
        self._ = get_translator(self.lang)
        self.apply_i18n()
        self.page.update()

    def apply_i18n(self) -> None:
        """Применяет переводы к элементам интерфейса"""
        self.design_label.value = self._("Does the design have color variations?")
        self.personalization_label.value = self._(
            "Does the design have personalization\n(e.g., text from the client)?"
        )
        self.size_price_label.value = self._("Sizes and prices")
        self.print_type_dd.label = self._("Print Type")
        self.print_type_dd.options[0].text = self._("Decals")
        self.print_type_dd.options[1].text = self._("Wallpapers")
        self.title_field.label = self._("Listing Title")
        self.sku_field.label = "SKU"
        self.sku_field.hint_text = self._("e.g.: VN007")
        self.lang_dd.label = self._("Language")
        self.keyword_field.label = self._("Keywords")
        self.keyword_field.hint_text = self._("e.g. (in plural): Dog Wall Stickers")
        self.main_image_link_field.label = self._("Main Image Link")
        self.second_image_link_field.label = self._("Secondary Image Link")
        self.second_image_link_field.helper_text = self._(
            "If there is no second image of the design, leave it blank."
        )
        self.submit_button.text = self._("Generate Spreadsheet")
        self.design_radio.content.controls[0].content.label = self._("Yes")
        self.design_radio.content.controls[1].content.label = self._("No")
        self.personalization_radio.content.controls[0].content.label = self._("Yes")
        self.personalization_radio.content.controls[1].content.label = self._("No")
        price_hints = [
            self._("e.g.: 16.99"),
            self._("e.g.: 27.99"),
            self._("e.g.: 60.99"),
            self._("e.g.: 79.99"),
        ]
        width_hints = [
            self._("e.g: 16"),
            self._("e.g.: 22"),
            self._("e.g.: 35"),
            self._("e.g.: 44"),
        ]
        height_hints = [
            self._("e.g.: 22"),
            self._("e.g.: 30"),
            self._("e.g.: 48"),
            self._("e.g.: 60"),
        ]
        for index, row in enumerate(self.sizes_column.controls):
            row.controls[0].label = self._("Width")
            row.controls[0].hint_text = width_hints[index % len(width_hints)]
            row.controls[1].label = self._("Height")
            row.controls[1].hint_text = height_hints[index % len(height_hints)]
            row.controls[2].label = self._("Price")
            row.controls[2].hint_text = price_hints[index % len(price_hints)]

    def add_size(self, e: ft.ControlEvent) -> None:
        """Добавляет блоки с высотой, шириной и ценой, а также подсказки"""
        price_hints = [
            self._("e.g.: 16.99"),
            self._("e.g.: 27.99"),
            self._("e.g.: 60.99"),
            self._("e.g.: 79.99"),
        ]
        width_hints = [
            self._("e.g: 16"),
            self._("e.g.: 22"),
            self._("e.g.: 35"),
            self._("e.g.: 44"),
        ]
        height_hints = [
            self._("e.g.: 22"),
            self._("e.g.: 30"),
            self._("e.g.: 48"),
            self._("e.g.: 60"),
        ]

        index = len(self.sizes_column.controls)

        hint = price_hints[index % len(price_hints)]
        width_hint = width_hints[index % len(width_hints)]
        height_hint = height_hints[index % len(height_hints)]

        width_field = ft.TextField(
            label=self._("Width"),
            width=200,
            input_filter=ft.NumbersOnlyInputFilter(),
            hint_text=width_hint,
        )
        height_field = ft.TextField(
            label=self._("Height"),
            width=200,
            input_filter=ft.NumbersOnlyInputFilter(),
            hint_text=height_hint,
        )
        price_field = ft.TextField(
            label=self._("Price"),
            width=200,
            hint_text=hint,
            input_filter=ft.InputFilter(
                allow=True, regex_string=r"^(?!.*\..*\.)[0-9.]*$"
            ),
        )

        row = ft.Row(
            controls=[width_field, height_field, price_field],
            alignment=ft.MainAxisAlignment.CENTER,
        )
        self.sizes_column.controls.append(row)
        self.page.update()

    def remove_size(self, e: ft.ControlEvent) -> None:
        """Убирает блоки с высотой, шириной и ценой, а также подсказки"""
        if self.sizes_column.controls:
            self.sizes_column.controls.pop()
            self.page.update()

    def make_size_buttons(self) -> ft.Control:
        """Создает кнопки для добавления и убирания размера"""
        add_button = ft.IconButton(ft.Icons.ADD, on_click=self.add_size, icon_size=30)
        remove_button = ft.IconButton(
            ft.Icons.REMOVE, on_click=self.remove_size, icon_size=30
        )
        buttons_row = ft.Row(controls=[add_button, remove_button], spacing=80)
        return buttons_row

    def folder_picker_result(self, e: ft.FilePickerResultEvent) -> None:
        """Функция обратного вызова для получения пути к директории для сохранения файла таблицы"""
        if e.path:
            self.submit_form(e.path)
        else:
            self.progress_ring.visible = False
            self.submit_button.disabled = False
            self.page.update()

    def validate_fields(self) -> bool:
        """Проверяет валидность полей формы"""
        valid = True

        if not self.title_field.value.strip():
            self.title_field.error_text = self._("This field is required")
            valid = False
        else:
            self.title_field.error_text = None

        if not self.sku_field.value.strip():
            self.sku_field.error_text = self._("This field is required")
            valid = False
        else:
            self.sku_field.error_text = None

        if not self.keyword_field.value.strip():
            self.keyword_field.error_text = self._("This field is required")
            valid = False
        else:
            self.keyword_field.error_text = None

        if not self.main_image_link_field.value.strip():
            self.main_image_link_field.error_text = self._("This field is required")
            valid = False
        else:
            self.main_image_link_field.error_text = None

        for row in self.sizes_column.controls:
            width = row.controls[0].value
            height = row.controls[1].value
            price = row.controls[2].value

            if not width.strip():
                row.controls[0].error_text = self._("This field is required")
                valid = False
            else:
                row.controls[0].error_text = None

            if not height.strip():
                row.controls[1].error_text = self._("This field is required")
                valid = False
            else:
                row.controls[1].error_text = None

            if not price.strip():
                row.controls[2].error_text = self._("This field is required")
                valid = False
            else:
                row.controls[2].error_text = None

        self.page.update()
        return valid

    def clear_errors(self) -> None:
        """Очищает заполненные поля при ошибках"""
        self.progress_ring.visible = False
        self.page.update()
        time.sleep(2)
        self.title_field.error_text = None
        self.sku_field.error_text = None
        self.keyword_field.error_text = None
        self.main_image_link_field.error_text = None
        for row in self.sizes_column.controls:
            for ctrl in row.controls:
                ctrl.error_text = None
        self.page.update()

    def submit_form(self, folder: os.PathLike | str) -> None:
        """Передает данные из заполненных полей в класс-фабрику для последующей обработки"""
        shaper = DataShaperFactory.create_shaper(self.print_type_dd.value)
        self.progress_ring.visible = True
        self.success_icon.visible = False
        self.submit_button.disabled = True
        self.page.update()

        time.sleep(0.1)

        try:
            if not self.validate_fields():
                error_snack_bar = ft.SnackBar(
                    ft.Text(self._("Please fill in all required fields")), open=True
                )
                self.page.overlay.append(error_snack_bar)
                self.page.update()
                self.clear_errors()
                return

            title = self.title_field.value
            sku = self.sku_field.value
            keyword = self.keyword_field.value
            image_link = self.main_image_link_field.value
            second_image_link = self.second_image_link_field.value
            design_choice = self.design_radio.value
            personalization_choice = self.personalization_radio.value

            for row in self.sizes_column.controls:
                width = int(row.controls[0].value)
                height = int(row.controls[1].value)
                price = float(row.controls[2].value.replace(",", "."))
                shaper.add_record(
                    title=title,
                    keyword=keyword,
                    sku=sku,
                    image_link=image_link,
                    height=height,
                    width=width,
                    price=price,
                    second_image_link=second_image_link,
                    color_choice=(
                        design_choice if self.print_type_dd.value == "decals" else None
                    ),
                    personalization_choice=(
                        personalization_choice
                        if self.print_type_dd.value == "decals"
                        else None
                    ),
                )
            shaper.write_file(sku, folder)

            self.progress_ring.visible = False
            self.success_icon.visible = True

            snack_bar = ft.SnackBar(ft.Text(self._("Spreadsheet generated")), open=True)
            self.page.overlay.append(snack_bar)
            self.page.update()
        except Exception as ex:
            alert = ft.AlertDialog(
                title=ft.Text(self._("Error: %(err)s") % {"err": ex}),
                open=True,
            )
            self.page.open(alert)
        finally:
            self.title_field.value = ""
            self.sku_field.value = ""
            self.keyword_field.value = ""
            self.main_image_link_field.value = ""
            self.second_image_link_field.value = ""
            self.design_radio.value = "no"
            self.personalization_radio.value = "No"
            self.submit_button.disabled = False
            for row in self.sizes_column.controls:
                row.controls[0].value = ""
                row.controls[1].value = ""
                row.controls[2].value = ""
            self.page.update()

    def init_ui(self) -> None:
        """Главная функция, которая отрисовывает графический интерфейс"""

        self.page.add(
            ft.Row(
                [ft.Image("logo.png", fit=ft.ImageFit.FIT_HEIGHT, height=70)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Row([self.lang_dd], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([self.print_type_dd], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([self.title_field], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([self.sku_field], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([self.keyword_field], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([self.main_image_link_field], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(
                [self.second_image_link_field], alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Row([self.design_container], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(),
            ft.Row(
                [self.personalization_container], alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Divider(),
            ft.Row([self.size_price_label], alignment=ft.MainAxisAlignment.CENTER),
            self.sizes_column,
            ft.Row([self.buttons_row], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(),
            ft.Row([self.submit_row], alignment=ft.MainAxisAlignment.CENTER),
        )


def main(page: ft.Page) -> None:
    """Главная функция, которая запускает приложение"""
    WayfairFlatMaker(page)


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
