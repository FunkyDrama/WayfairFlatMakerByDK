"""Text rules enforced by the Wayfair upload template's validation formulas."""

import re

# Rejected in Product Name, part numbers, Marketing Copy, and Feature Bullets.
# Wayfair checks with SEARCH(), which ignores case, so "ø" fails like "Ø".
FORBIDDEN_CHARACTERS = "<>Ø•‣⁃⁌⁍™∙⌀◦"
MAX_PRODUCT_NAME_CHARS = 254
MAX_MARKETING_COPY_CHARS = 1500

FORBIDDEN_PATTERN = re.compile(
    f"[{re.escape(FORBIDDEN_CHARACTERS + FORBIDDEN_CHARACTERS.lower())}]"
)


# Letters keep words readable ("Søft" -> "Soft"); other symbols become spaces.
FORBIDDEN_LETTER_REPLACEMENTS = str.maketrans({"Ø": "O", "ø": "o"})


def remove_forbidden_characters(text: str) -> str:
    """Remove characters Wayfair rejects and tidy the spacing."""

    text = text.translate(FORBIDDEN_LETTER_REPLACEMENTS)
    return re.sub(r"\s+", " ", FORBIDDEN_PATTERN.sub(" ", text)).strip()


def truncate_at_sentence(text: str, max_chars: int) -> str:
    """Shorten text to ``max_chars``, ending on a full sentence when possible."""

    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    if not text[max_chars].isspace():
        truncated = truncated.rsplit(" ", maxsplit=1)[0]
    sentence_end = max(truncated.rfind(mark) for mark in ".!?")
    if sentence_end >= len(truncated) // 2:
        return truncated[: sentence_end + 1].strip()
    return truncated.rstrip(" ,;:")[: max_chars - 1] + "."
