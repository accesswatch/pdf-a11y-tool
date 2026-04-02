"""Audit report generation (Markdown and CSV).

This module takes a list of Finding objects and renders them as
human-readable Markdown or machine-readable CSV reports, suitable for
export or inclusion in documentation.

When an optional ``pikepdf.Pdf`` object is supplied, the Markdown report
includes deep analysis sections: PDF metadata, consolidated findings,
form fields assessment, reading order assessment, a simulated screen
reader preview, and a projected after-remediation scorecard.

Public API
----------
ReportFormat     -- Enum: MARKDOWN or CSV.
ReportGenerator  -- Accepts findings and a document path; produces a
                    formatted report string or writes to a file.
"""
from __future__ import annotations

import contextlib
import csv
import enum
import io
import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pikepdf

from pdf_a11y.core.validator import Finding

logger = logging.getLogger(__name__)


class ReportFormat(enum.Enum):
    """Supported report output formats."""

    MARKDOWN = "markdown"
    CSV = "csv"


class ReportAudience(enum.Enum):
    """Target audience for remediation instructions.

    TOOL  -- Instructions reference PDF Accessibility Tool shortcuts and panels.
    ACROBAT -- Instructions reference Adobe Acrobat Pro menus and dialogs.
    """

    TOOL = "tool"
    ACROBAT = "acrobat"


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

# Weight per severity level used for the accessibility score.
_SEVERITY_WEIGHTS: dict[str, float] = {
    "error": 5.0,
    "warning": 2.0,
    "tip": 0.5,
}

# Grade thresholds (inclusive lower bound).
_GRADE_THRESHOLDS: list[tuple[int, str]] = [
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (50, "D"),
    (0, "F"),
]


def compute_score(findings: list[Finding]) -> tuple[int, str]:
    """Compute an accessibility score (0-100) and letter grade.

    ``Score = max(0, 100 - sum(weight_per_finding))``.
    """
    penalty = sum(_SEVERITY_WEIGHTS.get(f.severity, 1.0) for f in findings)
    score = max(0, int(100 - penalty))
    grade = "F"
    for threshold, letter in _GRADE_THRESHOLDS:
        if score >= threshold:
            grade = letter
            break
    return score, grade


# ---------------------------------------------------------------------------
# pikepdf helpers (shared with builtin_checks.py)
# ---------------------------------------------------------------------------

def _resolve(obj: pikepdf.Object) -> pikepdf.Object:
    """Resolve indirect references."""
    while isinstance(obj, pikepdf.Object) and hasattr(obj, "is_indirect") and obj.is_indirect:
        with contextlib.suppress(Exception):
            obj = obj.get_object()
            continue
        break
    return obj


def _get_struct_tree_root(pdf: pikepdf.Pdf) -> pikepdf.Dictionary | None:
    try:
        s = pdf.Root.get("/StructTreeRoot")
        if s is None:
            return None
        return pikepdf.Dictionary(s)
    except Exception:
        return None


def _walk_elements(node: pikepdf.Object) -> list[pikepdf.Dictionary]:
    """Return all StructElem dictionaries depth-first."""
    results: list[pikepdf.Dictionary] = []
    _walk_elements_r(node, results)
    return results


def _walk_elements_r(
    node: pikepdf.Object, results: list[pikepdf.Dictionary]
) -> None:
    try:
        node = _resolve(node)
    except Exception:
        return
    if not isinstance(node, pikepdf.Dictionary):
        return
    results.append(node)
    kids = node.get("/K")
    if kids is None:
        return
    try:
        kids = _resolve(kids)
    except Exception:
        return
    if isinstance(kids, pikepdf.Array):
        for child in kids:
            _walk_elements_r(child, results)
    elif isinstance(kids, pikepdf.Dictionary):
        _walk_elements_r(kids, results)


def _page_index(elem: pikepdf.Dictionary, pdf: pikepdf.Pdf) -> int | None:
    """Zero-based page index for a StructElem, or None."""
    pg = elem.get("/Pg")
    if pg is None:
        return None
    try:
        pg = _resolve(pg)
        for idx, page in enumerate(pdf.pages):
            if page.obj.objgen == pg.objgen:
                return idx
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# PDF metadata extraction
# ---------------------------------------------------------------------------

def _extract_metadata(pdf: pikepdf.Pdf) -> dict[str, str]:
    """Extract document metadata from the PDF /Info dictionary."""
    meta: dict[str, str] = {}
    try:
        info = pdf.docinfo
        for key, label in [
            ("/Title", "title"),
            ("/Author", "author"),
            ("/Creator", "source_application"),
            ("/Producer", "producer"),
            ("/CreationDate", "created"),
            ("/ModDate", "modified"),
        ]:
            val = info.get(key)
            if val is not None:
                raw = str(val)
                # Parse PDF date format D:YYYYMMDDHHmmSS
                if label in ("created", "modified") and raw.startswith("D:"):
                    raw = _format_pdf_date(raw)
                meta[label] = raw
    except Exception:
        pass
    try:
        meta["pages"] = str(len(pdf.pages))
    except Exception:
        pass
    try:
        meta["pdf_version"] = str(pdf.pdf_version)
    except Exception:
        pass
    try:
        lang = pdf.Root.get("/Lang")
        if lang is not None:
            meta["language"] = str(lang)
    except Exception:
        pass
    return meta


def _format_pdf_date(raw: str) -> str:
    """Convert D:20260209... to a human-readable date."""
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?(\d{2})?", raw)
    if not m:
        return raw
    parts = [m.group(1), m.group(2), m.group(3)]
    date_str = "-".join(parts)
    if m.group(4) and m.group(5):
        date_str += f" {m.group(4)}:{m.group(5)}"
    return date_str


# ---------------------------------------------------------------------------
# Consolidated findings (group duplicates)
# ---------------------------------------------------------------------------

def _consolidate_findings(findings: list[Finding]) -> list[dict]:
    """Group findings by (rule_id, description-stem) and add counts.

    Returns a list of dicts with keys: rule_id, severity, wcag, description,
    count, pages, finding (sample Finding object).
    """
    groups: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        # Group by rule_id (ignore page-specific details)
        groups[f.rule_id].append(f)

    consolidated: list[dict] = []
    for rule_id, group in groups.items():
        pages = sorted({f.page for f in group if f.page is not None})
        page_str = ", ".join(str(p) for p in pages) if pages else "doc"
        consolidated.append({
            "rule_id": rule_id,
            "severity": group[0].severity,
            "wcag": group[0].wcag,
            "description": group[0].description,
            "count": len(group),
            "pages": page_str,
            "finding": group[0],
        })
    return consolidated


# ---------------------------------------------------------------------------
# Form fields analysis
# ---------------------------------------------------------------------------

