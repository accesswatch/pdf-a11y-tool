"""
scan_epub.py -- ePub (.epub) Accessibility Scanner
====================================================
Persistent utility for ePub document accessibility audits.
Checks against EPUB Accessibility 1.1 + WCAG 2.2 AA.

Checks:
  Package metadata:
    - Document title (dc:title)                       [EPUB-E001]
    - Unique identifier (dc:identifier)               [EPUB-E002]
    - Document language (dc:language)                  [EPUB-E003]
    - Accessibility metadata (schema:accessMode, etc.) [EPUB-E007]

  Navigation:
    - Table of contents (nav toc / NCX)               [EPUB-E004]
    - Page list (nav page-list)                        [EPUB-W001]
    - Landmarks (nav landmarks)                        [EPUB-W002]

  Content documents:
    - Image alt text in all spine XHTML               [EPUB-E005]
    - Spine reading order integrity                    [EPUB-E006]
    - Heading hierarchy per content document           [EPUB-W003]
    - Table headers in content documents               [EPUB-W004]
    - Ambiguous link text                              [EPUB-W005]

  Best practices:
    - Accessibility summary quality                    [EPUB-T001]
    - Author metadata (dc:creator)                     [EPUB-T002]
    - Description metadata (dc:description)            [EPUB-T003]

Usage:
    python tools/scan_epub.py <epub_or_folder> [--json] [--output file.json]

Dependencies: lxml (pip install lxml)

This file is PERMANENT -- do not delete. Used by agents and mcp_server.py.
"""

import sys
import json
import argparse
import re
import tempfile
import shutil
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from collections import Counter

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
    "ncx": "http://www.daisy.org/z3986/2005/ncx/",
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
}

AMBIGUOUS_LINK_TEXT = {
    "click here", "here", "more", "read more", "learn more", "link",
    "more info", "details", "this", "this link", "go", "continue",
}


# ---------------------------------------------------------------------------
# Container / OPF parsing
# ---------------------------------------------------------------------------

def _find_opf_path(extract_dir: Path) -> Path | None:
    """Read META-INF/container.xml to locate the OPF rootfile."""
    container_xml = extract_dir / "META-INF" / "container.xml"
    if not container_xml.exists():
        return None
    tree = etree.parse(str(container_xml))
    rootfile = tree.find(".//container:rootfile", NS)
    if rootfile is None:
        return None
    full_path = rootfile.get("full-path", "")
    if not full_path:
        return None
    return extract_dir / full_path


def _parse_opf(opf_path: Path) -> tuple[etree._Element, str]:
    """Parse OPF and return (root element, epub version string)."""
    tree = etree.parse(str(opf_path))
    root = tree.getroot()
    version = root.get("version", "3.0")
    return root, version


# ---------------------------------------------------------------------------
# Metadata checks
# ---------------------------------------------------------------------------

def _check_title(opf_root: etree._Element) -> list[dict]:
    title = opf_root.find(".//dc:title", NS)
    if title is None or not (title.text or "").strip():
        return [{"rule": "EPUB-E001", "severity": "Error",
                 "wcag": "2.4.2", "message": "dc:title is absent or empty in the package document",
                 "fix": "Add <dc:title>Descriptive Title</dc:title> to the OPF metadata"}]
    return []


def _check_identifier(opf_root: etree._Element) -> list[dict]:
    uid_attr = opf_root.get("unique-identifier", "")
    ident = opf_root.find(f".//dc:identifier[@id='{uid_attr}']", NS) if uid_attr else None
    if ident is None:
        # Try any dc:identifier
        any_id = opf_root.find(".//dc:identifier", NS)
        if any_id is None or not (any_id.text or "").strip():
            return [{"rule": "EPUB-E002", "severity": "Error",
                     "wcag": "", "message": "dc:identifier is absent or does not match unique-identifier on <package>",
                     "fix": "Add <dc:identifier id=\"uid\">urn:uuid:...</dc:identifier> and set unique-identifier=\"uid\" on <package>"}]
    return []


