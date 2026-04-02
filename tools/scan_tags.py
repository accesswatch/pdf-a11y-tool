"""
scan_tags.py — PDF Tag Tree Structure Scanner
==============================================
Persistent utility for PDF accessibility audits.
Analyzes the full PDF structure tree:
  - Form element placement (in-order vs. dumped at end of tree)
  - List element continuity across page breaks
  - Non-standard role mappings (InlineShape, Textbox, etc.)
  - Heading hierarchy
  - Table structure (TH/TD/THead/TBody presence)
  - Artifact coverage

Usage:
    python tools/scan_tags.py <pdf_or_folder> [--json] [--output file.json]

Dependencies: pikepdf (pip install pikepdf)

This file is PERMANENT — do not delete. Used by agents and scan_all.py.
"""

import sys
import os
import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict

try:
    import pikepdf
    from pikepdf import Dictionary, Array, Name
except ImportError:
    sys.exit("ERROR: pikepdf not installed. Run: pip install pikepdf")


# ---------------------------------------------------------------------------
# Tag tree traversal
# ---------------------------------------------------------------------------

STANDARD_ROLES = {
    "Document", "Part", "Sect", "Div", "Caption", "BlockQuote", "NonStruct",
    "TOC", "TOCI", "Index", "P", "H", "H1", "H2", "H3", "H4", "H5", "H6",
    "L", "LI", "Lbl", "LBody", "Table", "TR", "TH", "TD", "THead", "TBody",
    "TFoot", "Span", "Quote", "Note", "Reference", "BibEntry", "Code",
    "Figure", "Formula", "Form", "Link", "Annot", "Ruby", "Warichu",
    "RB", "RT", "RP", "WT", "WP", "Artifact",
}


def tag_name(obj) -> str:
    """Return the tag type string for a structure element."""
    try:
        s = obj.get("/S", None)
        if s is not None:
            return str(s).lstrip("/")
    except Exception:
        pass
    return "Unknown"


def iter_struct_tree(node, depth: int = 0):  # noqa: ANN201 — yields tuples
    """
    Yield (depth, tag_name, node) for every element in the structure tree.
    Handles both Dictionary nodes and Array children.
    """
    if isinstance(node, Dictionary):
        name = tag_name(node)
        yield depth, name, node
        kids = node.get("/K", None)
        if kids is None:
            return
        if isinstance(kids, Array):
            for kid in kids:
                try:
                    yield from iter_struct_tree(kid, depth + 1)
                except Exception:
                    pass
        elif isinstance(kids, Dictionary):
            yield from iter_struct_tree(kids, depth + 1)
        # Integer MCIDs are leaf nodes, skip
    elif isinstance(node, Array):
        for item in node:
            try:
                yield from iter_struct_tree(item, depth + 1)
            except Exception:
                pass


def collect_tag_counts(root_node) -> Counter:
    counts = Counter()
    for _depth, name, _node in iter_struct_tree(root_node):
        counts[name] += 1
    return counts


def find_top_level_children(root_node) -> list:
    """Return the immediate children (depth=1) tag names of the root."""
    children = []
    if not isinstance(root_node, Dictionary):
        return children
    kids = root_node.get("/K", None)
    if kids is None:
        return children
    if isinstance(kids, Array):
        for kid in kids:
            if isinstance(kid, Dictionary):
                children.append(tag_name(kid))
    elif isinstance(kids, Dictionary):
        children.append(tag_name(kids))
    return children


def get_struct_tree_root(pdf) -> tuple:
    """Return (struct_tree_root_element, role_map_dict)."""
    root = pdf.Root
    struct_tree_root = root.get("/StructTreeRoot", None)
    if struct_tree_root is None:
        return None, {}
    role_map = {}
    rm = struct_tree_root.get("/RoleMap", None)
    if rm and isinstance(rm, Dictionary):
        for k, v in rm.items():
            role_map[str(k).lstrip("/")] = str(v).lstrip("/")
    return struct_tree_root, role_map