def _analyze_form_fields(pdf: pikepdf.Pdf) -> dict:
    """Enumerate AcroForm fields and return analysis data."""
    result: dict = {
        "total": 0,
        "fields": [],
        "missing_tooltip": 0,
        "missing_name": 0,
        "has_tooltips": 0,
        "field_types": Counter(),
    }
    try:
        acro_form = pdf.Root.get("/AcroForm")
        if acro_form is None:
            return result
        acro_form = _resolve(acro_form)
        fields = acro_form.get("/Fields")
        if fields is None:
            return result
        fields = _resolve(fields)
        if not isinstance(fields, pikepdf.Array):
            return result
    except Exception:
        return result

    for field_obj in fields:
        try:
            field_obj = _resolve(field_obj)
            if not isinstance(field_obj, pikepdf.Dictionary):
                continue
            name = str(field_obj.get("/T", "")) if field_obj.get("/T") else ""
            tooltip = str(field_obj.get("/TU", "")) if field_obj.get("/TU") else ""
            ft = str(field_obj.get("/FT", "")).lstrip("/") if field_obj.get("/FT") else "Unknown"
            ff = 0
            with contextlib.suppress(Exception):
                ff = int(field_obj.get("/Ff", 0))

            field_info = {
                "name": name,
                "tooltip": tooltip,
                "type": ft,
                "flags": ff,
                "required": bool(ff & 2),  # bit 2 = Required
            }
            result["fields"].append(field_info)
            result["total"] += 1
            result["field_types"][ft] += 1
            if not tooltip.strip():
                result["missing_tooltip"] += 1
            else:
                result["has_tooltips"] += 1
            if not name.strip():
                result["missing_name"] += 1
        except Exception:
            continue

    return result


# ---------------------------------------------------------------------------
# Reading order analysis
# ---------------------------------------------------------------------------

def _analyze_reading_order(pdf: pikepdf.Pdf) -> dict:
    """Analyze the structure tree reading order."""
    result: dict = {
        "total_elements": 0,
        "by_page": defaultdict(lambda: {"count": 0, "tags": Counter()}),
        "tag_counts": Counter(),
        "has_structure": False,
        "leaf_sequence": [],
    }
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return result
    result["has_structure"] = True

    elements = _walk_elements(str_root)
    for elem in elements:
        try:
            s_type = str(elem.get("/S", "")).lstrip("/")
            if not s_type:
                continue
            result["total_elements"] += 1
            result["tag_counts"][s_type] += 1
            page = _page_index(elem, pdf)
            if page is not None:
                result["by_page"][page + 1]["count"] += 1
                result["by_page"][page + 1]["tags"][s_type] += 1

            # Track leaf-level items for reading order sequence
            k = elem.get("/K")
            if k is not None:
                is_leaf = False
                try:
                    k = _resolve(k)
                    if isinstance(k, pikepdf.Array):
                        has_content = any(
                            not isinstance(_resolve(item), pikepdf.Dictionary)
                            or str(_resolve(item).get("/Type", "")) in ("/MCR", "/OBJR")
                            for item in k
                        )
                        has_child = any(
                            isinstance(_resolve(item), pikepdf.Dictionary)
                            and "/S" in _resolve(item)
                            for item in k
                        )
                        is_leaf = has_content and not has_child
                    elif not isinstance(k, pikepdf.Dictionary) or str(k.get("/Type", "")) in ("/MCR", "/OBJR"):
                        is_leaf = True
                except Exception:
                    pass
                if is_leaf:
                    result["leaf_sequence"].append({
                        "tag": s_type,
                        "page": (page + 1) if page is not None else None,
                        "alt": str(elem.get("/Alt", "")).strip() if elem.get("/Alt") else "",
                    })
        except Exception:
            continue

    return result


# ---------------------------------------------------------------------------
# Screen reader preview simulation
# ---------------------------------------------------------------------------

def _simulate_screen_reader(
    pdf: pikepdf.Pdf, findings: list[Finding]
) -> list[str]:
    """Produce a simulated screen reader linearized text preview.

    Walks the structure tree and produces lines like:
      Heading level 1: Document Title       (p.1)
      Text field: First Name                (p.1)
      WARNING: field missing tooltip
    """
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return ["(No structure tree -- screen readers cannot navigate this document)"]

    # Build a set of warnings keyed by (rule_id, page)
    warnings_by_page: dict[int | None, list[str]] = defaultdict(list)
    for f in findings:
        if f.severity == "error":
            warnings_by_page[f.page].append(f"WARNING: {f.description}")
        elif f.severity == "warning" and f.rule_id in (
            "PDFBP.TABLE_SCOPE", "PDFBP.NONSTD_NO_ALT", "PDFBP.NO_HEADINGS"
        ):
            warnings_by_page[f.page].append(f"WARNING: {f.description}")

    lines: list[str] = []
    _SR_TAG_LABELS = {
        "H1": "Heading level 1",
        "H2": "Heading level 2",
        "H3": "Heading level 3",
        "H4": "Heading level 4",
        "H5": "Heading level 5",
        "H6": "Heading level 6",
        "P": "",
        "Span": "",
        "Table": "Table",
        "TR": "",
        "TH": "Column header",
        "TD": "",
        "L": "List",
        "LI": "List item",
        "LBody": "",
        "Figure": "Image",
        "Form": "Text field",
        "Link": "Link",
        "Sect": "",
        "Document": "",
        "Part": "",
        "Art": "",
        "Div": "",
        "BlockQuote": "Block quote",
        "Caption": "Caption",
        "InlineShape": "Image",
        "Textbox": "Text box",
    }

    elements = _walk_elements(str_root)
    for elem in elements:
        try:
            s_type = str(elem.get("/S", "")).lstrip("/")
            if not s_type or s_type in ("Document", "StructTreeRoot", "Sect", "Part", "Art", "Div", "TR"):
                continue

            # Check if leaf
            k = elem.get("/K")
            if k is None:
                continue
            try:
                k_resolved = _resolve(k)
                has_content = False
                has_child_se = False
                items = list(k_resolved) if isinstance(k_resolved, pikepdf.Array) else [k_resolved]
                for item in items:
                    try:
                        item = _resolve(item)
                    except Exception:
                        continue
                    try:
                        int(item)
                        has_content = True
                        continue
                    except (TypeError, ValueError):
                        pass
                    if isinstance(item, pikepdf.Dictionary):
                        if "/S" in item:
                            has_child_se = True
                        elif str(item.get("/Type", "")) in ("/MCR", "/OBJR"):
                            has_content = True
                if not has_content or has_child_se:
                    # Container or empty -- could still announce tables
                    if s_type == "Table":
                        page = _page_index(elem, pdf)
                        page_str = f"(p.{page + 1})" if page is not None else ""
                        # Count rows and columns
                        rows = sum(
                            1 for e in _walk_elements(elem)
                            if str(e.get("/S", "")).lstrip("/") == "TR"
                        )
                        cols = 0
                        for e in _walk_elements(elem):
                            if str(e.get("/S", "")).lstrip("/") == "TR":
                                cols = sum(
                                    1 for c in _walk_elements(e)
                                    if str(c.get("/S", "")).lstrip("/") in ("TH", "TD")
                                )
                                break
                        lines.append(
                            f"Table with {rows} rows and {cols} columns"
                            f"  {page_str}".rstrip()
                        )
                    elif s_type == "L":
                        page = _page_index(elem, pdf)
                        page_str = f"(p.{page + 1})" if page is not None else ""
                        items_count = sum(
                            1 for e in _walk_elements(elem)
                            if str(e.get("/S", "")).lstrip("/") == "LI"
                        )
                        lines.append(f"List with {items_count} items  {page_str}".rstrip())
                    continue
            except Exception:
                continue

            page = _page_index(elem, pdf)
            page_str = f"(p.{page + 1})" if page is not None else ""
            label = _SR_TAG_LABELS.get(s_type, s_type)

            # Get text content from /Alt, /ActualText, or field /TU
            text = ""
            alt = elem.get("/Alt")
            if alt is not None:
                text = str(alt).strip()
            if not text:
                actual = elem.get("/ActualText")
                if actual is not None:
                    text = str(actual).strip()

            # For Form elements, try to get field name from OBJR
            if s_type == "Form" and not text:
                try:
                    for item in items:
                        item = _resolve(item)
                        if isinstance(item, pikepdf.Dictionary):
                            if str(item.get("/Type", "")) == "/OBJR":
                                obj_ref = item.get("/Obj")
                                if obj_ref is not None:
                                    obj_ref = _resolve(obj_ref)
                                    tu = obj_ref.get("/TU")
                                    if tu:
                                        text = str(tu).strip()
                                    elif obj_ref.get("/T"):
                                        text = str(obj_ref["/T"]).strip()
                except Exception:
                    pass

            if label and text:
                lines.append(f"{label}: {text}  {page_str}".rstrip())
            elif label:
                lines.append(f"{label}  {page_str}".rstrip())
            elif text:
                lines.append(f"{text}  {page_str}".rstrip())

            # Inject any warnings relevant to this element type on this page
            if s_type == "TH":
                # Check scope
                attrs = elem.get("/A")
                has_scope = False
                if attrs is not None:
                    with contextlib.suppress(Exception):
                        attrs = _resolve(attrs)
                        if isinstance(attrs, pikepdf.Dictionary):
                            has_scope = attrs.get("/Scope") is not None
                        elif isinstance(attrs, pikepdf.Array):
                            for a in attrs:
                                a = _resolve(a)
                                if isinstance(a, pikepdf.Dictionary) and a.get("/Scope") is not None:
                                    has_scope = True
                                    break
                if not has_scope:
                    lines.append("  WARNING: header has no Scope attribute")

        except Exception:
            continue

    # Append document-level warnings
    for w in warnings_by_page.get(None, []):
        lines.append(w)

    return lines


