"""
fix_pdf.py — PDF Accessibility Auto-Fixer
==========================================
Applies deterministic accessibility fixes to PDF files:
  Tier 1 (metadata):
    - Missing document title (XMP + Info dict)
    - DisplayDocTitle flag
    - Missing document language (/Lang)
    - Tab order (/Tabs /S on pages)
    - PDF/UA identifier
    - MarkInfo /Marked flag
  Tier 2 (structural):
    - Form field tooltips (/TU entries)
    - Table header marking guidance
    - Heading skip detection guidance

Uses pikepdf for all operations.
Always creates a backup and writes to a new -fixed.pdf file.
Never overwrites the original.

This file is PERMANENT — do not delete.
"""

import json
import shutil
import sys
from pathlib import Path

try:
    import pikepdf
    HAS_PIKEPDF = True
except ImportError:
    HAS_PIKEPDF = False

# ---------------------------------------------------------------------------
# Fix functions
# ---------------------------------------------------------------------------

def _fix_title(pdf: "pikepdf.Pdf", title: str = "") -> dict:
    """Set document title in Info dict and XMP metadata."""
    # Check existing title
    existing = ""
    if pdf.docinfo.get("/Title"):
        existing = str(pdf.docinfo["/Title"]).strip()
    if existing:
        return {"rule": "PDFUA.METADATA.TITLE", "status": "skipped", "reason": f"Title already set: {existing[:80]}"}

    new_title = title or "TODO: Add descriptive document title"
    pdf.docinfo["/Title"] = new_title

    # Also set in XMP if possible
    with pdf.open_metadata() as meta:
        meta["dc:title"] = new_title

    return {"rule": "PDFUA.METADATA.TITLE", "status": "fixed", "detail": f"Set title to '{new_title}'"}


def _fix_display_doc_title(pdf: "pikepdf.Pdf") -> dict:
    """Set ViewerPreferences.DisplayDocTitle to true."""
    root = pdf.Root
    if "/ViewerPreferences" not in root:
        root["/ViewerPreferences"] = pikepdf.Dictionary()
    vp = root["/ViewerPreferences"]
    current = vp.get("/DisplayDocTitle", False)
    if current:
        return {"rule": "PDFUA.METADATA.DISPLAY_TITLE", "status": "skipped", "reason": "DisplayDocTitle already true"}
    vp["/DisplayDocTitle"] = True
    return {"rule": "PDFUA.METADATA.DISPLAY_TITLE", "status": "fixed", "detail": "Set DisplayDocTitle to true"}


def _fix_language(pdf: "pikepdf.Pdf", lang: str = "en-US") -> dict:
    """Set document language /Lang in catalog."""
    root = pdf.Root
    existing = str(root.get("/Lang", "")).strip()
    if existing:
        return {"rule": "PDFUA.METADATA.LANG", "status": "skipped", "reason": f"Language already set: {existing}"}
    root["/Lang"] = lang
    return {"rule": "PDFUA.METADATA.LANG", "status": "fixed", "detail": f"Set document language to {lang}"}


def _fix_tab_order(pdf: "pikepdf.Pdf") -> list[dict]:
    """Set /Tabs /S (structure order) on all pages missing it."""
    results = []
    for i, page in enumerate(pdf.pages, 1):
        existing = page.get("/Tabs", None)
        if existing is not None:
            continue
        page["/Tabs"] = pikepdf.Name("/S")
        results.append({
            "rule": "PDFUA.NAV.TAB_ORDER",
            "status": "fixed",
            "detail": f"Set tab order to /S (structure) on page {i}",
        })
    if not results:
        results.append({"rule": "PDFUA.NAV.TAB_ORDER", "status": "skipped", "reason": "All pages already have tab order set"})
    return results


