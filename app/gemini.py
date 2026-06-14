"""Gemini API integration for AI-assisted listing content."""

from __future__ import annotations

from dataclasses import dataclass
import json
import mimetypes
from pathlib import Path
import re
from typing import Any
from urllib.error import URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from google import genai
from google.genai import errors, types

from app.settings import settings
from data.models import MarketingTexts

MAX_INLINE_IMAGE_BYTES = 18 * 1024 * 1024
MAX_MARKETING_COPY_CHARS = 700
MAX_FEATURE_BULLET_WORDS = 15


@dataclass(frozen=True)
class TitleKeywordSuggestion:
    """Suggested listing title and keyword phrase."""

    title: str
    keyword: str


class GeminiUserError(RuntimeError):
    """Gemini failure with a message safe to show to operators."""

    def __init__(self, technical_message: str, user_message: str) -> None:
        """Store both technical and user-facing details."""

        super().__init__(technical_message)
        self.user_message = user_message


class GeminiClient:
    """Gemini SDK client for AI-assisted listing content."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize the API key and model name."""

        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self._image_cache: dict[str, tuple[bytes, str]] = {}

    @property
    def is_configured(self) -> bool:
        """Return whether the Gemini API key is available."""

        return bool(self.api_key)

    def suggest_title_keywords(
        self,
        image_url: str,
        print_type: str | None,
    ) -> TitleKeywordSuggestion:
        """Generate a title and keyword phrase from the main product image."""

        if not self.api_key:
            raise GeminiUserError(
                "Gemini API key is not configured.",
                "AI generation is not configured. Please contact the administrator.",
            )

        image_bytes, mime_type = self.download_image(image_url)
        product_name = product_label(print_type)
        title_requirements = title_requirements_for_print_type(print_type)
        keyword_suffix = keyword_suffix_for_print_type(print_type)
        prompt = (
            "You are a senior Wayfair SEO marketplace copywriter for wall decor. "
            "Analyze the main product image and infer the visible subject, style, "
            "room/use case, and buyer search intent. Return JSON only with keys "
            "title and keyword. Title rules: natural American English, optimized "
            "for Wayfair search, target 120-170 characters, absolute maximum 245 "
            "characters, no SKU, no brand name, no URL, no quotation marks, no ALL "
            "CAPS, no keyword stuffing, no unsupported claims. The title must not "
            "be abstract: it must include the visible subject/theme plus clear "
            f"product-category wording required here: {title_requirements}. "
            "Do not mention packaging, shipping tubes, installation steps, ink "
            "technology, country of printing, certifications, or material claims "
            "in the title unless they are visibly part of the product image. "
            "Prefer specific searchable descriptors such as room, style, color, "
            "theme, nursery, kids room, bedroom, living room, ocean, floral, animal, "
            "boho, tropical, vintage, modern, or watercolor when visible. "
            "Keyword rules: one concise plural SEO phrase, 2-5 words before the "
            "required product suffix, no commas, no adjectives that are not visible, "
            f"must end exactly with '{keyword_suffix}', e.g. 'Dog {keyword_suffix}'. "
            f"Product category: {product_name}."
        )
        response = self.generate_json(
            [
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                {"text": prompt},
            ]
        )
        title = clean_text_value(response.get("title"))
        keyword = clean_text_value(response.get("keyword"))
        if not title or not keyword:
            raise GeminiUserError(
                "Gemini did not return title and keyword.",
                "AI could not create a title and keywords from this image. Try again or fill them manually.",
            )
        return TitleKeywordSuggestion(title=title, keyword=keyword)

    def generate_marketing_texts(
        self,
        title: str,
        keyword: str,
        print_type: str,
    ) -> MarketingTexts:
        """Generate marketing copy and feature bullets for a listing."""

        if not self.api_key:
            raise GeminiUserError(
                "Gemini API key is not configured.",
                "AI text generation is not configured. Standard template text was used.",
            )

        product_name = product_label(print_type)
        benefit_guidance = benefit_guidance_for_print_type(print_type)
        prompt = (
            "You are a senior Wayfair SEO marketplace copywriter for wall decor. "
            "Write high-converting, search-friendly ecommerce copy in natural "
            "American English for a Wayfair product upload. Return JSON only with "
            "keys marketing_copy, feature_bullet_1, feature_bullet_2, "
            "feature_bullet_3, feature_bullet_4, feature_bullet_5. "
            "SEO goals: use the keyword phrase naturally, include relevant buyer "
            "intent terms such as wall decor, nursery, bedroom, living room, office, "
            "peel and stick, removable, mural, decal, wallpaper only when they fit "
            "the product category. Avoid keyword stuffing. "
            "Compliance rules: no brand names, no SKU, no price, no discounts, no "
            "shipping or delivery promises, no guarantees, no medical/safety claims, "
            "no claims not implied by the product category. Do not mention Wayfair. "
            "Use only approved product facts from the product-specific guidance; "
            "do not invent certifications, guarantees, child-safety claims, or "
            "environmental claims beyond that guidance. "
            "Style: warm, clear, specific, practical, and ready for a product page. "
            "Marketing copy rules: one short single paragraph, complete sentences, "
            "180-450 characters, no line breaks, no bullet formatting, no trademark "
            "symbols, no copyright symbols, no registered symbols, no emoji, no "
            "extra spacing. "
            "Feature bullet rules: each bullet must be 15 words or less, one short "
            "sentence fragment or sentence, one product aspect only, no line breaks, "
            "no special symbols, no punctuation-heavy formatting. Provide all five "
            "bullets. Bullets should cover distinct facts: visual impact, material "
            "or print quality, installation, size/fit, room use case, surface "
            "compatibility, or packaging when relevant. "
            f"Product-specific benefit guidance: {benefit_guidance}. "
            f"Listing title: {title}. Keyword phrase: {keyword}. "
            f"Product category: {product_name}."
        )
        response = self.generate_json([{"text": prompt}])
        return MarketingTexts(
            marketing_copy=clean_marketing_copy(
                required_text(response, "marketing_copy")
            ),
            feature_bullet_1=clean_feature_bullet(
                required_text(response, "feature_bullet_1")
            ),
            feature_bullet_2=clean_feature_bullet(
                required_text(response, "feature_bullet_2")
            ),
            feature_bullet_3=clean_feature_bullet(
                required_text(response, "feature_bullet_3")
            ),
            feature_bullet_4=clean_feature_bullet(
                required_text(response, "feature_bullet_4")
            ),
            feature_bullet_5=clean_feature_bullet(
                required_text(response, "feature_bullet_5")
            ),
        )

    def generate_json(self, parts: list[types.Part | dict[str, str]]) -> dict[str, Any]:
        """Call Gemini and parse the JSON object from response text."""

        if self.client is None:
            raise GeminiUserError(
                "Gemini API key is not configured.",
                "AI generation is not configured. Please contact the administrator.",
            )

        contents: Any = [
            part.get("text", "") if isinstance(part, dict) else part for part in parts
        ]
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    response_mime_type="application/json",
                ),
            )
        except errors.APIError as exc:
            raise gemini_api_error(exc) from exc
        except (OSError, URLError) as exc:
            raise GeminiUserError(
                "Gemini API request failed.",
                "AI service is temporarily unavailable. Try again later.",
            ) from exc

        return parse_json_object(extract_response_text(response))

    def download_image(self, image_url: str) -> tuple[bytes, str]:
        """Download an image URL and return bytes plus a Gemini-compatible MIME type.

        Results are cached by normalized URL for the lifetime of the client instance
        so repeated "Suggest" clicks on the same image skip the network round-trip.
        """

        normalized_url = normalize_public_image_url(image_url)
        if normalized_url in self._image_cache:
            return self._image_cache[normalized_url]

        request = Request(
            normalized_url,
            headers={"User-Agent": "WayfairFlatMaker/1.0"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=30) as response:
                image_bytes = response.read(MAX_INLINE_IMAGE_BYTES + 1)
                content_type = response.headers.get("Content-Type", "")
        except (OSError, URLError) as exc:
            raise GeminiUserError(
                "Could not download the image for Gemini.",
                "AI could not download the main image. Check that the image link opens publicly.",
            ) from exc

        if not image_bytes:
            raise GeminiUserError(
                "Downloaded image is empty.",
                "AI could not read the main image. Please use another image link.",
            )
        if len(image_bytes) > MAX_INLINE_IMAGE_BYTES:
            raise GeminiUserError(
                "Image is too large for inline Gemini analysis.",
                "The main image is too large for AI analysis. Please use a smaller image.",
            )
        result = image_bytes, guess_image_mime_type(normalized_url, content_type)
        self._image_cache[normalized_url] = result
        return result


def normalize_public_image_url(url: str) -> str:
    """Normalize Dropbox preview links to raw downloadable links."""

    parts = urlsplit(url)
    if not parts.netloc.lower().endswith("dropbox.com"):
        return url

    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.pop("dl", None)
    query["raw"] = "1"
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def guess_image_mime_type(url: str, content_type: str) -> str:
    """Return a safe image MIME type for Gemini inline_data."""

    normalized_content_type = content_type.split(";", maxsplit=1)[0].strip().lower()
    if normalized_content_type.startswith("image/"):
        return normalized_content_type

    guessed_type = mimetypes.guess_type(Path(urlsplit(url).path).name)[0]
    if guessed_type and guessed_type.startswith("image/"):
        return guessed_type
    return "image/jpeg"


def extract_response_text(response: Any) -> str:
    """Extract text from a Gemini SDK response."""

    text = getattr(response, "text", "")
    if isinstance(text, str) and text.strip():
        return text.strip()
    raise GeminiUserError(
        "Gemini response has no text output.",
        "AI did not return usable text. Try again.",
    )


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from raw model output."""

    cleaned_text = text.strip()
    if cleaned_text.startswith("```"):
        cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text)
        cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

    try:
        data = json.loads(cleaned_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned_text, flags=re.DOTALL)
        if not match:
            raise GeminiUserError(
                "Gemini did not return valid JSON.",
                "AI returned an unexpected answer. Try again.",
            ) from None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            raise GeminiUserError(
                "Gemini did not return valid JSON.",
                "AI returned an unexpected answer. Try again.",
            ) from None

    if not isinstance(data, dict):
        raise GeminiUserError(
            "Gemini JSON response is not an object.",
            "AI returned an unexpected answer. Try again.",
        )
    return data


def clean_text_value(value: Any) -> str:
    """Normalize a Gemini text field value."""

    if not isinstance(value, str):
        return ""
    return normalize_plain_text(value)


def normalize_plain_text(value: str) -> str:
    """Remove formatting and restricted symbols from model-generated text."""

    normalized = re.sub(r"[\r\n\t]+", " ", value)
    normalized = normalized.replace("™", "").replace("®", "").replace("©", "")
    normalized = normalized.replace("•", "").replace("*", "")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def clean_marketing_copy(value: str) -> str:
    """Return a single-paragraph product description safe for Wayfair."""

    cleaned = normalize_plain_text(value)
    if len(cleaned) <= MAX_MARKETING_COPY_CHARS:
        return cleaned

    truncated = cleaned[:MAX_MARKETING_COPY_CHARS].rsplit(" ", maxsplit=1)[0]
    sentence_end = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
    if sentence_end >= 120:
        return truncated[: sentence_end + 1].strip()
    return truncated.rstrip(" ,;:") + "."


def clean_feature_bullet(value: str) -> str:
    """Return a concise feature bullet within Wayfair's word limit."""

    cleaned = normalize_plain_text(value).strip(" -:;,.")
    words = cleaned.split()
    if len(words) > MAX_FEATURE_BULLET_WORDS:
        cleaned = " ".join(words[:MAX_FEATURE_BULLET_WORDS]).rstrip(" ,;:.")
    return cleaned


def required_text(data: dict[str, Any], key: str) -> str:
    """Return a required non-empty text field from a Gemini JSON object."""

    value = clean_text_value(data.get(key))
    if not value:
        raise GeminiUserError(
            f"Gemini response is missing {key}.",
            "AI returned incomplete text. Try again.",
        )
    return value


def gemini_api_error(error: errors.APIError) -> GeminiUserError:
    """Map Gemini SDK errors to operator-friendly messages."""

    status_code = getattr(error, "code", None)
    detail = str(error)

    if status_code in {400, 401, 403}:
        return GeminiUserError(
            f"Gemini API request failed: {detail}",
            "AI generation is not configured correctly. Please contact the administrator.",
        )
    if status_code == 429:
        return GeminiUserError(
            f"Gemini API request failed: {detail}",
            "AI limit was reached. Try again later.",
        )
    if isinstance(status_code, int) and status_code >= 500:
        return GeminiUserError(
            f"Gemini API request failed: {detail}",
            "AI service is temporarily unavailable. Try again later.",
        )
    return GeminiUserError(
        f"Gemini API request failed: {detail}",
        "AI generation failed. Try again later.",
    )


def product_label(print_type: str | None) -> str:
    """Return a human-readable product category for prompts."""

    if print_type == "wallpapers":
        return "wallpaper and wall mural"
    return "wall decal and wall sticker"


def title_requirements_for_print_type(print_type: str | None) -> str:
    """Return required product wording for generated titles."""

    if print_type == "wallpapers":
        return (
            "include 'Wallpaper' and include 'Wall Mural' when the design reads as "
            "a full-wall scene, mural, landscape, nursery scene, or large botanical "
            "wall design"
        )
    return "include 'Vinyl Wall Decal' or 'Wall Sticker'"


def benefit_guidance_for_print_type(print_type: str | None) -> str:
    """Return product-specific benefit guidance for generated bullets."""

    if print_type == "wallpapers":
        return (
            "Approved wallpaper facts: available in four finishes/material options "
            "(Smooth Peel & Stick, Luxury Canvas Texture, Non-Woven Wallpaper, and "
            "Premium Non-Woven); 40-inch wide panels help reduce seams, simplify "
            "installation, improve pattern alignment, and create a cleaner finished "
            "look; custom printed in the USA; made to order; printed with HP Latex "
            "inks; designed for bedrooms, nurseries, living rooms, offices, kids "
            "rooms, and statement walls; measuring before ordering helps customers "
            "choose the right size; easy room refresh and polished wall-mural impact."
        )
    return (
        "Approved decal facts: made from high-quality waterproof vinyl; suitable for "
        "smooth surfaces; easy DIY installation with transfer tape and step-by-step "
        "application; available in multiple sizes; optional color palette for designs "
        "with color choices; clean decorative impact for walls and other smooth "
        "surfaces; shipped in a protective kraft mailing tube with caps to help "
        "protect the decal in transit."
    )


def keyword_suffix_for_print_type(print_type: str | None) -> str:
    """Return the expected keyword suffix for a print type."""

    return "Wallpapers" if print_type == "wallpapers" else "Wall Stickers"