# ---------------------------------------------------------------------------
# Deep analysis per issue type
# ---------------------------------------------------------------------------

_WCAG_NAMES: dict[str, str] = {
    "1.1.1": "Non-text Content",
    "1.3.1": "Info and Relationships",
    "1.3.2": "Meaningful Sequence",
    "2.4.1": "Bypass Blocks",
    "2.4.2": "Page Titled",
    "2.4.3": "Focus Order",
    "2.4.6": "Headings and Labels",
    "3.1.1": "Language of Page",
    "4.1.2": "Name, Role, Value",
}


def _deep_analysis_section(
    findings: list[Finding],
    pdf: pikepdf.Pdf,
    audience: ReportAudience,
) -> list[str]:
    """Generate deep analysis sections for significant issues."""
    lines: list[str] = []
    consolidated = _consolidate_findings(findings)
    issue_number = 0

    for entry in consolidated:
        rule_id = entry["rule_id"]
        count = entry["count"]
        f = entry["finding"]

        # Only produce deep analysis for notable issues
        if rule_id in (
            "PDFUA.TITLE", "PDFBP.NO_HEADINGS", "PDFBP.NONSTD_NO_ALT",
            "PDFBP.TABLE_SCOPE", "PDFBP.TABLE_HEADERS",
            "PDFBP.FLAT_STRUCTURE", "PDFBP.FORMS_DETACHED",
            "PDFBP.UNDERSCORE_FILL", "PDFUA.FORMS",
            "PDFUA.IMG.ALT", "PDFUA.HEADINGS",
        ):
            issue_number += 1
            lines.extend(_deep_analysis_for_rule(
                issue_number, rule_id, count, entry, pdf, audience
            ))

    return lines


def _deep_analysis_for_rule(
    issue_num: int,
    rule_id: str,
    count: int,
    entry: dict,
    pdf: pikepdf.Pdf,
    audience: ReportAudience,
) -> list[str]:
    """Return deep analysis lines for a specific rule."""
    lines: list[str] = []
    f: Finding = entry["finding"]
    severity_label = {"error": "CRITICAL", "warning": "Important", "tip": "Recommended"}.get(
        f.severity, f.severity.capitalize()
    )
    wcag_name = _WCAG_NAMES.get(f.wcag, "")
    wcag_ref = f"{f.wcag} ({wcag_name})" if wcag_name else f.wcag
    count_str = f" (x{count})" if count > 1 else ""

    lines.append(f"### Issue {issue_num}: {_friendly_rule_name(rule_id)}{count_str}")
    lines.append("")
    lines.append(f"**Severity**: {severity_label}")
    lines.append(f"**WCAG**: {wcag_ref}")
    lines.append(f"**Impact**: {_impact_description(rule_id)}")
    lines.append("")

    # "What the tool detects" section
    detect_text = _what_tool_detects(rule_id, count, pdf)
    if detect_text:
        lines.append("**What the tool detects:**")
        lines.append("")
        lines.append(detect_text)
        lines.append("")

    # Inventory tables for rules with multiple occurrences
    inventory = _inventory_table(rule_id, pdf)
    if inventory:
        lines.extend(inventory)

    # Remediation steps
    lines.append(f"#### How to fix: {_audience_label(audience)}")
    lines.append("")
    fix_steps = _detailed_fix_steps(rule_id, audience)
    for i, step in enumerate(fix_steps, 1):
        lines.append(f"{i}. {step}")
    lines.append("")

    # Also show the other tool's steps
    other = ReportAudience.ACROBAT if audience == ReportAudience.TOOL else ReportAudience.TOOL
    lines.append(f"#### How to fix: {_audience_label(other)}")
    lines.append("")
    other_steps = _detailed_fix_steps(rule_id, other)
    for i, step in enumerate(other_steps, 1):
        lines.append(f"{i}. {step}")
    lines.append("")
    lines.append("---")
    lines.append("")

    return lines


def _friendly_rule_name(rule_id: str) -> str:
    """Map a rule_id to a human-friendly issue title."""
    names: dict[str, str] = {
        "PDFUA.TITLE": "Missing Document Title",
        "PDFBP.NO_HEADINGS": "No Headings",
        "PDFBP.NONSTD_NO_ALT": "Non-Standard Tags Without Alt Text",
        "PDFBP.TABLE_SCOPE": "Table Headers Missing Scope",
        "PDFBP.TABLE_HEADERS": "Table Missing Header Cells",
        "PDFBP.FLAT_STRUCTURE": "Flat Document Structure",
        "PDFBP.FORMS_DETACHED": "Form Fields Detached From Labels",
        "PDFBP.UNDERSCORE_FILL": "Underscore Fill Patterns",
        "PDFUA.FORMS": "Form Fields Missing Tooltips",
        "PDFUA.IMG.ALT": "Images Missing Alt Text",
        "PDFUA.HEADINGS": "Heading Hierarchy Issues",
        "PDFUA.BOOKMARKS": "Missing Bookmarks",
        "PDFBP.DISPLAY_TITLE": "Display Document Title Not Set",
        "PDFBP.NAV.TABORDER": "Tab Order Not Set to Structure",
    }
    return names.get(rule_id, rule_id)


