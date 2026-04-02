"""
extractor_xlsx.py — Excel Workbook Image Extraction
=====================================================
Extracts images from .xlsx files using openpyxl.

This file is PERMANENT — do not delete.
"""

from __future__ import annotations

import hashlib
import io
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import AltTextConfig

from .client import ExtractedImage

log = logging.getLogger(__name__)


def extract_images(path: Path, config: "AltTextConfig") -> list[ExtractedImage]:
    """Extract images from an Excel workbook.

    Args:
        path: Path to the .xlsx file.
        config: AltTextConfig controlling extraction behavior.

    Returns:
        List of ExtractedImage objects.
    """
    try:
        import openpyxl
    except ImportError:
        log.warning("openpyxl not installed — cannot extract Excel images")
        return []

    images: list[ExtractedImage] = []
    seen_hashes: set[str] = set()

    try:
        wb = openpyxl.load_workbook(str(path), data_only=True)
    except Exception as exc:
        log.error("Failed to open xlsx %s: %s", path, exc)
        return []

    try:
        img_idx = 0
        for ws in wb.worksheets:
            sheet_name = ws.title

            for img_obj in ws._images:
                name = getattr(img_obj, "name", None) or f"Image_{img_idx}"
                desc = getattr(img_obj, "desc", None) or ""

                # Skip if existing alt and configured
                if config.skip_existing_alt and desc.strip():
                    continue

                # Get image bytes
                try:
                    if hasattr(img_obj, "_data"):
                        image_bytes = img_obj._data()
                    elif hasattr(img_obj, "ref"):
                        image_bytes = img_obj.ref.getvalue() if hasattr(img_obj.ref, 'getvalue') else img_obj.ref.read()
                    else:
                        continue
                except Exception:
                    continue

                if not image_bytes:
                    continue

                # Skip duplicates
                if config.skip_duplicate_images:
                    img_hash = hashlib.md5(image_bytes).hexdigest()
                    if img_hash in seen_hashes:
                        continue
                    seen_hashes.add(img_hash)

                # Determine MIME type from image header
                mime_type = _detect_mime(image_bytes)

                # Get surrounding cell values
                surrounding = _get_nearby_cells(ws)

                images.append(ExtractedImage(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    page_number=None,
                    image_index=img_idx,
                    image_name=name,
                    existing_alt=desc.strip() if desc.strip() else None,
                    surrounding_text=surrounding,
                    sheet_name=sheet_name,
                ))
                img_idx += 1
    finally:
        wb.close()

    return images


def _detect_mime(data: bytes) -> str:
    """Detect image MIME type from magic bytes."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if data[:4] == b"GIF8":
        return "image/gif"
    if data[:2] in (b"BM",):
        return "image/bmp"
    return "image/png"  # default fallback


def _get_nearby_cells(ws, max_cells: int = 20) -> str:
    """Get string values from the first cells in the worksheet."""
    parts: list[str] = []
    count = 0
    for row in ws.iter_rows(min_row=1, max_row=10, max_col=10, values_only=True):
        for val in row:
            if val is not None:
                parts.append(str(val))
                count += 1
                if count >= max_cells:
                    return " | ".join(parts)[:500]
    return " | ".join(parts)[:500]