def _check_language(opf_root: etree._Element) -> list[dict]:
    lang = opf_root.find(".//dc:language", NS)
    if lang is None or not (lang.text or "").strip():
        return [{"rule": "EPUB-E003", "severity": "Error",
                 "wcag": "3.1.1", "message": "dc:language is absent or empty in the package document",
                 "fix": "Add <dc:language>en</dc:language> (or appropriate BCP 47 tag) to OPF metadata"}]
    return []


def _check_a11y_metadata(opf_root: etree._Element, version: str) -> list[dict]:
    """Check for schema.org accessibility metadata (EPUB 3 only)."""
    if version.startswith("2"):
        return []  # EPUB 2 doesn't support schema: properties

    metadata = opf_root.find("opf:metadata", NS)
    if metadata is None:
        return []

    meta_texts = []
    for meta in metadata.findall("opf:meta", NS):
        prop = meta.get("property", "")
        if prop.startswith("schema:access") or prop.startswith("schema:accessibility"):
            meta_texts.append((prop, (meta.text or "").strip()))

    found_props = {p for p, _ in meta_texts}
    required = {"schema:accessMode", "schema:accessibilityFeature", "schema:accessibilitySummary"}
    missing = required - found_props

    findings = []
    if missing:
        findings.append({"rule": "EPUB-E007", "severity": "Error",
                         "wcag": "", "message": f"Missing accessibility metadata: {', '.join(sorted(missing))}",
                         "fix": "Add schema:accessMode, schema:accessibilityFeature, and schema:accessibilitySummary to OPF metadata"})

    # Tip: check summary quality
    for prop, text in meta_texts:
        if prop == "schema:accessibilitySummary" and text and len(text.split()) < 50:
            findings.append({"rule": "EPUB-T001", "severity": "Info",
                             "wcag": "", "message": f"accessibilitySummary is brief ({len(text.split())} words) -- more detail improves discoverability",
                             "fix": "Expand the accessibility summary to describe conformance level, features, and any known limitations"})
    return findings


def _check_author(opf_root: etree._Element) -> list[dict]:
    creator = opf_root.find(".//dc:creator", NS)
    if creator is None or not (creator.text or "").strip():
        return [{"rule": "EPUB-T002", "severity": "Info",
                 "wcag": "", "message": "dc:creator is absent -- impacts screen reader document identification",
                 "fix": "Add <dc:creator>Author Name</dc:creator> to OPF metadata"}]
    return []


def _check_description(opf_root: etree._Element) -> list[dict]:
    desc = opf_root.find(".//dc:description", NS)
    if desc is None or not (desc.text or "").strip():
        return [{"rule": "EPUB-T003", "severity": "Info",
                 "wcag": "", "message": "dc:description is absent -- improves catalog discoverability for AT users",
                 "fix": "Add <dc:description>Brief description</dc:description> to OPF metadata"}]
    return []


# ---------------------------------------------------------------------------
# Navigation checks
# ---------------------------------------------------------------------------

def _find_nav_path(opf_root: etree._Element, opf_dir: Path) -> Path | None:
    """Find the EPUB 3 navigation document from the manifest."""
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


def _find_ncx_path(opf_root: etree._Element, opf_dir: Path) -> Path | None:
    """Find the EPUB 2 NCX file from the manifest."""
    manifest = opf_root.find("opf:manifest", NS)
    if manifest is None:
        return None
    for item in manifest.findall("opf:item", NS):
        media = item.get("media-type", "")
        if media == "application/x-dtbncx+xml":
            href = item.get("href", "")
            if href:
                return opf_dir / href
    return None