def _impact_description(rule_id: str) -> str:
    """Return an impact description for a rule."""
    impacts: dict[str, str] = {
        "PDFUA.TITLE": (
            "Screen readers announce the filename instead of a meaningful "
            "title when opening the document."
        ),
        "PDFBP.NO_HEADINGS": (
            "Screen reader users cannot navigate between form sections. "
            "The document may have clear visual sections but they are all "
            "tagged as paragraphs instead of heading tags."
        ),
        "PDFBP.NONSTD_NO_ALT": (
            "Screen readers encounter unnamed non-text elements. Users "
            "hear the tag type name (e.g., 'InlineShape') with no context "
            "about what the element represents."
        ),
        "PDFBP.TABLE_SCOPE": (
            "Screen readers cannot associate data cells with their headers "
            "when navigating the table, making data relationships unclear."
        ),
        "PDFBP.TABLE_HEADERS": (
            "Without header cells, screen readers cannot announce column "
            "or row labels when navigating data cells."
        ),
        "PDFBP.FLAT_STRUCTURE": (
            "A flat tag tree with many direct children and no sections "
            "makes it impossible for screen reader users to navigate "
            "by section or understand the document's organization."
        ),
        "PDFBP.FORMS_DETACHED": (
            "Screen readers encounter all text first, then all fields, "
            "making it impossible to associate fields with their labels."
        ),
        "PDFBP.UNDERSCORE_FILL": (
            "Screen readers announce each underscore character individually, "
            "creating a poor experience. These should be marked as artifacts "
            "if a form field is overlaid."
        ),
        "PDFUA.FORMS": (
            "Form fields without tooltips are announced as unlabeled "
            "to screen reader users, who cannot determine the field's purpose."
        ),
        "PDFUA.IMG.ALT": (
            "Images without alternative text are invisible to screen reader "
            "users. The content or function conveyed by the image is lost."
        ),
        "PDFUA.HEADINGS": (
            "Skipped heading levels (e.g., H1 followed by H3) disrupt "
            "screen reader heading navigation and suggest missing content."
        ),
    }
    return impacts.get(rule_id, "Assistive technology users may have difficulty with this content.")


def _what_tool_detects(rule_id: str, count: int, pdf: pikepdf.Pdf) -> str:
    """Return a 'What the tool detects' explanation for a rule."""
    if rule_id == "PDFUA.TITLE":
        display = ""
        with contextlib.suppress(Exception):
            vp = pdf.Root.get("/ViewerPreferences")
            if vp is not None:
                vp = _resolve(vp)
                dt = vp.get("/DisplayDocTitle")
                if dt is not None and str(dt).lower() == "true":
                    display = " The DisplayDocTitle viewer preference is already set to true, which means once a title is added it will be displayed correctly."
        return (
            f"The built-in checker flags PDFUA.TITLE as an error. The Document "
            f"Properties panel shows the Title field as empty.{display}"
        )

    if rule_id == "PDFBP.NO_HEADINGS":
        str_root = _get_struct_tree_root(pdf)
        p_count = 0
        if str_root is not None:
            for elem in _walk_elements(str_root):
                if str(elem.get("/S", "")).lstrip("/") == "P":
                    p_count += 1
        return (
            f"The structure tree contains {p_count} /P tags and zero /H1 through /H6 tags. "
            f"The Tag Tree panel displays this flat list of paragraphs, making the problem "
            f"immediately visible. The Screen Reader Preview shows \"{p_count} consecutive "
            f"paragraphs with no headings\" and the Headings Only mode returns \"0 headings found.\""
        )

    if rule_id == "PDFBP.NONSTD_NO_ALT":
        return (
            f"The Tag Tree panel shows {count} non-standard tag(s) without /Alt attributes. "
            f"The Alt Text panel lists these as \"{count} non-standard elements missing alt text\" "
            f"and displays thumbnails of the rendered page regions."
        )

    if rule_id == "PDFBP.TABLE_SCOPE":
        return (
            f"The Table Editor shows {count} TH cell(s) with no Scope attribute. "
            f"Without Scope, screen readers cannot determine whether each header "
            f"applies to its row or column."
        )

    if rule_id == "PDFBP.FLAT_STRUCTURE":
        child_count = 0
        str_root = _get_struct_tree_root(pdf)
        if str_root is not None:
            k = str_root.get("/K")
            if k is not None:
                with contextlib.suppress(Exception):
                    k = _resolve(k)
                    if isinstance(k, pikepdf.Array):
                        child_count = len(k)
        return (
            f"The document root has {child_count} direct children with no /Sect, /Part, "
            f"or /Art grouping elements. The Tag Tree shows a flat list of elements "
            f"that should be organized into logical sections."
        )

    if rule_id == "PDFBP.FORMS_DETACHED":
        return (
            "The reading order analysis shows form fields grouped in a contiguous "
            "block at the end of the structure tree, separated from their visual "
            "labels. The Auto-Sort Reading Order tool can detect and fix this by "
            "interleaving fields with their labels."
        )

    return ""


def _inventory_table(rule_id: str, pdf: pikepdf.Pdf) -> list[str]:
    """Return an inventory table for rules with multiple elements."""
    lines: list[str] = []

    if rule_id == "PDFBP.NONSTD_NO_ALT":
        str_root = _get_struct_tree_root(pdf)
        if str_root is None:
            return lines
        role_map = {}
        with contextlib.suppress(Exception):
            rm = pdf.Root.get("/StructTreeRoot")
            if rm is not None:
                rm = _resolve(rm)
                rm_dict = rm.get("/RoleMap")
                if rm_dict is not None:
                    rm_dict = _resolve(rm_dict)
                    if isinstance(rm_dict, pikepdf.Dictionary):
                        for k in rm_dict:
                            role_map[str(k).lstrip("/")] = str(rm_dict[k]).lstrip("/")

        items: list[dict] = []
        idx = 0
        for elem in _walk_elements(str_root):
            s_type = str(elem.get("/S", "")).lstrip("/")
            if not s_type:
                continue
            if s_type in role_map or s_type not in (
                "Document", "StructTreeRoot", "P", "H1", "H2", "H3", "H4",
                "H5", "H6", "Span", "Table", "TR", "TH", "TD", "L", "LI",
                "LBody", "Figure", "Form", "Link", "Sect", "Part", "Art",
                "Div", "BlockQuote", "Quote", "Note", "Caption", "Label",
            ):
                alt = elem.get("/Alt")
                actual = elem.get("/ActualText")
                if (alt is None or not str(alt).strip()) and (actual is None or not str(actual).strip()):
                    page = _page_index(elem, pdf)
                    maps_to = role_map.get(s_type, "")
                    items.append({
                        "index": idx,
                        "page": (page + 1) if page is not None else "?",
                        "tag": s_type,
                        "maps_to": maps_to,
                    })
                    idx += 1

        if items:
            lines.append("**Detailed inventory:**")
            lines.append("")
            lines.append("| Index | Page | Tag | Maps To | Recommended Action |")
            lines.append("|-------|------|-----|---------|-------------------|")
            for item in items:
                action = "Mark as decorative artifact" if item["tag"] in ("InlineShape",) else "Add alt text or change type"
                lines.append(
                    f"| {item['index']} | {item['page']} | /{item['tag']} | "
                    f"{item['maps_to']} | {action} |"
                )
            lines.append("")

    if rule_id == "PDFBP.TABLE_SCOPE":
        str_root = _get_struct_tree_root(pdf)
        if str_root is None:
            return lines
        th_count = 0
        for elem in _walk_elements(str_root):
            if str(elem.get("/S", "")).lstrip("/") == "TH":
                th_count += 1
        if th_count:
            lines.append(f"The table contains {th_count} TH cells that all require Scope attributes.")
            lines.append("")

    return lines


def _detailed_fix_steps(rule_id: str, audience: ReportAudience) -> list[str]:
    """Return multi-step numbered fix instructions for a rule and audience."""
    if audience == ReportAudience.TOOL:
        return _tool_fix_steps(rule_id)
    return _acrobat_fix_steps(rule_id)


