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
    _("e.g. (in plural): Dog Wallpapers"),
    _("✨ Suggest title & keywords"),
    _("Generating..."),
    _("Title and keywords generated"),
    _("AI generation is not configured. Please contact the administrator."),
    _("AI text generation is not configured. Standard template text was used."),
    _("AI generation is not configured correctly. Please contact the administrator."),
    _("AI limit was reached. Try again later."),
    _("AI limit was reached. Standard template text was used. Try again later."),
    _("AI service is temporarily unavailable. Try again later."),
    _("AI service is temporarily unavailable. Standard template text was used."),
    _("AI generation failed. Try again later."),
    _("AI generation failed. Standard template text was used."),
    _("AI text generation failed. Standard template text was used."),
    _(
        "AI could not download the main image. Check that the image link opens publicly."
    ),
    _("AI could not read the main image. Please use another image link."),
    _("The main image is too large for AI analysis. Please use a smaller image."),
    _("AI did not return usable text. Try again."),
    _("AI returned an unexpected answer. Try again."),
    _("AI returned incomplete text. Try again."),
    _(
        "AI could not create a title and keywords from this image. Try again or fill them manually."
    ),
    _("AI could not generate a title and keywords. Try again or fill them manually."),
    _("Could not load price data. Check your internet connection and try again."),
)
