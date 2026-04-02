"""
extractor_pdf.py — PDF Image Extraction
=========================================
Extracts images from PDF files using PyMuPDF (fitz).

This file is PERMANENT — do not delete.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import AltTextConfig

from .client import ExtractedImage

log = logging.getLogger(__name__)

# MIME mapping from PyMuPDF image extension
_MIME_MAP = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "jpx": "image/jp2",
    "tiff": "image/tiff",
    "tif": "image/tiff",
    "bmp": "image/bmp",
    "jbig2": "image/x-jbig2",
    "pam": "image/x-portable-anymap",
}


def extract_images(path: Path, config: "AltTextConfig") -> list[ExtractedImage]:
    """Extract images from a PDF file.

    Requires PyMuPDF (fitz). Returns ExtractedImage objects with
    page number, xref, surrounding text, and existing alt text.

    Args:
        path: Path to the PDF file.
        config: AltTextConfig controlling min size, dedup, etc.

    Returns:
        List of ExtractedImage objects.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        log.warning("PyMuPDF not installed — cannot extract PDF images. pip install PyMuPDF")
        return []

    images: list[ExtractedImage] = []
    seen_hashes: set[str] = set()

    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        log.error("Failed to open PDF %s: %s", path, exc)
        return []

    # Pre-load figure alt texts from the structure tree via pikepdf
    figure_alts = _get_figure_alts_from_structure_tree(path)
    page_alt_queues: dict[int, list[str]] = {}
    unassigned_alts: list[str] = []
    for pg, alt in figure_alts:
        if pg is not None:
            page_alt_queues.setdefault(pg, []).append(alt)
        else:
            unassigned_alts.append(alt)

    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            surrounding_text = page.get_text("text")[:500]

            # Alt texts for this page, matched sequentially to images
            alt_queue = list(page_alt_queues.get(page_num, []))

            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]

                try:
                    base_image = doc.extract_image(xref)
                except Exception:
                    continue

                if not base_image or not base_image.get("image"):
                    continue

                image_bytes = base_image["image"]
                ext = base_image.get("ext", "png")
                width = base_image.get("width", 0)
                height = base_image.get("height", 0)

                # Skip tiny images (likely decorative)
                if width < config.min_image_size or height < config.min_image_size:
                    continue

                # Skip duplicates
                if config.skip_duplicate_images:
                    img_hash = hashlib.md5(image_bytes).hexdigest()
                    if img_hash in seen_hashes:
                        continue
                    seen_hashes.add(img_hash)

                mime_type = _MIME_MAP.get(ext, "image/png")

                # Match alt text: page-specific queue first, then unassigned
                existing_alt = None
                if img_idx < len(alt_queue):
                    existing_alt = alt_queue[img_idx]
                elif unassigned_alts:
                    existing_alt = unassigned_alts.pop(0)

                # Skip images with existing alt if configured
                if config.skip_existing_alt and existing_alt:
                    continue

                images.append(ExtractedImage(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    page_number=page_num + 1,
                    image_index=img_idx,
                    image_name=f"page{page_num + 1}_img{img_idx}",
                    existing_alt=existing_alt,
                    surrounding_text=surrounding_text,
                    xref=xref,
                ))
    finally:
        doc.close()

    return images


def _get_figure_alts_from_structure_tree(path: Path) -> list[tuple[int | None, str]]:
    """Use pikepdf to read /Alt texts from Figure elements in the structure tree.

    Returns [(page_0based_or_None, alt_text), ...] in tree traversal order.
    """
    try:
        import pikepdf
    except ImportError:
        return []

    results: list[tuple[int | None, str]] = []
    try:
        with pikepdf.open(str(path)) as pdf:
            struct_tree = pdf.Root.get("/StructTreeRoot")
            if not struct_tree:
                return []

            # Map page object numbers to 0-based page indices
            page_obj_map: dict[tuple, int] = {}
            for i, page in enumerate(pdf.pages):
                try:
                    page_obj_map[page.obj.objgen] = i
                except Exception:
                    pass

            def _resolve_page(node: pikepdf.Dictionary) -> int | None:
                """Determine the page number for a structure element."""
                # Check /Pg on the element itself
                pg = node.get("/Pg")
                if pg is not None:
                    try:
                        return page_obj_map.get(pg.objgen)
                    except Exception:
                        pass
                # Check /K children for /Pg (MCR or OBJR dicts)
                kids = node.get("/K")
                if kids is not None:
                    items = kids if isinstance(kids, pikepdf.Array) else [kids]
                    for k in items:
                        try:
                            if isinstance(k, pikepdf.Dictionary):
                                cpg = k.get("/Pg")
                                if cpg is not None:
                                    return page_obj_map.get(cpg.objgen)
                        except Exception:
                            pass
                return None

            def _walk(node) -> None:
                if isinstance(node, pikepdf.Array):
                    for item in node:
                        try:
                            _walk(item)
                        except Exception:
                            pass
                    return
                if not isinstance(node, pikepdf.Dictionary):
                    return

                s_type = str(node.get("/S", ""))
                if s_type in ("/Figure", "Figure"):
                    raw_alt = node.get("/Alt")
                    if raw_alt is not None:
                        alt_text = str(raw_alt).strip().rstrip("\x00")
                        if alt_text:
                            page_num = _resolve_page(node)
                            results.append((page_num, alt_text))

                # Recurse into /K children
                kids = node.get("/K")
                if kids is not None:
                    if isinstance(kids, pikepdf.Array):
                        for kid in kids:
                            try:
                                _walk(kid)
                            except Exception:
                                pass
                    elif isinstance(kids, pikepdf.Dictionary):
                        _walk(kids)

            _walk(struct_tree)
    except Exception as exc:
        log.debug("Failed to read structure tree for alt text: %s", exc)

    return results
