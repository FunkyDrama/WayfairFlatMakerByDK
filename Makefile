i18n-extract:
	pybabel extract -F babel.cfg -o locales/app.pot .

i18n-update:
	pybabel update -i locales/app.pot -d locales -D app

i18n-compile:
	pybabel compile -d locales -D app