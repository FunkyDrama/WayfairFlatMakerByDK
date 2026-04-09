"""Validation helpers for form controls."""

from collections.abc import Callable

import flet as ft

Translator = Callable[[str], str]
LinkChecker = Callable[[str], bool]
UrlChecker = Callable[[str], bool]


def field_title(control: ft.TextField | ft.Dropdown) -> str:
    """Return a human-readable field name for validation messages."""

    label = control.label
    return label if isinstance(label, str) and label else "Field"


def validation_summary_message(error_kinds: set[str], translate: Translator) -> str:
    """Build a compact validation summary based on collected error kinds."""

    has_missing = "missing" in error_kinds
    has_invalid = "invalid" in error_kinds
    if has_missing and has_invalid:
        return translate(
            "Please fill in the required fields and choose the required options, and enter valid values in the highlighted fields."
        )
    if has_missing:
        return translate(
            "Please fill in the required fields and choose the required options."
        )
    if has_invalid:
        return translate("Please enter valid values in the highlighted fields.")
    return translate("Please fix the highlighted fields.")


def require_value(
    control: ft.TextField,
    error_kinds: set[str],
    translate: Translator,
) -> bool:
    """Require a non-empty value for a text field."""

    value = (control.value or "").strip()
    if not value:
        error_kinds.add("missing")
        control.error = translate("%(field)s is required.") % {
            "field": field_title(control)
        }
        return False
    control.error = None
    return True


def require_plain_text(
    control: ft.TextField,
    error_kinds: set[str],
    translate: Translator,
    *,
    contains_link: LinkChecker,
) -> bool:
    """Require a non-empty text value that does not contain links."""

    if not require_value(control, error_kinds, translate):
        return False
    if contains_link((control.value or "").strip()):
        error_kinds.add("invalid")
        control.error = translate("Links are not allowed in %(field)s.") % {
            "field": field_title(control)
        }
        return False
    control.error = None
    return True


def require_dropdown(
    control: ft.Dropdown,
    error_kinds: set[str],
    translate: Translator,
) -> bool:
    """Require a selected dropdown value."""

    value = (control.value or "").strip()
    if not value:
        error_kinds.add("missing")
        control.error_text = translate("%(field)s is required.") % {
            "field": field_title(control)
        }
        return False
    control.error_text = None
    return True


def require_url(
    control: ft.TextField,
    error_kinds: set[str],
    translate: Translator,
    *,
    required: bool,
    is_valid_url: UrlChecker,
) -> bool:
    """Require a valid URL or allow the field to stay empty when optional."""

    value = (control.value or "").strip()
    if not value:
        if required:
            error_kinds.add("missing")
            control.error = translate("%(field)s is required.") % {
                "field": field_title(control)
            }
            return False
        control.error = None
        return True
    if not is_valid_url(value):
        error_kinds.add("invalid")
        control.error = translate("Enter a valid URL for %(field)s.") % {
            "field": field_title(control)
        }
        return False
    control.error = None
    return True
