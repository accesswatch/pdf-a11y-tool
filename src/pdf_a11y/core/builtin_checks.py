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


# Text-bearing tags that contribute to reading order content
_TEXT_TAGS = frozenset({
    "P", "H", "H1", "H2", "H3", "H4", "H5", "H6",
    "Span", "LI", "LBody", "Label", "Caption",
    "TD", "TH", "Figure", "InlineShape", "Textbox",
    "BlockQuote", "Quote", "Note",
})


def _is_leaf(elem: pikepdf.Dictionary) -> bool:
    """True if elem has MCIDs or OBJR (content) and no child struct elems."""
    kids = elem.get("/K")
    if kids is None:
        return False
    try:
        kids = _resolve(kids)
    except Exception:
        return False

    has_content = False
    has_child_se = False

    if isinstance(kids, pikepdf.Array):
        items = list(kids)
    else:
        items = [kids]

    for item in items:
        try:
            item = _resolve(item)
        except Exception:
            continue
        # Integer MCID
        try:
            int(item)
            has_content = True
            continue
        except (TypeError, ValueError):
            pass
        if isinstance(item, pikepdf.Dictionary):
            if "/S" in item:
                has_child_se = True
            else:
                obj_type = str(item.get("/Type", ""))
                if obj_type in ("/MCR", "/OBJR"):
                    has_content = True

    return has_content and not has_child_se


def _classify_leaves(
    node: pikepdf.Object,
) -> list[tuple[str, pikepdf.Object]]:
    """Walk struct tree depth-first and return (kind, elem) for each leaf.

    kind is "form" for /Form elements, "text" for text-bearing elements.
    """
    results: list[tuple[str, pikepdf.Object]] = []
    _classify_leaves_walk(node, results)
    return results


def _classify_leaves_walk(
    node: pikepdf.Object,
    results: list[tuple[str, pikepdf.Object]],
) -> None:
    try:
        node = _resolve(node)
    except Exception:
        return
    if not isinstance(node, pikepdf.Dictionary):
        return

    has_tag = "/S" in node

    if has_tag:
        tag = str(node.get("/S", "")).lstrip("/")

        if _is_leaf(node):
            if tag == "Form":
                results.append(("form", node))
            else:
                results.append(("text", node))
            return

    # Container (or StructTreeRoot which has no /S) -- recurse into /K
    kids = node.get("/K")
    if kids is None:
        return
    try:
        kids = _resolve(kids)
    except Exception:
        return
    if isinstance(kids, pikepdf.Array):
        for child in kids:
            _classify_leaves_walk(child, results)
    elif isinstance(kids, pikepdf.Dictionary):
        _classify_leaves_walk(kids, results)


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
                remediation=(
                    "Open Document Properties (Alt+Enter), Tab to the Title "
                    "field, type the title, then press Enter to apply."
                ),
                acrobat_remediation=(
                    "File > Properties > Description tab > Title field. "
                    "Enter the title and press OK."
                ),
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
                    "Open Document Properties (Alt+Enter), Tab to the "
                    "Language field, type the language code (e.g. 'en-US'), "
                    "then press Enter to apply."
                ),
                acrobat_remediation=(
                    "File > Properties > Advanced tab > Language dropdown. "
                    "Select the language and press OK."
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
                    "Re-export from the source application with "
                    "'Tagged PDF' enabled, or use the Auto-Tagger "
                    "(Alt+T, A) to generate tags from content."
                ),
                acrobat_remediation=(
                    "Accessibility > Autotag Document, or re-export from "
                    "the source application with 'Tagged PDF' enabled."
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
                        remediation=(
                            "Open Document Properties (Alt+Enter) and "
                            "enable the 'Marked' flag."
                        ),
                        acrobat_remediation=(
                            "Re-export with tagging enabled, or use "
                            "Accessibility > Autotag Document."
                        ),
                    )
                )
        else:
            findings.append(
                Finding(
                    rule_id="PDFUA.TAGGED",
                    severity="error",
                    wcag="1.3.1",
                    description="MarkInfo dictionary is missing.",
                    remediation=(
                        "Open Document Properties (Alt+Enter) and "
                        "enable the 'Marked' flag."
                    ),
                    acrobat_remediation=(
                        "Re-export with tagging enabled, or use "
                        "Accessibility > Autotag Document."
                    ),
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
                remediation=(
                    "Use the Auto-Tagger (Alt+T, A) to generate tags "
                    "from document content."
                ),
                acrobat_remediation=(
                    "Accessibility > Autotag Document to generate "
                    "structure from content."
                ),
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
                    remediation=(
                        "Use the Auto-Tagger (Alt+T, A) to generate tags "
                        "from document content."
                    ),
                    acrobat_remediation=(
                        "Accessibility > Autotag Document to generate "
                        "structure from content."
                    ),
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
                                "In the Tag Tree, arrow to the Figure element "
                                "and press F2 to edit alt text. If the image "
                                "is decorative, press Delete and choose "
                                "'Mark as Artifact'."
                            ),
                            acrobat_remediation=(
                                "In the Tags panel, select the Figure tag, "
                                "open Properties (Ctrl+E), and enter "
                                "Alternative Text. For decorative images, "
                                "change the tag to Artifact."
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
                                "In the Tag Tree, arrow to the heading "
                                "element and press F2 to change its type "
                                f"(expected H{prev_level + 1} before H{level})."
                            ),
                            acrobat_remediation=(
                                "In the Tags panel, select the heading tag, "
                                "open Properties (Ctrl+E), and change Type "
                                f"to H{prev_level + 1}."
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
                                        "In the Table Editor, Tab to the header "
                                        "cell, press Enter to select it, then "
                                        "use the Scope dropdown to set Row or "
                                        "Column. Press Enter to apply."
                                    ),
                                    acrobat_remediation=(
                                        "In the Tags panel, select the TH tag, "
                                        "open Properties (Ctrl+E) > Tag tab, "
                                        "and set Scope to Row or Column."
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
                                "In the Table Editor, select the first row "
                                "and press Ctrl+H to convert cells to TH. "
                                "Then set Scope on each header."
                            ),
                            acrobat_remediation=(
                                "In the Tags panel, select each TD in the header "
                                "row, open Properties (Ctrl+E), and change Type "
                                "to TH. Then set Scope to Column."
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
                            "In the Field Properties panel, Tab to the "
                            "Tooltip field and enter a descriptive label. "
                            "Press Enter to apply."
                        ),
                        acrobat_remediation=(
                            "Select the form field, open Properties "
                            "(Ctrl+E), General tab, and enter a Tooltip."
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
                        remediation=(
                            "In the Field Properties panel, Tab to the "
                            "Name field and enter a unique name. "
                            "Press Enter to apply."
                        ),
                        acrobat_remediation=(
                            "Select the form field, open Properties "
                            "(Ctrl+E), General tab, and enter a Name."
                        ),
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
                        "Use Tools > Generate Bookmarks from Headings "
                        "(Alt+T, B). If no headings exist, add headings "
                        "first, then generate bookmarks."
                    ),
                    acrobat_remediation=(
                        "Open the Bookmarks panel (Ctrl+B). Manually add "
                        "bookmarks for each section, or use a plugin to "
                        "generate from headings."
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
                        "Open Document Properties (Alt+Enter), Tab to the "
                        "'Display document title in title bar' checkbox, "
                        "and press Space to enable it."
                    ),
                    acrobat_remediation=(
                        "File > Properties > Initial View tab. Set "
                        "'Show' to 'Document Title'."
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
                        "Open Document Properties (Alt+Enter), Tab to the "
                        "'Display document title in title bar' checkbox, "
                        "and press Space to enable it."
                    ),
                    acrobat_remediation=(
                        "File > Properties > Initial View tab. Set "
                        "'Show' to 'Document Title'."
                    ),
                )
            ]
    except Exception:
        pass
    return []