def get_document_node(struct_tree_root) -> object:
    """Get the main content /Document or /Part node under StructTreeRoot."""
    if struct_tree_root is None:
        return None
    kids = struct_tree_root.get("/K", None)
    if kids is None:
        return None
    if isinstance(kids, Array) and len(kids) > 0:
        first = kids[0]
        if isinstance(first, Dictionary):
            return first
    elif isinstance(kids, Dictionary):
        return kids
    return None


# ---------------------------------------------------------------------------
# Form tag placement analysis
# ---------------------------------------------------------------------------

def analyze_form_tag_placement(struct_tree_root) -> dict:
    """
    Determine whether Form elements are inline (adjacent to labels) or
    dumped at the end of the tag tree (accessibility issue).

    Returns a dict describing the condition.
    """
    result = {
        "form_tags_in_tree": 0,
        "form_tags_inline": 0,       # adjacent to content in reading order
        "form_tags_orphaned": 0,     # at top level / end of tree
        "form_placement": "unknown", # "good", "orphaned", "acroform_only", "mixed"
        "orphaned_positions": [],    # depth=1 positions (top-level Form siblings)
    }

    if struct_tree_root is None:
        result["form_placement"] = "no_struct_tree"
        return result

    # Check top-level children of StructTreeRoot for Form elements
    top_children = find_top_level_children(struct_tree_root)
    top_form_count = sum(1 for c in top_children if c == "Form")
    top_non_form = [c for c in top_children if c != "Form"]

    # Walk the full tree and count Form occurrences at each depth
    depth_form_counts = Counter()
    total_forms = 0
    for depth, name, _node in iter_struct_tree(struct_tree_root):
        if name == "Form":
            total_forms += 1
            depth_form_counts[depth] += 1

    result["form_tags_in_tree"] = total_forms

    if total_forms == 0:
        result["form_placement"] = "acroform_only"
        return result

    # Forms at depth 1 (direct children of StructTreeRoot) are "orphaned"
    # They should be at depth >= 3 (StructTreeRoot → Document → P → Form)
    orphaned = depth_form_counts.get(1, 0)
    inline = total_forms - orphaned

    result["form_tags_orphaned"] = orphaned
    result["form_tags_inline"] = inline

    # Also check if there's a /Document node followed by Form siblings at depth=1
    if top_form_count > 0 and any(c in ("Document", "Part") for c in top_non_form):
        result["orphaned_positions"] = [
            f"depth=1 (siblings of {', '.join(top_non_form[:3])})"
        ]

    if orphaned > 0 and inline == 0:
        result["form_placement"] = "orphaned"
    elif orphaned > 0 and inline > 0:
        result["form_placement"] = "mixed"
    elif orphaned == 0 and inline > 0:
        result["form_placement"] = "good"
    else:
        result["form_placement"] = "acroform_only"

    return result


# ---------------------------------------------------------------------------
# List continuity analysis
# ---------------------------------------------------------------------------

def analyze_list_structure(struct_tree_root) -> dict:
    """
    Find split lists — cases where multiple <L> elements appear at the
    same depth/parent, indicating a multi-page list was broken apart.
    """
    result = {
        "total_list_elements": 0,
        "split_lists": [],   # list of dicts describing each split
        "has_split_lists": False,
    }

    if struct_tree_root is None:
        return result

    # Collect all L elements and their depths
    list_elements = []
    for depth, name, node in iter_struct_tree(struct_tree_root):
        if name == "L":
            li_count = 0
            kids = node.get("/K", None)
            if kids:
                if isinstance(kids, Array):
                    li_count = sum(1 for k in kids if isinstance(k, Dictionary) and tag_name(k) == "LI")
                elif isinstance(kids, Dictionary) and tag_name(kids) == "LI":
                    li_count = 1
            list_elements.append({"depth": depth, "li_count": li_count})

    result["total_list_elements"] = len(list_elements)

    # Group consecutive L elements at the same depth — strong signal for splits
    if len(list_elements) >= 2:
        # Simple heuristic: if multiple L elements exist and at least one has
        # very few items (≤ 5) while another has many (> 5), likely a split
        for i in range(len(list_elements) - 1):
            a = list_elements[i]
            b = list_elements[i + 1]
            if a["depth"] == b["depth"]:
                total = a["li_count"] + b["li_count"]
                if b["li_count"] <= 5 or a["li_count"] <= 5:
                    result["split_lists"].append({
                        "list_a_items": a["li_count"],
                        "list_b_items": b["li_count"],
                        "total_items": total,
                        "description": (
                            f"List split: {a['li_count']} items + "
                            f"{b['li_count']} items = {total} total. "
                            f"Screen readers will announce as two separate lists."
                        ),
                    })

    result["has_split_lists"] = len(result["split_lists"]) > 0
    return result


