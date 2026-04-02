"""
parser.py — LLM Response Parser
==================================
Parses the HTML response from the vision LLM into structured data.

This file is PERMANENT — do not delete.
"""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser


class ParseError(RuntimeError):
    """Raised when the LLM response cannot be parsed."""
    def __init__(self, message: str, raw_response: str = ""):
        super().__init__(message)
        self.raw_response = raw_response


@dataclass
class AltTextResult:
    """Parsed alt text result from a single model."""
    concise_alt: str
    detailed_description: str
    model: str = ""
    profile: str = "auto"
    page_number: int | None = None
    image_index: int = 0
    existing_alt: str | None = None
    source_format: str = ""
    location: str = ""


@dataclass
class ModelError:
    """Records a model that failed during generation."""
    model: str
    error_type: str   # "rate_limit", "auth", "parse", "timeout", "api"
    message: str


@dataclass
class ImageAltTextOptions:
    """Alt text options for a single image (one per model)."""
    page_number: int | None
    image_index: int
    location: str
    existing_alt: str | None
    profile_used: str
    options: list[AltTextResult] = field(default_factory=list)
    errors: list[ModelError] = field(default_factory=list)


@dataclass
class AltTextReport:
    """Full report for a document's images."""
    file_path: str
    source_format: str
    total_images: int
    images: list[ImageAltTextOptions] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# HTML parser
# ---------------------------------------------------------------------------

class _AltExtractor(HTMLParser):
    """Extract alt attribute from <img> and text from <figcaption>."""

    def __init__(self):
        super().__init__()
        self.alt_text: str | None = None
        self.figcaption_text: str | None = None
        self._in_figcaption = False
        self._figcaption_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag == "img" and self.alt_text is None:
            self.alt_text = attr_dict.get("alt", "")
        if tag == "figcaption":
            self._in_figcaption = True
            self._figcaption_parts = []

    def handle_endtag(self, tag):
        if tag == "figcaption" and self._in_figcaption:
            self._in_figcaption = False
            self.figcaption_text = " ".join(self._figcaption_parts).strip()

    def handle_data(self, data):
        if self._in_figcaption:
            self._figcaption_parts.append(data)


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences wrapping HTML."""
    text = text.strip()
    # Remove ```html ... ``` or ``` ... ```
    pattern = r'^```(?:html)?\s*\n?(.*?)\n?\s*```$'
    match = re.match(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def parse_response(raw: str) -> tuple[str, str]:
    """Parse an LLM response into (concise_alt, detailed_description).

    Args:
        raw: Raw LLM response text.

    Returns:
        Tuple of (concise alt text, detailed description).

    Raises:
        ParseError: If no <img> tag is found.
    """
    cleaned = _strip_code_fences(raw)

    parser = _AltExtractor()
    parser.feed(cleaned)

    if parser.alt_text is None:
        raise ParseError(
            "Could not find <img> tag in LLM response.",
            raw_response=raw,
        )

    concise = parser.alt_text.strip()
    detailed = (parser.figcaption_text or "").strip()

    return concise, detailed
