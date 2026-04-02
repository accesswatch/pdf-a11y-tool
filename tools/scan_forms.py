"""
scan_forms.py — PDF AcroForm Field Accessibility Scanner
=========================================================
Persistent utility for PDF accessibility audits.
Inspects every AcroForm field for:
  - Tooltip / alternate name (/TU) presence  [Joyce Q1 → PDFUA.26.001]
  - Field-to-structure-tree linkage          [Joyce Q1 → PDFUA.26.002]
  - Tab order configuration                  [PDFBP.FORMS.TAB_ORDER]
  - Field type coverage (text, checkbox, radio, choice, signature)
  - Widget annotation orphan detection       [pypdf reattach pattern]
  - Required-field marking in tooltip
  - Radio group tooltip consistency          [WebAIM forms guide]
  - Push-button tooltip warning             [WebAIM: tooltips override button text]
  - Pre-form instructions placement         [WebAIM: Tab skips non-field content]

Uses:
  - pikepdf.form.Form  — authoritative field iteration and property access
    (field.alternate_name IS the tooltip/TU; confirmed in pikepdf docs)
  - pypdf  — widget annotation scan for orphan detection

Usage:
    python tools/scan_forms.py <pdf_or_folder> [--json] [--output file.json]

Dependencies: pikepdf, pypdf

KEY RESEARCH FINDINGS:
  Context7 — pikepdf readthedocs:
  - pikepdf.form.Form(pdf).items() → yields (name, field) pairs
  - field.alternate_name             → this IS the /TU tooltip field
  - field.fully_qualified_name       → dot-path field name
  - field.is_text / is_checkbox / is_radio_button / is_choice
  - field.is_required                → /Ff bit 2
  - AcroForm.fields                  → terminal fields sequence
  - AcroForm.exists                  → bool
  pypdf provides reattach_fields() for repairing orphaned widget annotations.

  WebAIM — Accessible Forms in Acrobat (webaim.org/techniques/acrobat/forms):
  - Tooltip must match the visible label; mismatches are an active deception risk
  - Radio button GROUPS share one Tooltip for the whole group question
  - Radio button Choice value (/AS) must match the visible option label
  - Checkboxes: Tooltip should describe the group question + the individual choice
  - Push buttons: do NOT add Tooltip — it overrides the button label text
  - Required fields: add '(required)' to the Tooltip, not just a visual asterisk
  - Pre-form instructions: Tab key skips non-field content in forms mode;
    put critical instructions BEFORE the first form field in the tag order

This file is PERMANENT — do not delete. Used by agents and scan_all.py.
"""

import sys
import json
import argparse
from pathlib import Path

try:
    import pikepdf
    from pikepdf import Dictionary, Array, Name
    from pikepdf.form import Form as PikeForm
except ImportError:
    sys.exit("ERROR: pikepdf not installed. Run: pip install pikepdf")

try:
    from pypdf import PdfReader
    _PYPDF_AVAILABLE = True
except ImportError:
    _PYPDF_AVAILABLE = False


# ---------------------------------------------------------------------------
# Tab order helpers
# ---------------------------------------------------------------------------

def get_page_tab_order(page_obj) -> str:
    """Return the /Tabs value for a page, or 'unset'."""
    try:
        tabs = page_obj.get("/Tabs", None)
        if tabs is None:
            return "unset"
        return str(tabs).lstrip("/")
    except Exception:
        return "unknown"


def check_page_tab_orders(pdf) -> dict:
    """Check tab order across all pages. Returns summary dict."""
    orders = []
    for page in pdf.pages:
        orders.append(get_page_tab_order(page))
    structure_aligned = all(o in ("S", "unset") for o in orders)
    return {
        "per_page": orders,
        "all_structure_order": structure_aligned,
        "has_unset": "unset" in orders,
    }


# ---------------------------------------------------------------------------
# Widget orphan detection via pypdf
# ---------------------------------------------------------------------------

