"""Gemini API integration for AI-assisted listing content."""

from __future__ import annotations

from dataclasses import dataclass
import io
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
import httpx
from PIL import Image, UnidentifiedImageError

from app.settings import settings
from data.models import MarketingTexts

MAX_INLINE_IMAGE_BYTES = 18 * 1024 * 1024
# Large images make the upload, not generation, dominate response time.
MAX_MODEL_IMAGE_SIDE_PX = 1024
MAX_MODEL_IMAGE_BYTES = 500 * 1024
MODEL_IMAGE_JPEG_QUALITY = 85
REQUEST_TIMEOUT_MS = 30_000
RETRY_OPTIONS = types.HttpRetryOptions(
    attempts=2,
    initial_delay=1.0,
    max_delay=8.0,
    http_status_codes=[408, 500, 502, 503, 504],
)
MAX_MARKETING_COPY_WORDS = 250
MAX_FEATURE_BULLET_WORDS = 15
FEATURE_BULLET_KEYS = tuple(f"feature_bullet_{index}" for index in range(1, 9))

SYSTEM_INSTRUCTION = (
    "You are a senior Wayfair marketplace copywriter and SEO specialist for wall "
    "decor: vinyl wall decals, wall stickers, wallpaper, and wall murals. You write "
    "natural American English for product data that is uploaded to Wayfair and "
    "shown on the customer-facing product page.\n"
    "Compliance rules that always apply:\n"
    "- No brand names, SKUs, prices, discounts, URLs, or mentions of Wayfair.\n"
    "- No shipping or delivery promises, guarantees, warranties, medical, safety, "
    "child-safety, environmental, or certification claims.\n"
    "- Use only the approved product facts you are given and what is clearly "
    "visible in the image. Never invent materials, features, or claims.\n"
    "- No abbreviations, no ALL CAPS, no quotation marks, no emoji, and no "
    "trademark, copyright, or registered symbols.\n"
    "- Plain text only: no line breaks, bullet characters, markdown, or extra "
    "spacing.\n"
    "- Use search phrases naturally; never stuff keywords or repeat the same "
    "phrase."
)

TITLE_KEYWORD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Wayfair product title."},
        "keyword": {"type": "string", "description": "Plural SEO keyword phrase."},
    },
    "required": ["title", "keyword"],
}

