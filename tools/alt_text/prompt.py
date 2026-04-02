"""
prompt.py — Layered Prompt Assembly
=====================================
Builds the system prompt for the vision LLM by assembling layers:
base instructions, profile, format context, language, audience, etc.

This file is PERMANENT — do not delete.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import AltTextConfig

# ---------------------------------------------------------------------------
# Base prompt (always included)
# ---------------------------------------------------------------------------

BASE_PROMPT = """\
You are an alternative-text specialist following WCAG 2.2 guidelines.
Analyze the attached image and return ONLY the following two HTML blocks, \
with no other text before, after, or between them:

BLOCK 1 -- a self-closing img tag:
<img src="" alt="{concise alt text}" />

BLOCK 2 -- a figure with figcaption:
<figure>
  <img src="" alt="{same concise alt text}" aria-describedby="img-desc" />
  <figcaption id="img-desc">{detailed description, 2-4 sentences}</figcaption>
</figure>

Rules:
- Describe what the image communicates, not just what it looks like.
- Never start the alt text with "Image of" or "Picture of".
- For images of text, reproduce the text.
- For charts/graphs, describe the key data trend.
- For decorative images, set alt="" and note "decorative" in the figcaption.
"""

# ---------------------------------------------------------------------------
# Format context templates
# ---------------------------------------------------------------------------

_FORMAT_CONTEXT = {
    "pdf": (
        'This image appears on page {page_number} of the PDF document.\n'
        'Surrounding text: "{surrounding_text}"\n'
        'Current alt text in PDF structure tree: "{existing_alt}"'
    ),
    "docx": (
        'This image ("{image_name}") is in a Word document (.docx).\n'
        'It appears near the following paragraph text: "{surrounding_text}"\n'
        'Current alt text (descr attribute): "{existing_alt}"'
    ),
    "xlsx": (
        'This image is on sheet "{sheet_name}" of an Excel workbook (.xlsx).\n'
        'Nearby cell values: "{surrounding_text}"\n'
        'Current description: "{existing_alt}"'
    ),
    "pptx": (
        'This image ("{image_name}") is on slide {page_number} '
        'of a PowerPoint presentation.\n'
        'Other text on this slide: "{surrounding_text}"\n'
        'Current alt text (descr attribute): "{existing_alt}"'
    ),
    "epub": (
        'This image (src="{image_name}") is in an ePub content document.\n'
        'Surrounding paragraph text: "{surrounding_text}"\n'
        'Current alt attribute: "{existing_alt}"'
    ),
}


def build_prompt(
    profile_prompt: str,
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
) -> str:
    """Assemble the full system prompt from layers.

    Args:
        profile_prompt: The profile-specific instruction text.
        source_format: Document format (pdf, docx, xlsx, pptx, epub).
        page_number: Page/slide/sheet number (1-based).
        image_name: Name identifier for the image.
        surrounding_text: Text near the image in the document.
        existing_alt: Current alt text if any.
        sheet_name: Sheet name (xlsx only).
        language: BCP 47 language tag.
        audience: Target audience description.
        style_guide: Freeform style instructions.
        max_alt_length: Max chars for concise alt text.
        context: Document-level context string.

    Returns:
        Complete system prompt string.
    """
    parts = [BASE_PROMPT]

    # Profile instructions
    if profile_prompt:
        parts.append(f"\nProfile instructions:\n{profile_prompt}")

    # Document context
    if context:
        parts.append(f"\nDocument context: {context}")

    # Format-specific context
    if source_format and source_format in _FORMAT_CONTEXT:
        template = _FORMAT_CONTEXT[source_format]
        fmt_text = template.format(
            page_number=page_number or "?",
            image_name=image_name or "unknown",
            surrounding_text=(surrounding_text or "")[:500],
            existing_alt=existing_alt or "none",
            sheet_name=sheet_name or "?",
        )
        parts.append(f"\nCONTEXT:\n{fmt_text}")

    # Language directive
    if language and language.lower() != "en":
        parts.append(f"\nWrite the alt text in {language}.")

    # Audience
    if audience:
        parts.append(
            f"\nThe target audience for this document is: {audience}. "
            "Adjust vocabulary, complexity, and assumed knowledge accordingly."
        )

    # Style guide
    if style_guide:
        parts.append(
            f"\nAdditional style rules from the organization's guidelines:\n"
            f"{style_guide}"
        )

    # Max length
    parts.append(f"\nKeep the concise alt text under {max_alt_length} characters.")

    return "\n".join(parts)
