"""
client.py — GitHub Models API Client
======================================
HTTP client for calling vision-capable LLMs via the GitHub Models API.
Handles auth, rate limits, retries, and request assembly.

This file is PERMANENT — do not delete.
"""

from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from .auth import get_github_token
from .models import DEFAULT_MODEL, validate_models
from .parser import (
    AltTextReport,
    AltTextResult,
    ImageAltTextOptions,
    ModelError,
    ParseError,
    parse_response,
)
from .profiles import resolve_profile
from .prompt import build_prompt

if TYPE_CHECKING:
    from .config import AltTextConfig

log = logging.getLogger(__name__)

API_URL = "https://models.github.ai/inference/chat/completions"
REQUEST_TIMEOUT = 60
MAX_RETRIES = 2
RETRY_DELAY = 2  # seconds


# ---------------------------------------------------------------------------
# Dataclass for extracted images (shared across extractors)
# ---------------------------------------------------------------------------

@dataclass
class ExtractedImage:
    """An image extracted from a document for alt text generation."""
    image_bytes: bytes
    mime_type: str  # "image/png", "image/jpeg", etc.
    page_number: int | None = None
    image_index: int = 0
    image_name: str = ""
    existing_alt: str | None = None
    surrounding_text: str = ""
    sheet_name: str = ""
    slide_number: int | None = None
    shape_name: str = ""
    content_doc: str = ""
    image_src: str = ""
    xref: int | None = None  # PDF only


# ---------------------------------------------------------------------------
# Single image generation
# ---------------------------------------------------------------------------

def generate_for_image(
    image_bytes: bytes,
    mime_type: str = "image/png",
    model: str = DEFAULT_MODEL,
    profile: str = "auto",
    source_format: str = "",
    page_number: int | None = None,
    image_name: str = "",
    surrounding_text: str = "",
    existing_alt: str = "",
    sheet_name: str = "",
    language: str = "en",
    audience: str = "",
    style_guide: str = "",
    max_alt_length: int = 125,
    context: str = "",
    custom_profiles: dict | None = None,
) -> AltTextResult:
    """Generate alt text for a single image.

    Args:
        image_bytes: Raw bytes of the image.
        mime_type: MIME type (image/png, image/jpeg, etc.).
        model: Model identifier from the registry.
        All other args: forwarded to prompt builder and result.

    Returns:
        AltTextResult with concise and detailed alt text.

    Raises:
        AuthError: No GitHub token available.
        ModelNotAllowedError: Invalid model ID.
        ParseError: LLM response could not be parsed.
        httpx.HTTPStatusError: API returned an error.
    """
    validate_models([model])
    token = get_github_token()

    profile_def = resolve_profile(profile, custom_profiles)
    system_prompt = build_prompt(
        profile_prompt=profile_def["prompt"],
        source_format=source_format,
        page_number=page_number,
        image_name=image_name,
        surrounding_text=surrounding_text,
        existing_alt=existing_alt,
        sheet_name=sheet_name,
        language=language,
        audience=audience,
        style_guide=style_guide,
        max_alt_length=max_alt_length,
        context=context,
    )

    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_uri = f"data:{mime_type};base64,{b64}"

    raw = _call_api(token, model, system_prompt, data_uri)
    concise, detailed = parse_response(raw)

    return AltTextResult(
        concise_alt=concise,
        detailed_description=detailed,
        model=model,
        profile=profile,
        page_number=page_number,
        image_index=0,
        existing_alt=existing_alt,
        source_format=source_format,
        location=image_name,
    )


# ---------------------------------------------------------------------------
# Document-level generation
# ---------------------------------------------------------------------------