MARKETING_TEXTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "marketing_copy": {
            "type": "string",
            "description": "Single-paragraph product description.",
        },
        **{
            key: {"type": "string", "description": "Feature bullet, max 15 words."}
            for key in FEATURE_BULLET_KEYS
        },
    },
    "required": ["marketing_copy", *FEATURE_BULLET_KEYS],
}


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
        fallback_model: str | None = None,
    ) -> None:
        """Initialize the API key and model names."""

        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.fallback_model = fallback_model or settings.gemini_fallback_model
        self.client = (
            genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(
                    timeout=REQUEST_TIMEOUT_MS, retry_options=RETRY_OPTIONS
                ),
            )
            if self.api_key
            else None
        )
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
            f"Product category: {product_name}.\n"
            "Task: study the attached main product image and write a Wayfair "
            "product title and a keyword phrase for it.\n"
            "First identify what is visible: the main subject or theme, art style, "
            "dominant colors, and the rooms or buyers it suits.\n"
            "Title rules:\n"
            "- 100-170 characters, never more than 200.\n"
            "- Start with the visible subject or theme, then the product category "
            f"wording: {title_requirements}.\n"
            "- Add specific, searchable descriptors only when they are visible: "
            "style (boho, vintage, modern, watercolor, tropical, minimalist), color, "
            "theme (floral, animal, ocean, botanical, geometric), and room or "
            "audience (nursery, kids room, bedroom, living room, office).\n"
            "- Do not mention packaging, installation, ink, country of printing, "
            "certifications, or materials unless they are visibly part of the "
            "design.\n"
            "Keyword rules:\n"
            "- One concise plural phrase with 1-4 descriptive words before the "
            "product suffix, no commas, no adjectives that are not visible.\n"
            f"- It must end exactly with '{keyword_suffix}', for example "
            f"'Dog {keyword_suffix}' or 'Watercolor Floral {keyword_suffix}'."
        )
        response = self.generate_json(
            [
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                {"text": prompt},
            ],
            TITLE_KEYWORD_SCHEMA,
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
        has_color_variations: bool = False,
    ) -> MarketingTexts:
        """Generate marketing copy and feature bullets for a listing."""

        if not self.api_key:
            raise GeminiUserError(
                "Gemini API key is not configured.",
                "AI text generation is not configured. Standard template text was used.",
            )

        product_name = product_label(print_type)
        benefit_guidance = benefit_guidance_for_print_type(
            print_type, has_color_variations
        )
        prompt = (
            f"Product category: {product_name}.\n"
            f"Listing title: {title}\n"
            f"Keyword phrase: {keyword}\n"
            f"Approved product facts: {benefit_guidance}\n"
            "Task: write the marketing copy and eight feature bullets for this "
            "listing. Describe the design from the title; describe the product only "
            "with the approved facts.\n"
            "Marketing copy rules:\n"
            "- One paragraph of complete sentences, 120-200 words, never more than "
            f"{MAX_MARKETING_COPY_WORDS} words.\n"
            "- Give a compelling, informative overview: what the design shows and "
            "its style, the look it creates, rooms and occasions it suits, and the "
            "key product benefits from the approved facts.\n"
            "- Use the keyword phrase once or twice, naturally; work in related "
            "searches such as wall decor, nursery, bedroom, living room, or office "
            "only where they fit.\n"
            "- Warm, clear, specific, and practical; no hype or filler.\n"
            "Feature bullet rules:\n"
            f"- Each bullet is at most {MAX_FEATURE_BULLET_WORDS} words, covers one "
            "product aspect, and starts with a capital letter.\n"
            "- The eight bullets each cover a different fact, chosen from: design "
            "and visual impact, style and color, material or print quality, finish "
            "or material options, installation, size options and fit, room use, "
            "surface compatibility, and packaging or print origin when they are "
            "approved facts.\n"
            "- Never repeat a fact across bullets; order them from most to least "
            "important for a shopper.\n"
            "- Do not repeat the marketing copy word for word."
            + (
                ""
                if has_color_variations or print_type == "wallpapers"
                else "\nColor rule: the design is sold only as shown. Do not write "
                "about colors being selectable, color palettes, or color schemes."
            )
        )
        response = self.generate_json([{"text": prompt}], MARKETING_TEXTS_SCHEMA)
        bullets = [
            clean_feature_bullet(required_text(response, key))
            for key in FEATURE_BULLET_KEYS
        ]
        return MarketingTexts(
            marketing_copy=clean_marketing_copy(
                required_text(response, "marketing_copy")
            ),
            feature_bullet_1=bullets[0],
            feature_bullet_2=bullets[1],
            feature_bullet_3=bullets[2],
            feature_bullet_4=bullets[3],
            feature_bullet_5=bullets[4],
            feature_bullet_6=bullets[5],
            feature_bullet_7=bullets[6],
            feature_bullet_8=bullets[7],
        )

    def generate_json(
        self,
        parts: list[types.Part | dict[str, str]],
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Call Gemini with a JSON schema and parse the returned object."""

        if self.client is None:
            raise GeminiUserError(
                "Gemini API key is not configured.",
                "AI generation is not configured. Please contact the administrator.",
            )

        contents: Any = [
            part.get("text", "") if isinstance(part, dict) else part for part in parts
        ]
        models = list(dict.fromkeys([self.model, self.fallback_model]))
        for index, model in enumerate(models):
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_json_schema=response_schema,
                        thinking_config=thinking_config_for_model(model),
                    ),
                )
            except errors.APIError as exc:
                # Overloaded (5xx) or rate-limited (429) models can fail even after
                # retries; quotas and capacity are per model, so try the fallback.
                is_unavailable = isinstance(exc.code, int) and (
                    exc.code == 429 or exc.code >= 500
                )
                if is_unavailable and index < len(models) - 1:
                    continue
                raise gemini_api_error(exc) from exc
            except httpx.TimeoutException as exc:
                if index < len(models) - 1:
                    continue
                raise GeminiUserError(
                    "Gemini API request timed out.",
                    "AI service is temporarily unavailable. Try again later.",
                ) from exc
            except (OSError, URLError) as exc:
                raise GeminiUserError(
                    "Gemini API request failed.",
                    "AI service is temporarily unavailable. Try again later.",
                ) from exc
            return parse_json_object(extract_response_text(response))

        raise AssertionError("unreachable: the model loop always returns or raises")

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
        result = shrink_image_for_model(
            image_bytes, guess_image_mime_type(normalized_url, content_type)
        )
        self._image_cache[normalized_url] = result
        return result


def thinking_config_for_model(model: str) -> types.ThinkingConfig | None:
    """Return the fastest thinking setting each model generation supports."""

    name = model.removeprefix("models/")
    if name.startswith("gemini-2"):
        # Gemini 2.x uses thinking budgets; only Flash models can turn it off.
        return types.ThinkingConfig(thinking_budget=0) if "flash" in name else None
    return types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW)


def shrink_image_for_model(image_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    """Downscale large images to a JPEG that is quick to upload to Gemini."""

    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            if (
                max(image.size) <= MAX_MODEL_IMAGE_SIDE_PX
                and len(image_bytes) <= MAX_MODEL_IMAGE_BYTES
            ):
                return image_bytes, mime_type
            image.thumbnail((MAX_MODEL_IMAGE_SIDE_PX, MAX_MODEL_IMAGE_SIDE_PX))
            rgba_image = image.convert("RGBA")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return image_bytes, mime_type

    # Flatten transparency onto white so JPEG does not turn it black.
    flattened = Image.new("RGB", rgba_image.size, "white")
    flattened.paste(rgba_image, mask=rgba_image.getchannel("A"))
    buffer = io.BytesIO()
    flattened.save(buffer, format="JPEG", quality=MODEL_IMAGE_JPEG_QUALITY)
    return buffer.getvalue(), "image/jpeg"


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
    words = cleaned.split()
    if len(words) <= MAX_MARKETING_COPY_WORDS:
        return cleaned

    truncated = " ".join(words[:MAX_MARKETING_COPY_WORDS])
    sentence_end = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
    if sentence_end >= len(truncated) // 2:
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


def benefit_guidance_for_print_type(
    print_type: str | None,
    has_color_variations: bool = False,
) -> str:
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
    color_facts = (
        "precision cut from solid-color vinyl; available in a wide palette of solid "
        "vinyl colors to match any decor"
        if has_color_variations
        else "printed in full color exactly as shown in the design"
    )
    return (
        "Approved decal facts: made from high-quality waterproof vinyl; "
        f"{color_facts}; suitable for smooth surfaces; easy DIY installation with "
        "transfer tape and step-by-step application; available in multiple sizes; "
        "clean decorative impact for walls and other smooth surfaces; shipped in a "
        "protective kraft mailing tube with caps to help protect the decal in transit."
    )


def keyword_suffix_for_print_type(print_type: str | None) -> str:
    """Return the expected keyword suffix for a print type."""

    return "Wallpapers" if print_type == "wallpapers" else "Wall Stickers"