def _tool_fix_steps(rule_id: str) -> list[str]:
    """PDF Accessibility Tool remediation steps."""
    steps: dict[str, list[str]] = {
        "PDFUA.TITLE": [
            "Open **Document Properties** (Alt+Enter).",
            "**Tab** to the Title field.",
            "Type the document title.",
            "Press **Enter** to apply. The tool writes the title to both /Info /Title and XMP dc:title metadata simultaneously.",
            "The checker reruns automatically and the PDFUA.TITLE error clears from the Issues panel.",
        ],
        "PDFBP.NO_HEADINGS": [
            "**Tag Tree panel** (Alt+3): Use the arrow keys to navigate to each bold section header.",
            "Press **F2** to open the Change Type editor. Select /H1 for the document title, /H2 for sections.",
            "Press **Enter** to confirm. Repeat for each heading.",
            "Alternatively, use **Auto-Tagger** (Alt+T, A): Review the heading candidate list, press **Space** to accept/reject each, then **Enter** on Apply.",
            "After applying, the **Screen Reader Preview** refreshes to show the new heading structure.",
        ],
        "PDFBP.NONSTD_NO_ALT": [
            "**Alt Text Panel** (Alt+4): The non-standard elements are listed.",
            "For decorative items: Press **Space** on the \"Mark as decorative\" checkbox.",
            "Press **Alt+N** to advance to the next element and repeat.",
            "For meaningful images: Type appropriate alt text in the field and press Enter.",
            "Alternatively, in the **Tag Tree**: Navigate to each element, press **Delete** and choose \"Mark as Artifact\" for decorative items.",
        ],
        "PDFBP.TABLE_SCOPE": [
            "In the **Table Editor**, Tab to the first header cell.",
            "Press **Enter** to select it.",
            "Use the **Scope dropdown** to set Row or Column.",
            "Press **Enter** to apply. Repeat for each TH cell.",
        ],
        "PDFBP.TABLE_HEADERS": [
            "In the **Table Editor**, select the first row of cells.",
            "Press **Ctrl+H** to convert TD cells to TH header cells.",
            "Then set Scope on each new header cell.",
        ],
        "PDFBP.FLAT_STRUCTURE": [
            "In the **Tag Tree**, select the Document root.",
            "Press **Insert** to add a /Sect child.",
            "Select related heading and content elements, press **Ctrl+X** to cut.",
            "Arrow to the Sect element, press **Ctrl+V** to paste.",
            "Repeat for each logical section of the document.",
        ],
        "PDFBP.FORMS_DETACHED": [
            "Use **Auto-Sort Reading Order** (Alt+T, R) to interleave form fields with their labels.",
            "Preview the proposed order in the dialog.",
            "Press **Enter** to apply. Each field is reparented to follow its label.",
            "Ctrl+Z undoes all changes if needed.",
        ],
        "PDFBP.UNDERSCORE_FILL": [
            "In the **Tag Tree**, navigate to each paragraph with underscore fills.",
            "If a form field overlaps, press **Delete** and choose 'Mark as Artifact'.",
            "The **'Clean All Underscore Fills'** batch action (Alt+T, U) processes all flagged elements at once.",
        ],
        "PDFUA.FORMS": [
            "In the **Field Properties panel**, Tab to the Tooltip field.",
            "Enter a descriptive label that matches the visual label.",
            "Press **Enter** to apply. Repeat for each field.",
        ],
        "PDFUA.IMG.ALT": [
            "**Alt Text Panel** (Alt+4): The images are listed.",
            "For each image, type appropriate alt text describing the content.",
            "Press **Enter** to apply, then **Alt+N** for next image.",
            "For decorative images, check **Mark as decorative** instead.",
        ],
        "PDFUA.HEADINGS": [
            "In the **Tag Tree** (Alt+3), navigate to the heading with the wrong level.",
            "Press **F2** to open the Change Type editor.",
            "Select the correct heading level (H1-H6) maintaining proper hierarchy.",
            "Press **Enter** to confirm.",
        ],
    }
    return steps.get(rule_id, ["Follow the remediation guidance in the Findings section above."])


def _acrobat_fix_steps(rule_id: str) -> list[str]:
    """Adobe Acrobat Pro remediation steps."""
    steps: dict[str, list[str]] = {
        "PDFUA.TITLE": [
            "Open **File > Properties** (Ctrl+D).",
            "In the **Description** tab, Tab to the Title field.",
            "Type the title and press **OK**.",
            "Open File > Properties again, go to **Initial View** tab, verify \"Show\" is set to \"Document Title\".",
        ],
        "PDFBP.NO_HEADINGS": [
            "Open the **Tags panel** (View > Show/Hide > Navigation Panes > Tags).",
            "Expand the tag tree and locate each paragraph that should be a heading.",
            "Select the /P tag, press **Ctrl+E** to open Properties.",
            "In the **Tag** tab, change the Type from P to H1 (title) or H2 (sections). Press **OK**.",
            "Repeat for all heading candidates.",
        ],
        "PDFBP.NONSTD_NO_ALT": [
            "In the **Tags panel**, select the non-standard tag.",
            "Press **Ctrl+E** to open Properties.",
            "Enter **Alternative Text** for meaningful content.",
            "For decorative items, change Type to **Artifact**.",
        ],
        "PDFBP.TABLE_SCOPE": [
            "In the **Tags panel**, select a TH tag.",
            "Press **Ctrl+E** to open Properties > Tag tab.",
            "Set **Scope** to Row or Column.",
            "Press **OK**. Repeat for each TH cell.",
        ],
        "PDFBP.TABLE_HEADERS": [
            "In the **Tags panel**, select each TD in the header row.",
            "Press **Ctrl+E** to open Properties.",
            "Change **Type** from TD to TH.",
            "Then set Scope to Column. Press **OK**.",
        ],
        "PDFBP.FLAT_STRUCTURE": [
            "In the **Tags panel**, create new Sect tags under Document.",
            "Drag or cut/paste related heading and content tags into each section.",
        ],
        "PDFBP.FORMS_DETACHED": [
            "In the **Tags panel**, cut each Form tag (Ctrl+X).",
            "Paste it (Ctrl+V) after the P tag that contains its label text.",
            "Repeat for each field. Or use the **Order panel** to drag fields inline.",
        ],
        "PDFBP.UNDERSCORE_FILL": [
            "In the **Tags panel**, find each paragraph with underscore fills.",
            "If a form field overlaps, select the tag.",
            "Press **Ctrl+E**, change Type to **Artifact**. Press **OK**.",
        ],
        "PDFUA.FORMS": [
            "Select the form field in the document.",
            "Open Properties (**Ctrl+E**), General tab.",
            "Enter a descriptive **Tooltip** matching the visual label.",
            "Press **OK**. Repeat for each field.",
        ],
        "PDFUA.IMG.ALT": [
            "In the **Tags panel**, select the Figure tag.",
            "Press **Ctrl+E** to open Properties.",
            "Enter **Alternative Text** describing the image content.",
            "For decorative images, change type to Artifact.",
        ],
        "PDFUA.HEADINGS": [
            "In the **Tags panel**, select the heading tag.",
            "Press **Ctrl+E** to open Properties.",
            "Change the **Type** to the correct heading level (H1-H6).",
            "Press **OK**.",
        ],
    }
    return steps.get(rule_id, ["Follow the remediation guidance in the Findings section above."])


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def _findings_by_severity(findings: list[Finding]) -> dict[str, list[Finding]]:
    groups: dict[str, list[Finding]] = {"error": [], "warning": [], "tip": []}
    for f in findings:
        groups.setdefault(f.severity, []).append(f)
    return groups


