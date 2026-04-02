"""
fix_epub.py -- ePub Accessibility Auto-Fixer
=============================================
Applies deterministic accessibility fixes to .epub files:
  - Missing document title (dc:title)            [EPUB-E001]
  - Missing document language (dc:language)       [EPUB-E003]
  - Missing navigation document (nav.xhtml)       [EPUB-E004]
  - Missing image alt text placeholders           [EPUB-E005]
  - Spine integrity (duplicates, dangling refs)   [EPUB-E006]
  - Missing accessibility metadata (schema:*)     [EPUB-E007]
  - Heading hierarchy repair in content docs      [EPUB-W003]
  - Missing author metadata (dc:creator)          [EPUB-T002]

Always creates a backup and writes to a new -fixed.epub file.
Never overwrites the original.

Usage (standalone):
    python tools/fix_epub.py input.epub [--output fixed.epub] [--rules EPUB-E001,EPUB-E003]

Dependencies: lxml (pip install lxml)

This file is PERMANENT -- do not delete.
"""

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile, BadZipFile, ZIP_DEFLATED, ZIP_STORED

try:
    from lxml import etree
    HAS_LXML = True
except ImportError:
    HAS_LXML = False


# ---------------------------------------------------------------------------
# Namespace helpers
# ---------------------------------------------------------------------------

NS = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "epub": "http://www.idpf.org/2007/ops",
    "xhtml": "http://www.w3.org/1999/xhtml",
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
}

# Register namespaces to avoid lxml adding ns0, ns1 prefixes
for prefix, uri in NS.items():
    etree.register_namespace(prefix, uri)


def _find_opf_path(extract_dir: Path) -> tuple[Path | None, str]:
    """Read META-INF/container.xml to locate the OPF rootfile. Returns (path, relative_path)."""
    container_xml = extract_dir / "META-INF" / "container.xml"
    if not container_xml.exists():
        return None, ""
    tree = etree.parse(str(container_xml))
    rootfile = tree.find(".//container:rootfile", NS)
    if rootfile is None:
        return None, ""
    full_path = rootfile.get("full-path", "")
    if not full_path:
        return None, ""
    return extract_dir / full_path, full_path


# ---------------------------------------------------------------------------
# Fix functions
# ---------------------------------------------------------------------------

def _fix_title(opf_root: etree._Element, title: str = "") -> dict:
    """Set dc:title if missing."""
    existing = opf_root.find(".//dc:title", NS)
    if existing is not None and (existing.text or "").strip():
        return {"rule": "EPUB-E001", "status": "skipped", "reason": "Title already set"}

    metadata = opf_root.find("opf:metadata", NS)
    if metadata is None:
        return {"rule": "EPUB-E001", "status": "failed", "reason": "No metadata element in OPF"}

    new_title = title or "TODO: Add descriptive document title"
    if existing is not None:
        existing.text = new_title
    else:
        el = etree.SubElement(metadata, "{%s}title" % NS["dc"])
        el.text = new_title
    return {"rule": "EPUB-E001", "status": "fixed", "detail": f"Set dc:title to '{new_title}'"}


def _fix_language(opf_root: etree._Element, lang: str = "en") -> dict:
    """Set dc:language if missing."""
    existing = opf_root.find(".//dc:language", NS)
    if existing is not None and (existing.text or "").strip():
        return {"rule": "EPUB-E003", "status": "skipped", "reason": "Language already set"}

    metadata = opf_root.find("opf:metadata", NS)
    if metadata is None:
        return {"rule": "EPUB-E003", "status": "failed", "reason": "No metadata element in OPF"}

    if existing is not None:
        existing.text = lang
    else:
        el = etree.SubElement(metadata, "{%s}language" % NS["dc"])
        el.text = lang
    return {"rule": "EPUB-E003", "status": "fixed", "detail": f"Set dc:language to '{lang}'"}