def _fix_pdfua_identifier(pdf: "pikepdf.Pdf") -> dict:
    """Add PDF/UA-1 identifier via XMP metadata."""
    try:
        with pdf.open_metadata() as meta:
            existing = meta.get("pdfuaid:part", "")
            if existing:
                return {"rule": "PDFUA.METADATA.PDFUA_ID", "status": "skipped", "reason": f"PDF/UA identifier already present: part={existing}"}
            meta["pdfuaid:part"] = "1"
        return {"rule": "PDFUA.METADATA.PDFUA_ID", "status": "fixed", "detail": "Set pdfuaid:part=1 (PDF/UA-1)"}
    except Exception as e:
        return {"rule": "PDFUA.METADATA.PDFUA_ID", "status": "failed", "reason": str(e)}


def _fix_marked_content(pdf: "pikepdf.Pdf") -> dict:
    """Ensure /MarkInfo /Marked true in catalog."""
    root = pdf.Root
    if "/MarkInfo" not in root:
        root["/MarkInfo"] = pikepdf.Dictionary()
    mi = root["/MarkInfo"]
    current = mi.get("/Marked", False)
    if current:
        return {"rule": "PDFUA.STRUCTURE.MARKED", "status": "skipped", "reason": "Already marked as tagged PDF"}
    mi["/Marked"] = True
    return {"rule": "PDFUA.STRUCTURE.MARKED", "status": "fixed",
            "detail": "Set /MarkInfo /Marked true — NOTE: this flag alone does not create tags; full tagging requires Acrobat Pro"}


# ---------------------------------------------------------------------------
# Tier 2 — Structural fixes
# ---------------------------------------------------------------------------

def _fix_form_tooltips(pdf: "pikepdf.Pdf") -> list[dict]:
    """Add /TU (tooltip) entries to form fields that lack them [PDFUA.FORM.TU].

    Uses the field's /T (partial name) as the tooltip text when /TU is missing.
    This provides a baseline; human review should refine the tooltips.
    """
    root = pdf.Root
    acroform = root.get("/AcroForm")
    if acroform is None:
        return [{"rule": "PDFUA.FORM.TU", "status": "skipped",
                 "reason": "Document has no AcroForm (no form fields)"}]

    fields = acroform.get("/Fields")
    if fields is None or len(fields) == 0:
        return [{"rule": "PDFUA.FORM.TU", "status": "skipped",
                 "reason": "AcroForm has no fields"}]

    fixed_count = 0
    for field_ref in fields:
        try:
            field = field_ref
            # Resolve indirect reference
            if hasattr(field_ref, "resolve"):
                field = field_ref.resolve()
        except Exception:
            continue

        tu = field.get("/TU")
        if tu is not None and str(tu).strip():
            continue

        # Use /T (partial field name) as fallback tooltip
        t_val = field.get("/T")
        if t_val:
            tooltip = str(t_val).strip()
            # Clean up common naming patterns
            tooltip = tooltip.replace("_", " ").replace(".", " ")
        else:
            tooltip = "TODO: Add tooltip"

        field["/TU"] = pikepdf.String(tooltip)
        fixed_count += 1

    if fixed_count > 0:
        return [{"rule": "PDFUA.FORM.TU", "status": "fixed",
                 "detail": f"Added /TU tooltips to {fixed_count} form field(s) — review tooltip text for clarity"}]
    return [{"rule": "PDFUA.FORM.TU", "status": "skipped",
             "reason": "All form fields already have tooltips"}]