# ---------------------------------------------------------------------------
# Role map / non-standard tag analysis
# ---------------------------------------------------------------------------

def analyze_role_map(struct_tree_root, role_map: dict) -> dict:
    """Find non-standard tag types that lack a role mapping."""
    result = {
        "non_standard_tags": [],
        "unmapped_tags": [],
        "role_map": role_map,
    }

    if struct_tree_root is None:
        return result

    seen_non_standard = set()
    for _depth, name, _node in iter_struct_tree(struct_tree_root):
        if name not in STANDARD_ROLES and name not in ("Unknown",):
            seen_non_standard.add(name)

    for tag in seen_non_standard:
        result["non_standard_tags"].append(tag)
        if tag not in role_map:
            result["unmapped_tags"].append(tag)

    return result


# ---------------------------------------------------------------------------
# Heading hierarchy analysis
# ---------------------------------------------------------------------------

def analyze_headings(struct_tree_root) -> dict:
    result = {"heading_levels_used": [], "skipped_levels": []}
    if struct_tree_root is None:
        return result

    levels_seen = set()
    for _depth, name, _node in iter_struct_tree(struct_tree_root):
        if name in ("H1", "H2", "H3", "H4", "H5", "H6"):
            levels_seen.add(int(name[1]))

    if levels_seen:
        result["heading_levels_used"] = sorted(levels_seen)
        max_level = max(levels_seen)
        expected = set(range(1, max_level + 1))
        skipped = sorted(expected - levels_seen)
        if skipped:
            result["skipped_levels"] = skipped

    return result


# ---------------------------------------------------------------------------
# Table structure analysis
# ---------------------------------------------------------------------------

def analyze_tables(struct_tree_root) -> dict:
    result = {
        "table_count": 0,
        "has_thead": False,
        "has_tbody": False,
        "has_th": False,
        "th_count": 0,
        "td_count": 0,
        "tr_count": 0,
        "scope_attributes_present": False,  # would require deeper inspection
    }
    if struct_tree_root is None:
        return result

    tag_counts = collect_tag_counts(struct_tree_root)
    result["table_count"] = tag_counts.get("Table", 0)
    result["has_thead"] = tag_counts.get("THead", 0) > 0
    result["has_tbody"] = tag_counts.get("TBody", 0) > 0
    result["has_th"] = tag_counts.get("TH", 0) > 0
    result["th_count"] = tag_counts.get("TH", 0)
    result["td_count"] = tag_counts.get("TD", 0)
    result["tr_count"] = tag_counts.get("TR", 0)
    return result


# ---------------------------------------------------------------------------
# Reading order analysis
# ---------------------------------------------------------------------------