def _findings_by_page(findings: list[Finding]) -> dict[int | None, list[Finding]]:
    groups: dict[int | None, list[Finding]] = {}
    for f in findings:
        groups.setdefault(f.page, []).append(f)
    return groups


def _remediation_for_audience(
    finding: Finding, audience: ReportAudience
) -> str:
    """Return the remediation text appropriate for the audience."""
    if audience == ReportAudience.ACROBAT:
        return finding.acrobat_remediation or finding.remediation
    return finding.remediation


def _audience_label(audience: ReportAudience) -> str:
    """Human-readable label for the target audience."""
    if audience == ReportAudience.ACROBAT:
        return "Adobe Acrobat Pro"
    return "PDF Accessibility Tool"


def generate_markdown(
    findings: list[Finding],
    pdf_path: str | Path | None = None,
    verapdf_used: bool = False,
    audience: ReportAudience = ReportAudience.TOOL,
    pdf: pikepdf.Pdf | None = None,
) -> str:
    """Generate a Markdown accessibility audit report.

    Parameters
    ----------
    audience:
        Controls which remediation instructions appear.  ``TOOL`` emits
        PDF Accessibility Tool instructions; ``ACROBAT`` emits Adobe
        Acrobat Pro instructions.
    pdf:
        Optional open ``pikepdf.Pdf`` object.  When supplied the report
        includes deep analysis sections: PDF metadata, consolidated
        findings, form fields assessment, reading order, screen reader
        preview, and projected scores.
    """
    lines: list[str] = []
    score, grade = compute_score(findings)
    by_severity = _findings_by_severity(findings)
    error_count = len(by_severity.get("error", []))
    warning_count = len(by_severity.get("warning", []))
    tip_count = len(by_severity.get("tip", []))
    total = len(findings)
    tool_label = _audience_label(audience)
    file_stem = Path(pdf_path).stem if pdf_path else "document"
    file_name = Path(pdf_path).name if pdf_path else ""

    # ------------------------------------------------------------------
    # Header -- use document title style like old reports
    # ------------------------------------------------------------------
    lines.append(f"# PDF Accessibility Audit Report: {file_stem}")
    lines.append("")

    # ------------------------------------------------------------------
    # Audit Information (enriched with PDF metadata when available)
    # ------------------------------------------------------------------
    lines.append("## Audit Information")
    lines.append("")
    lines.append(f"- **Date**: {datetime.now(timezone.utc).strftime('%B %d, %Y')}")
    lines.append(f"- **Tool**: PDF Accessibility Tool v0.1.0 (built-in checks only{', veraPDF enabled' if verapdf_used else ', veraPDF not installed'})")
    if file_name:
        lines.append(f"- **File**: {file_name}")

    if pdf is not None:
        meta = _extract_metadata(pdf)
        if meta.get("source_application"):
            lines.append(f"- **Source application**: {meta['source_application']}")
        if meta.get("author"):
            lines.append(f"- **Author**: {meta['author']}")
        if meta.get("created"):
            lines.append(f"- **Created**: {meta['created']}")
        if meta.get("pages"):
            lines.append(f"- **Pages**: {meta['pages']}")
        if meta.get("pdf_version"):
            lines.append(f"- **PDF version**: {meta['pdf_version']}")
    lines.append("")

    # ------------------------------------------------------------------
    # Executive Summary (narrative style)
    # ------------------------------------------------------------------
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- **Score**: {score}/100 (Grade: {grade})")
    lines.append(f"- **Errors**: {error_count}")
    lines.append(f"- **Warnings**: {warning_count}")

    # Count deep analysis issues (only when pdf available)
    deep_count = 0
    if pdf is not None:
        consolidated = _consolidate_findings(findings)
        deep_rules = {
            "PDFUA.TITLE", "PDFBP.NO_HEADINGS", "PDFBP.NONSTD_NO_ALT",
            "PDFBP.TABLE_SCOPE", "PDFBP.TABLE_HEADERS", "PDFBP.FLAT_STRUCTURE",
            "PDFBP.FORMS_DETACHED", "PDFBP.UNDERSCORE_FILL", "PDFUA.FORMS",
            "PDFUA.IMG.ALT", "PDFUA.HEADINGS",
        }
        deep_count = sum(1 for c in consolidated if c["rule_id"] in deep_rules)
        if deep_count:
            lines.append(f"- **Deep analysis issues**: {deep_count}")
    lines.append(f"- **Total actionable issues**: {total}")
    lines.append("")

    if total == 0:
        lines.append("No accessibility issues were found. The document meets all checked requirements.")
        lines.append("")
        return "\n".join(lines)

    # Narrative summary
    if pdf is not None:
        lines.append(_narrative_summary(findings, pdf, file_stem))
        lines.append("")

    # ------------------------------------------------------------------
    # Built-in Checker Findings (consolidated table)
    # ------------------------------------------------------------------
    consolidated = _consolidate_findings(findings)
    lines.append("## Built-in Checker Findings")
    lines.append("")
    lines.append("| Severity | Rule ID | WCAG | Page | Description |")
    lines.append("|----------|---------|------|------|-------------|")
    for entry in consolidated:
        count_str = f" (x{entry['count']})" if entry["count"] > 1 else ""
        lines.append(
            f"| {entry['severity'].capitalize()} | {entry['rule_id']} | "
            f"{entry['wcag']} | {entry['pages']} | "
            f"{entry['description']}{count_str} |"
        )
    lines.append("")

    # ------------------------------------------------------------------
    # Deep Analysis Findings (when pdf available)
    # ------------------------------------------------------------------
    if pdf is not None:
        deep_lines = _deep_analysis_section(findings, pdf, audience)
        if deep_lines:
            lines.append("## Deep Analysis Findings")
            lines.append("")
            lines.append(
                "The following issues were identified through structure tree "
                "analysis, reading order mapping, and content flow analysis."
            )
            lines.append("")
            lines.append(
                "Each issue includes two remediation paths so you can use "
                "whichever tool you prefer:"
            )
            lines.append("")
            lines.append("- **PDF Accessibility Tool**: Our tool, with fully keyboard-operable instructions")
            lines.append("- **Adobe Acrobat Pro**: The industry-standard commercial alternative")
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.extend(deep_lines)

    # ------------------------------------------------------------------
    # Form Fields Assessment (when pdf available)
    # ------------------------------------------------------------------
    if pdf is not None:
        form_lines = _form_fields_assessment(pdf, findings)
        if form_lines:
            lines.extend(form_lines)

    # ------------------------------------------------------------------
    # Reading Order Assessment (when pdf available)
    # ------------------------------------------------------------------
    if pdf is not None:
        ro_lines = _reading_order_assessment(pdf, findings)
        if ro_lines:
            lines.extend(ro_lines)

    # ------------------------------------------------------------------
    # Screen Reader Preview (when pdf available)
    # ------------------------------------------------------------------
    if pdf is not None:
        sr_lines = _simulate_screen_reader(pdf, findings)
        if sr_lines:
            lines.append("## Screen Reader Preview (Simulated)")
            lines.append("")
            lines.append(
                "This section approximates what a screen reader (NVDA, JAWS, "
                "VoiceOver) would announce when reading this document from top "
                "to bottom. Warnings are inserted inline where a screen reader "
                "user would encounter the problem."
            )
            lines.append("")
            lines.append("```")
            for sr_line in sr_lines:
                lines.append(sr_line)
            lines.append("```")
            lines.append("")

    # ------------------------------------------------------------------
    # Remediation Priority (with dual-tool columns)
    # ------------------------------------------------------------------
    lines.append("## Remediation Priority")
    lines.append("")

    priority_sections = [
        ("Immediate (Errors -- must fix for PDF/UA conformance)", "error"),
        ("Soon (Warnings -- significant accessibility improvement)", "warning"),
        ("When Possible (Tips)", "tip"),
    ]
    for section_title, severity in priority_sections:
        sev_findings = by_severity.get(severity, [])
        if not sev_findings:
            continue
        lines.append(f"### {section_title}")
        lines.append("")

        # Dual-tool table format
        if pdf is not None:
            lines.append("| Priority | Issue | WCAG | PDF Accessibility Tool | Adobe Acrobat Pro |")
            lines.append("|----------|-------|------|----------------------|-------------------|")
            seen_rules: set[str] = set()
            priority_num = 0
            for f in sev_findings:
                if f.rule_id in seen_rules:
                    continue
                seen_rules.add(f.rule_id)
                priority_num += 1
                tool_fix = f.remediation.split(". ")[0] + "." if f.remediation else ""
                acrobat_fix = f.acrobat_remediation.split(". ")[0] + "." if f.acrobat_remediation else ""
                lines.append(
                    f"| {priority_num} | {_friendly_rule_name(f.rule_id)} | "
                    f"{f.wcag} | {tool_fix} | {acrobat_fix} |"
                )
            lines.append("")
        else:
            for f in sev_findings:
                lines.append(f"1. **{f.rule_id}**: {f.description}")
                fix_text = _remediation_for_audience(f, audience)
                if fix_text:
                    lines.append(f"   - {fix_text}")
            lines.append("")

    # ------------------------------------------------------------------
    # Accessibility Scorecard (with projected after-remediation)
    # ------------------------------------------------------------------
    lines.append("## Accessibility Scorecard")
    lines.append("")

    if pdf is not None:
        projected_score = min(100, score + int(error_count * 5 + warning_count * 2 + tip_count * 0.5))
        projected_grade = "F"
        for threshold, letter in _GRADE_THRESHOLDS:
            if projected_score >= threshold:
                projected_grade = letter
                break

        lines.append("| Metric | Current | After Remediation (Projected) |")
        lines.append("|--------|---------|-------------------------------|")
        lines.append(f"| Score | {score}/100 | {projected_score}/100 |")
        lines.append(f"| Grade | {grade} | {projected_grade} |")
        lines.append(f"| Errors | {error_count} | 0 |")
        lines.append(f"| Warnings | {warning_count} | 0 |")

        # Additional metrics from PDF analysis
        ro = _analyze_reading_order(pdf)
        heading_count = sum(
            1 for tag, cnt in ro["tag_counts"].items()
            if re.match(r"^H\d$", tag)
        )
        figure_count = ro["tag_counts"].get("Figure", 0)
        form_data = _analyze_form_fields(pdf)

        if heading_count == 0 and any(f.rule_id == "PDFBP.NO_HEADINGS" for f in findings):
            lines.append("| Headings | 0 | 5+ (estimated after fix) |")
        else:
            lines.append(f"| Headings | {heading_count} | {heading_count} |")

        if form_data["total"] > 0:
            lines.append(
                f"| Form fields with tooltips | {form_data['has_tooltips']}/{form_data['total']} "
                f"| {form_data['total']}/{form_data['total']} |"
            )
    else:
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Score | {score}/100 |")
        lines.append(f"| Grade | {grade} |")
        lines.append(f"| Errors | {error_count} |")
        lines.append(f"| Warnings | {warning_count} |")
        lines.append(f"| Tips | {tip_count} |")
    lines.append("")

    return "\n".join(lines)


