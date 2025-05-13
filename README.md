# 🧾 Wayfair Listing Spreadsheet Generator

This software is designed to **quickly generate product spreadsheets for uploading listings to Wayfair**.

It is a commercial tool created for a company that produces customizable print products such as **wall decals, wallpapers, stickers**, and more. The source code is published with their permission. You are free to adapt this tool to your specific product type.

## 📦 Features

- Generate Wayfair-compliant listing spreadsheets  
- User-friendly desktop interface (built with [Flet](https://flet.dev/))  
- Excel (XLSX) file generation using `openpyxl`  
- Lightweight and fast  
- Easily extendable for your own product types

## 🛠 Installation

> Requires **Python 3.12+** and [Poetry](https://python-poetry.org/) for dependency management.

1. Clone the repository:

```bash
git clone https://github.com/FunkyDrama/WayfairFlatMakerByDK.git
```

2. Install dependencies:

```bash
poetry install
```

3. Run the app:

```bash
poetry run python main.py
```

## 📄 How to Use

1. Go to your Wayfair account:  
   `Product Management → Add Products → Composite SKUs` tab.  
2. Select your **brand** and **product category**.  
3. Download a **blank template spreadsheet** from Wayfair.  
4. Use this tool to automatically generate a completed spreadsheet based on your products.

## 🧰 Build Executable

### For macOS

```bash
flet build macos \
  --build-number=1 \
  --build-version=1.0.0 \
  --project=WayfairFlatMakerByDK \
  --product=WayfairFlatMakerByDK
```

### For Windows

```bash
flet pack main.py \
  --add-data "assets:assets" \
  --add-data "decal_template.xlsx;." \
  --add-data "wallpaper_template.xlsx;." \
  --icon assets/icon_windows.png \
  --name WayfairFlatMakerByDK
```

> Ensure you have the Flet CLI installed:  
> `poetry add flet-cli`

## 📚 Dependencies

Some of the main libraries used:

- [`flet`](https://pypi.org/project/flet/) – Build cross-platform GUI in Python  
- [`openpyxl`](https://pypi.org/project/openpyxl/) – Excel file generation  
- [`watchdog`](https://pypi.org/project/watchdog/) – Filesystem monitoring (optional)  
- [`httpx`](https://pypi.org/project/httpx/) – HTTP client  
- [`anyio`](https://pypi.org/project/anyio/) – Async compatibility layer  

> Full list of packages can be found in [`poetry.lock`](./poetry.lock).

## 👤 License

This code is provided as-is with permission for public use, but **not open source** in the traditional sense. Please do not redistribute commercially without prior agreement.

## 🙏 Credits

Made by me in cooperation with a printing company specializing in custom wall decor who allowed me to share this code as many other times earlier.