def _fix_a11y_metadata(opf_root: etree._Element) -> list[dict]:
    """Add missing schema.org accessibility metadata (EPUB 3 only)."""
    version = opf_root.get("version", "3.0")
    if version.startswith("2"):
        return [{"rule": "EPUB-E007", "status": "skipped",
                 "reason": "EPUB 2 does not support schema: accessibility metadata"}]

    metadata = opf_root.find("opf:metadata", NS)
    if metadata is None:
        return [{"rule": "EPUB-E007", "status": "failed", "reason": "No metadata element in OPF"}]

    # Check which properties exist
    existing_props = set()
    for meta in metadata.findall("opf:meta", NS):
        prop = meta.get("property", "")
        if prop.startswith("schema:access"):
            existing_props.add(prop)

    required = {
        "schema:accessMode": "textual",
        "schema:accessibilityFeature": "structuralNavigation",
        "schema:accessibilitySummary": "TODO: Describe accessibility features and conformance level",
    }

    fixes = []
    for prop, default_val in required.items():
        if prop not in existing_props:
            el = etree.SubElement(metadata, "{%s}meta" % NS["opf"])
            el.set("property", prop)
            el.text = default_val
            fixes.append({"rule": "EPUB-E007", "status": "fixed",
                          "detail": f"Added {prop}={default_val}"})

    if not fixes:
        fixes.append({"rule": "EPUB-E007", "status": "skipped",
                       "reason": "All required accessibility metadata already present"})
    return fixes


def _fix_author(opf_root: etree._Element, author: str = "") -> dict:
    """Set dc:creator if missing."""
    existing = opf_root.find(".//dc:creator", NS)
    if existing is not None and (existing.text or "").strip():
        return {"rule": "EPUB-T002", "status": "skipped", "reason": "Author already set"}

    metadata = opf_root.find("opf:metadata", NS)
    if metadata is None:
        return {"rule": "EPUB-T002", "status": "failed", "reason": "No metadata element in OPF"}

    new_author = author or "TODO: Add author name"
    if existing is not None:
        existing.text = new_author
    else:
        el = etree.SubElement(metadata, "{%s}creator" % NS["dc"])
        el.text = new_author
    return {"rule": "EPUB-T002", "status": "fixed", "detail": f"Set dc:creator to '{new_author}'"}


def _fix_alt_text(extract_dir: Path, opf_root: etree._Element,
                  use_alt_text_generator: bool = False,
                  alt_text_models: list[str] | None = None,
                  alt_text_context: str = "",
                  epub_path: Path | None = None) -> list[dict]:
    """Add alt text to images missing alt attributes in content documents.

    When use_alt_text_generator is True, generates real alt text via
    the vision LLM. Otherwise, adds TODO placeholders.
    """
    manifest = opf_root.find("opf:manifest", NS)
    spine = opf_root.find("opf:spine", NS)
    if manifest is None or spine is None:
        return [{"rule": "EPUB-E005", "status": "failed",
                 "reason": "Could not locate manifest/spine in OPF"}]

    opf_dir = extract_dir
    # Find OPF directory by looking at container.xml
    opf_path_obj, opf_rel = _find_opf_path(extract_dir)
    if opf_path_obj:
        opf_dir = opf_path_obj.parent

    # Build id -> href map
    id_href = {}
    for item in manifest.findall("opf:item", NS):
        item_id = item.get("id", "")
        href = item.get("href", "")
        if item_id and href:
            id_href[item_id] = href

    fixes = []
    fixed_count = 0
    generated_count = 0
    for ref in spine.findall("opf:itemref", NS):
        idref = ref.get("idref", "")
        href = id_href.get(idref, "")
        if not href:
            continue
        content_path = opf_dir / href
        if not content_path.exists():
            continue

        try:
            tree = etree.parse(str(content_path))
        except etree.XMLSyntaxError:
            continue

        modified = False
        for img in tree.iter("{%s}img" % NS["xhtml"]):
            alt = img.get("alt")
            if alt is None:
                src = img.get("src", "image")

                generated_alt = None
                if use_alt_text_generator:
                    generated_alt = _generate_alt_for_epub_image(
                        opf_dir, content_path, src,
                        alt_text_models, alt_text_context,
                    )

                if generated_alt:
                    img.set("alt", generated_alt)
                    generated_count += 1
                else:
                    img.set("alt", f"TODO: Describe {src}")

                modified = True
                fixed_count += 1

        if modified:
            tree.write(str(content_path), xml_declaration=True,
                       encoding="UTF-8", pretty_print=True)

    if fixed_count > 0:
        detail = f"Added alt text to {fixed_count} image(s)"
        if generated_count:
            detail += f" ({generated_count} generated, {fixed_count - generated_count} placeholder)"
        fixes.append({"rule": "EPUB-E005", "status": "fixed", "detail": detail})
    else:
        fixes.append({"rule": "EPUB-E005", "status": "skipped",
                       "reason": "No images missing alt text found"})
    return fixes


