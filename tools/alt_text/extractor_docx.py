"""
extractor_docx.py — Word Document Image Extraction
====================================================
Extracts images from .docx files using python-docx and zipfile.

This file is PERMANENT — do not delete.
"""

from __future__ import annotations

import hashlib
import logging
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree  # type: ignore[no-redef]

if TYPE_CHECKING:
    from .config import AltTextConfig

from .client import ExtractedImage

log = logging.getLogger(__name__)

_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
}

_MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".emf": "image/x-emf",
    ".wmf": "image/x-wmf",
    ".svg": "image/svg+xml",
}


def extract_images(path: Path, config: "AltTextConfig") -> list[ExtractedImage]:
    """Extract images from a Word document.

    Args:
        path: Path to the .docx file.
        config: AltTextConfig controlling extraction behavior.

    Returns:
        List of ExtractedImage objects.
    """
    images: list[ExtractedImage] = []
    seen_hashes: set[str] = set()

    try:
        zf = zipfile.ZipFile(str(path), "r")
    except (zipfile.BadZipFile, FileNotFoundError) as exc:
        log.error("Failed to open docx %s: %s", path, exc)
        return []

    try:
        # Parse relationships to map rId -> target
        rel_map = _parse_relationships(zf)

        # Parse document.xml
        try:
            doc_xml = zf.read("word/document.xml")
        except KeyError:
            log.error("No word/document.xml in %s", path)
            return []

        root = etree.fromstring(doc_xml)
        body = root.find(f"{{{_NS['w']}}}body")
        if body is None:
            return []

        img_idx = 0
        drawings = body.iter(f"{{{_NS['w']}}}drawing")
        for drawing in drawings:
            for docPr in drawing.iter(f"{{{_NS['wp']}}}docPr"):
                name = docPr.get("name", "Image")
                descr = docPr.get("descr", "").strip()

                # Find the image relationship ID
                blip = drawing.find(f".//{{{_NS['a']}}}blip")
                if blip is None:
                    continue
                r_embed = blip.get(f"{{{_NS['r']}}}embed", "")
                if not r_embed:
                    continue

                target = rel_map.get(r_embed, "")
                if not target:
                    continue

                # Read image bytes from zip
                img_path = f"word/{target}" if not target.startswith("word/") else target
                try:
                    image_bytes = zf.read(img_path)
                except KeyError:
                    # Try without word/ prefix
                    try:
                        image_bytes = zf.read(target)
                    except KeyError:
                        continue

                # Determine MIME type
                ext = Path(target).suffix.lower()
                mime_type = _MIME_MAP.get(ext, "image/png")

                # Skip duplicates
                if config.skip_duplicate_images:
                    img_hash = hashlib.md5(image_bytes).hexdigest()
                    if img_hash in seen_hashes:
                        continue
                    seen_hashes.add(img_hash)

                # Skip if existing alt and configured to skip
                if config.skip_existing_alt and descr:
                    continue

                # Get surrounding text
                surrounding = _get_surrounding_text(drawing)

                images.append(ExtractedImage(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    page_number=None,
                    image_index=img_idx,
                    image_name=name,
                    existing_alt=descr if descr else None,
                    surrounding_text=surrounding,
                ))
                img_idx += 1
    finally:
        zf.close()

    return images


def _parse_relationships(zf: zipfile.ZipFile) -> dict[str, str]:
    """Parse word/_rels/document.xml.rels to get rId -> target mapping."""
    rel_map: dict[str, str] = {}
    try:
        rels_xml = zf.read("word/_rels/document.xml.rels")
        root = etree.fromstring(rels_xml)
        for rel in root:
            rid = rel.get("Id", "")
            target = rel.get("Target", "")
            if rid and target:
                rel_map[rid] = target
    except (KeyError, etree.XMLSyntaxError if hasattr(etree, 'XMLSyntaxError') else Exception):
        pass
    return rel_map


def _get_surrounding_text(drawing_elem) -> str:
    """Get text from sibling paragraphs near the drawing."""
    parts: list[str] = []
    parent = drawing_elem.getparent() if hasattr(drawing_elem, 'getparent') else None
    if parent is None:
        return ""

    # Get text from the containing paragraph
    for t in parent.iter(f"{{{_NS['w']}}}t"):
        text = t.text
        if text:
            parts.append(text)

    # Get text from previous and next siblings
    grandparent = parent.getparent() if hasattr(parent, 'getparent') else None
    if grandparent is not None:
        children = list(grandparent)
        try:
            idx = children.index(parent)
        except ValueError:
            return " ".join(parts)[:500]

        for offset in (-1, 1):
            sibling_idx = idx + offset
            if 0 <= sibling_idx < len(children):
                for t in children[sibling_idx].iter(f"{{{_NS['w']}}}t"):
                    text = t.text
                    if text:
                        parts.append(text)

    return " ".join(parts)[:500]