def _fix_table_headers(pdf: "pikepdf.Pdf") -> list[dict]:
    """Guidance fix for table headers [PDFUA.TABLE.HEADERS].

    Marking specific cells as /TH requires understanding the table's semantic
    structure, which needs human judgment. This fix detects whether tables exist
    without /TH and returns actionable Acrobat Pro guidance.
    """
    root = pdf.Root
    struct_root = root.get("/StructTreeRoot")
    if struct_root is None:
        return [{"rule": "PDFUA.TABLE.HEADERS", "status": "needs-human",
                 "reason": "No structure tree — tag the PDF first, then mark table headers",
                 "acrobat_steps": [
                     "Acrobat Pro → Accessibility → Autotag Document",
                     "Then: Tags panel → find <Table> elements",
                     "Change first-row <TD> cells to <TH>",
                     "Add scope=\"Column\" or scope=\"Row\" attributes",
                 ]}]

    # Walk the structure tree looking for Table/TH
    def _has_tag(node, tag_name: str) -> bool:
        s_type = str(node.get("/S", "")).strip("/")
        if s_type == tag_name:
            return True
        kids = node.get("/K")
        if kids is None:
            return False
        if isinstance(kids, pikepdf.Array):
            for kid in kids:
                try:
                    resolved = kid if not hasattr(kid, "resolve") else kid.resolve()
                    if isinstance(resolved, pikepdf.Dictionary) and _has_tag(resolved, tag_name):
                        return True
                except Exception:
                    continue
        elif isinstance(kids, pikepdf.Dictionary):
            if _has_tag(kids, tag_name):
                return True
        return False

    has_table = _has_tag(struct_root, "Table")
    has_th = _has_tag(struct_root, "TH")

    if not has_table:
        return [{"rule": "PDFUA.TABLE.HEADERS", "status": "skipped",
                 "reason": "No tagged tables found in document"}]

    if has_th:
        return [{"rule": "PDFUA.TABLE.HEADERS", "status": "skipped",
                 "reason": "Table headers (/TH) already present"}]

    return [{"rule": "PDFUA.TABLE.HEADERS", "status": "needs-human",
             "reason": "Tables found but no /TH header cells in tag tree",
             "acrobat_steps": [
                 "Acrobat Pro → Tags panel → expand <Table>",
                 "Locate the header row's <TD> cells",
                 "Right-click each → Properties → change Type to TH",
                 "Set Scope to Column or Row as appropriate",
             ]}]


def _fix_heading_skip(pdf: "pikepdf.Pdf") -> list[dict]:
    """Guidance fix for heading level skips [PDFBP.HEADING.SKIP].

    Retagging headings requires human judgment about document structure.
    This fix detects heading skips and provides Acrobat Pro remediation guidance.
    """
    root = pdf.Root
    struct_root = root.get("/StructTreeRoot")
    if struct_root is None:
        return [{"rule": "PDFBP.HEADING.SKIP", "status": "needs-human",
                 "reason": "No structure tree — tag the PDF first, then verify heading hierarchy",
                 "acrobat_steps": [
                     "Acrobat Pro → Accessibility → Autotag Document",
                     "Then: Tags panel → verify H1→H2→H3 hierarchy with no gaps",
                 ]}]

    # Collect heading levels from tag tree
    heading_levels = []

    def _collect_headings(node):
        s_type = str(node.get("/S", "")).strip("/")
        if len(s_type) == 2 and s_type[0] == "H" and s_type[1].isdigit():
            heading_levels.append(int(s_type[1]))
        kids = node.get("/K")
        if kids is None:
            return
        if isinstance(kids, pikepdf.Array):
            for kid in kids:
                try:
                    resolved = kid if not hasattr(kid, "resolve") else kid.resolve()
                    if isinstance(resolved, pikepdf.Dictionary):
                        _collect_headings(resolved)
                except Exception:
                    continue
        elif isinstance(kids, pikepdf.Dictionary):
            _collect_headings(kids)

    _collect_headings(struct_root)

    if not heading_levels:
        return [{"rule": "PDFBP.HEADING.SKIP", "status": "skipped",
                 "reason": "No tagged headings found"}]

    # Detect skips
    skips = []
    for i in range(1, len(heading_levels)):
        if heading_levels[i] > heading_levels[i - 1] + 1:
            skips.append(f"H{heading_levels[i-1]}→H{heading_levels[i]}")

    if not skips:
        return [{"rule": "PDFBP.HEADING.SKIP", "status": "skipped",
                 "reason": "Heading hierarchy has no gaps"}]

    return [{"rule": "PDFBP.HEADING.SKIP", "status": "needs-human",
             "reason": f"Heading level skips detected: {', '.join(skips[:10])}",
             "acrobat_steps": [
                 "Acrobat Pro → Tags panel → locate skipped headings",
                 "Right-click heading tag → Properties → change to correct level",
                 "Ensure hierarchy flows H1→H2→H3 without gaps",
             ]}]