def _check_navigation(opf_root: etree._Element, opf_dir: Path, version: str) -> list[dict]:
    findings = []

    if version.startswith("2"):
        # EPUB 2: check NCX
        ncx_path = _find_ncx_path(opf_root, opf_dir)
        if ncx_path is None or not ncx_path.exists():
            findings.append({"rule": "EPUB-E004", "severity": "Error",
                             "wcag": "2.4.5", "message": "NCX file (toc.ncx) is absent -- no table of contents for EPUB 2",
                             "fix": "Add a toc.ncx file with a complete navMap"})
        else:
            ncx_tree = etree.parse(str(ncx_path))
            nav_map = ncx_tree.find(".//ncx:navMap", NS)
            if nav_map is None or len(nav_map.findall("ncx:navPoint", NS)) == 0:
                findings.append({"rule": "EPUB-E004", "severity": "Error",
                                 "wcag": "2.4.5", "message": "NCX navMap is empty -- no table of contents entries",
                                 "fix": "Populate the navMap with navPoint entries for each spine item"})
        return findings

    # EPUB 3: check nav document
    nav_path = _find_nav_path(opf_root, opf_dir)
    if nav_path is None or not nav_path.exists():
        findings.append({"rule": "EPUB-E004", "severity": "Error",
                         "wcag": "2.4.5", "message": "Navigation document (nav.xhtml) is absent or not found in manifest",
                         "fix": "Create a navigation document with <nav epub:type=\"toc\"> and reference it in the manifest with properties=\"nav\""})
        return findings

    nav_tree = etree.parse(str(nav_path))
    nav_root = nav_tree.getroot()

    # Check for TOC nav
    toc_nav = nav_root.find(".//{%s}nav[@{%s}type='toc']" % (NS["xhtml"], NS["epub"]))
    if toc_nav is None:
        findings.append({"rule": "EPUB-E004", "severity": "Error",
                         "wcag": "2.4.5", "message": "Navigation document has no <nav epub:type=\"toc\"> element",
                         "fix": "Add <nav epub:type=\"toc\"> with an ordered list of chapter links"})

    # Check for page-list
    page_nav = nav_root.find(".//{%s}nav[@{%s}type='page-list']" % (NS["xhtml"], NS["epub"]))
    if page_nav is None:
        findings.append({"rule": "EPUB-W001", "severity": "Warning",
                         "wcag": "", "message": "Navigation document has no <nav epub:type=\"page-list\"> -- recommended when print pagination exists",
                         "fix": "Add <nav epub:type=\"page-list\"> if the publication maps to a print edition"})

    # Check for landmarks
    landmarks_nav = nav_root.find(".//{%s}nav[@{%s}type='landmarks']" % (NS["xhtml"], NS["epub"]))
    if landmarks_nav is None:
        findings.append({"rule": "EPUB-W002", "severity": "Warning",
                         "wcag": "2.4.1", "message": "Navigation document has no <nav epub:type=\"landmarks\"> element",
                         "fix": "Add <nav epub:type=\"landmarks\"> with links to TOC, start of content, etc."})

    return findings


# ---------------------------------------------------------------------------
# Spine / reading order check
# ---------------------------------------------------------------------------

def _check_spine(opf_root: etree._Element) -> list[dict]:
    """Check spine integrity -- EPUB-E006."""
    spine = opf_root.find("opf:spine", NS)
    manifest = opf_root.find("opf:manifest", NS)
    if spine is None or manifest is None:
        return [{"rule": "EPUB-E006", "severity": "Error",
                 "wcag": "1.3.2", "message": "Spine or manifest element missing from OPF",
                 "fix": "Ensure the OPF has both <manifest> and <spine> elements"}]

    manifest_ids = {item.get("id") for item in manifest.findall("opf:item", NS)}
    itemrefs = spine.findall("opf:itemref", NS)

    if not itemrefs:
        return [{"rule": "EPUB-E006", "severity": "Error",
                 "wcag": "1.3.2", "message": "Spine has no itemref elements -- no reading order defined",
                 "fix": "Add itemref elements to the spine referencing content documents"}]

    findings = []
    seen_idrefs = []
    for ref in itemrefs:
        idref = ref.get("idref", "")
        if idref in seen_idrefs:
            findings.append({"rule": "EPUB-E006", "severity": "Error",
                             "wcag": "1.3.2", "message": f"Duplicate idref '{idref}' in spine",
                             "fix": f"Remove the duplicate spine reference to '{idref}'"})
        elif idref and idref not in manifest_ids:
            findings.append({"rule": "EPUB-E006", "severity": "Error",
                             "wcag": "1.3.2", "message": f"Spine references '{idref}' which is not in the manifest",
                             "fix": f"Add an item with id='{idref}' to the manifest or remove the spine reference"})
        seen_idrefs.append(idref)

    return findings