def generate_for_document(
    file_path: str | Path,
    config: AltTextConfig | None = None,
    models: list[str] | None = None,
    profile: str | None = None,
) -> AltTextReport:
    """Generate alt text for all images in a document.

    Auto-detects format from extension, extracts images, and generates
    alt text using each requested model.

    Args:
        file_path: Path to the document.
        config: Optional AltTextConfig. Auto-loaded if None.
        models: Override models list. Falls back to config.models.
        profile: Override profile name. Falls back to config.profile.

    Returns:
        AltTextReport with alt text options for each image.
    """
    from .config import AltTextConfig, load_config

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    if config is None:
        config = load_config()

    use_models = validate_models(models or config.models)
    use_profile = profile or config.profile

    # Detect format and extract
    ext = file_path.suffix.lower().lstrip(".")
    format_map = {
        "pdf": ("pdf", _extract_pdf),
        "docx": ("docx", _extract_docx),
        "xlsx": ("xlsx", _extract_xlsx),
        "pptx": ("pptx", _extract_pptx),
        "epub": ("epub", _extract_epub),
    }

    if ext not in format_map:
        raise ValueError(
            f"Unsupported format: .{ext}. "
            f"Supported: {', '.join('.' + k for k in format_map)}"
        )

    source_format, extract_fn = format_map[ext]
    images = extract_fn(file_path, config)

    report = AltTextReport(
        file_path=str(file_path),
        source_format=source_format,
        total_images=len(images),
    )

    if not images:
        return report

    token = get_github_token()

    for img in images:
        img_options = ImageAltTextOptions(
            page_number=img.page_number,
            image_index=img.image_index,
            location=img.image_name or img.image_src or f"image_{img.image_index}",
            existing_alt=img.existing_alt,
            profile_used=use_profile,
        )

        profile_def = resolve_profile(use_profile, config.custom_profiles)
        system_prompt = build_prompt(
            profile_prompt=profile_def["prompt"],
            source_format=source_format,
            page_number=img.page_number or img.slide_number,
            image_name=img.image_name,
            surrounding_text=img.surrounding_text,
            existing_alt=img.existing_alt or "",
            sheet_name=img.sheet_name,
            language=config.language,
            audience=config.audience,
            style_guide=config.style_guide,
            max_alt_length=config.max_alt_length,
            context=config.context,
        )

        b64 = base64.b64encode(img.image_bytes).decode("ascii")
        data_uri = f"data:{img.mime_type};base64,{b64}"

        for model in use_models:
            try:
                raw = _call_api(token, model, system_prompt, data_uri)
                concise, detailed = parse_response(raw)
                img_options.options.append(AltTextResult(
                    concise_alt=concise,
                    detailed_description=detailed,
                    model=model,
                    profile=use_profile,
                    page_number=img.page_number,
                    image_index=img.image_index,
                    existing_alt=img.existing_alt,
                    source_format=source_format,
                    location=img_options.location,
                ))
            except ParseError as exc:
                img_options.errors.append(ModelError(
                    model=model,
                    error_type="parse",
                    message=str(exc),
                ))
            except httpx.HTTPStatusError as exc:
                error_type = "rate_limit" if exc.response.status_code == 429 else "api"
                img_options.errors.append(ModelError(
                    model=model,
                    error_type=error_type,
                    message=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                ))
            except Exception as exc:
                img_options.errors.append(ModelError(
                    model=model,
                    error_type="api",
                    message=str(exc),
                ))

        report.images.append(img_options)

    return report


# ---------------------------------------------------------------------------
# API call with retry
# ---------------------------------------------------------------------------

def _call_api(token: str, model: str, system_prompt: str, data_uri: str) -> str:
    """Call the GitHub Models API and return the raw response text."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_uri},
                    }
                ],
            },
        ],
        "max_tokens": 800,
    }

    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
                resp = client.post(API_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code == 429 and attempt < MAX_RETRIES:
                retry_after = int(
                    exc.response.headers.get("Retry-After", RETRY_DELAY)
                )
                log.warning(
                    "Rate limited (429), retrying in %ds (attempt %d/%d)",
                    retry_after, attempt + 1, MAX_RETRIES,
                )
                time.sleep(min(retry_after, 30))
                continue
            raise
        except httpx.TimeoutException as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                log.warning(
                    "Timeout, retrying in %ds (attempt %d/%d)",
                    RETRY_DELAY, attempt + 1, MAX_RETRIES,
                )
                time.sleep(RETRY_DELAY)
                continue
            raise

    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Extractor dispatch (lazy imports)
# ---------------------------------------------------------------------------

def _extract_pdf(path: Path, config: AltTextConfig) -> list[ExtractedImage]:
    from .extractor_pdf import extract_images
    return extract_images(path, config)


def _extract_docx(path: Path, config: AltTextConfig) -> list[ExtractedImage]:
    from .extractor_docx import extract_images
    return extract_images(path, config)


def _extract_xlsx(path: Path, config: AltTextConfig) -> list[ExtractedImage]:
    from .extractor_xlsx import extract_images
    return extract_images(path, config)


def _extract_pptx(path: Path, config: AltTextConfig) -> list[ExtractedImage]:
    from .extractor_pptx import extract_images
    return extract_images(path, config)


def _extract_epub(path: Path, config: AltTextConfig) -> list[ExtractedImage]:
    from .extractor_epub import extract_images
    return extract_images(path, config)