def _narrative_summary(
    findings: list[Finding], pdf: pikepdf.Pdf, file_stem: str
) -> str:
    """Generate a narrative description of the document and its problems."""
    meta = _extract_metadata(pdf)
    ro = _analyze_reading_order(pdf)
    form_data = _analyze_form_fields(pdf)

    parts: list[str] = []

    # Describe the document type
    source = meta.get("source_application", "")
    if "Word" in source:
        parts.append(f"This is a document created in Microsoft Word")
    elif "Excel" in source:
        parts.append(f"This is a spreadsheet created in Microsoft Excel")
    elif "PowerPoint" in source:
        parts.append(f"This is a presentation created in Microsoft PowerPoint")
    else:
        parts.append(f"This is a PDF document")

    pages = meta.get("pages", "")
    if pages:
        parts[-1] += f" ({pages} pages)"
    parts[-1] += "."

    # Describe what's tagged
    if ro["has_structure"]:
        parts.append(f"The document is tagged with {ro['total_elements']} structure elements.")
    else:
        parts.append("The document is not tagged, making it largely inaccessible to screen readers.")

    # Form fields
    if form_data["total"] > 0:
        parts.append(f"It contains {form_data['total']} form fields.")

    # Key problems
    error_rules = {f.rule_id for f in findings if f.severity == "error"}
    warning_rules = {f.rule_id for f in findings if f.severity == "warning"}
    problems: list[str] = []
    if "PDFUA.TITLE" in error_rules:
        problems.append("missing document title")
    if "PDFBP.NO_HEADINGS" in warning_rules:
        problems.append("no heading structure")
    if "PDFBP.NONSTD_NO_ALT" in warning_rules:
        nonstandard_count = sum(1 for f in findings if f.rule_id == "PDFBP.NONSTD_NO_ALT")
        problems.append(f"{nonstandard_count} non-standard elements without alt text")
    if "PDFBP.TABLE_SCOPE" in warning_rules:
        scope_count = sum(1 for f in findings if f.rule_id == "PDFBP.TABLE_SCOPE")
        problems.append(f"table header cells without scope attributes (x{scope_count})")
    if "PDFBP.FORMS_DETACHED" in error_rules:
        problems.append("form fields detached from their labels in reading order")
    if "PDFUA.FORMS" in error_rules:
        form_count = sum(1 for f in findings if f.rule_id == "PDFUA.FORMS")
        problems.append(f"{form_count} form field(s) missing tooltips")

    if problems:
        parts.append(
            "Key issues include: " + ", ".join(problems) + "."
        )

    return " ".join(parts)