def _fix_image_alt_text(pdf, file_path: Path,
                        use_alt_text_generator: bool = False,
                        alt_text_models: list[str] | None = None,
                        alt_text_context: str = "") -> list[dict]:
    """Add alt text to images in the PDF structure tree.

    When use_alt_text_generator is True, extracts images via PyMuPDF
    and generates real alt text. Otherwise reports as needs-human.
    """
    if not use_alt_text_generator:
        return [{"rule": "PDFUA.IMG.ALT", "status": "needs-human",
                 "reason": "Alt text requires describing image content — "
                           "enable alt-text-generator or use Acrobat Pro",
                 "acrobat_steps": [
                     "Acrobat Pro → Tags panel → locate <Figure> tags",
                     "Right-click → Properties → add Alt Text",
                     "Or: Tools → Accessibility → Set Alternate Text",
                 ]}]

    try:
        from alt_text.client import generate_for_document
        from alt_text.config import load_config

        config = load_config()
        report = generate_for_document(
            file_path, config=config,
            models=alt_text_models, profile="auto",
        )

        if not report.images:
            return [{"rule": "PDFUA.IMG.ALT", "status": "skipped",
                     "reason": "No images found in PDF"}]

        results = []
        for img_opt in report.images:
            if img_opt.options:
                best = img_opt.options[0]
                # Write alt text back to PDF structure tree
                wrote = _write_alt_to_structure(
                    pdf, best.concise_alt, img_opt.page_number, img_opt.image_index
                )
                if wrote:
                    results.append({
                        "rule": "PDFUA.IMG.ALT",
                        "status": "fixed",
                        "detail": f"Page {img_opt.page_number}, image {img_opt.image_index}: "
                                  f"'{best.concise_alt[:80]}...'",
                    })
                else:
                    results.append({
                        "rule": "PDFUA.IMG.ALT",
                        "status": "needs-human",
                        "reason": f"Generated alt text but could not write to structure tree "
                                  f"(page {img_opt.page_number}). Use Acrobat Pro to set: "
                                  f"'{best.concise_alt[:80]}'",
                    })
            else:
                errors = "; ".join(e.message for e in img_opt.errors)
                results.append({
                    "rule": "PDFUA.IMG.ALT",
                    "status": "failed",
                    "reason": f"Page {img_opt.page_number}: {errors}",
                })

        return results if results else [
            {"rule": "PDFUA.IMG.ALT", "status": "skipped", "reason": "No images needed alt text"}
        ]
    except ImportError:
        return [{"rule": "PDFUA.IMG.ALT", "status": "needs-human",
                 "reason": "alt_text package not available — install httpx and PyMuPDF"}]
    except Exception as exc:
        return [{"rule": "PDFUA.IMG.ALT", "status": "failed",
                 "reason": f"Alt text generation error: {exc}"}]


def _write_alt_to_structure(pdf, alt_text: str, page_num: int | None,
                            image_index: int) -> bool:
    """Try to write alt text to a Figure tag in the PDF structure tree."""
    try:
        struct_root = pdf.Root.get("/StructTreeRoot")
        if struct_root is None:
            return False

        kids = struct_root.get("/K")
        if kids is None:
            return False

        # Walk structure tree looking for Figure elements
        figure_count = 0
        for elem in _walk_struct_tree(kids):
            s_type = str(elem.get("/S", ""))
            if s_type in ("/Figure", "Figure"):
                if figure_count == image_index:
                    elem[pikepdf.Name("/Alt")] = pikepdf.String(alt_text)
                    return True
                figure_count += 1
        return False
    except Exception:
        return False