def _generate_alt_for_epub_image(
    opf_dir: Path, content_path: Path, src: str,
    models: list[str] | None, context: str,
) -> str | None:
    """Try to generate alt text using the alt-text generator."""
    try:
        from alt_text.client import generate_for_image
    except ImportError:
        return None

    try:
        img_path = content_path.parent / src
        if not img_path.exists():
            img_path = opf_dir / src
        if not img_path.exists():
            return None

        image_bytes = img_path.read_bytes()
        ext = img_path.suffix.lower()
        mime_map = {
            ".png": "image/png", ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg", ".gif": "image/gif",
            ".svg": "image/svg+xml",
        }
        mime_type = mime_map.get(ext, "image/png")

        result = generate_for_image(
            image_bytes=image_bytes,
            mime_type=mime_type,
            model=(models or ["openai/gpt-4.1"])[0],
            profile="auto",
            source_format="epub",
            image_name=Path(src).name,
            context=context,
        )
        return result.concise_alt if result.concise_alt else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Navigation document fixer  [EPUB-E004]
# ---------------------------------------------------------------------------

def _find_nav_path(opf_root: etree._Element, opf_dir: Path) -> Path | None:
    """Find EPUB 3 navigation document from the manifest."""
    manifest = opf_root.find("opf:manifest", NS)
    if manifest is None:
        return None
    for item in manifest.findall("opf:item", NS):
        props = item.get("properties", "")
        if "nav" in props.split():
            href = item.get("href", "")
            if href:
                return opf_dir / href
    return None


def _get_spine_content_paths(opf_root: etree._Element, opf_dir: Path) -> list[tuple[str, Path]]:
    """Return list of (href, resolved_path) for spine content documents."""
    manifest = opf_root.find("opf:manifest", NS)
    spine = opf_root.find("opf:spine", NS)
    if manifest is None or spine is None:
        return []
    id_href = {}
    for item in manifest.findall("opf:item", NS):
        item_id = item.get("id", "")
        href = item.get("href", "")
        if item_id and href:
            id_href[item_id] = href
    result = []
    for ref in spine.findall("opf:itemref", NS):
        idref = ref.get("idref", "")
        href = id_href.get(idref, "")
        if href:
            p = opf_dir / href
            if p.exists():
                result.append((href, p))
    return result


def _extract_headings(content_path: Path) -> list[tuple[int, str]]:
    """Extract (level, text) for all headings in a content document."""
    heading_re = re.compile(r"\{.*\}h([1-6])")
    headings = []
    try:
        tree = etree.parse(str(content_path))
    except etree.XMLSyntaxError:
        return headings
    for el in tree.iter():
        m = heading_re.match(el.tag)
        if m:
            text = "".join(el.itertext()).strip() or f"Heading {m.group(1)}"
            headings.append((int(m.group(1)), text))
    return headings


def _build_toc_ol(entries: list[tuple[str, int, str]]) -> etree._Element:
    """Build a flat <ol> TOC from (href, level, text) tuples."""
    ol = etree.Element("{%s}ol" % NS["xhtml"])
    for href, _level, text in entries:
        li = etree.SubElement(ol, "{%s}li" % NS["xhtml"])
        a = etree.SubElement(li, "{%s}a" % NS["xhtml"])
        a.set("href", href)
        a.text = text
    return ol


