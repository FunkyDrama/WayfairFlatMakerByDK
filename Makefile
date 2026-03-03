DOMAIN ?= app
LOCALES_DIR ?= locales
POT_FILE ?= $(LOCALES_DIR)/$(DOMAIN).pot
LANG ?=

.PHONY: i18n-extract i18n-update i18n-compile i18n-init i18n-all build-macos build-windows

i18n-extract:
	pybabel extract -F i18n/babel.cfg -o $(POT_FILE) .

i18n-update: i18n-extract
	pybabel update -i $(POT_FILE) -d $(LOCALES_DIR) -D $(DOMAIN)

i18n-compile:
	pybabel compile -d $(LOCALES_DIR) -D $(DOMAIN)

i18n-init: i18n-extract
ifndef LANG
	$(error LANG is required. Usage: make i18n-init LANG=de)
endif
	pybabel init -i $(POT_FILE) -d $(LOCALES_DIR) -D $(DOMAIN) -l $(LANG)

i18n-all: i18n-update i18n-compile

build-macos:
	poetry run flet build macos

build-windows:
	poetry run flet build windows

build-windows-onefile:
	poetry run flet pack main.py --add-data "assets:assets" --add-data "locales:locales" --icon assets/icon_windows.png --name WayfairFlatMakerByDK