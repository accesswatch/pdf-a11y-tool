"""
formats.py — Output Format Adapters
======================================
Wraps parsed alt text into the requested output format.

This file is PERMANENT — do not delete.
"""

from __future__ import annotations
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .parser import AltTextResult


def format_native(concise: str, detailed: str, **kwargs) -> dict:
    """Format for direct write-back into the source document.

    kwargs may include: source_format, xref, image_name, sheet_name,
    slide_number, shape_name, content_doc, image_src, etc.
    """
    fmt = kwargs.get("source_format", "")
    base = {"concise_alt": concise, "detailed_description": detailed}

    if fmt == "pdf":
        base["alt"] = concise
        base["actual_text"] = detailed
        if "xref" in kwargs:
            base["xref"] = kwargs["xref"]
    elif fmt == "docx":
        base["descr"] = concise
        if "image_name" in kwargs:
            base["docPr_name"] = kwargs["image_name"]
    elif fmt == "xlsx":
        base["descr"] = concise
        if "sheet_name" in kwargs:
            base["sheet"] = kwargs["sheet_name"]
        if "image_index" in kwargs:
            base["image_index"] = kwargs["image_index"]
    elif fmt == "pptx":
        base["descr"] = concise
        if "slide_number" in kwargs:
            base["slide"] = kwargs["slide_number"]
        if "shape_name" in kwargs:
            base["shape_name"] = kwargs["shape_name"]
    elif fmt == "epub":
        base["alt"] = concise
        if "content_doc" in kwargs:
            base["content_doc"] = kwargs["content_doc"]
        if "image_src" in kwargs:
            base["src"] = kwargs["image_src"]

    return base


def format_html(concise: str, detailed: str, **kwargs) -> str:
    """Return <img> and <figure> HTML tags."""
    img = f'<img src="" alt="{_escape_attr(concise)}" />'
    figure = (
        f'<figure>\n'
        f'  <img src="" alt="{_escape_attr(concise)}" '
        f'aria-describedby="img-desc" />\n'
        f'  <figcaption id="img-desc">{_escape_html(detailed)}</figcaption>\n'
        f'</figure>'
    )
    return f"{img}\n\n{figure}"


def format_markdown(concise: str, detailed: str, **kwargs) -> str:
    """Return markdown image syntax with blockquote description."""
    md_img = f"![{concise}]()"
    md_desc = f"> {detailed}" if detailed else ""
    return f"{md_img}\n\n{md_desc}" if md_desc else md_img


def format_json(concise: str, detailed: str, **kwargs) -> str:
    """Return full JSON object."""
    return json.dumps({
        "concise_alt": concise,
        "detailed_description": detailed,
        "model": kwargs.get("model", ""),
        "profile": kwargs.get("profile", "auto"),
        "page_number": kwargs.get("page_number"),
        "image_index": kwargs.get("image_index", 0),
    }, indent=2)


def format_plain(concise: str, detailed: str, **kwargs) -> str:
    """Return plain text: concise + detailed."""
    parts = [f"Alt: {concise}"]
    if detailed:
        parts.append(f"Description: {detailed}")
    return "\n".join(parts)


def format_pdf_tag(concise: str, detailed: str, **kwargs) -> dict:
    """Return dict for PDF/UA tag writing."""
    return {"alt": concise, "actual_text": detailed}


def format_docx_tag(concise: str, detailed: str, **kwargs) -> dict:
    """Return dict matching OOXML descr attribute format."""
    return {"descr": concise}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _escape_attr(text: str) -> str:
    """Escape for use in HTML attribute values."""
    return (text
            .replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _escape_html(text: str) -> str:
    """Escape for use in HTML text content."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


# ---------------------------------------------------------------------------
# Adapter dispatch
# ---------------------------------------------------------------------------

FORMAT_ADAPTERS = {
    "native": format_native,
    "html": format_html,
    "markdown": format_markdown,
    "json": format_json,
    "plain": format_plain,
    "pdf-tag": format_pdf_tag,
    "docx": format_docx_tag,
}


def apply_format(fmt: str, concise: str, detailed: str, **kwargs):
    """Apply the requested output format adapter."""
    adapter = FORMAT_ADAPTERS.get(fmt)
    if adapter is None:
        valid = ", ".join(FORMAT_ADAPTERS.keys())
        raise ValueError(f"Unknown output format '{fmt}'. Valid formats: {valid}")
    return adapter(concise, detailed, **kwargs)