def _fix_navigation(extract_dir: Path, opf_root: etree._Element) -> list[dict]:
    """Create or repair the EPUB 3 navigation document [EPUB-E004]."""
    version = opf_root.get("version", "3.0")
    if version.startswith("2"):
        return [{"rule": "EPUB-E004", "status": "skipped",
                 "reason": "EPUB 2 navigation (NCX) auto-generation not supported"}]

    opf_path_obj, opf_rel = _find_opf_path(extract_dir)
    opf_dir = opf_path_obj.parent if opf_path_obj else extract_dir

    nav_path = _find_nav_path(opf_root, opf_dir)
    spine_docs = _get_spine_content_paths(opf_root, opf_dir)

    # Collect first headings from each content doc for TOC
    toc_entries: list[tuple[str, int, str]] = []
    for href, cpath in spine_docs:
        headings = _extract_headings(cpath)
        if headings:
            toc_entries.append((href, headings[0][0], headings[0][1]))
        else:
            label = Path(href).stem.replace("-", " ").replace("_", " ").title()
            toc_entries.append((href, 1, label))

    if not toc_entries:
        return [{"rule": "EPUB-E004", "status": "skipped",
                 "reason": "No spine content documents found to build TOC from"}]

    fixes = []

    if nav_path and nav_path.exists():
        # Nav document exists -- check for missing <nav epub:type="toc">
        nav_tree = etree.parse(str(nav_path))
        nav_root = nav_tree.getroot()
        toc_nav = nav_root.find(
            ".//{%s}nav[@{%s}type='toc']" % (NS["xhtml"], NS["epub"]))
        if toc_nav is not None:
            # TOC already present -- check landmarks
            landmarks = nav_root.find(
                ".//{%s}nav[@{%s}type='landmarks']" % (NS["xhtml"], NS["epub"]))
            if landmarks is None:
                body = nav_root.find(".//{%s}body" % NS["xhtml"])
                if body is not None:
                    lm_nav = etree.SubElement(body, "{%s}nav" % NS["xhtml"])
                    lm_nav.set("{%s}type" % NS["epub"], "landmarks")
                    lm_h = etree.SubElement(lm_nav, "{%s}h2" % NS["xhtml"])
                    lm_h.text = "Landmarks"
                    lm_ol = etree.SubElement(lm_nav, "{%s}ol" % NS["xhtml"])
                    li_toc = etree.SubElement(lm_ol, "{%s}li" % NS["xhtml"])
                    a_toc = etree.SubElement(li_toc, "{%s}a" % NS["xhtml"])
                    a_toc.set("{%s}type" % NS["epub"], "toc")
                    a_toc.set("href", "#toc")
                    a_toc.text = "Table of Contents"
                    if spine_docs:
                        li_body = etree.SubElement(lm_ol, "{%s}li" % NS["xhtml"])
                        a_body = etree.SubElement(li_body, "{%s}a" % NS["xhtml"])
                        a_body.set("{%s}type" % NS["epub"], "bodymatter")
                        a_body.set("href", spine_docs[0][0])
                        a_body.text = "Start of Content"
                    nav_tree.write(str(nav_path), xml_declaration=True,
                                   encoding="UTF-8", pretty_print=True)
                    fixes.append({"rule": "EPUB-E004", "status": "fixed",
                                  "detail": "Added landmarks nav to existing navigation document"})
            if not fixes:
                fixes.append({"rule": "EPUB-E004", "status": "skipped",
                              "reason": "Navigation document with TOC already exists"})
            return fixes

        # No TOC nav element -- add one
        body = nav_root.find(".//{%s}body" % NS["xhtml"])
        if body is None:
            return [{"rule": "EPUB-E004", "status": "failed",
                     "reason": "Nav document exists but has no <body> element"}]

        toc_nav_el = etree.SubElement(body, "{%s}nav" % NS["xhtml"])
        toc_nav_el.set("{%s}type" % NS["epub"], "toc")
        toc_nav_el.set("id", "toc")
        h1 = etree.SubElement(toc_nav_el, "{%s}h1" % NS["xhtml"])
        h1.text = "Table of Contents"
        toc_nav_el.append(_build_toc_ol(toc_entries))

        nav_tree.write(str(nav_path), xml_declaration=True,
                       encoding="UTF-8", pretty_print=True)
        fixes.append({"rule": "EPUB-E004", "status": "fixed",
                      "detail": f"Added TOC with {len(toc_entries)} entries to existing nav document"})
        return fixes

    # No nav document at all -- create one
    nav_filename = "nav.xhtml"
    nav_path = opf_dir / nav_filename

    xhtml_ns = NS["xhtml"]
    epub_ns = NS["epub"]
    root = etree.Element("{%s}html" % xhtml_ns,
                         nsmap={None: xhtml_ns, "epub": epub_ns})
    root.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
    head = etree.SubElement(root, "{%s}head" % xhtml_ns)
    title_el = etree.SubElement(head, "{%s}title" % xhtml_ns)
    title_el.text = "Navigation"
    body = etree.SubElement(root, "{%s}body" % xhtml_ns)

    # TOC
    toc_nav_el = etree.SubElement(body, "{%s}nav" % xhtml_ns)
    toc_nav_el.set("{%s}type" % epub_ns, "toc")
    toc_nav_el.set("id", "toc")
    h1 = etree.SubElement(toc_nav_el, "{%s}h1" % xhtml_ns)
    h1.text = "Table of Contents"
    toc_nav_el.append(_build_toc_ol(toc_entries))

    # Landmarks
    lm_nav = etree.SubElement(body, "{%s}nav" % xhtml_ns)
    lm_nav.set("{%s}type" % epub_ns, "landmarks")
    lm_h = etree.SubElement(lm_nav, "{%s}h2" % xhtml_ns)
    lm_h.text = "Landmarks"
    lm_ol = etree.SubElement(lm_nav, "{%s}ol" % xhtml_ns)
    li_toc = etree.SubElement(lm_ol, "{%s}li" % xhtml_ns)
    a_toc = etree.SubElement(li_toc, "{%s}a" % xhtml_ns)
    a_toc.set("{%s}type" % epub_ns, "toc")
    a_toc.set("href", nav_filename)
    a_toc.text = "Table of Contents"
    if spine_docs:
        li_body = etree.SubElement(lm_ol, "{%s}li" % xhtml_ns)
        a_body = etree.SubElement(li_body, "{%s}a" % xhtml_ns)
        a_body.set("{%s}type" % epub_ns, "bodymatter")
        a_body.set("href", spine_docs[0][0])
        a_body.text = "Start of Content"

    tree = etree.ElementTree(root)
    tree.write(str(nav_path), xml_declaration=True,
               encoding="UTF-8", pretty_print=True)

    # Register in manifest with properties="nav"
    manifest = opf_root.find("opf:manifest", NS)
    if manifest is not None:
        nav_item = etree.SubElement(manifest, "{%s}item" % NS["opf"])
        nav_item.set("id", "nav")
        nav_item.set("href", nav_filename)
        nav_item.set("media-type", "application/xhtml+xml")
        nav_item.set("properties", "nav")

    fixes.append({"rule": "EPUB-E004", "status": "fixed",
                  "detail": f"Created {nav_filename} with TOC ({len(toc_entries)} entries) and landmarks"})
    return fixes


