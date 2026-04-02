"""Built-in accessibility checks (pure pikepdf, no external tools required).

This module implements a suite of PDF accessibility checks that run entirely
within Python using pikepdf. Checks cover PDF/UA-1 and WCAG 2.1 Level AA
requirements including structure tree presence, language, title, alt text on
figures, form fields, heading hierarchy, table headers, and more.

No external tools (Java, veraPDF) are needed. This module is the primary
checker that covers the most common accessibility issues.

Public API
----------
BuiltinChecker   -- Runs all built-in checks on a PdfDocument and returns
                    a list[Finding].
"""
from __future__ import annotations

import logging
import re

import pikepdf

from pdf_a11y.core.validator import Finding

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve(obj: pikepdf.Object) -> pikepdf.Object:
    """Resolve indirect references."""
    while isinstance(obj, pikepdf.Object) and hasattr(obj, "is_indirect") and obj.is_indirect:
        try:
            obj = obj.get_object()
        except Exception:
            break
    return obj


def _get_struct_tree_root(pdf: pikepdf.Pdf) -> pikepdf.Dictionary | None:
    """Return the StructTreeRoot dictionary, or None."""
    try:
        s = pdf.Root.get("/StructTreeRoot")
        if s is None:
            return None
        return pikepdf.Dictionary(s)
    except Exception:
        return None


def _walk_struct_tree(node: pikepdf.Object) -> list[pikepdf.Object]:
    """Yield all structure elements in depth-first order."""
    results: list[pikepdf.Object] = []
    _walk_struct_tree_recursive(node, results)
    return results


