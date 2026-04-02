"""
extractor_epub.py — ePub Image Extraction
===========================================
Extracts images from .epub files using zipfile and lxml.

This file is PERMANENT — do not delete.
"""

from __future__ import annotations

import hashlib
import logging
import zipfile
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree  # type: ignore[no-redef]

if TYPE_CHECKING:
    from .config import AltTextConfig

from .client import ExtractedImage

log = logging.getLogger(__name__)

_XHTML_NS = "http://www.w3.org/1999/xhtml"

_MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
}


def extract_images(path: Path, config: "AltTextConfig") -> list[ExtractedImage]:
    """Extract images from an ePub file.

    Reads the OPF manifest to find content documents, then parses
    each XHTML file for <img> elements and extracts the referenced images.

    Args:
        path: Path to the .epub file.
        config: AltTextConfig controlling extraction behavior.

    Returns:
        List of ExtractedImage objects.
    """
    images: list[ExtractedImage] = []
    seen_hashes: set[str] = set()

    try:
        zf = zipfile.ZipFile(str(path), "r")
    except (zipfile.BadZipFile, FileNotFoundError) as exc:
        log.error("Failed to open epub %s: %s", path, exc)
        return []

    try:
        # Find OPF file via META-INF/container.xml
        opf_path = _find_opf_path(zf)
        if not opf_path:
            log.error("No OPF file found in %s", path)
            return []

        opf_dir = str(PurePosixPath(opf_path).parent)

        # Parse OPF to get content documents from spine
        try:
            opf_xml = zf.read(opf_path)
        except KeyError:
            return []

        opf_root = etree.fromstring(opf_xml)
        ns = {"opf": "http://www.idpf.org/2007/opf"}

        manifest = opf_root.find("opf:manifest", ns)
        spine = opf_root.find("opf:spine", ns)
        if manifest is None or spine is None:
            return []

        # Build id -> href map
        id_href: dict[str, str] = {}
        for item in manifest.findall("opf:item", ns):
            item_id = item.get("id", "")
            href = item.get("href", "")
            if item_id and href:
                id_href[item_id] = href

        img_idx = 0
        for ref in spine.findall("opf:itemref", ns):
            idref = ref.get("idref", "")
            href = id_href.get(idref, "")
            if not href:
                continue

            content_zip_path = f"{opf_dir}/{href}" if opf_dir else href
            # Normalize path
            content_zip_path = str(PurePosixPath(content_zip_path))

            try:
                content_xml = zf.read(content_zip_path)
            except KeyError:
                continue

            try:
                tree = etree.fromstring(content_xml)
            except (etree.XMLSyntaxError if hasattr(etree, 'XMLSyntaxError') else Exception):
                continue

            # Get surrounding text
            surrounding = _get_content_text(tree)

            # Find all <img> elements
            for img_elem in tree.iter(f"{{{_XHTML_NS}}}img"):
                src = img_elem.get("src", "")
                alt = img_elem.get("alt")

                if not src:
                    continue

                # Skip if existing alt and configured
                if config.skip_existing_alt and alt and alt.strip():
                    continue

                # Resolve image path relative to the content document
                content_dir = str(PurePosixPath(content_zip_path).parent)
                img_zip_path = str(PurePosixPath(content_dir) / src)

                try:
                    image_bytes = zf.read(img_zip_path)
                except KeyError:
                    # Try relative to OPF dir
                    try:
                        image_bytes = zf.read(f"{opf_dir}/{src}" if opf_dir else src)
                    except KeyError:
                        continue

                if not image_bytes:
                    continue

                # Skip duplicates
                if config.skip_duplicate_images:
                    img_hash = hashlib.md5(image_bytes).hexdigest()
                    if img_hash in seen_hashes:
                        continue
                    seen_hashes.add(img_hash)

                ext = PurePosixPath(src).suffix.lower()
                mime_type = _MIME_MAP.get(ext, "image/png")

                images.append(ExtractedImage(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    page_number=None,
                    image_index=img_idx,
                    image_name=PurePosixPath(src).name,
                    existing_alt=alt if alt and alt.strip() else None,
                    surrounding_text=surrounding,
                    content_doc=href,
                    image_src=src,
                ))
                img_idx += 1
    finally:
        zf.close()

    return images


def _find_opf_path(zf: zipfile.ZipFile) -> str:
    """Find the OPF file path from META-INF/container.xml."""
    try:
        container_xml = zf.read("META-INF/container.xml")
        root = etree.fromstring(container_xml)
        ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
        rootfile = root.find(".//c:rootfile", ns)
        if rootfile is not None:
            return rootfile.get("full-path", "")
    except (KeyError, Exception):
        pass

    # Fallback: look for .opf files
    for name in zf.namelist():
        if name.endswith(".opf"):
            return name
    return ""


def _get_content_text(root) -> str:
    """Extract text content from an XHTML element tree."""
    parts: list[str] = []
    for elem in root.iter():
        if elem.text and elem.text.strip():
            parts.append(elem.text.strip())
        if elem.tail and elem.tail.strip():
            parts.append(elem.tail.strip())
    return " ".join(parts)[:500]
