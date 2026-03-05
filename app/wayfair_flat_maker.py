import asyncio
import os

import flet as ft

from data import DataShaperFactory
from i18n import get_translator

SUPPORTED_LANGUAGES = (
    ("ru", "Русский"),
    ("uk", "Українська"),
    ("en", "English"),
    ("sq", "Shqip"),
)


class WayfairFlatMaker:
    """Главный класс для формирования графического интерфейса"""

    def __init__(self, page: ft.Page, lang: str, prefs: ft.SharedPreferences) -> None:
        self.page = page
        self._configure_page()
        self.lang = lang
        self.prefs = prefs
        self._ = get_translator(lang=self.lang)

        self._build_controls()
        self.init_ui()

    def _configure_page(self) -> None:
        self.page.window.maximized = True
        self.page.title = "Wayfair Flat Maker by Daniel K"
        self.page.scroll = ft.ScrollMode.ALWAYS
        self.page.window.resizable = True

    def _build_controls(self) -> None:
        self.lang_dd = ft.Dropdown(
            width=200,
            value=self.lang,
            options=[
                ft.DropdownOption(key=code, text=label)
                for code, label in SUPPORTED_LANGUAGES
            ],
            on_select=self.on_lang_change,
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
        self.image_links_column = ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
        )
        self.image_buttons_row = self.make_image_buttons()
        self.folder_picker = ft.FilePicker()
        self.page.services.append(self.folder_picker)

        self.submit_button_text = ft.Text(self._("Generate Spreadsheet"))
        self.submit_button = ft.ElevatedButton(
            content=self.submit_button_text,
            on_click=self.on_submit_click,
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
                ft.DropdownOption(key="decals", text=self._("Decals")),
                ft.DropdownOption(key="wallpapers", text=self._("Wallpapers")),
            ],
            on_select=self.get_dropdown_value,
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
        self.image_links_column.controls.append(self._make_image_link_row(0))

    def _hint_sets(self) -> tuple[list[str], list[str], list[str]]:
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
        return price_hints, width_hints, height_hints

    def _make_size_row(self, index: int) -> ft.Row:
        price_hints, width_hints, height_hints = self._hint_sets()
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

        return ft.Row(
            controls=[width_field, height_field, price_field],
            alignment=ft.MainAxisAlignment.CENTER,
        )

    def _make_image_link_row(self, index: int) -> ft.Row:
        return ft.Row(
            controls=[
                ft.TextField(
                    label=f"{self._('Image Link')} #{index + 1}",
                    expand=True,
                )
            ],
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
        )

    def get_dropdown_value(self, e: ft.ControlEvent) -> None:
        """Получение значения из выпадающего меню. Необходимо для класса-фабрики и обновления интерфейса"""
        if self.print_type_dd.value == "wallpapers":
            self.design_container.visible = False
            self.personalization_container.visible = False
        if self.print_type_dd.value == "decals":
            self.design_container.visible = True
            self.personalization_container.visible = True
        self.page.update()

    async def on_lang_change(self, e: ft.ControlEvent) -> None:
        self.lang = e.control.value
        await self.prefs.set("lang", self.lang)
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
        self.submit_button_text.value = self._("Generate Spreadsheet")
        self.design_radio.content.controls[0].content.label = self._("Yes")
        self.design_radio.content.controls[1].content.label = self._("No")
        self.personalization_radio.content.controls[0].content.label = self._("Yes")
        self.personalization_radio.content.controls[1].content.label = self._("No")
        price_hints, width_hints, height_hints = self._hint_sets()
        for index, row in enumerate(self.sizes_column.controls):
            row.controls[0].label = self._("Width")
            row.controls[0].hint_text = width_hints[index % len(width_hints)]
            row.controls[1].label = self._("Height")
            row.controls[1].hint_text = height_hints[index % len(height_hints)]
            row.controls[2].label = self._("Price")
            row.controls[2].hint_text = price_hints[index % len(price_hints)]

        for index, row in enumerate(self.image_links_column.controls):
            row.controls[0].label = f"{self._('Image Link')} #{index + 1}"

    def add_size(self, e: ft.ControlEvent) -> None:
        """Добавляет блоки с высотой, шириной и ценой, а также подсказки"""
        index = len(self.sizes_column.controls)
        row = self._make_size_row(index)
        self.sizes_column.controls.append(row)
        self.page.update()

    def remove_size(self, e: ft.ControlEvent) -> None:
        """Убирает блоки с высотой, шириной и ценой, а также подсказки"""
        if self.sizes_column.controls:
            self.sizes_column.controls.pop()
            self.page.update()

    def make_size_buttons(self) -> ft.Control:
        """Создает кнопки для добавления и убирания размера"""
        add_button = ft.IconButton(
            icon=ft.Icons.ADD, on_click=self.add_size, icon_size=30
        )
        remove_button = ft.IconButton(
            icon=ft.Icons.REMOVE, on_click=self.remove_size, icon_size=30
        )
        return ft.Row(controls=[add_button, remove_button], spacing=80)

    def add_image_link(self, e: ft.ControlEvent) -> None:
        index = len(self.image_links_column.controls)
        row = self._make_image_link_row(index)
        self.image_links_column.controls.append(row)
        self.page.update()

    def remove_image_link(self, e: ft.ControlEvent) -> None:
        if len(self.image_links_column.controls) > 1:
            self.image_links_column.controls.pop()
            self.page.update()

    def make_image_buttons(self) -> ft.Control:
        add_button = ft.IconButton(
            icon=ft.Icons.ADD, on_click=self.add_image_link, icon_size=30
        )
        remove_button = ft.IconButton(
            icon=ft.Icons.REMOVE, on_click=self.remove_image_link, icon_size=30
        )
        return ft.Row(controls=[add_button, remove_button], spacing=80)

    async def on_submit_click(self, e: ft.ControlEvent) -> None:
        directory_path = await self.folder_picker.get_directory_path(
            dialog_title=self._("Choose a folder to save the file"),
        )
        if directory_path:
            await self.submit_form(directory_path)
            return

        self.progress_ring.visible = False
        self.submit_button.disabled = False
        self.page.update()

    def _require_value(self, control: ft.TextField) -> bool:
        value = (control.value or "").strip()
        if not value:
            control.error = self._("This field is required")
            return False
        control.error = None
        return True

    def _require_dropdown(self, control: ft.Dropdown) -> bool:
        value = (control.value or "").strip()
        if not value:
            control.error_text = self._("This field is required")
            return False
        control.error_text = None
        return True

    def validate_fields(self) -> bool:
        """Проверяет валидность полей формы"""
        valid = True

        valid = self._require_dropdown(self.print_type_dd) and valid
        valid = self._require_value(self.title_field) and valid
        valid = self._require_value(self.sku_field) and valid
        valid = self._require_value(self.keyword_field) and valid
        if not self.image_links_column.controls:
            valid = False
        else:
            valid = (
                self._require_value(self.image_links_column.controls[0].controls[0])
                and valid
            )
            for image_row in self.image_links_column.controls[1:]:
                image_row.controls[0].error = None

        for row in self.sizes_column.controls:
            width_field, height_field, price_field = row.controls
            valid = self._require_value(width_field) and valid
            valid = self._require_value(height_field) and valid
            valid = self._require_value(price_field) and valid

        self.page.update()
        return valid

    async def clear_errors(self) -> None:
        """Очищает заполненные поля при ошибках"""
        self.progress_ring.visible = False
        self.page.update()
        await asyncio.sleep(2)
        self.print_type_dd.error_text = None
        self.title_field.error = None
        self.sku_field.error = None
        self.keyword_field.error = None
        for image_row in self.image_links_column.controls:
            image_row.controls[0].error = None
        for row in self.sizes_column.controls:
            for ctrl in row.controls:
                ctrl.error = None
        self.page.update()

    async def submit_form(self, folder: os.PathLike | str) -> None:
        """Передает данные из заполненных полей в класс-фабрику для последующей обработки"""
        self.progress_ring.visible = True
        self.success_icon.visible = False
        self.submit_button.disabled = True
        self.page.update()

        await asyncio.sleep(0.1)

        try:
            if not self.validate_fields():
                snack_bar = ft.SnackBar(
                    ft.Text(self._("Please fill in all required fields"))
                )
                self.page.show_dialog(snack_bar)
                await self.clear_errors()
                return
            shaper = DataShaperFactory.create_shaper(self.print_type_dd.value)

            title = self.title_field.value
            sku = self.sku_field.value
            keyword = self.keyword_field.value
            image_links = [
                image_row.controls[0].value.strip()
                for image_row in self.image_links_column.controls
                if (image_row.controls[0].value or "").strip()
            ]
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
                    image_links=image_links,
                    height=height,
                    width=width,
                    price=price,
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

            snack_bar = ft.SnackBar(ft.Text(self._("Spreadsheet generated")))
            self.page.show_dialog(snack_bar)
            self.page.update()
        except Exception as ex:
            alert = ft.AlertDialog(
                title=ft.Text(self._("Error: %(err)s") % {"err": ex}),
            )
            self.page.show_dialog(alert)
        finally:
            self.title_field.value = ""
            self.sku_field.value = ""
            self.keyword_field.value = ""
            for image_row in self.image_links_column.controls:
                image_row.controls[0].value = ""
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
                controls=[
                    ft.Image(src="logo.png", fit=ft.BoxFit.FIT_HEIGHT, height=70)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Row(controls=[self.lang_dd], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(
                controls=[self.print_type_dd], alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Row(controls=[self.title_field], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(controls=[self.sku_field], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(
                controls=[self.keyword_field], alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Row(
                controls=[
                    ft.Container(
                        content=self.image_links_column,
                        expand=True,
                    )
                ],
                expand=True,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[self.image_buttons_row], alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Row(
                controls=[self.design_container], alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Divider(),
            ft.Row(
                controls=[self.personalization_container],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Divider(),
            ft.Row(
                controls=[self.size_price_label],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            self.sizes_column,
            ft.Row(controls=[self.buttons_row], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(),
            ft.Row(controls=[self.submit_row], alignment=ft.MainAxisAlignment.CENTER),
        )