# ---------------------------------------------------------------------------
# Content document checks
# ---------------------------------------------------------------------------

def _get_spine_hrefs(opf_root: etree._Element, opf_dir: Path) -> list[Path]:
    """Resolve spine itemrefs to content document file paths."""
    spine = opf_root.find("opf:spine", NS)
    manifest = opf_root.find("opf:manifest", NS)
    if spine is None or manifest is None:
        return []

    # Build id -> href map
    id_href = {}
    for item in manifest.findall("opf:item", NS):
        item_id = item.get("id", "")
        href = item.get("href", "")
        if item_id and href:
            id_href[item_id] = href

    paths = []
    for ref in spine.findall("opf:itemref", NS):
        idref = ref.get("idref", "")
        href = id_href.get(idref, "")
        if href:
            p = opf_dir / href
            if p.exists():
                paths.append(p)
    return paths


def _check_images(content_files: list[Path]) -> list[dict]:
    """Check all content documents for missing alt text -- EPUB-E005."""
    findings = []
    for fpath in content_files:
        try:
            tree = etree.parse(str(fpath))
        except etree.XMLSyntaxError:
            continue
        for img in tree.iter("{%s}img" % NS["xhtml"]):
            alt = img.get("alt")
            role = img.get("role", "")
            if alt is None:
                src = img.get("src", "unknown")
                findings.append({"rule": "EPUB-E005", "severity": "Error",
                                 "wcag": "1.1.1",
                                 "message": f"Image missing alt attribute: {src} in {fpath.name}",
                                 "fix": "Add alt=\"descriptive text\" or alt=\"\" role=\"presentation\" for decorative images"})
            elif not alt.strip() and role != "presentation":
                src = img.get("src", "unknown")
                findings.append({"rule": "EPUB-E005", "severity": "Error",
                                 "wcag": "1.1.1",
                                 "message": f"Image has empty alt without role=\"presentation\": {src} in {fpath.name}",
                                 "fix": "Add descriptive alt text or add role=\"presentation\" for decorative images"})
        # Also check SVG title/desc
        for svg in tree.iter("{http://www.w3.org/2000/svg}svg"):
            title_el = svg.find("{http://www.w3.org/2000/svg}title")
            if title_el is None or not (title_el.text or "").strip():
                findings.append({"rule": "EPUB-E005", "severity": "Error",
                                 "wcag": "1.1.1",
                                 "message": f"SVG element missing <title> in {fpath.name}",
                                 "fix": "Add a <title> element as the first child of <svg>"})
        # Check MathML alttext
        for math_el in tree.iter("{http://www.w3.org/1998/Math/MathML}math"):
            alttext = math_el.get("alttext", "")
            if not alttext.strip():
                findings.append({"rule": "EPUB-E005", "severity": "Error",
                                 "wcag": "1.1.1",
                                 "message": f"MathML element missing alttext attribute in {fpath.name}",
                                 "fix": "Add alttext=\"description of the equation\" to the <math> element"})
    return findings


def _check_headings(content_files: list[Path]) -> list[dict]:
    """Check heading hierarchy in each content document -- EPUB-W003."""
    findings = []
    heading_re = re.compile(r"\{.*\}h([1-6])")
    for fpath in content_files:
        try:
            tree = etree.parse(str(fpath))
        except etree.XMLSyntaxError:
            continue
        levels = []
        for el in tree.iter():
            m = heading_re.match(el.tag)
            if m:
                levels.append(int(m.group(1)))
        if not levels:
            continue
        # Check for skipped levels
        for i in range(1, len(levels)):
            if levels[i] > levels[i - 1] + 1:
                findings.append({"rule": "EPUB-W003", "severity": "Warning",
                                 "wcag": "2.4.6",
                                 "message": f"Heading level skipped: h{levels[i-1]} to h{levels[i]} in {fpath.name}",
                                 "fix": f"Use h{levels[i-1]+1} instead of h{levels[i]}, or add the missing intermediate heading"})
    return findings