def _walk_struct_tree_recursive(
    node: pikepdf.Object, results: list[pikepdf.Object]
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
            _walk_struct_tree_recursive(child, results)
    elif isinstance(kids, pikepdf.Dictionary):
        _walk_struct_tree_recursive(kids, results)


def _heading_level(type_name: str) -> int | None:
    """Return the heading level (1-6) if type_name is H1..H6, else None."""
    m = re.match(r"^H(\d)$", type_name)
    if m:
        return int(m.group(1))
    return None


def _page_index_for_element(
    element: pikepdf.Dictionary, pdf: pikepdf.Pdf
) -> int | None:
    """Try to determine the page index for a structure element."""
    pg = element.get("/Pg")
    if pg is None:
        return None
    try:
        pg = _resolve(pg)
        for i, page in enumerate(pdf.pages):
            if page.obj == pg:
                return i
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_title(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFUA.TITLE: document must have a non-empty Title."""
    title = ""
    try:
        title = str(pdf.docinfo.get("/Title", "")).strip()
    except Exception:
        pass
    if not title:
        return [
            Finding(
                rule_id="PDFUA.TITLE",
                severity="error",
                wcag="2.4.2",
                description="Document title is missing.",
                remediation="Set the document title in File > Properties > Description > Title.",
            )
        ]
    return []


def _check_language(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFUA.LANG: catalog /Lang must be set."""
    lang = ""
    try:
        lang_val = pdf.Root.get("/Lang")
        if lang_val is not None:
            lang = str(lang_val).strip()
    except Exception:
        pass
    if not lang:
        return [
            Finding(
                rule_id="PDFUA.LANG",
                severity="error",
                wcag="3.1.1",
                description="Document language is not set.",
                remediation=(
                    "Set the document language in File > Properties > "
                    "Advanced > Language (e.g. 'en-US')."
                ),
            )
        ]
    return []


def _check_tagged(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFUA.TAGGED: PDF must have a StructTreeRoot and MarkInfo/Marked = true."""
    findings: list[Finding] = []
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        findings.append(
            Finding(
                rule_id="PDFUA.TAGGED",
                severity="error",
                wcag="1.3.1",
                description="PDF is not tagged (no StructTreeRoot).",
                remediation=(
                    "Add a structure tree to the document. Re-export from "
                    "the authoring tool with 'Tagged PDF' enabled."
                ),
            )
        )
        return findings

    # Check MarkInfo/Marked
    try:
        mark_info = pdf.Root.get("/MarkInfo")
        if mark_info is not None:
            marked = mark_info.get("/Marked")
            if marked is None or not bool(marked):
                findings.append(
                    Finding(
                        rule_id="PDFUA.TAGGED",
                        severity="error",
                        wcag="1.3.1",
                        description="MarkInfo/Marked is not set to true.",
                        remediation="Set MarkInfo/Marked to true in the document catalog.",
                    )
                )
        else:
            findings.append(
                Finding(
                    rule_id="PDFUA.TAGGED",
                    severity="error",
                    wcag="1.3.1",
                    description="MarkInfo dictionary is missing.",
                    remediation="Add MarkInfo with Marked=true to the document catalog.",
                )
            )
    except Exception:
        pass

    return findings


def _check_empty_struct_tree(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFUA.TAGGED: struct tree exists but has no child elements."""
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []  # Already caught by _check_tagged
    kids = str_root.get("/K")
    if kids is None:
        return [
            Finding(
                rule_id="PDFUA.TAGGED",
                severity="error",
                wcag="1.3.1",
                description="Structure tree is present but empty (no child elements).",
                remediation="Tag document content inside structure elements.",
            )
        ]
    try:
        kids = _resolve(kids)
        if isinstance(kids, pikepdf.Array) and len(kids) == 0:
            return [
                Finding(
                    rule_id="PDFUA.TAGGED",
                    severity="error",
                    wcag="1.3.1",
                    description="Structure tree is present but empty (no child elements).",
                    remediation="Tag document content inside structure elements.",
                )
            ]
    except Exception:
        pass
    return []


def _check_figure_alt_text(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFUA.IMG.ALT: Figure elements must have an /Alt attribute."""
    findings: list[Finding] = []
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []

    for elem in _walk_struct_tree(str_root):
        try:
            s_type = str(elem.get("/S", ""))
            if s_type in ("/Figure", "Figure"):
                alt = elem.get("/Alt")
                if alt is None or str(alt).strip() == "":
                    page = _page_index_for_element(elem, pdf)
                    findings.append(
                        Finding(
                            rule_id="PDFUA.IMG.ALT",
                            severity="error",
                            wcag="1.1.1",
                            description="Figure element does not have alt text.",
                            page=page + 1 if page is not None else None,
                            remediation=(
                                "Add descriptive alt text to the Figure element, "
                                "or mark it as an artifact if decorative."
                            ),
                        )
                    )
        except Exception:
            continue

    return findings


def _check_headings(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFUA.HEADINGS: heading levels must not be skipped."""
    findings: list[Finding] = []
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []

    prev_level = 0
    for elem in _walk_struct_tree(str_root):
        try:
            s_type = str(elem.get("/S", ""))
            # Strip leading slash if present
            clean = s_type.lstrip("/")
            level = _heading_level(clean)
            if level is not None:
                if prev_level > 0 and level > prev_level + 1:
                    page = _page_index_for_element(elem, pdf)
                    findings.append(
                        Finding(
                            rule_id="PDFUA.HEADINGS",
                            severity="warning",
                            wcag="2.4.6",
                            description=(
                                f"Heading level skipped: H{prev_level} to H{level}."
                            ),
                            page=page + 1 if page is not None else None,
                            remediation=(
                                "Ensure heading levels do not skip "
                                f"(expected H{prev_level + 1} before H{level})."
                            ),
                        )
                    )
                prev_level = level
        except Exception:
            continue

    return findings


def _check_table_headers(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.TABLE_HEADERS / PDFBP.TABLE_SCOPE: tables need TH with Scope."""
    findings: list[Finding] = []
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []

    for elem in _walk_struct_tree(str_root):
        try:
            s_type = str(elem.get("/S", "")).lstrip("/")
            if s_type == "Table":
                # Walk children looking for TH elements
                table_elements = _walk_struct_tree(elem)
                has_th = False
                for te in table_elements:
                    te_type = str(te.get("/S", "")).lstrip("/")
                    if te_type == "TH":
                        has_th = True
                        # Check for Scope attribute
                        attrs = te.get("/A")
                        has_scope = False
                        if attrs is not None:
                            attrs = _resolve(attrs)
                            if isinstance(attrs, pikepdf.Dictionary):
                                has_scope = attrs.get("/Scope") is not None
                            elif isinstance(attrs, pikepdf.Array):
                                for a in attrs:
                                    a = _resolve(a)
                                    if isinstance(a, pikepdf.Dictionary):
                                        if a.get("/Scope") is not None:
                                            has_scope = True
                                            break
                        if not has_scope:
                            page = _page_index_for_element(te, pdf)
                            findings.append(
                                Finding(
                                    rule_id="PDFBP.TABLE_SCOPE",
                                    severity="warning",
                                    wcag="1.3.1",
                                    description=(
                                        "TH element is missing the Scope attribute."
                                    ),
                                    page=page + 1 if page is not None else None,
                                    remediation=(
                                        "Set the Scope attribute on each TH to "
                                        "'Row', 'Column', or 'Both'."
                                    ),
                                )
                            )
                if not has_th:
                    page = _page_index_for_element(elem, pdf)
                    findings.append(
                        Finding(
                            rule_id="PDFBP.TABLE_HEADERS",
                            severity="warning",
                            wcag="1.3.1",
                            description="Table has no header cells (TH elements).",
                            page=page + 1 if page is not None else None,
                            remediation=(
                                "Add TH elements to the first row or column."
                            ),
                        )
                    )
        except Exception:
            continue

    return findings


def _check_form_fields(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFUA.FORMS: form fields must have TU (tooltip) and T (name)."""
    findings: list[Finding] = []
    try:
        acro_form = pdf.Root.get("/AcroForm")
        if acro_form is None:
            return []
        acro_form = _resolve(acro_form)
        fields = acro_form.get("/Fields")
        if fields is None:
            return []
        fields = _resolve(fields)
        if not isinstance(fields, pikepdf.Array):
            return []
    except Exception:
        return []

    for field in fields:
        try:
            field = _resolve(field)
            if not isinstance(field, pikepdf.Dictionary):
                continue
            name = field.get("/T")
            tooltip = field.get("/TU")
            if tooltip is None or str(tooltip).strip() == "":
                findings.append(
                    Finding(
                        rule_id="PDFUA.FORMS",
                        severity="error",
                        wcag="4.1.2",
                        description="Form field is missing a tooltip (TU entry).",
                        element=str(name) if name is not None else None,
                        remediation=(
                            "Add a tooltip (TU) to each interactive form field "
                            "for screen reader accessibility."
                        ),
                    )
                )
            if name is None or str(name).strip() == "":
                findings.append(
                    Finding(
                        rule_id="PDFUA.FORMS",
                        severity="error",
                        wcag="4.1.2",
                        description="Form field is missing a name (T entry).",
                        remediation="Set the T (name) entry on each form field.",
                    )
                )
        except Exception:
            continue

    return findings


def _check_bookmarks(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFUA.BOOKMARKS: documents with >20 pages should have bookmarks."""
    try:
        page_count = len(pdf.pages)
    except Exception:
        return []
    if page_count <= 20:
        return []
    try:
        outlines = pdf.Root.get("/Outlines")
        if outlines is None:
            return [
                Finding(
                    rule_id="PDFUA.BOOKMARKS",
                    severity="warning",
                    wcag="2.4.1",
                    description=(
                        f"Document has {page_count} pages but no bookmarks."
                    ),
                    remediation=(
                        "Add bookmarks (Outlines) that mirror the heading structure."
                    ),
                )
            ]
    except Exception:
        pass
    return []


def _check_display_doc_title(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.DISPLAY_TITLE: ViewerPreferences/DisplayDocTitle should be true."""
    try:
        vp = pdf.Root.get("/ViewerPreferences")
        if vp is None:
            return [
                Finding(
                    rule_id="PDFBP.DISPLAY_TITLE",
                    severity="warning",
                    wcag="2.4.2",
                    description="DisplayDocTitle is not set (no ViewerPreferences).",
                    remediation=(
                        "Set ViewerPreferences/DisplayDocTitle to true so "
                        "the title shows in the title bar."
                    ),
                )
            ]
        vp = _resolve(vp)
        ddt = vp.get("/DisplayDocTitle")
        if ddt is None or not bool(ddt):
            return [
                Finding(
                    rule_id="PDFBP.DISPLAY_TITLE",
                    severity="warning",
                    wcag="2.4.2",
                    description="DisplayDocTitle is not set to true.",
                    remediation=(
                        "Set ViewerPreferences/DisplayDocTitle to true so "
                        "the title shows in the title bar."
                    ),
                )
            ]
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Main checker class
# ---------------------------------------------------------------------------

# All registered checks, run in order.
_CHECKS = [
    _check_title,
    _check_language,
    _check_tagged,
    _check_empty_struct_tree,
    _check_figure_alt_text,
    _check_headings,
    _check_table_headers,
    _check_form_fields,
    _check_bookmarks,
    _check_display_doc_title,
]


class BuiltinChecker:
    """Run all built-in accessibility checks on a pikepdf.Pdf.

    Usage::

        checker = BuiltinChecker()
        findings = checker.run(pdf)

    Each finding uses the same :class:`Finding` dataclass as the veraPDF
    validator, so results from both sources can be combined seamlessly.
    """

    def run(self, pdf: pikepdf.Pdf) -> list[Finding]:
        """Run every built-in check and return combined findings."""
        findings: list[Finding] = []
        for check_fn in _CHECKS:
            try:
                findings.extend(check_fn(pdf))
            except Exception as exc:
                logger.error("Built-in check %s failed: %s", check_fn.__name__, exc)
        return findings

    def run_on_document(self, doc: "pdf_a11y.core.document.PdfDocument") -> list[Finding]:
        """Convenience: run checks on a :class:`PdfDocument` wrapper.

        Raises :class:`ValueError` if no document is open.
        """
        return self.run(doc.pdf)