def _check_figure_caption_adjacency(struct_tree_root) -> list:
    """
    Find Figure elements and verify their Caption sibling immediately follows them
    in the tag tree. A Caption that is separated from its Figure means screen
    readers may not associate the image with its description.
    """
    issues = []

    def _check_kids(node):
        if not isinstance(node, Dictionary):
            return
        kids = node.get("/K", None)
        if kids is None:
            return
        child_list = []
        if isinstance(kids, Array):
            for kid in kids:
                if isinstance(kid, Dictionary):
                    child_list.append((tag_name(kid), kid))
        elif isinstance(kids, Dictionary):
            child_list = [(tag_name(kids), kids)]

        for i, (name, child_node) in enumerate(child_list):
            if name == "Figure":
                if i + 1 < len(child_list):
                    next_name, _ = child_list[i + 1]
                    if next_name != "Caption":
                        issues.append({
                            "issue": "figure_caption_not_adjacent",
                            "next_sibling": next_name,
                            "description": (
                                f"Figure element is followed by '{next_name}' "
                                "instead of a Caption. Screen readers may not "
                                "associate the image with its description text."
                            ),
                        })
                # Recurse into Figure children
                _check_kids(child_node)
            elif isinstance(child_node, Dictionary):
                _check_kids(child_node)

    _check_kids(struct_tree_root)
    return issues


def _check_figure_alt_text(struct_tree_root) -> dict:
    """Check all Figure elements for /Alt text.

    Returns dict with:
        - figures_total: count of Figure elements
        - figures_missing_alt: list of dicts with location info
        - figures_with_alt: list of dicts with existing alt text
    """
    result = {"figures_total": 0, "figures_missing_alt": [], "figures_with_alt": []}

    for _depth, name, node in iter_struct_tree(struct_tree_root):
        if name != "Figure":
            continue
        result["figures_total"] += 1

        alt = None
        try:
            raw = node.get("/Alt", None)
            if raw is not None:
                alt = str(raw).strip()
        except Exception:
            pass

        # Try to identify location from /K MCID or /T or /ID
        loc_hint = ""
        try:
            title = node.get("/T", None)
            if title is not None:
                loc_hint = str(title).strip()
        except Exception:
            pass

        if not alt:
            result["figures_missing_alt"].append({
                "title": loc_hint,
            })
        else:
            result["figures_with_alt"].append({
                "title": loc_hint,
                "alt": alt,
            })

    return result


def _build_page_objgen_map(pdf_pages) -> dict:
    """Build mapping from page object (id, gen) tuple to zero-based page index."""
    page_map = {}
    for i, page in enumerate(pdf_pages):
        try:
            page_map[page.objgen] = i
        except Exception:
            pass
    return page_map


def _collect_struct_tree_mcid_order(struct_tree_root, pdf_pages) -> dict:
    """
    Walk the structure tree and collect MCIDs in logical reading order.
    Returns {page_idx: [mcid, ...]} where the list order reflects the
    tree traversal order (= intended reading order for AT).

    Handles three types of leaf references:
      - Integer MCID (inherits page from nearest ancestor /Pg)
      - Dictionary with /Type /MCR — Marked Content Reference with /Pg and /MCID
      - Dictionary with /Type /OBJR — Object Reference (form field), skipped
    """
    page_map = _build_page_objgen_map(pdf_pages)
    page_mcids = defaultdict(list)

    def walk(node, inherited_pg_idx):
        if isinstance(node, int):
            if inherited_pg_idx is not None:
                page_mcids[inherited_pg_idx].append(node)
            return

        if isinstance(node, Array):
            for item in node:
                try:
                    walk(item, inherited_pg_idx)
                except Exception:
                    pass
            return

        if not isinstance(node, Dictionary):
            return

        # Resolve /Pg for this node
        pg = node.get("/Pg", None)
        pg_idx = inherited_pg_idx
        if pg is not None:
            try:
                pg_idx = page_map.get(pg.objgen, inherited_pg_idx)
            except Exception:
                pass

        # Marked Content Reference leaf
        node_type = str(node.get("/Type", "")).lstrip("/")
        if node_type == "MCR":
            mcid_val = node.get("/MCID", None)
            if mcid_val is not None and pg_idx is not None:
                try:
                    page_mcids[pg_idx].append(int(mcid_val))
                except (TypeError, ValueError):
                    pass
            return

        if node_type == "OBJR":
            return  # Object references (form widgets) — skip

        # Recurse into kids
        kids = node.get("/K", None)
        if kids is not None:
            walk(kids, pg_idx)

    walk(struct_tree_root, None)
    return dict(page_mcids)