def _check_tables(content_files: list[Path]) -> list[dict]:
    """Check tables for headers in content documents -- EPUB-W004."""
    findings = []
    for fpath in content_files:
        try:
            tree = etree.parse(str(fpath))
        except etree.XMLSyntaxError:
            continue
        for table in tree.iter("{%s}table" % NS["xhtml"]):
            has_th = len(table.findall(".//{%s}th" % NS["xhtml"])) > 0
            if not has_th:
                findings.append({"rule": "EPUB-W004", "severity": "Warning",
                                 "wcag": "1.3.1",
                                 "message": f"Data table has no <th> elements in {fpath.name}",
                                 "fix": "Add <th scope=\"col\"> or <th scope=\"row\"> elements to the table header row"})
    return findings


def _check_links(content_files: list[Path]) -> list[dict]:
    """Check for ambiguous link text -- EPUB-W005."""
    findings = []
    for fpath in content_files:
        try:
            tree = etree.parse(str(fpath))
        except etree.XMLSyntaxError:
            continue
        for a_el in tree.iter("{%s}a" % NS["xhtml"]):
            text = (a_el.text or "").strip().lower()
            # Also gather all inner text
            full_text = "".join(a_el.itertext()).strip().lower()
            check_text = full_text or text
            if check_text in AMBIGUOUS_LINK_TEXT:
                href = a_el.get("href", "")
                findings.append({"rule": "EPUB-W005", "severity": "Warning",
                                 "wcag": "2.4.4",
                                 "message": f"Ambiguous link text \"{check_text}\" in {fpath.name}",
                                 "fix": f"Replace with descriptive text that explains where the link goes"})
    return findings


# ---------------------------------------------------------------------------
# Fixed-layout detection
# ---------------------------------------------------------------------------

def _is_fixed_layout(opf_root: etree._Element) -> bool:
    """Detect fixed-layout EPUB (rendition:layout pre-paginated)."""
    metadata = opf_root.find("opf:metadata", NS)
    if metadata is None:
        return False
    for meta in metadata.findall("opf:meta", NS):
        prop = meta.get("property", "")
        if prop == "rendition:layout" and (meta.text or "").strip() == "pre-paginated":
            return True
    return False


# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------