def _check_no_headings(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.NO_HEADINGS: tagged document should have at least one heading."""
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []  # Untagged -- caught elsewhere

    for elem in _walk_struct_tree(str_root):
        try:
            s_type = str(elem.get("/S", "")).lstrip("/")
            if _heading_level(s_type) is not None:
                return []  # At least one heading exists
        except Exception:
            continue

    return [
        Finding(
            rule_id="PDFBP.NO_HEADINGS",
            severity="warning",
            wcag="2.4.6",
            description=(
                "Document has no headings (H1-H6). "
                "Screen reader users cannot navigate by heading."
            ),
            remediation=(
                "In the Tag Tree, arrow to each section title, "
                "press F2, and change the type from P to H1, H2, "
                "etc. Or use Auto-Tagger (Alt+T, A) to detect "
                "heading candidates automatically."
            ),
            acrobat_remediation=(
                "In the Tags panel, select each paragraph that "
                "should be a heading, open Properties (Ctrl+E), "
                "and change Type to H1, H2, etc."
            ),
        )
    ]


def _check_nonstd_no_alt(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.NONSTD_NO_ALT: non-standard tags (from RoleMap) without alt text."""
    findings: list[Finding] = []
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []

    # Collect non-standard tag names from RoleMap
    role_map = str_root.get("/RoleMap")
    nonstd_names: set[str] = set()
    if role_map is not None:
        try:
            role_map = _resolve(role_map)
            for key in role_map:
                nonstd_names.add(str(key))
        except Exception:
            pass

    if not nonstd_names:
        return []

    for elem in _walk_struct_tree(str_root):
        try:
            s_type = str(elem.get("/S", ""))
            if s_type in nonstd_names:
                alt = elem.get("/Alt")
                actual = elem.get("/ActualText")
                has_text = (
                    (alt is not None and str(alt).strip() not in ("", "()"))
                    or (actual is not None and str(actual).strip() not in ("", "()"))
                )
                if not has_text:
                    page = _page_index_for_element(elem, pdf)
                    findings.append(
                        Finding(
                            rule_id="PDFBP.NONSTD_NO_ALT",
                            severity="warning",
                            wcag="1.1.1",
                            description=(
                                f"Non-standard tag {s_type} has no alt text or actual text."
                            ),
                            page=page + 1 if page is not None else None,
                            remediation=(
                                "In the Tag Tree, arrow to the element, "
                                "press F2 to add alt text. If decorative, "
                                "press Delete and choose 'Mark as Artifact' "
                                "to remove it from the tag tree."
                            ),
                            acrobat_remediation=(
                                "In the Tags panel, select the tag, open "
                                "Properties (Ctrl+E), and enter Alternative "
                                "Text. For decorative items, change to Artifact."
                            ),
                        )
                    )
        except Exception:
            continue

    return findings


def _check_forms_detached(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.FORMS_DETACHED: form fields grouped at end of reading order."""
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []

    leaves = _classify_leaves(str_root)
    if not leaves:
        return []

    form_indices = [i for i, (kind, _) in enumerate(leaves) if kind == "form"]
    if len(form_indices) < 2:
        return []

    total_leaves = len(leaves)
    total_forms = len(form_indices)
    total_text = total_leaves - total_forms

    if total_text == 0:
        return []

    # Check if the form fields occupy a contiguous block at the end
    first_form = form_indices[0]
    last_form = form_indices[-1]
    block_size = last_form - first_form + 1

    # Count how many text elements appear interleaved in the form block
    text_in_block = sum(
        1 for i in range(first_form, last_form + 1)
        if leaves[i][0] == "text"
    )

    # Threshold: >50% of form fields in a contiguous block at the end,
    # with minimal text interleaved (< 10% of block is text)
    forms_in_block = block_size - text_in_block
    pct_forms_detached = forms_in_block / total_forms

    if (
        pct_forms_detached >= 0.5
        and first_form > total_text * 0.5
        and text_in_block / max(block_size, 1) < 0.1
    ):
        return [
            Finding(
                rule_id="PDFBP.FORMS_DETACHED",
                severity="error",
                wcag="1.3.2",
                description=(
                    f"{forms_in_block} of {total_forms} form fields are grouped at "
                    f"reading order positions {first_form}-{last_form}, after all page "
                    f"content (positions 0-{first_form - 1}). Screen readers encounter "
                    f"all text first, then all fields, making it impossible to associate "
                    f"fields with their labels."
                ),
                remediation=(
                    "Use Auto-Sort Reading Order (Alt+T, R) to "
                    "interleave form fields with their labels. "
                    "Preview the proposed order, then press Enter "
                    "to apply. In the Tag Tree, each field is "
                    "reparented to follow its label. Ctrl+Z undoes all."
                ),
                acrobat_remediation=(
                    "In the Tags panel, cut each Form tag (Ctrl+X) "
                    "and paste it (Ctrl+V) after the P tag that "
                    "contains its label text. Repeat for each field. "
                    "Or use the Order panel to drag fields inline."
                ),
            )
        ]

    return []


def _check_underscore_fill(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.UNDERSCORE_FILL: pages with long underscore fill lines.

    Uses pypdfium2 for text extraction since underscore content lives in
    the content stream (MCIDs), not in /ActualText metadata.
    """
    try:
        import pypdfium2  # noqa: F811
    except ImportError:
        return []  # pypdfium2 not installed, skip this check

    findings: list[Finding] = []
    pdf_path = getattr(pdf, "filename", None)
    if pdf_path is None:
        return []

    try:
        pf = pypdfium2.PdfDocument(str(pdf_path))
    except Exception:
        return []

    total_underscore_lines = 0
    pages_affected: list[int] = []

    try:
        for pg_idx in range(len(pf)):
            try:
                page = pf[pg_idx]
                tp = page.get_textpage()
                full_text = tp.get_text_range()
            except Exception:
                continue

            page_count = 0
            for line in full_text.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                n_underscore = stripped.count("_")
                total_chars = len(stripped)
                if total_chars == 0:
                    continue
                pct = n_underscore / total_chars
                has_run = "____________" in stripped  # 12+ consecutive
                if pct >= 0.3 and has_run:
                    page_count += 1

            if page_count > 0:
                total_underscore_lines += page_count
                pages_affected.append(pg_idx + 1)
    finally:
        pf.close()

    if total_underscore_lines > 0:
        page_str = ", ".join(str(p) for p in pages_affected)
        findings.append(
            Finding(
                rule_id="PDFBP.UNDERSCORE_FILL",
                severity="warning",
                wcag="1.3.1",
                description=(
                    f"{total_underscore_lines} line(s) on page(s) {page_str} contain "
                    f"underscore fill patterns (e.g., 'Name ___________'). Screen "
                    f"readers announce each underscore character individually. These "
                    f"should be marked as artifacts if a form field is overlaid."
                ),
                remediation=(
                    "In the Tag Tree, navigate to each paragraph "
                    "with underscore fills. If a form field overlaps, "
                    "press Delete and choose 'Mark as Artifact' to "
                    "remove the underscores from the tag tree. The "
                    "'Clean All Underscore Fills' batch action "
                    "(Alt+T, U) processes all flagged elements at once."
                ),
                acrobat_remediation=(
                    "In the Tags panel, find each P tag containing "
                    "underscore fills. Select the tag, open Properties "
                    "(Ctrl+E), and change Type to Artifact. If the "
                    "label text before the underscores is meaningful, "
                    "split the tag: keep the label as a P and convert "
                    "only the underscore portion to Artifact."
                ),
            )
        )

    return findings


def _check_tab_order(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.NAV.TABORDER: each page should use structure-based tab order (/Tabs /S)."""
    findings: list[Finding] = []
    try:
        for pg_idx, page in enumerate(pdf.pages):
            tabs = page.get("/Tabs")
            if tabs is None or str(tabs) != "/S":
                findings.append(
                    Finding(
                        rule_id="PDFBP.NAV.TABORDER",
                        severity="warning",
                        wcag="2.4.3",
                        description=(
                            f"Page {pg_idx + 1} tab order is not set to "
                            "structure order (/Tabs /S)."
                        ),
                        page=pg_idx + 1,
                        remediation=(
                            "In the Accessibility Checker results, right-click "
                            "the Tab Order finding and choose Fix. This sets "
                            "/Tabs /S on all pages at once."
                        ),
                        acrobat_remediation=(
                            "Run Accessibility Check (Alt+A). Under Page Content, "
                            "right-click Tab Order and choose Fix. Adobe sets "
                            "tab order to match the structure order on every page."
                        ),
                    )
                )
    except Exception:
        pass

    return findings


def _check_text_extractable(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.TEXT.EXTRACTABLE: detect scanned/image-only PDFs with no extractable text."""
    try:
        import pypdfium2
    except ImportError:
        return []

    pdf_path = getattr(pdf, "filename", None)
    if pdf_path is None:
        return []

    try:
        pf = pypdfium2.PdfDocument(str(pdf_path))
    except Exception:
        return []

    total_pages = len(pf)
    pages_no_text: list[int] = []

    try:
        for pg_idx in range(total_pages):
            try:
                page = pf[pg_idx]
                tp = page.get_textpage()
                text = tp.get_text_range().strip()
                if len(text) < 5:
                    pages_no_text.append(pg_idx + 1)
            except Exception:
                pages_no_text.append(pg_idx + 1)
    finally:
        pf.close()

    if total_pages > 0 and len(pages_no_text) == total_pages:
        return [
            Finding(
                rule_id="PDFBP.TEXT.EXTRACTABLE",
                severity="error",
                wcag="1.1.1",
                description=(
                    "No extractable text found on any page. This is likely a "
                    "scanned or image-only PDF. Screen readers cannot read it "
                    "without OCR."
                ),
                remediation=(
                    "Run OCR via Edit > Preferences > Document Processing "
                    "to add a text layer. Better yet, obtain the source "
                    "document and re-export as a tagged PDF."
                ),
                acrobat_remediation=(
                    "Scan & OCR > Recognize Text > In This File. Set language "
                    "and output to Searchable Image. Then run Accessibility > "
                    "Autotag Document."
                ),
            )
        ]

    if len(pages_no_text) > 0:
        page_str = ", ".join(str(p) for p in pages_no_text[:10])
        suffix = f" (and {len(pages_no_text) - 10} more)" if len(pages_no_text) > 10 else ""
        return [
            Finding(
                rule_id="PDFBP.TEXT.EXTRACTABLE",
                severity="warning",
                wcag="1.1.1",
                description=(
                    f"{len(pages_no_text)} of {total_pages} pages have no extractable text "
                    f"(pages {page_str}{suffix}). These may be scanned images."
                ),
                remediation=(
                    "Run OCR on the affected pages to add text layers."
                ),
                acrobat_remediation=(
                    "Scan & OCR > Recognize Text > In This File. Set language "
                    "and output to Searchable Image."
                ),
            )
        ]

    return []


def _check_alt_text_length(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.ALT_LENGTH: flag excessively long alt text (>250 chars)."""
    findings: list[Finding] = []
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []

    for elem in _walk_struct_tree(str_root):
        try:
            s_type = str(elem.get("/S", "")).lstrip("/")
            if s_type != "Figure":
                continue
            alt = elem.get("/Alt")
            if alt is None:
                continue
            alt_str = str(alt).strip()
            if len(alt_str) > 250:
                page = _page_index_for_element(elem, pdf)
                findings.append(
                    Finding(
                        rule_id="PDFBP.ALT_LENGTH",
                        severity="warning",
                        wcag="1.1.1",
                        description=(
                            f"Figure alt text is {len(alt_str)} characters. "
                            "Consider shortening to under 250 characters or using "
                            "a long description approach."
                        ),
                        page=page + 1 if page is not None else None,
                        remediation=(
                            "Select the figure, press F2 to edit alt text, "
                            "and shorten to a concise description. For complex "
                            "images, add a nearby paragraph with the full description."
                        ),
                        acrobat_remediation=(
                            "In the Tags panel, select the Figure tag, open "
                            "Properties (Ctrl+E), and shorten the Alternative "
                            "Text. For complex images, add a Caption tag with "
                            "the detailed description."
                        ),
                    )
                )
        except Exception:
            continue

    return findings


def _check_alt_text_quality(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.ALT_QUALITY: detect placeholder/filename alt text on figures."""
    _BAD_PATTERNS = [
        re.compile(r"\.(png|jpg|jpeg|gif|bmp|tiff?|svg|webp|ico)$", re.I),
        re.compile(r"^image\s*\d*$", re.I),
        re.compile(r"^picture\s*\d*$", re.I),
        re.compile(r"^photo\s*\d*$", re.I),
        re.compile(r"^img[\s_-]?\d+$", re.I),
        re.compile(r"^figure\s*\d*$", re.I),
        re.compile(r"^graphic\s*\d*$", re.I),
        re.compile(r"^screenshot\s*\d*$", re.I),
        re.compile(r"^untitled\s*\d*$", re.I),
        re.compile(r"^DSC[_-]?\d+$", re.I),
        re.compile(r"^IMG[_-]?\d+$", re.I),
    ]

    findings: list[Finding] = []
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []

    for elem in _walk_struct_tree(str_root):
        try:
            s_type = str(elem.get("/S", "")).lstrip("/")
            if s_type != "Figure":
                continue
            alt = elem.get("/Alt")
            if alt is None:
                continue
            alt_str = str(alt).strip()
            if not alt_str:
                continue
            for pattern in _BAD_PATTERNS:
                if pattern.search(alt_str):
                    page = _page_index_for_element(elem, pdf)
                    findings.append(
                        Finding(
                            rule_id="PDFBP.ALT_QUALITY",
                            severity="warning",
                            wcag="1.1.1",
                            description=(
                                f"Figure alt text '{alt_str}' appears to be a "
                                "filename or placeholder, not a meaningful description."
                            ),
                            page=page + 1 if page is not None else None,
                            element=alt_str,
                            remediation=(
                                "Select the figure and press F2 to edit alt text. "
                                "Replace the filename with a concise description "
                                "of what the image conveys."
                            ),
                            acrobat_remediation=(
                                "In the Tags panel, select the Figure tag, open "
                                "Properties (Ctrl+E), and replace the Alternative "
                                "Text with a meaningful description."
                            ),
                        )
                    )
                    break
        except Exception:
            continue

    return findings


def _check_lang_valid(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.LANG_VALID: validate /Lang against BCP 47 pattern."""
    _BCP47 = re.compile(
        r"^[a-zA-Z]{2,3}"          # primary language subtag
        r"(-[a-zA-Z]{4})?"          # optional script subtag
        r"(-[a-zA-Z]{2}|\d{3})?"    # optional region subtag
        r"(-([a-zA-Z\d]{5,8}|\d[a-zA-Z\d]{3}))*$"  # optional variant
    )

    lang = ""
    try:
        lang_val = pdf.Root.get("/Lang")
        if lang_val is not None:
            lang = str(lang_val).strip()
    except Exception:
        pass

    if not lang:
        return []  # Missing lang caught by _check_language

    if not _BCP47.match(lang):
        return [
            Finding(
                rule_id="PDFBP.LANG_VALID",
                severity="error",
                wcag="3.1.1",
                description=(
                    f"Document language '{lang}' is not a valid BCP 47 code. "
                    "Screen readers may use the wrong speech synthesizer."
                ),
                remediation=(
                    "Open Document Properties (Alt+Enter), Tab to the "
                    "Language field, and enter a valid BCP 47 code "
                    "(e.g. 'en', 'en-US', 'fr-CA')."
                ),
                acrobat_remediation=(
                    "File > Properties > Advanced tab > Language dropdown. "
                    "Select a valid language. Common codes: English (en-US), "
                    "French (fr-FR), Spanish (es-ES)."
                ),
            )
        ]
    return []


def _check_link_text(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.LINK_TEXT: detect non-descriptive link text in /Link elements."""
    _BAD_LINK_TEXT = re.compile(
        r"^(click\s+here|here|more|read\s+more|learn\s+more|"
        r"link|see\s+more|details|info|this\s+link|"
        r"go|go\s+here|visit|press\s+here)$",
        re.I,
    )
    _URL_PATTERN = re.compile(
        r"^https?://\S{20,}$", re.I
    )

    findings: list[Finding] = []
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []

    for elem in _walk_struct_tree(str_root):
        try:
            s_type = str(elem.get("/S", "")).lstrip("/")
            if s_type != "Link":
                continue
            alt = elem.get("/Alt")
            actual = elem.get("/ActualText")
            text = ""
            if alt is not None:
                text = str(alt).strip()
            elif actual is not None:
                text = str(actual).strip()

            if not text:
                continue

            is_bad = _BAD_LINK_TEXT.match(text) or _URL_PATTERN.match(text)
            if is_bad:
                page = _page_index_for_element(elem, pdf)
                display_text = text[:50] + "..." if len(text) > 50 else text
                findings.append(
                    Finding(
                        rule_id="PDFBP.LINK_TEXT",
                        severity="warning",
                        wcag="2.4.4",
                        description=(
                            f"Link text '{display_text}' is not descriptive. "
                            "Screen reader users navigating by links hear only "
                            "the link text, with no surrounding context."
                        ),
                        page=page + 1 if page is not None else None,
                        element=display_text,
                        remediation=(
                            "Select the link text and replace it with a "
                            "description of where the link goes or what it does."
                        ),
                        acrobat_remediation=(
                            "Edit the link text in the source document to be "
                            "descriptive, then re-export. In Acrobat, select the "
                            "Link tag > Properties > Alternative Text, and enter "
                            "a meaningful description."
                        ),
                    )
                )
        except Exception:
            continue

    return findings


def _check_empty_tags(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.EMPTY_TAGS: tags with no content cause screen readers to say 'blank'."""
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []

    empty_count = 0
    for elem in _walk_struct_tree(str_root):
        try:
            s_type = str(elem.get("/S", "")).lstrip("/")
            # Only flag content tags, not grouping containers
            if s_type not in _TEXT_TAGS:
                continue
            kids = elem.get("/K")
            if kids is None:
                empty_count += 1
        except Exception:
            continue

    if empty_count > 0:
        return [
            Finding(
                rule_id="PDFBP.EMPTY_TAGS",
                severity="warning",
                wcag="1.3.1",
                description=(
                    f"{empty_count} empty content tag(s) found (P, Span, etc. "
                    "with no children). Screen readers announce these as 'blank'."
                ),
                remediation=(
                    "In the Tag Tree, locate empty tags (highlighted "
                    "in yellow) and press Delete to remove them. "
                    "Or use the 'Clean Empty Tags' batch action."
                ),
                acrobat_remediation=(
                    "In the Tags panel, locate empty P or Span tags "
                    "(they highlight nothing on the page). Right-click "
                    "and choose Delete Tag. Repeat for all empty tags."
                ),
            )
        ]
    return []


def _check_duplicate_field_names(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.FORMS.DUPLICATE_NAMES: form fields must have unique names.

    Per the remediation guide: 'Fields CANNOT have duplicate names.'
    Duplicate names cause assistive technology to confuse fields.
    Note: Radio buttons sharing a group name is correct -- only non-radio
    duplicates are flagged.
    """
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

    name_counts: dict[str, int] = {}
    for field in fields:
        try:
            field = _resolve(field)
            if not isinstance(field, pikepdf.Dictionary):
                continue
            name = field.get("/T")
            if name is None:
                continue
            name_str = str(name).strip()
            if not name_str:
                continue

            # Skip radio buttons -- they intentionally share group names
            ft = field.get("/FT")
            if ft is not None and str(ft) == "/Btn":
                ff = field.get("/Ff")
                if ff is not None:
                    try:
                        ff_int = int(ff)
                        # Bit 16 = radio, bit 17 = pushbutton
                        if ff_int & (1 << 15):  # radio button
                            continue
                    except (TypeError, ValueError):
                        pass

            name_counts[name_str] = name_counts.get(name_str, 0) + 1
        except Exception:
            continue

    for name_str, count in name_counts.items():
        if count > 1:
            findings.append(
                Finding(
                    rule_id="PDFBP.FORMS.DUPLICATE_NAMES",
                    severity="error",
                    wcag="4.1.2",
                    description=(
                        f"Form field name '{name_str}' is used {count} times. "
                        "Each field must have a unique name."
                    ),
                    element=name_str,
                    remediation=(
                        "In the Field Properties panel for each duplicate, "
                        "Tab to the Name field and assign a unique name."
                    ),
                    acrobat_remediation=(
                        "Open Prepare Forms, then for each duplicate field, "
                        "double-click to open Properties > General tab, and "
                        "change the Name to be unique."
                    ),
                )
            )

    return findings


def _check_radio_group(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.FORMS.RADIO_GROUP: radio buttons must share a group name per question.

    Per the remediation guide: 'When adding radio buttons to a question you
    must ensure that the group name is the same for all of them.' This check
    flags radio button groups with only one button (likely misconfigured).
    """
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

    radio_groups: dict[str, int] = {}
    for field in fields:
        try:
            field = _resolve(field)
            if not isinstance(field, pikepdf.Dictionary):
                continue
            ft = field.get("/FT")
            if ft is None or str(ft) != "/Btn":
                continue
            ff = field.get("/Ff")
            if ff is None:
                continue
            try:
                ff_int = int(ff)
            except (TypeError, ValueError):
                continue
            # Bit 16 (0-indexed bit 15) = radio button
            if not (ff_int & (1 << 15)):
                continue
            # Bit 17 (0-indexed bit 16) = pushbutton -- skip
            if ff_int & (1 << 16):
                continue

            name = field.get("/T")
            if name is not None:
                name_str = str(name).strip()
                # Count child widgets (options) under /Kids
                kids = field.get("/Kids")
                if kids is not None:
                    try:
                        kids = _resolve(kids)
                        if isinstance(kids, pikepdf.Array):
                            radio_groups[name_str] = len(kids)
                        else:
                            radio_groups[name_str] = 1
                    except Exception:
                        radio_groups[name_str] = 1
                else:
                    radio_groups[name_str] = 1
        except Exception:
            continue

    for group_name, count in radio_groups.items():
        if count < 2:
            findings.append(
                Finding(
                    rule_id="PDFBP.FORMS.RADIO_GROUP",
                    severity="warning",
                    wcag="4.1.2",
                    description=(
                        f"Radio button group '{group_name}' has only {count} option. "
                        "Radio buttons should have at least 2 options per group."
                    ),
                    element=group_name,
                    remediation=(
                        "In the Field Properties for the radio button, "
                        "ensure the group name matches the question. Add "
                        "another radio button with the same group name."
                    ),
                    acrobat_remediation=(
                        "In Prepare Forms, add another radio button. When "
                        "naming it, use the SAME group name as the existing "
                        "button. Adobe groups radio buttons by shared name."
                    ),
                )
            )

    return findings


def _check_list_structure(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.LIST_STRUCT: validate L > LI > LBody nesting per PDF/UA.

    Lists in a tagged PDF must follow the structure: L contains LI,
    LI contains LBody (and optionally Lbl). Incorrect nesting (e.g.
    P tags inside L without LI wrapper) breaks screen reader list
    navigation.
    """
    findings: list[Finding] = []
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []

    for elem in _walk_struct_tree(str_root):
        try:
            s_type = str(elem.get("/S", "")).lstrip("/")
            if s_type != "L":
                continue

            kids = elem.get("/K")
            if kids is None:
                continue
            kids = _resolve(kids)
            child_list = list(kids) if isinstance(kids, pikepdf.Array) else [kids]

            has_li = False
            bad_children: list[str] = []
            for child in child_list:
                try:
                    child = _resolve(child)
                    if not isinstance(child, pikepdf.Dictionary):
                        continue
                    ct = str(child.get("/S", "")).lstrip("/")
                    if ct == "LI":
                        has_li = True
                    elif ct and ct not in ("LI", "Caption"):
                        bad_children.append(ct)
                except Exception:
                    continue

            if bad_children:
                page = _page_index_for_element(elem, pdf)
                findings.append(
                    Finding(
                        rule_id="PDFBP.LIST_STRUCT",
                        severity="warning",
                        wcag="1.3.1",
                        description=(
                            f"List (L) contains non-LI children: "
                            f"{', '.join(bad_children[:5])}. Lists must use "
                            f"L > LI > LBody structure."
                        ),
                        page=page + 1 if page is not None else None,
                        remediation=(
                            "In the Tag Tree, select the misplaced tags "
                            "inside the L element. Wrap each in an LI > LBody "
                            "structure, or move them outside the list."
                        ),
                        acrobat_remediation=(
                            "In the Tags panel, create LI tags inside the L tag, "
                            "then drag the misplaced elements into LBody tags "
                            "inside each LI."
                        ),
                    )
                )

            # Check LI children have LBody
            if has_li:
                for child in child_list:
                    try:
                        child = _resolve(child)
                        if not isinstance(child, pikepdf.Dictionary):
                            continue
                        ct = str(child.get("/S", "")).lstrip("/")
                        if ct != "LI":
                            continue
                        li_kids = child.get("/K")
                        if li_kids is None:
                            continue
                        li_kids = _resolve(li_kids)
                        li_children = (
                            list(li_kids)
                            if isinstance(li_kids, pikepdf.Array)
                            else [li_kids]
                        )
                        has_lbody = any(
                            str(_resolve(lc).get("/S", "")).lstrip("/") == "LBody"
                            for lc in li_children
                            if isinstance(_resolve(lc), pikepdf.Dictionary)
                        )
                        if not has_lbody:
                            page = _page_index_for_element(child, pdf)
                            findings.append(
                                Finding(
                                    rule_id="PDFBP.LIST_STRUCT",
                                    severity="warning",
                                    wcag="1.3.1",
                                    description=(
                                        "LI element is missing an LBody child."
                                    ),
                                    page=page + 1 if page is not None else None,
                                    remediation=(
                                        "In the Tag Tree, add an LBody tag "
                                        "inside the LI and move the content into it."
                                    ),
                                    acrobat_remediation=(
                                        "In the Tags panel, right-click the LI, "
                                        "choose New Tag > LBody, then drag the "
                                        "content into the new LBody tag."
                                    ),
                                )
                            )
                    except Exception:
                        continue

        except Exception:
            continue

    return findings


def _check_figure_caption(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.FIGURE_CAPTION: figures should be adjacent to their captions.

    In a well-formed tagged PDF, a Figure and its Caption should be siblings
    or the Caption should be a child of a container that also holds the Figure.
    This checks for orphaned Caption tags (not near any Figure).
    """
    findings: list[Finding] = []
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []

    # Walk top-level children looking for captions without adjacent figures
    for elem in _walk_struct_tree(str_root):
        try:
            s_type = str(elem.get("/S", "")).lstrip("/")
            if s_type != "Caption":
                continue
            # Check parent for a sibling Figure
            parent = elem.get("/P")
            if parent is None:
                continue
            parent = _resolve(parent)
            if not isinstance(parent, pikepdf.Dictionary):
                continue
            parent_kids = parent.get("/K")
            if parent_kids is None:
                continue
            parent_kids = _resolve(parent_kids)
            sibling_list = (
                list(parent_kids)
                if isinstance(parent_kids, pikepdf.Array)
                else [parent_kids]
            )
            has_figure_sibling = False
            for sib in sibling_list:
                try:
                    sib = _resolve(sib)
                    if isinstance(sib, pikepdf.Dictionary):
                        st = str(sib.get("/S", "")).lstrip("/")
                        if st == "Figure":
                            has_figure_sibling = True
                            break
                except Exception:
                    continue

            if not has_figure_sibling:
                page = _page_index_for_element(elem, pdf)
                findings.append(
                    Finding(
                        rule_id="PDFBP.FIGURE_CAPTION",
                        severity="tip",
                        wcag="1.1.1",
                        description=(
                            "Caption tag is not adjacent to a Figure tag. "
                            "Consider grouping the figure and caption together."
                        ),
                        page=page + 1 if page is not None else None,
                        remediation=(
                            "In the Tag Tree, move the Caption tag to be a "
                            "sibling of its Figure, or wrap both in a Div."
                        ),
                        acrobat_remediation=(
                            "In the Tags panel, cut the Caption tag and paste "
                            "it next to the Figure tag it describes. Or create a "
                            "Div container and place both inside it."
                        ),
                    )
                )
        except Exception:
            continue

    return findings


def _check_art_tags(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.ART_TAGS: detect Art tags that typically indicate messy structure.

    Per the remediation guide: 'often you will see <Art> under <Document>
    with many tags underneath it. Which means you'll need to do some tag
    tree clean up.'
    """
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []

    art_count = 0
    for elem in _walk_struct_tree(str_root):
        try:
            s_type = str(elem.get("/S", "")).lstrip("/")
            if s_type == "Art":
                art_count += 1
        except Exception:
            continue

    if art_count > 0:
        return [
            Finding(
                rule_id="PDFBP.ART_TAGS",
                severity="tip",
                wcag="1.3.1",
                description=(
                    f"{art_count} Art tag(s) found. Art tags often indicate "
                    "the document structure needs cleanup -- content should be "
                    "moved out of Art containers into proper heading/paragraph "
                    "structure."
                ),
                remediation=(
                    "In the Tag Tree, expand each Art tag. Move its "
                    "children (headings, paragraphs, etc.) out to the "
                    "Document level, then delete the empty Art tag."
                ),
                acrobat_remediation=(
                    "In the Tags panel, expand each Art tag. Cut the child "
                    "tags (Ctrl+X) and paste (Ctrl+V) them under Document "
                    "at the correct position. Delete the empty Art tag."
                ),
            )
        ]
    return []


def _check_sect_nesting(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.SECT_NESTING: excessive Sect nesting (common in PowerPoint exports).

    Per the remediation guide, PowerPoint PDFs often have nested Sect tags
    that add useless layers. Deep nesting (>3 levels) is flagged.
    """
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []

    max_depth = 0

    def _measure_sect_depth(node: pikepdf.Object, depth: int) -> None:
        nonlocal max_depth
        try:
            node = _resolve(node)
        except Exception:
            return
        if not isinstance(node, pikepdf.Dictionary):
            return

        s_type = str(node.get("/S", "")).lstrip("/")
        current = depth + 1 if s_type == "Sect" else depth
        if current > max_depth:
            max_depth = current

        kids = node.get("/K")
        if kids is None:
            return
        try:
            kids = _resolve(kids)
        except Exception:
            return
        if isinstance(kids, pikepdf.Array):
            for child in kids:
                _measure_sect_depth(child, current)
        elif isinstance(kids, pikepdf.Dictionary):
            _measure_sect_depth(kids, current)

    _measure_sect_depth(str_root, 0)

    if max_depth > 3:
        return [
            Finding(
                rule_id="PDFBP.SECT_NESTING",
                severity="tip",
                wcag="1.3.1",
                description=(
                    f"Sect tags are nested {max_depth} levels deep. "
                    "This is common in PowerPoint exports and adds unnecessary "
                    "complexity for screen readers."
                ),
                remediation=(
                    "Flatten the Sect hierarchy: move child elements "
                    "up to reduce nesting to 1-2 levels maximum."
                ),
                acrobat_remediation=(
                    "In the Tags panel, expand deeply nested Sect tags. "
                    "Cut the child tags and paste them at a higher level "
                    "in the tree. Delete the empty Sect containers."
                ),
            )
        ]
    return []


def _check_tooltip_quality(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.FORMS.TOOLTIP_QUALITY: tooltips must be descriptive.

    Per the remediation guide: tooltips should identify the question/purpose.
    Short, generic tooltips like 'text', 'field', 'input' don't help users.
    Also flags tooltips that contain only the field type name.
    """
    _GENERIC_TOOLTIPS = re.compile(
        r"^(text|field|input|button|check|radio|select|combo|"
        r"choice|option|entry|box|value|form|data|item|edit)$",
        re.I,
    )

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
            if tooltip is None:
                continue  # Missing tooltip caught by _check_form_fields
            tooltip_str = str(tooltip).strip()
            if not tooltip_str:
                continue
            if _GENERIC_TOOLTIPS.match(tooltip_str):
                findings.append(
                    Finding(
                        rule_id="PDFBP.FORMS.TOOLTIP_QUALITY",
                        severity="warning",
                        wcag="4.1.2",
                        description=(
                            f"Form field tooltip '{tooltip_str}' is generic and "
                            "not descriptive. Screen reader users rely on tooltips "
                            "to understand the field's purpose."
                        ),
                        element=str(name) if name is not None else None,
                        remediation=(
                            "In the Field Properties panel, change the Tooltip "
                            "to describe the question or purpose of this field "
                            "(e.g. 'First Name', 'Date of Birth (MM/DD/YYYY)')."
                        ),
                        acrobat_remediation=(
                            "Open Prepare Forms, double-click the field, go to "
                            "General tab, and change the Tooltip to be descriptive. "
                            "Include the question or label the field answers."
                        ),
                    )
                )
        except Exception:
            continue

    return findings


def _check_flat_structure(pdf: pikepdf.Pdf) -> list[Finding]:
    """PDFBP.FLAT_STRUCTURE: all elements direct children of Document with no /Sect."""
    str_root = _get_struct_tree_root(pdf)
    if str_root is None:
        return []

    kids = str_root.get("/K")
    if kids is None:
        return []

    try:
        kids = _resolve(kids)
    except Exception:
        return []

    # Single-child root: check if it's the Document element
    if isinstance(kids, pikepdf.Dictionary):
        doc_node = kids
    elif isinstance(kids, pikepdf.Array):
        if len(kids) == 0:
            return []
        doc_node = _resolve(kids[0])
        if not isinstance(doc_node, pikepdf.Dictionary):
            return []
    else:
        return []

    s_type = str(doc_node.get("/S", "")).lstrip("/")
    if s_type != "Document":
        return []

    doc_kids = doc_node.get("/K")
    if doc_kids is None:
        return []
    try:
        doc_kids = _resolve(doc_kids)
    except Exception:
        return []

    if not isinstance(doc_kids, pikepdf.Array):
        return []

    # Check: does any child have tag type Sect, Part, or Art?
    has_grouping = False
    child_count = 0
    for child in doc_kids:
        try:
            child = _resolve(child)
            if isinstance(child, pikepdf.Dictionary) and "/S" in child:
                child_count += 1
                ct = str(child.get("/S", "")).lstrip("/")
                if ct in ("Sect", "Part", "Art", "Div"):
                    has_grouping = True
                    break
        except Exception:
            continue

    if not has_grouping and child_count > 10:
        return [
            Finding(
                rule_id="PDFBP.FLAT_STRUCTURE",
                severity="tip",
                wcag="1.3.1",
                description=(
                    f"Document has {child_count} direct children with no sectioning "
                    "(Sect/Part/Art). Consider grouping related elements into sections."
                ),
                remediation=(
                    "In the Tag Tree, select the Document root, "
                    "press Insert to add a Sect child, then "
                    "select related elements and press Ctrl+X to "
                    "cut, arrow to the Sect, and Ctrl+V to paste."
                ),
                acrobat_remediation=(
                    "In the Tags panel, create new Sect tags under "
                    "Document, then drag or cut/paste related "
                    "heading and content tags into each section."
                ),
            )
        ]

    return []


# ---------------------------------------------------------------------------
# Main checker class
# ---------------------------------------------------------------------------

# All registered checks, run in order.
_CHECKS = [
    _check_title,
    _check_language,
    _check_lang_valid,
    _check_tagged,
    _check_empty_struct_tree,
    _check_figure_alt_text,
    _check_alt_text_length,
    _check_alt_text_quality,
    _check_headings,
    _check_no_headings,
    _check_nonstd_no_alt,
    _check_empty_tags,
    _check_list_structure,
    _check_figure_caption,
    _check_art_tags,
    _check_sect_nesting,
    _check_flat_structure,
    _check_table_headers,
    _check_link_text,
    _check_form_fields,
    _check_duplicate_field_names,
    _check_radio_group,
    _check_tooltip_quality,
    _check_forms_detached,
    _check_underscore_fill,
    _check_tab_order,
    _check_text_extractable,
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