def _extract_content_stream_mcids(pdf, page_idx: int) -> list:
    """
    Parse a page's content stream and return MCIDs in paint order.
    This is the VISUAL order — the sequence in which glyphs are drawn to the page.
    Comparing this to the structure tree order reveals reading order mismatches.
    """
    page = pdf.pages[page_idx]
    mcids = []
    try:
        for operands, operator in pikepdf.parse_content_stream(page):
            if str(operator) == "BDC" and len(operands) >= 2:
                props = operands[1]
                if isinstance(props, Dictionary):
                    mcid_val = props.get("/MCID", None)
                    if mcid_val is not None:
                        try:
                            mcids.append(int(mcid_val))
                        except (TypeError, ValueError):
                            pass
    except Exception:
        pass
    return mcids


def _inversion_rate(tree_order: list, stream_order: list) -> float:
    """
    Calculate the fraction of element pairs that appear in a DIFFERENT order
    between tree_order (logical/AT reading order) and stream_order (paint order).

    Returns 0.0 (identical) to 1.0 (completely reversed).
    A rate above 0.25 is a strong signal of reading order mismatch.

    Uses a naive O(n²) count — fine for typical MCID counts (<200/page).
    """
    pos = {mcid: i for i, mcid in enumerate(tree_order)}
    common = [x for x in stream_order if x in pos]
    n = len(common)
    if n < 2:
        return 0.0
    ranks = [pos[x] for x in common]
    inversions = sum(
        1 for i in range(n) for j in range(i + 1, n) if ranks[i] > ranks[j]
    )
    max_inv = n * (n - 1) / 2
    return inversions / max_inv if max_inv > 0 else 0.0


def analyze_reading_order(pdf, struct_tree_root) -> dict:
    """
    Multi-heuristic reading order analysis for PDF documents.

    Heuristic 1 — Figure-Caption adjacency (structural):
      Checks whether every Figure element is immediately followed by its Caption
      sibling in the tag tree. Separation indicates AT may not associate the
      image with its description.

    Heuristic 2 — MCID pair inversion rate (per-page):
      Compares the MCID sequence in the structure tree (logical AT reading order)
      against the MCID sequence in the content stream (visual paint order).
      A high inversion rate (> 25% of element pairs) means the document is
      visually laid out in a different order than screen readers will read it.
      Classic cause: multi-column layouts, sidebars, text boxes overlaid on images.

    Always sets manual_review_required = True because full verification requires
    the Acrobat Pro Reading Order tool or live AT testing. No automated check
    can substitute for human verification of the complete reading sequence.
    """
    result = {
        "figure_caption_issues": [],
        "mcid_order_issues": [],
        "pages_checked": 0,
        "pages_with_order_issues": 0,
        "manual_review_required": True,
    }

    if struct_tree_root is None:
        return result

    # Heuristic 1: Figure-Caption adjacency
    result["figure_caption_issues"] = _check_figure_caption_adjacency(struct_tree_root)

    # Heuristic 2: MCID order comparison
    try:
        page_count = len(pdf.pages)
        result["pages_checked"] = page_count

        struct_order = _collect_struct_tree_mcid_order(struct_tree_root, pdf.pages)
        problem_pages = []

        for page_idx in range(page_count):
            stream_mcids = _extract_content_stream_mcids(pdf, page_idx)
            tree_mcids = struct_order.get(page_idx, [])

            # Need at least 3 elements in both to make a meaningful comparison
            if len(stream_mcids) < 3 or len(tree_mcids) < 3:
                continue

            inv = _inversion_rate(tree_mcids, stream_mcids)
            if inv > 0.25:
                problem_pages.append({
                    "page": page_idx + 1,
                    "inversion_rate": round(inv, 2),
                    "stream_elements": len(stream_mcids),
                    "tree_elements": len(tree_mcids),
                })

        result["mcid_order_issues"] = problem_pages
        result["pages_with_order_issues"] = len(problem_pages)

    except Exception as e:
        result["mcid_check_error"] = str(e)

    return result


