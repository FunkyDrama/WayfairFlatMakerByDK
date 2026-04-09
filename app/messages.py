"""Translation catalog anchors for strings that are not extracted from call sites."""


def _(message: str) -> str:
    """Return the raw message for Babel extraction."""

    return message


CATALOG: tuple[str, ...] = (
    _(
        "Image Link #1 warning: the design must cover at least 75 percent of the full room/staged image."
    ),
    _("Press Enter to autofill."),
    _(
        "Please fill in the required fields and choose the required options, and enter valid values in the highlighted fields."
    ),
    _("Please fill in the required fields and choose the required options."),
    _("Please enter valid values in the highlighted fields."),
    _("Please fix the highlighted fields."),
    _("%(field)s is required."),
    _("Links are not allowed in %(field)s."),
    _("Enter a valid URL for %(field)s."),
)