def scan_epub(file_path: Path, max_content_docs: int = 200) -> dict:
    """Scan an ePub file for accessibility issues.

    Args:
        file_path: Path to the .epub file.
        max_content_docs: Maximum number of content documents to scan (for large ePubs).

    Returns:
        Dict with keys: file, epub_version, fixed_layout, findings, errors, metadata.
    """
    if not HAS_LXML:
        return {"file": str(file_path), "findings": [],
                "errors": ["lxml is not installed. Run: pip install lxml"]}

    file_path = Path(file_path)
    if not file_path.exists():
        return {"file": str(file_path), "findings": [],
                "errors": [f"File not found: {file_path}"]}

    result = {
        "file": str(file_path),
        "epub_version": "unknown",
        "fixed_layout": False,
        "findings": [],
        "errors": [],
        "metadata": {},
    }

    # Extract to temp directory
    tmp_dir = Path(tempfile.mkdtemp(prefix="epub_scan_"))
    try:
        try:
            with ZipFile(str(file_path), "r") as zf:
                # Zip slip protection: reject entries with path traversal
                for info in zf.infolist():
                    target = (tmp_dir / info.filename).resolve()
                    if not str(target).startswith(str(tmp_dir.resolve())):
                        result["errors"].append(f"Blocked zip slip attack: {info.filename}")
                        return result
                zf.extractall(str(tmp_dir))
        except BadZipFile:
            result["errors"].append("File is not a valid ZIP/EPUB archive")
            return result
        except RuntimeError as e:
            if "password" in str(e).lower() or "encrypt" in str(e).lower():
                result["errors"].append("EPUB archive is password-protected -- unable to audit")
            else:
                result["errors"].append(f"Failed to extract EPUB: {e}")
            return result

        # Validate mimetype
        mimetype_file = tmp_dir / "mimetype"
        if not mimetype_file.exists():
            result["errors"].append("Missing 'mimetype' file -- may not be a valid EPUB")

        # Find and parse OPF
        opf_path = _find_opf_path(tmp_dir)
        if opf_path is None or not opf_path.exists():
            result["errors"].append("Cannot locate OPF package document via META-INF/container.xml")
            return result

        opf_root, version = _parse_opf(opf_path)
        result["epub_version"] = version
        opf_dir = opf_path.parent

        # Fixed-layout detection
        result["fixed_layout"] = _is_fixed_layout(opf_root)

        # Extract basic metadata for the result
        title_el = opf_root.find(".//dc:title", NS)
        lang_el = opf_root.find(".//dc:language", NS)
        creator_el = opf_root.find(".//dc:creator", NS)
        result["metadata"] = {
            "title": (title_el.text or "").strip() if title_el is not None else "",
            "language": (lang_el.text or "").strip() if lang_el is not None else "",
            "creator": (creator_el.text or "").strip() if creator_el is not None else "",
        }

        # Run all checks
        result["findings"].extend(_check_title(opf_root))
        result["findings"].extend(_check_identifier(opf_root))
        result["findings"].extend(_check_language(opf_root))
        result["findings"].extend(_check_a11y_metadata(opf_root, version))
        result["findings"].extend(_check_author(opf_root))
        result["findings"].extend(_check_description(opf_root))
        result["findings"].extend(_check_navigation(opf_root, opf_dir, version))
        result["findings"].extend(_check_spine(opf_root))

        # Content document checks
        content_files = _get_spine_hrefs(opf_root, opf_dir)
        if len(content_files) > max_content_docs:
            result["errors"].append(
                f"Large EPUB: {len(content_files)} content documents, scanning first {max_content_docs}")
            content_files = content_files[:max_content_docs]

        result["findings"].extend(_check_images(content_files))
        result["findings"].extend(_check_headings(content_files))
        result["findings"].extend(_check_tables(content_files))
        result["findings"].extend(_check_links(content_files))

        # Fixed-layout warning
        if result["fixed_layout"]:
            result["findings"].append({
                "rule": "EPUB-W006", "severity": "Warning",
                "wcag": "1.4.1",
                "message": "Fixed-layout EPUB detected -- inherently less accessible, requires manual reading order verification",
                "fix": "Consider providing a reflowable alternative or ensure reading order is correct for assistive technology"
            })

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return result


# ---------------------------------------------------------------------------
# Folder scanner
# ---------------------------------------------------------------------------

def scan_folder(folder: Path) -> list[dict]:
    """Scan all .epub files in a folder."""
    results = []
    for epub in sorted(folder.rglob("*.epub")):
        results.append(scan_epub(epub))
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Scan ePub files for accessibility issues")
    parser.add_argument("path", help="Path to an .epub file or folder")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", help="Write results to this file")
    args = parser.parse_args()

    target = Path(args.path)
    if target.is_dir():
        results = scan_folder(target)
    elif target.suffix.lower() == ".epub":
        results = [scan_epub(target)]
    else:
        sys.exit(f"Error: Not an .epub file or folder: {target}")

    if args.json or args.output:
        output = json.dumps(results, indent=2, default=str)
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"Results written to: {args.output}")
        else:
            print(output)
    else:
        for r in results:
            print(f"\n{'='*60}")
            print(f"File: {r['file']}")
            print(f"EPUB Version: {r['epub_version']}")
            print(f"Fixed Layout: {r['fixed_layout']}")
            if r["errors"]:
                for e in r["errors"]:
                    print(f"  ERROR: {e}")
            errs = sum(1 for f in r["findings"] if f.get("severity") == "Error")
            warns = sum(1 for f in r["findings"] if f.get("severity") == "Warning")
            infos = sum(1 for f in r["findings"] if f.get("severity") == "Info")
            print(f"Findings: {errs} errors, {warns} warnings, {infos} info")
            for f in r["findings"]:
                sev = f.get("severity", "?")
                rule = f.get("rule", "?")
                msg = f.get("message", "")
                print(f"  [{sev}] {rule}: {msg}")


if __name__ == "__main__":
    main()