# ---------------------------------------------------------------------------
# Main scan function
# ---------------------------------------------------------------------------

def scan_tags(pdf_path: Path) -> dict:
    result = {
        "file": pdf_path.name,
        "path": str(pdf_path),
        "struct_tree_present": False,
        "tag_counts": {},
        "form_placement": {},
        "list_structure": {},
        "role_map": {},
        "headings": {},
        "tables": {},
        "reading_order": {},
        "findings": [],
        "errors": [],
    }

    try:
        with pikepdf.open(pdf_path) as pdf:
            struct_tree_root, role_map = get_struct_tree_root(pdf)

            if struct_tree_root is None:
                result["findings"].append({
                    "rule": "PDFUA.STRUCT.NOTREE",
                    "severity": "Error",
                    "confidence": "High",
                    "message": "No StructTreeRoot found — document has no tag structure.",
                    "fix": "Must be re-exported with tagging enabled or fully remediated.",
                })
                return result

            result["struct_tree_present"] = True
            result["role_map"] = role_map

            tag_counts = collect_tag_counts(struct_tree_root)
            result["tag_counts"] = dict(tag_counts)

            # Form placement
            fp = analyze_form_tag_placement(struct_tree_root)
            result["form_placement"] = fp

            if fp["form_placement"] == "orphaned":
                result["findings"].append({
                    "rule": "PDFUA.FORM.STRUCT",
                    "severity": "Error",
                    "confidence": "High",
                    "matterhorn": "14-002",
                    "wcag": "1.3.2",
                    "message": (
                        f"{fp['form_tags_in_tree']} Form element(s) are placed as "
                        "siblings of /Document at the end of the tag tree — "
                        "not adjacent to their corresponding label elements."
                    ),
                    "fix": (
                        "Re-export from source Word/InDesign with proper tag settings, "
                        "or use Acrobat Pro Tags panel to move each Form element "
                        "next to its corresponding label P element."
                    ),
                })
            elif fp["form_placement"] == "mixed":
                result["findings"].append({
                    "rule": "PDFUA.FORM.STRUCT",
                    "severity": "Warning",
                    "confidence": "Medium",
                    "matterhorn": "14-002",
                    "wcag": "1.3.2",
                    "message": (
                        f"{fp['form_tags_orphaned']} of {fp['form_tags_in_tree']} "
                        "Form elements are out of reading order. "
                        f"{fp['form_tags_inline']} are correctly placed."
                    ),
                    "fix": "Move orphaned Form elements next to label P elements in tag tree.",
                })
            elif fp["form_placement"] == "acroform_only":
                result["findings"].append({
                    "rule": "PDFBP.FORM.STRUCT",
                    "severity": "Warning",
                    "confidence": "High",
                    "matterhorn": "14-002",
                    "wcag": "1.3.1",
                    "message": (
                        "Form fields are accessible via AcroForm only — "
                        "no /Form elements in the structure tree. "
                        "Functionally accessible if tooltips are present."
                    ),
                    "fix": "Re-export from source document with form field tagging enabled.",
                })

            # List continuity
            ls = analyze_list_structure(struct_tree_root)
            result["list_structure"] = ls
            if ls["has_split_lists"]:
                for split in ls["split_lists"]:
                    result["findings"].append({
                        "rule": "PDFBP.LIST.CONTINUATION",
                        "severity": "Warning",
                        "confidence": "Medium",
                        "matterhorn": None,
                        "wcag": "1.3.1",
                        "message": split["description"],
                        "fix": (
                            "In source Word document: set 'Keep with next' on list items "
                            "before the page break. Or merge the two <L> elements in the "
                            "Acrobat Pro Tags panel."
                        ),
                    })

            # Non-standard roles
            rm_analysis = analyze_role_map(struct_tree_root, role_map)
            result["role_map_analysis"] = rm_analysis
            for unmapped in rm_analysis["unmapped_tags"]:
                result["findings"].append({
                    "rule": "PDFQ.NONSTD.ROLE",
                    "severity": "Info",
                    "confidence": "High",
                    "message": (
                        f"Non-standard tag '{unmapped}' has no role mapping. "
                        "PDF/UA validators may flag this as undefined."
                    ),
                    "fix": (
                        f"Add a role mapping in the RoleMap: '{unmapped}' → '/P' "
                        "(if text content) or mark as Artifact if decorative."
                    ),
                })

            # Headings
            hdg = analyze_headings(struct_tree_root)
            result["headings"] = hdg
            if hdg["skipped_levels"]:
                result["findings"].append({
                    "rule": "PDFBP.HEADING.SKIP",
                    "severity": "Warning",
                    "confidence": "High",
                    "wcag": "1.3.1",
                    "message": f"Heading levels skipped: {hdg['skipped_levels']}",
                    "fix": "Ensure heading hierarchy is H1→H2→H3 without gaps.",
                })

            # Tables
            tbl = analyze_tables(struct_tree_root)
            result["tables"] = tbl
            if tbl["table_count"] > 0 and not tbl["has_th"]:
                result["findings"].append({
                    "rule": "PDFUA.TABLE.HEADERS",
                    "severity": "Error",
                    "confidence": "Medium",
                    "matterhorn": "15-003",
                    "wcag": "1.3.1",
                    "message": "Table present but no /TH (header cell) elements found.",
                    "fix": "Add /TH tags to header row cells in the Tags panel.",
                })

            # Figure alt text check
            fig_alt = _check_figure_alt_text(struct_tree_root)
            result["figure_alt"] = fig_alt

            if fig_alt["figures_total"] > 0 and fig_alt["figures_missing_alt"]:
                missing_count = len(fig_alt["figures_missing_alt"])
                total = fig_alt["figures_total"]
                result["findings"].append({
                    "rule": "PDFUA.IMG.ALT",
                    "severity": "Error",
                    "confidence": "High",
                    "matterhorn": "13-004",
                    "wcag": "1.1.1",
                    "message": (
                        f"{missing_count} of {total} Figure element(s) "
                        "missing /Alt text in the structure tree."
                    ),
                    "fix": (
                        "In Acrobat Pro: Tags panel \u2192 right-click each Figure tag \u2192 "
                        "Properties \u2192 add Alternate Text. Or use the Accessibility "
                        "tool \u2192 Set Alternate Text."
                    ),
                })

            # Reading order analysis
            ro = analyze_reading_order(pdf, struct_tree_root)
            result["reading_order"] = ro

            if ro["figure_caption_issues"]:
                result["findings"].append({
                    "rule": "PDFBP.ORDER.FIGURE",
                    "severity": "Warning",
                    "confidence": "Medium",
                    "wcag": "1.3.2",
                    "matterhorn": "09-004",
                    "message": (
                        f"{len(ro['figure_caption_issues'])} image(s) (Figure elements) "
                        "are not immediately followed by a Caption in the tag tree. "
                        "Screen readers may not associate the image with its description."
                    ),
                    "fix": (
                        "In the Acrobat Pro Tags panel, ensure each <Figure> tag is "
                        "immediately followed by its corresponding <Caption> as the next sibling. "
                        "The Figure and Caption should be children of the same parent element."
                    ),
                    "outcome": (
                        "A screen reader user listening to this document may hear the image "
                        "described (if alt text is present), then hear unrelated paragraph text, "
                        "then hear the caption — making the connection between image and "
                        "caption unclear or lost entirely."
                    ),
                    "manual_review": False,
                })

            if ro["mcid_order_issues"]:
                affected_pages = [str(p["page"]) for p in ro["mcid_order_issues"]]
                worst = max(ro["mcid_order_issues"], key=lambda p: p["inversion_rate"])
                result["findings"].append({
                    "rule": "PDFBP.ORDER.MCID",
                    "severity": "Warning",
                    "confidence": "Medium",
                    "wcag": "1.3.2",
                    "matterhorn": "09-004",
                    "message": (
                        f"Structure-tree reading order may not match visual layout on "
                        f"{len(ro['mcid_order_issues'])} page(s): pages {affected_pages}. "
                        f"Highest mismatch on page {worst['page']} "
                        f"({int(worst['inversion_rate'] * 100)}% of element pairs out of order). "
                        "This typically indicates multi-column layouts, sidebars, or "
                        "text boxes not correctly threaded in the tag tree."
                    ),
                    "fix": (
                        "Open in Acrobat Pro → All Tools → Accessibility → Reading Order tool. "
                        "Click 'Show page content groups'. The numbered boxes show AT reading order. "
                        "Verify the sequence is correct, then drag groups to reorder if needed. "
                        "Re-export from source with 'Use document structure for tab order' enabled."
                    ),
                    "outcome": (
                        "Screen reader users on the affected pages may hear content in the wrong "
                        "sequence — for example: an entire right column read before the left, "
                        "a sidebar interspersed mid-sentence, or a figure caption read pages "
                        "before the image it describes."
                    ),
                    "manual_review": True,
                    "details": ro["mcid_order_issues"],
                })

            # Always: mandatory manual review finding for reading order
            result["findings"].append({
                "rule": "PDFQ.ORDER.MANUAL",
                "severity": "Info",
                "confidence": "High",
                "wcag": "1.3.2",
                "matterhorn": "09-004",
                "message": (
                    "Reading order requires manual verification. Automated MCID analysis "
                    "can detect structural signals but cannot confirm correct logical sequence "
                    "for every layout type. Verification is required using Acrobat Pro's "
                    "Reading Order tool or live testing with a screen reader."
                ),
                "fix": (
                    "All Tools → Accessibility → Reading Order → Show page content groups. "
                    "Verify numbered boxes match intended reading sequence. "
                    "Test with NVDA (Insert+Down for continuous reading) or JAWS (Insert+Down). "
                    "Pay special attention to: form fields, sidebars, multi-column content, "
                    "and any text that overlaps images."
                ),
                "outcome": (
                    "If reading order is not verified, any page with non-trivial layout may "
                    "be read in the wrong sequence by JAWS, NVDA, or Narrator users — from "
                    "mildly confusing to completely unusable depending on the layout complexity."
                ),
                "manual_review": True,
            })

    except Exception as e:
        result["errors"].append(f"Could not analyze tags: {e}")

    return result