# ---------------------------------------------------------------------------
# Spine integrity fixer  [EPUB-E006]
# ---------------------------------------------------------------------------

def _fix_spine(opf_root: etree._Element) -> list[dict]:
    """Remove duplicate idrefs and dangling references from spine [EPUB-E006]."""
    spine = opf_root.find("opf:spine", NS)
    manifest = opf_root.find("opf:manifest", NS)
    if spine is None or manifest is None:
        return [{"rule": "EPUB-E006", "status": "failed",
                 "reason": "Spine or manifest element missing from OPF"}]

    manifest_ids = {item.get("id") for item in manifest.findall("opf:item", NS)}
    itemrefs = spine.findall("opf:itemref", NS)
    if not itemrefs:
        return [{"rule": "EPUB-E006", "status": "skipped",
                 "reason": "No spine itemrefs to validate"}]

    to_remove = []
    seen = set()
    removed_dups = 0
    removed_dangling = 0

    for ref in itemrefs:
        idref = ref.get("idref", "")
        if idref in seen:
            to_remove.append(ref)
            removed_dups += 1
        elif idref and idref not in manifest_ids:
            to_remove.append(ref)
            removed_dangling += 1
        else:
            seen.add(idref)

    for ref in to_remove:
        spine.remove(ref)

    fixes = []
    if removed_dups > 0:
        fixes.append({"rule": "EPUB-E006", "status": "fixed",
                      "detail": f"Removed {removed_dups} duplicate spine itemref(s)"})
    if removed_dangling > 0:
        fixes.append({"rule": "EPUB-E006", "status": "fixed",
                      "detail": f"Removed {removed_dangling} dangling spine itemref(s)"})
    if not fixes:
        fixes.append({"rule": "EPUB-E006", "status": "skipped",
                      "reason": "Spine references are valid"})
    return fixes