def _walk_struct_tree(node):
    """Yield structure elements from the tree."""
    if isinstance(node, pikepdf.Array):
        for item in node:
            yield from _walk_struct_tree(item)
    elif isinstance(node, pikepdf.Dictionary):
        yield node
        kids = node.get("/K")
        if kids is not None:
            yield from _walk_struct_tree(kids)


# ---------------------------------------------------------------------------
# Main fix orchestrator
# ---------------------------------------------------------------------------

_ALL_RULES = {
    # Tier 1 — Metadata
    "PDFUA.METADATA.TITLE": _fix_title,
    "PDFUA.METADATA.DISPLAY_TITLE": _fix_display_doc_title,
    "PDFUA.METADATA.LANG": _fix_language,
    "PDFUA.NAV.TAB_ORDER": _fix_tab_order,
    "PDFUA.METADATA.PDFUA_ID": _fix_pdfua_identifier,
    "PDFUA.STRUCTURE.MARKED": _fix_marked_content,
    # Tier 2 — Structural
    "PDFUA.FORM.TU": _fix_form_tooltips,
    "PDFUA.TABLE.HEADERS": _fix_table_headers,
    "PDFBP.HEADING.SKIP": _fix_heading_skip,
    # Tier 3 (upgradeable to Tier 2) — Alt text
    "PDFUA.IMG.ALT": _fix_image_alt_text,
}


def fix_pdf(file_path: Path, output_path: Path | None = None,
            rules: list[str] | None = None,
            title: str = "", lang: str = "en-US") -> dict:
    """Apply accessibility fixes to a PDF document.

    Args:
        file_path: Path to the original .pdf file.
        output_path: Where to save the fixed file. Defaults to <name>-fixed.pdf.
        rules: Optional list of rule IDs to fix. None = fix all.
        title: Custom title text. Empty = placeholder.
        lang: BCP 47 language tag. Default: en-US.

    Returns:
        Dict with keys: file, output, backup, fixes (list), summary.
    """
    if not HAS_PIKEPDF:
        return {"error": "pikepdf is not installed. Run: pip install pikepdf"}

    file_path = Path(file_path)
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}

    if output_path is None:
        output_path = file_path.with_stem(file_path.stem + "-fixed")
    else:
        output_path = Path(output_path)

    backup_path = file_path.with_stem(file_path.stem + "-backup")
    shutil.copy2(file_path, backup_path)

    with pikepdf.open(file_path) as pdf:
        all_fixes = []
        target_rules = rules if rules else list(_ALL_RULES.keys())

        for rule_id in target_rules:
            if rule_id not in _ALL_RULES:
                all_fixes.append({"rule": rule_id, "status": "unknown", "reason": f"Rule {rule_id} not supported for auto-fix"})
                continue

            func = _ALL_RULES[rule_id]
            if rule_id == "PDFUA.METADATA.TITLE":
                result = func(pdf, title)
            elif rule_id == "PDFUA.METADATA.LANG":
                result = func(pdf, lang)
            elif rule_id == "PDFUA.IMG.ALT":
                result = func(pdf, file_path)
            else:
                result = func(pdf)

            if isinstance(result, list):
                all_fixes.extend(result)
            else:
                all_fixes.append(result)

        pdf.save(str(output_path))

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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix PDF accessibility issues")
    parser.add_argument("input", help="Path to .pdf file")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--rules", help="Comma-separated rule IDs to fix")
    parser.add_argument("--title", default="", help="Document title")
    parser.add_argument("--lang", default="en-US", help="Document language (BCP 47)")
    args = parser.parse_args()

    rule_list = args.rules.split(",") if args.rules else None
    out = args.output if args.output else None
    result = fix_pdf(Path(args.input), Path(out) if out else None, rule_list, args.title, args.lang)
    print(json.dumps(result, indent=2))