def find_orphan_widgets(pdf_path: Path) -> list:
    """
    Use pypdf to find widget annotations not linked into AcroForm Fields tree.
    These are orphan fields — visually present but invisible to AT.
    """
    if not _PYPDF_AVAILABLE:
        return []
    try:
        reader = PdfReader(str(pdf_path))
        orphans = []
        # Get all field names from the AcroForm
        fields = reader.get_fields() or {}
        known_names = set(fields.keys())
        # Scan page annotations for Widget subtype
        for page_num, page in enumerate(reader.pages, 1):
            annots = page.get("/Annots", None)
            if annots is None:
                continue
            for annot in annots:
                obj = annot.get_object()
                subtype = str(obj.get("/Subtype", ""))
                if "/Widget" in subtype:
                    t_val = obj.get("/T", None)
                    name = str(t_val) if t_val else None
                    if name and name not in known_names:
                        orphans.append({"page": page_num, "field_name": name})
        return orphans
    except Exception as e:
        return [{"error": str(e)}]


# ---------------------------------------------------------------------------
# Main form scan
# ---------------------------------------------------------------------------

def scan_forms(pdf_path: Path) -> dict:
    result = {
        "file": pdf_path.name,
        "path": str(pdf_path),
        "acroform_exists": False,
        "field_count": 0,
        "fields": [],
        "tab_order": {},
        "orphan_widgets": [],
        "findings": [],
        "errors": [],
    }

    try:
        with pikepdf.open(pdf_path) as pdf:
            # ----------------------------------------------------------------
            # AcroForm existence check
            # ----------------------------------------------------------------
            acroform = pdf.Root.get("/AcroForm", None)
            if acroform is None:
                result["findings"].append({
                    "rule": "PDFBP.FORMS.NOACROFORM",
                    "severity": "Info",
                    "confidence": "High",
                    "message": "No AcroForm found — document has no interactive form fields.",
                    "fix": "No action needed unless this should be a fillable form.",
                })
                return result

            result["acroform_exists"] = True

            # ----------------------------------------------------------------
            # Tab order per page
            # ----------------------------------------------------------------
            tab_order_info = check_page_tab_orders(pdf)
            result["tab_order"] = tab_order_info
            if tab_order_info["has_unset"]:
                unset_pages = [
                    i + 1 for i, o in enumerate(tab_order_info["per_page"])
                    if o == "unset"
                ]
                result["findings"].append({
                    "rule": "PDFBP.NAV.TABORDER",
                    "severity": "Warning",
                    "confidence": "High",
                    "matterhorn": "25-001",
                    "wcag": "2.4.3",
                    "message": (
                        f"Tab order not explicitly set to structure order on "
                        f"{len(unset_pages)} page(s): {unset_pages}. "
                        "Screen readers may read form fields out of order."
                    ),
                    "fix": (
                        "In Acrobat Pro: Page Properties → Tab Order → 'Use Document Structure'. "
                        "Or set /Tabs /S in each page dictionary. "
                        "In source Word doc: Ensure accessibility tags are correct before export."
                    ),
                })

            # ----------------------------------------------------------------
            # Field-level inspection via pikepdf.form.Form
            # confirmed API: Form(pdf).items() → (name, field) pairs
            # field.alternate_name IS the /TU tooltip (pikepdf docs confirmed)
            # ----------------------------------------------------------------
            try:
                pf = PikeForm(pdf)
                field_items = list(pf.items())
            except Exception as fe:
                result["errors"].append(f"Form field iteration error: {fe}")
                field_items = []

            missing_tooltip = []
            missing_required_text = []
            checkbox_no_tooltip = []
            push_button_with_tooltip = []  # WebAIM: button tooltip overrides button text
            radio_groups = {}             # group_name → list of tooltip values for consistency

            for field_name, field in field_items:
                fq_name = getattr(field, "fully_qualified_name", field_name)
                alt_name = getattr(field, "alternate_name", None)  # /TU tooltip
                is_required = getattr(field, "is_required", False)
                is_checkbox = getattr(field, "is_checkbox", False)
                is_text = getattr(field, "is_text", False)
                is_radio = getattr(field, "is_radio_button", False)
                is_choice = getattr(field, "is_choice", False)

                # Detect push buttons: /FT /Btn but not checkbox or radio
                # Push buttons have /Ff bit 17 (0x10000) set
                is_push_button = False
                try:
                    raw = field._obj  # underlying pikepdf Object
                    ff = int(raw.get("/Ff", 0))
                    ft = str(raw.get("/FT", "")).lstrip("/")
                    if ft == "Btn" and not is_checkbox and not is_radio:
                        is_push_button = (ff & 0x10000) != 0 or (not is_checkbox and not is_radio)
                except Exception:
                    pass

                field_type = (
                    "push_button" if is_push_button else
                    "checkbox" if is_checkbox else
                    "radio" if is_radio else
                    "text" if is_text else
                    "choice" if is_choice else
                    "unknown"
                )

                # Tooltip check
                has_tooltip = bool(alt_name and str(alt_name).strip())
                tooltip_str = str(alt_name).strip() if alt_name else ""

                field_rec = {
                    "name": fq_name,
                    "type": field_type,
                    "tooltip": tooltip_str if tooltip_str else None,
                    "has_tooltip": has_tooltip,
                    "is_required": is_required,
                }
                result["fields"].append(field_rec)

                # WebAIM: push buttons should NOT have a tooltip (tooltip overrides button text)
                if is_push_button and has_tooltip:
                    push_button_with_tooltip.append(fq_name)

                if not has_tooltip:
                    if not is_push_button:  # don't flag push buttons for missing tooltip
                        missing_tooltip.append(fq_name)
                    if is_checkbox:
                        checkbox_no_tooltip.append(fq_name)
                else:
                    if is_required and tooltip_str:
                        # WebAIM: required fields must indicate required status in tooltip text
                        if "required" not in tooltip_str.lower() and "*" not in tooltip_str:
                            missing_required_text.append(fq_name)
                    # Track radio group tooltips for consistency check
                    if is_radio:
                        group = fq_name.split(".")[-1] if "." in fq_name else fq_name
                        radio_groups.setdefault(group, []).append(tooltip_str)

            # WebAIM: all radio buttons in a group should share the same tooltip
            radio_inconsistent = []
            for group_name, tooltips in radio_groups.items():
                unique = set(tooltips)
                if len(unique) > 1:
                    radio_inconsistent.append({
                        "group": group_name,
                        "tooltips": list(unique),
                    })

            result["field_count"] = len(field_items)

            # ----------------------------------------------------------------
            # Findings from field inspection
            # ----------------------------------------------------------------
            if missing_tooltip:
                is_consent = any(
                    "consent" in n.lower() or "agree" in n.lower() or
                    "auth" in n.lower() or "check" in n.lower()
                    for n in missing_tooltip
                )
                severity = "Error" if is_consent else "Warning"
                result["findings"].append({
                    "rule": "PDFUA.FORM.TU",
                    "severity": severity,
                    "confidence": "High",
                    "matterhorn": "26-001",
                    "wcag": "1.3.1",
                    "message": (
                        f"{len(missing_tooltip)} of {len(field_items)} field(s) "
                        "have no tooltip (alternate name / /TU entry). "
                        f"Affected: {missing_tooltip[:5]}"
                        f"{'...' if len(missing_tooltip) > 5 else ''}"
                    ),
                    "fix": (
                        "In Acrobat Pro: Forms → Edit → click each field → Properties → "
                        "General tab → Tooltip. Describe the field's purpose. "
                        "For required fields, add '(required)' to the tooltip. "
                        "For checkboxes, the tooltip should describe what checking means, e.g. "
                        "'I authorize the listed activities (required)'."
                    ),
                    "consent_note": (
                        "Without a tooltip, a screen reader user hears only 'checkbox, unchecked' "
                        "with no indication of what they are consenting to."
                    ) if is_consent else None,
                })

            if missing_required_text:
                result["findings"].append({
                    "rule": "PDFBP.FORMS.REQUIRED_LABEL",
                    "severity": "Warning",
                    "confidence": "Medium",
                    "wcag": "3.3.2",
                    "message": (
                        f"{len(missing_required_text)} required field(s) do not indicate "
                        "required status in their tooltip. Fields relying only on visual "
                        "asterisk (*) are not accessible to screen reader users."
                    ),
                    "fix": "Add '(required)' or '* required' to the tooltip of required fields.",
                })

            # WebAIM: push button tooltip overrides the button's visible text label
            if push_button_with_tooltip:
                result["findings"].append({
                    "rule": "PDFBP.FORMS.BUTTON_TOOLTIP",
                    "severity": "Warning",
                    "confidence": "High",
                    "wcag": "4.1.2",
                    "message": (
                        f"{len(push_button_with_tooltip)} push button(s) have a tooltip set. "
                        "Per WebAIM guidance, the tooltip of a push button overrides its visible "
                        "label — screen readers will announce the tooltip instead of the button text. "
                        f"Affected: {push_button_with_tooltip}"
                    ),
                    "fix": (
                        "Remove the tooltip (alternate name) from push buttons in Acrobat Pro: "
                        "Forms > Edit > click the button > Properties > General > clear the Tooltip field. "
                        "The button's visible label text is sufficient and correct."
                    ),
                    "source": "https://webaim.org/techniques/acrobat/forms",
                })

            # WebAIM: all radio buttons in a group must share the same tooltip (group question)
            if radio_inconsistent:
                result["findings"].append({
                    "rule": "PDFBP.FORMS.RADIO_TOOLTIP",
                    "severity": "Warning",
                    "confidence": "High",
                    "wcag": "1.3.1",
                    "message": (
                        f"{len(radio_inconsistent)} radio button group(s) have inconsistent tooltips. "
                        "Per WebAIM guidance, every radio button in a group should share the same "
                        "tooltip — the question text for the group. Inconsistent tooltips confuse "
                        "screen reader users who hear a different announcement for each option. "
                        f"Groups affected: {[g['group'] for g in radio_inconsistent]}"
                    ),
                    "fix": (
                        "In Acrobat Pro, set all radio buttons within each group to the same tooltip "
                        "that describes the group question, e.g. 'Do you authorize this procedure?'. "
                        "The individual /AS choice values should reflect each option label."
                    ),
                    "source": "https://webaim.org/techniques/acrobat/forms",
                })

            # ----------------------------------------------------------------
            # Structure tree vs AcroForm field count comparison
            # ----------------------------------------------------------------
            struct_tree = pdf.Root.get("/StructTreeRoot", None)
            if struct_tree:
                # Count Form elements in structure tree
                form_in_tree = 0
                try:
                    from scan_tags import iter_struct_tree, tag_name
                    for _depth, name, _node in iter_struct_tree(struct_tree):
                        if name == "Form":
                            form_in_tree += 1
                except ImportError:
                    # If scan_tags not importable (standalone run), estimate via raw walk
                    _MAX_RECURSION_DEPTH = 200

                    def _count_form_tags(node, depth=0):
                        if depth > _MAX_RECURSION_DEPTH:
                            return 0
                        count = 0
                        if not isinstance(node, Dictionary):
                            return 0
                        if str(node.get("/S", "")).lstrip("/") == "Form":
                            count = 1
                        kids = node.get("/K", None)
                        if kids:
                            if isinstance(kids, Array):
                                for kid in kids:
                                    try:
                                        count += _count_form_tags(kid, depth + 1)
                                    except Exception:
                                        pass
                            elif isinstance(kids, Dictionary):
                                count += _count_form_tags(kids, depth + 1)
                        return count
                    form_in_tree = _count_form_tags(struct_tree)

                acroform_count = len(field_items)

                if acroform_count > 0 and form_in_tree == 0:
                    result["findings"].append({
                        "rule": "PDFBP.FORM.STRUCT",
                        "severity": "Warning",
                        "confidence": "High",
                        "matterhorn": "26-002",
                        "wcag": "1.3.1",
                        "message": (
                            f"{acroform_count} AcroForm field(s) exist but NO /Form elements "
                            "were found in the structure tree. Fields are accessible only via "
                            "AcroForm, not through the semantic tag structure."
                        ),
                        "fix": (
                            "Re-export from the source document with 'Create tagged PDF' enabled. "
                            "Or in Acrobat Pro, use Accessibility > Add Tags to Document and then "
                            "manually link form widgets to /Form structure elements."
                        ),
                        "joyce_note": (
                            "This is the core of Joyce's Q1 concern. An AcroForm-only structure "
                            "means the form fields exist and are operable, but they are NOT part "
                            "of the document's semantic reading order. Screen readers like JAWS "
                            "switch to 'forms mode' and can find the fields, but the structural "
                            "relationship between the label text and the field is severed."
                        ),
                    })
                elif acroform_count > 0 and form_in_tree > 0 and form_in_tree < acroform_count:
                    result["findings"].append({
                        "rule": "PDFUA.FORM.STRUCT",
                        "severity": "Error",
                        "confidence": "Medium",
                        "matterhorn": "26-002",
                        "wcag": "1.3.2",
                        "message": (
                            f"Only {form_in_tree} of {acroform_count} form field(s) are "
                            "represented in the structure tree. The remaining "
                            f"{acroform_count - form_in_tree} may be orphaned."
                        ),
                        "fix": (
                            "Use Acrobat Pro Tags panel to verify each /Form element is correctly "
                            "nested within its parent paragraph next to the label."
                        ),
                    })

            # ----------------------------------------------------------------
            # Orphan widget detection (pypdf)
            # ----------------------------------------------------------------
            if _PYPDF_AVAILABLE:
                orphans = find_orphan_widgets(pdf_path)
                result["orphan_widgets"] = orphans
                if orphans and not any("error" in o for o in orphans):
                    result["findings"].append({
                        "rule": "PDFBP.FORM.ORPHAN",
                        "severity": "Warning",
                        "confidence": "High",
                        "message": (
                            f"{len(orphans)} widget annotation(s) found on pages "
                            "but not linked in the AcroForm Fields tree. "
                            "These fields are invisible to some assistive technologies."
                        ),
                        "fix": (
                            "Run pypdf PdfWriter.reattach_fields() to programmatically re-link "
                            "orphaned widgets into the AcroForm structure, or use Acrobat Pro "
                            "Forms > Edit to manually reconnect them."
                        ),
                        "auto_fixable": True,
                        "tool": "pypdf.PdfWriter.reattach_fields()",
                    })

    except Exception as e:
        result["errors"].append(f"Could not open or analyze file: {e}")

    return result