# ---------------------------------------------------------------------------
# Heading hierarchy fixer  [EPUB-W003]
# ---------------------------------------------------------------------------

def _fix_headings(extract_dir: Path, opf_root: etree._Element) -> list[dict]:
    """Repair skipped heading levels in content documents [EPUB-W003]."""
    opf_path_obj, _ = _find_opf_path(extract_dir)
    opf_dir = opf_path_obj.parent if opf_path_obj else extract_dir

    spine_docs = _get_spine_content_paths(opf_root, opf_dir)
    heading_re = re.compile(r"\{(.*)\}h([1-6])")
    total_fixed = 0

    for _href, cpath in spine_docs:
        try:
            tree = etree.parse(str(cpath))
        except etree.XMLSyntaxError:
            continue

        # Collect all headings in document order
        headings = []
        for el in tree.iter():
            m = heading_re.match(el.tag)
            if m:
                headings.append((el, m.group(1), int(m.group(2))))

        if not headings:
            continue

        # Repair: when a heading skips more than one level, lower it
        modified = False
        for i in range(1, len(headings)):
            el, ns_uri, level = headings[i]
            _, _, prev_level = headings[i - 1]
            if level > prev_level + 1:
                new_level = prev_level + 1
                el.tag = "{%s}h%d" % (ns_uri, new_level)
                headings[i] = (el, ns_uri, new_level)
                modified = True
                total_fixed += 1

        if modified:
            tree.write(str(cpath), xml_declaration=True,
                       encoding="UTF-8", pretty_print=True)

    if total_fixed > 0:
        return [{"rule": "EPUB-W003", "status": "fixed",
                 "detail": f"Repaired {total_fixed} skipped heading level(s) across content documents"}]
    return [{"rule": "EPUB-W003", "status": "skipped",
             "reason": "No heading hierarchy issues found"}]


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------

_ALL_RULES = {
    "EPUB-E001": "title",
    "EPUB-E003": "language",
    "EPUB-E004": "navigation",
    "EPUB-E005": "alt_text",
    "EPUB-E006": "spine",
    "EPUB-E007": "a11y_metadata",
    "EPUB-W003": "headings",
    "EPUB-T002": "author",
}


# ---------------------------------------------------------------------------
# Main fixer
# ---------------------------------------------------------------------------

