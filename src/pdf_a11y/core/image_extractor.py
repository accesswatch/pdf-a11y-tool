"""Image discovery and thumbnail generation.

This module scans a PDF for image XObjects (inline and referenced), extracts
them as PIL Images for display in the Alt Text panel, and provides thumbnail
generation for the image browser.

Planned public API:
    PdfImage         -- Dataclass holding an image reference, page index,
                        bounding box, and current alt text from the tag tree.
    ImageExtractor   -- Scans all pages and returns a list[PdfImage].
    get_thumbnail(image, max_size) -> PIL.Image.Image
        -- Returns a thumbnail of the image scaled to max_size.
"""
from __future__ import annotations