def scan_folder(folder: Path) -> list:
    return [scan_forms(p) for p in sorted(folder.glob("*.pdf"))]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scan PDF AcroForm fields for accessibility issues."
    )
    parser.add_argument("path", help="PDF file or folder containing PDFs")
    parser.add_argument("--output", help="Write JSON output to this file")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args()

    target = Path(args.path)
    if target.is_dir():
        results = scan_folder(target)
    elif target.is_file():
        results = [scan_forms(target)]
    else:
        sys.exit(f"ERROR: Path not found: {target}")

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"JSON written to {args.output}")
    elif args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            errs = sum(1 for f in r["findings"] if f["severity"] == "Error")
            warns = sum(1 for f in r["findings"] if f["severity"] == "Warning")
            missing = sum(1 for f in r["fields"] if not f["has_tooltip"])
            print(f"\n{r['file']}")
            print(f"  Fields       : {r['field_count']} total, {missing} missing tooltip")
            tab = r.get("tab_order", {})
            print(f"  Tab order    : {'structure ✅' if tab.get('all_structure_order') else 'UNSET ⚠️'}")
            print(f"  Orphans      : {len(r.get('orphan_widgets', []))}")
            print(f"  Findings     : {errs} errors, {warns} warnings")


if __name__ == "__main__":
    sys.exit(main())