def fix_epub(file_path, output_path=None, rules=None, title="", author="",
             lang="en") -> dict:
    """Fix accessibility issues in an ePub file.

    Args:
        file_path: Path to the .epub file.
        output_path: Optional output path. Default: <name>-fixed.epub.
        rules: List of rule IDs to fix. None = fix all.
        title: Custom document title.
        author: Custom author name.
        lang: BCP 47 language tag.

    Returns:
        Dict with keys: file, output, backup, fixes (list), summary.
    """
    if not HAS_LXML:
        return {"error": "lxml is not installed. Run: pip install lxml"}

    file_path = Path(file_path)
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}

    if output_path is None:
        output_path = file_path.with_stem(file_path.stem + "-fixed")
    else:
        output_path = Path(output_path)

    # Create backup
    backup_path = file_path.with_stem(file_path.stem + "-backup")
    shutil.copy2(file_path, backup_path)

    # Extract epub to temp dir
    tmp_dir = Path(tempfile.mkdtemp(prefix="epub_fix_"))
    try:
        try:
            with ZipFile(str(file_path), "r") as zf:
                # Zip slip protection: reject entries with path traversal
                for info in zf.infolist():
                    target = (tmp_dir / info.filename).resolve()
                    if not str(target).startswith(str(tmp_dir.resolve())):
                        shutil.rmtree(tmp_dir, ignore_errors=True)
                        return {"error": f"Blocked zip slip attack: {info.filename}"}
                zf.extractall(str(tmp_dir))
        except (BadZipFile, RuntimeError) as e:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return {"error": f"Failed to extract EPUB: {e}"}

        # Find and parse OPF
        opf_path, opf_rel = _find_opf_path(tmp_dir)
        if opf_path is None or not opf_path.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return {"error": "Cannot locate OPF package document"}

        opf_tree = etree.parse(str(opf_path))
        opf_root = opf_tree.getroot()

        all_fixes = []
        target_rules = rules if rules else list(_ALL_RULES.keys())

        for rule_id in target_rules:
            if rule_id not in _ALL_RULES:
                all_fixes.append({"rule": rule_id, "status": "unknown",
                                  "reason": f"Rule {rule_id} not supported for auto-fix"})
                continue

            rule_key = _ALL_RULES[rule_id]

            if rule_key == "title":
                result = _fix_title(opf_root, title)
            elif rule_key == "language":
                result = _fix_language(opf_root, lang)
            elif rule_key == "a11y_metadata":
                result = _fix_a11y_metadata(opf_root)
            elif rule_key == "alt_text":
                result = _fix_alt_text(tmp_dir, opf_root)
            elif rule_key == "navigation":
                result = _fix_navigation(tmp_dir, opf_root)
            elif rule_key == "spine":
                result = _fix_spine(opf_root)
            elif rule_key == "headings":
                result = _fix_headings(tmp_dir, opf_root)
            elif rule_key == "author":
                result = _fix_author(opf_root, author)
            else:
                result = {"rule": rule_id, "status": "unknown", "reason": "Internal error"}

            if isinstance(result, list):
                all_fixes.extend(result)
            else:
                all_fixes.append(result)

        # Write updated OPF back
        opf_tree.write(str(opf_path), xml_declaration=True,
                        encoding="UTF-8", pretty_print=True)

        # Repack EPUB
        _repack_epub(tmp_dir, output_path)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    fixed_count = sum(1 for f in all_fixes if f["status"] == "fixed")
    skipped_count = sum(1 for f in all_fixes if f["status"] == "skipped")
    failed_count = sum(1 for f in all_fixes if f["status"] == "failed")
    needs_human = sum(1 for f in all_fixes if f["status"] == "needs-human")

    return {
        "file": str(file_path),
        "output": str(output_path),
        "backup": str(backup_path),
        "fixes": all_fixes,
        "summary": {
            "fixed": fixed_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "needs_human": needs_human,
            "total_rules_attempted": len(target_rules),
        },
    }


def _repack_epub(extract_dir: Path, output_path: Path) -> None:
    """Repack an extracted EPUB directory into a valid .epub file.

    The mimetype file must be the first entry, stored uncompressed.
    """
    output_path = Path(output_path)
    with ZipFile(str(output_path), "w", ZIP_DEFLATED) as zf:
        # mimetype must be first and uncompressed
        mimetype_path = extract_dir / "mimetype"
        if mimetype_path.exists():
            zf.write(str(mimetype_path), "mimetype", compress_type=ZIP_STORED)

        for fpath in sorted(extract_dir.rglob("*")):
            if fpath.is_dir():
                continue
            arcname = str(fpath.relative_to(extract_dir))
            if arcname == "mimetype":
                continue  # Already added
            zf.write(str(fpath), arcname)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix ePub document accessibility issues")
    parser.add_argument("input", help="Path to .epub file")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--rules", help="Comma-separated rule IDs to fix")
    parser.add_argument("--title", default="", help="Document title")
    parser.add_argument("--author", default="", help="Document author")
    parser.add_argument("--lang", default="en", help="Document language (BCP 47)")
    args = parser.parse_args()

    rule_list = args.rules.split(",") if args.rules else None
    out = args.output if args.output else None
    result = fix_epub(Path(args.input), Path(out) if out else None,
                      rule_list, args.title, args.author, args.lang)
    print(json.dumps(result, indent=2))