def scan_folder(folder: Path) -> list:
    pdfs = sorted(folder.glob("*.pdf"))
    return [scan_tags(p) for p in pdfs]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scan PDF tag tree structure for accessibility issues."
    )
    parser.add_argument("path", help="PDF file or folder containing PDFs")
    parser.add_argument("--output", help="Write JSON output to this file")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args()

    target = Path(args.path)
    if target.is_dir():
        results = scan_folder(target)
    elif target.is_file():
        results = [scan_tags(target)]
    else:
        sys.exit(f"ERROR: Path not found: {target}")

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"JSON written to {args.output}")
    elif args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            fp = r.get("form_placement", {})
            ls = r.get("list_structure", {})
            errs = sum(1 for f in r["findings"] if f["severity"] == "Error")
            warns = sum(1 for f in r["findings"] if f["severity"] == "Warning")
            print(f"\n{r['file']}")
            print(f"  Form placement : {fp.get('form_placement','n/a')} "
                  f"({fp.get('form_tags_in_tree',0)} in tree, "
                  f"{fp.get('form_tags_orphaned',0)} orphaned)")
            print(f"  Lists          : {ls.get('total_list_elements',0)} list(s), "
                  f"{'SPLIT ⚠️' if ls.get('has_split_lists') else 'OK ✅'}")
            print(f"  Tags           : {r.get('tag_counts',{})}")
            print(f"  Findings       : {errs} errors, {warns} warnings")

    return 0


if __name__ == "__main__":
    sys.exit(main())