def _form_fields_assessment(
    pdf: pikepdf.Pdf, findings: list[Finding]
) -> list[str]:
    """Generate a Form Fields Assessment section."""
    form_data = _analyze_form_fields(pdf)
    if form_data["total"] == 0:
        return []

    lines: list[str] = []
    lines.append("## Form Fields Assessment")
    lines.append("")
    lines.append(f"The document contains **{form_data['total']} form fields**.")
    lines.append("")

    # Positive findings
    positives: list[str] = []
    if form_data["has_tooltips"] > 0:
        pct = int(form_data["has_tooltips"] / form_data["total"] * 100)
        positives.append(
            f"{form_data['has_tooltips']} of {form_data['total']} fields "
            f"({pct}%) have tooltips"
        )

    # Count required fields
    required = sum(1 for f in form_data["fields"] if f["required"])
    if required > 0:
        positives.append(f"{required} field(s) marked as required")

    if positives:
        lines.append("**Positive findings:**")
        lines.append("")
        for p in positives:
            lines.append(f"- {p}")
        lines.append("")

    # Fields inventory table
    if form_data["fields"]:
        lines.append("**Field inventory:**")
        lines.append("")
        lines.append("| Name | Type | Tooltip | Required |")
        lines.append("|------|------|---------|----------|")
        for f in form_data["fields"]:
            tt = f["tooltip"] if f["tooltip"] else "(missing)"
            req = "Yes" if f["required"] else ""
            ft_name = {"Tx": "Text", "Btn": "Button", "Ch": "Choice", "Sig": "Signature"}.get(
                f["type"], f["type"]
            )
            lines.append(f"| {f['name']} | {ft_name} | {tt} | {req} |")
        lines.append("")

    # Improvement opportunities
    improvements: list[str] = []
    if form_data["missing_tooltip"] > 0:
        improvements.append(
            f"Add tooltips to {form_data['missing_tooltip']} field(s) "
            f"missing them (WCAG 4.1.2)"
        )
    if required == 0 and form_data["total"] > 3:
        improvements.append(
            "Consider marking key fields as required so screen readers "
            "announce their mandatory status"
        )

    # Check for detached forms
    has_detached = any(f.rule_id == "PDFBP.FORMS_DETACHED" for f in findings)
    if has_detached:
        improvements.append(
            "Reorder form fields to interleave with their labels "
            "(currently grouped at end of reading order)"
        )

    if improvements:
        lines.append("**Improvement opportunities:**")
        lines.append("")
        lines.append("| Finding | Recommendation |")
        lines.append("|---------|---------------|")
        for imp in improvements:
            lines.append(f"| {imp.split('(')[0].strip()} | {imp} |")
        lines.append("")

    return lines


def _reading_order_assessment(
    pdf: pikepdf.Pdf, findings: list[Finding]
) -> list[str]:
    """Generate a Reading Order Assessment section."""
    ro = _analyze_reading_order(pdf)
    if not ro["has_structure"]:
        return []

    lines: list[str] = []
    lines.append("## Reading Order Assessment")
    lines.append("")
    lines.append(
        f"The structure tree defines reading order for "
        f"{ro['total_elements']} elements across "
        f"{len(ro['by_page'])} page(s)."
    )
    lines.append("")

    # Per-page breakdown
    for page_num in sorted(ro["by_page"].keys()):
        info = ro["by_page"][page_num]
        tag_summary = ", ".join(
            f"{count} {tag}" for tag, count in info["tags"].most_common(5)
        )
        lines.append(f"**Page {page_num}** ({info['count']} elements): {tag_summary}")
        lines.append("")

    # Reading order warnings
    has_detached = any(f.rule_id == "PDFBP.FORMS_DETACHED" for f in findings)
    has_flat = any(f.rule_id == "PDFBP.FLAT_STRUCTURE" for f in findings)

    if has_detached or has_flat:
        lines.append("**Reading order issues:**")
        lines.append("")
        if has_detached:
            lines.append(
                "- Form fields are grouped at the end of the reading order, "
                "separated from their labels. Screen readers will read all "
                "text first, then encounter all form fields without context."
            )
        if has_flat:
            lines.append(
                "- The document has a flat structure with no sectioning. "
                "Screen reader users cannot jump between sections."
            )
        lines.append("")

    # Recommendations
    lines.append("**Recommendations:**")
    lines.append("")
    if has_detached:
        lines.append(
            "- Use Auto-Sort Reading Order (Alt+T, R) to interleave "
            "form fields with their labels."
        )
    if has_flat:
        lines.append(
            "- Add /Sect grouping elements to organize content into "
            "logical sections."
        )
    heading_count = sum(
        cnt for tag, cnt in ro["tag_counts"].items()
        if re.match(r"^H\d$", tag)
    )
    if heading_count == 0:
        lines.append(
            "- Add headings (H1-H6) to provide navigational landmarks."
        )
    lines.append(
        "- Use the Reading Order overlay (Ctrl+Shift+O) to visually "
        "verify element sequence."
    )
    lines.append("")

    return lines


# ---------------------------------------------------------------------------
# CSV report
# ---------------------------------------------------------------------------


def generate_csv(
    findings: list[Finding],
    audience: ReportAudience = ReportAudience.TOOL,
) -> str:
    """Generate a CSV report with one row per finding.

    The *Remediation* column contains instructions for the selected
    ``audience`` only.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    tool_label = _audience_label(audience)
    writer.writerow(
        ["Rule ID", "Severity", "WCAG", "Page", "Element", "Description",
         f"Remediation ({tool_label})"]
    )
    for f in findings:
        writer.writerow(
            [
                f.rule_id,
                f.severity,
                f.wcag,
                f.page if f.page is not None else "",
                f.element or "",
                f.description,
                _remediation_for_audience(f, audience),
            ]
        )
    return output.getvalue()


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------


class ReportGenerator:
    """Generate accessibility reports in Markdown or CSV format.

    Usage::

        gen = ReportGenerator(findings, pdf_path="doc.pdf")
        md_text = gen.generate(ReportFormat.MARKDOWN)  # default: TOOL audience
        gen.write(ReportFormat.CSV, "report.csv", audience=ReportAudience.ACROBAT)

        # Write both reports at once:
        paths = gen.write_all(ReportFormat.MARKDOWN, "reports/")

        # Deep analysis (pass the pikepdf.Pdf object):
        gen = ReportGenerator(findings, pdf_path="doc.pdf", pdf=pdf)
        md_text = gen.generate(ReportFormat.MARKDOWN)
    """

    def __init__(
        self,
        findings: list[Finding],
        pdf_path: str | Path | None = None,
        verapdf_used: bool = False,
        pdf: pikepdf.Pdf | None = None,
    ) -> None:
        self._findings = findings
        self._pdf_path = pdf_path
        self._verapdf_used = verapdf_used
        self._pdf = pdf

    def generate(
        self,
        fmt: ReportFormat = ReportFormat.MARKDOWN,
        audience: ReportAudience = ReportAudience.TOOL,
    ) -> str:
        """Return the report as a string for the given audience."""
        if fmt == ReportFormat.MARKDOWN:
            return generate_markdown(
                self._findings, self._pdf_path, self._verapdf_used,
                audience=audience, pdf=self._pdf,
            )
        elif fmt == ReportFormat.CSV:
            return generate_csv(self._findings, audience=audience)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def write(
        self,
        fmt: ReportFormat,
        output_path: str | Path,
        audience: ReportAudience = ReportAudience.TOOL,
    ) -> Path:
        """Write a single report to a file and return the path."""
        output_path = Path(output_path)
        content = self.generate(fmt, audience=audience)
        output_path.write_text(content, encoding="utf-8")
        logger.info("Report written to %s", output_path)
        return output_path

    def write_all(
        self,
        fmt: ReportFormat,
        output_dir: str | Path,
        stem: str = "AUDIT",
    ) -> list[Path]:
        """Write one report per audience to *output_dir* and return paths.

        For Markdown this produces::

            <stem>-tool.md
            <stem>-acrobat.md

        For CSV::

            <stem>-tool.csv
            <stem>-acrobat.csv
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        ext = ".md" if fmt == ReportFormat.MARKDOWN else ".csv"
        paths: list[Path] = []
        for audience in ReportAudience:
            filename = f"{stem}-{audience.value}{ext}"
            p = self.write(fmt, output_dir / filename, audience=audience)
            paths.append(p)
        return paths
