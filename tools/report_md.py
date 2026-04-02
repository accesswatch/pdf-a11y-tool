"""
report_md.py — Markdown Accessibility Audit Report Generator
=============================================================
Reads scan_results.json (from scan_all.py) and produces a polished
Markdown report that matches the "Good Report" format:

  - Non-technical executive summary
  - Prioritised quick-fix steps
  - ⚠️  Manual Review Required section (READING ORDER FIRST)
  - Additional improvements
  - Summary table + priority action plan
  - What's already working
  - Time estimates
  - Technical Appendices (A–E)

Usage:
    python tools/report_md.py scan_results.json [--output REPORT.md]

This file is PERMANENT — do not delete.
"""

import sys
import json
import argparse
import datetime
from pathlib import Path
from collections import defaultdict

# Import shared rule catalog (single source of truth for rule knowledge)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from pdf_a11y.core import rule_catalog  # noqa: E402

try:
    from fix_tiers import automation_summary_md
    _HAS_FIX_TIERS = True
except ImportError:
    _HAS_FIX_TIERS = False
    def automation_summary_md(rule_ids, affected_count=0, total_count=0, remediation_applied=False):  # noqa: E302
        return ""


# ---------------------------------------------------------------------------
# Severity helpers
# ---------------------------------------------------------------------------

SEVERITY_EMOJI = {"Error": "\U0001f534", "Warning": "\U0001f7e1", "Info": "\U0001f535"}

# Re-export from shared catalog so report_html.py imports keep working
WCAG_LINKS = rule_catalog.WCAG_LINKS
REF_LINKS = rule_catalog.REF_LINKS

# Delegate to catalog helpers
_wcag_md = rule_catalog.wcag_md
_wcag_html = rule_catalog.wcag_html


def _ref_html(key: str) -> str:
    """Convert a REF_LINKS markdown link to an HTML <a> tag."""
    import re
    md = REF_LINKS.get(key, key)
    m = re.match(r'\[(.+?)\]\((.+?)\)', md)
    if m:
        return f'<a href="{m.group(2)}">{m.group(1)}</a>'
    return md

# Re-export from shared catalog
RULE_REFERENCE = rule_catalog.RULE_REFERENCE

READING_ORDER_RULES = rule_catalog.READING_ORDER_RULES

MANUAL_REVIEW_RULES = rule_catalog.MANUAL_REVIEW_RULES


# ---------------------------------------------------------------------------
# Data aggregation helpers
# ---------------------------------------------------------------------------

def _present_types(audit: dict) -> set:
    """Return the set of file types present in the scan (e.g. {'pdf', 'pptx'})."""
    return {f["type"] for f in audit.get("files", [])}


def _all_findings(audit: dict) -> list:
    """Flat list of all findings across all files, each annotated with file name."""
    out = []
    for f in audit.get("files", []):
        for fn in f.get("findings", []):
            out.append({**fn, "_file": f["file"], "_type": f["type"]})
    return out


def _findings_by_rule(findings: list) -> dict:
    """Group findings by rule ID, collecting affected files."""
    by_rule = defaultdict(lambda: {"files": [], "findings": []})
    for fn in findings:
        r = fn.get("rule", "UNKNOWN")
        by_rule[r]["files"].append(fn["_file"])
        by_rule[r]["findings"].append(fn)
    return by_rule


def _count_by_severity(findings: list) -> dict:
    c = {"Error": 0, "Warning": 0, "Info": 0}
    for f in findings:
        s = f.get("severity", "Info")
        c[s] = c.get(s, 0) + 1
    return c


def _unique_files_for_rule(by_rule: dict, rule: str) -> list:
    return sorted(set(by_rule[rule]["files"])) if rule in by_rule else []


def _active_rules(all_rules: list[str], by_rule: dict) -> list[str]:
    """Return only the rules that have actual findings in the scan results."""
    return [r for r in all_rules if r in by_rule]


def _plural(n: int, singular: str, plural: str | None = None) -> str:
    return f"{n} {singular if n == 1 else (plural or singular + 's')}"


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_header(audit: dict) -> str:
    s = audit["summary"]
    scan_date = audit.get("scan_date", "")[:10]
    try:
        display_date = datetime.datetime.fromisoformat(audit.get("scan_date", "")).strftime("%B %d, %Y")
    except Exception:
        display_date = scan_date

    type_labels = []
    for t, n in s.get("by_type", {}).items():
        if n:
            ext = {"pdf": "PDF", "docx": "Word", "xlsx": "Excel", "pptx": "PowerPoint",
                   "epub": "ePub", "md": "Markdown"}
            type_labels.append(f"{n} {ext.get(t, t.upper())}")

    doc_desc = ", ".join(type_labels) if type_labels else f"{s['total_files']} documents"

    return (
        f"# Accessibility Audit Report\n\n"
        f"| | |\n"
        f"|---|---|\n"
        f"| **Generated** | {display_date} |\n"
        f"| **Audience** | Document editors and accessibility reviewers |\n"
        f"| **Documents Reviewed** | {doc_desc} |\n"
        f"| **Overall Score** | {s['score']}/100 · Grade **{s['grade']}** |\n"
        f"\n---\n"
    )


def _render_executive_summary(audit: dict, by_rule: dict, all_f: list) -> str:
    s = audit["summary"]
    counts = _count_by_severity(all_f)
    errors = [r for r, d in by_rule.items()
              if any(fn.get("severity") == "Error" for fn in d["findings"])]
    warnings = [r for r, d in by_rule.items()
                if any(fn.get("severity") == "Warning" for fn in d["findings"])
                and r not in errors]

    # Working-well items
    working = []
    all_types = {f["type"] for f in audit.get("files", [])}
    pdf_files = [f for f in audit.get("files", []) if f["type"] == "pdf"]

    if pdf_files:
        tagged_errors = {r for r in errors if "STRUCT.NOTREE" in r or "STRUCT.TAGGED" in r}
        if not tagged_errors:
            working.append("PDF documents are properly tagged — the structural foundation is in place")
        img_errors = {r for r in errors if "IMG.ALT" == r or "PDFBP.ORDER.FIGURE" == r}
        if "PDFUA.METADATA.TITLE" not in errors:
            pass  # title present — mentioned later

    lines = [
        "## Executive Summary\n",
    ]

    if s["grade"] in ("A", "B"):
        lines.append(
            f"The {_plural(s['total_files'], 'document')} audited "
            f"score **{s['score']}/100 (Grade {s['grade']})** — a solid foundation. "
            "Most important structural requirements are already met.\n"
        )
    elif s["grade"] == "C":
        lines.append(
            f"The {_plural(s['total_files'], 'document')} audited "
            f"score **{s['score']}/100 (Grade {s['grade']})**. "
            "There is a good structural foundation, but several issues need attention "
            "to meet accessibility standards fully.\n"
        )
    else:
        lines.append(
            f"The {_plural(s['total_files'], 'document')} audited "
            f"score **{s['score']}/100 (Grade {s['grade']})**. "
            "Significant accessibility barriers were found that should be addressed before distribution.\n"
        )

    if errors:
        # Sort by number of affected files (highest impact first)
        errors.sort(key=lambda r: -len(_unique_files_for_rule(by_rule, r)))
        lines.append("### Main Issues Found\n")
        for rule in errors[:6]:
            ref = RULE_REFERENCE.get(rule, {})
            desc = ref[4] if ref else rule
            affected = _unique_files_for_rule(by_rule, rule)
            n = len(affected)
            total = s["total_files"]
            lines.append(f"- **{desc}** ({n} of {total} files)")
        lines.append("")

    if working:
        lines.append("### What Is Already Working\n")
        for w in working:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("---\n")
    return "\n".join(lines)


def _collect_fix_results(audit: dict) -> dict[str, list[dict]]:
    """Collect all applied fix results from audit data, grouped by rule ID.

    Returns a dict mapping rule_id -> list of fix detail dicts, e.g.:
        {"PDFUA.METADATA.TITLE": [
            {"file": "doc.pdf", "status": "fixed", "detail": "Set title to 'My Doc'"},
            {"file": "other.pdf", "status": "skipped", "reason": "Title already set"},
        ]}
    """
    results: dict[str, list[dict]] = {}
    for fe in audit.get("files", []):
        rem = fe.get("remediation", {})
        if not rem.get("applied"):
            continue
        fname = fe["file"]
        for fix in rem.get("fix_result", []):
            rule = fix.get("rule", "")
            if not rule:
                continue
            entry = {"file": fname, "status": fix.get("status", "?")}
            if fix.get("detail"):
                entry["detail"] = fix["detail"]
            if fix.get("reason"):
                entry["reason"] = fix["reason"]
            results.setdefault(rule, []).append(entry)
    return results


def _render_applied_changes_md(fix_results: dict[str, list[dict]],
                                rule_ids: list[str]) -> str:
    """Render a 'Changes Applied' block showing exact fix details for given rules.

    Only rendered when there are actual fix results. Shows the exact text of
    what was changed per file, so users can verify the automated modifications.
    """
    relevant: list[dict] = []
    for rid in rule_ids:
        relevant.extend(fix_results.get(rid, []))
    if not relevant:
        return ""

    lines = [
        "#### Changes Applied by the Toolkit\n",
        "The following changes were made automatically. "
        "**Review each change** to confirm accuracy.\n",
    ]
    # Group by status
    fixed = [r for r in relevant if r["status"] == "fixed"]
    skipped = [r for r in relevant if r["status"] == "skipped"]
    failed = [r for r in relevant if r["status"] == "failed"]
    needs_human = [r for r in relevant if r["status"] == "needs-human"]

    if fixed:
        lines.append("**Applied:**")
        for r in fixed:
            detail = r.get("detail", "")
            lines.append(f"- `{r['file']}` — {detail}")
        lines.append("")
    if skipped:
        lines.append("**Skipped (already correct):**")
        for r in skipped:
            reason = r.get("reason", "")
            lines.append(f"- `{r['file']}` — {reason}")
        lines.append("")
    if needs_human:
        lines.append("**Needs human review:**")
        for r in needs_human:
            detail = r.get("detail", r.get("reason", ""))
            lines.append(f"- `{r['file']}` — {detail}")
        lines.append("")
    if failed:
        lines.append("**Failed:**")
        for r in failed:
            reason = r.get("reason", "")
            lines.append(f"- `{r['file']}` — {reason}")
        lines.append("")

    return "\n".join(lines)


def _render_quick_fixes(by_rule: dict, audit: dict) -> str:
    """Generate prioritised step-by-step fix instructions for common errors.

    Each fix heading includes a compliance badge:
      🔴 Required  — WCAG / PDF/UA conformance requirement
      🟡 Recommended — best practice for usability

    Structure of each fix block:
      ### Fix N — Title (X of Y files)
      > badge
      #### What This Checks  — plain-English rule explanation
      #### How to Fix        — format-specific resolution steps
      #### Why This Matters   — impact on real users
      #### Changes Applied   — (when remediation was run) exact details of changes
    """
    s = audit["summary"]
    total = s["total_files"]
    types = _present_types(audit)
    rem_applied = audit.get("remediation", {}).get("enabled", False)
    fix_results = _collect_fix_results(audit) if rem_applied else {}
    sections = []

    fix_number = 1

    # ── Tagging ──
    tagged_files = sorted(set(
        _unique_files_for_rule(by_rule, "PDFUA.STRUCT.TAGGED") +
        _unique_files_for_rule(by_rule, "PDFUA.STRUCT.NOTREE")))
    if tagged_files:
        n = len(tagged_files)
        block = [
            f"### Fix {fix_number} — Tag the Document for Accessibility ({n} of {total} files)\n",
            f"> 🔴 **Required** — {_wcag_md('1.3.1')} / PDF/UA section 5.1\n",
            automation_summary_md(["PDFUA.STRUCT.TAGGED", "PDFUA.STRUCT.NOTREE"], n, total, remediation_applied=rem_applied),
            "#### What This Checks\n",
            "PDF/UA requires every PDF to contain a complete tag structure "
            "(rules `PDFUA.STRUCT.TAGGED` and `PDFUA.STRUCT.NOTREE`). "
            "Tags define the logical reading order and identify each element — "
            "headings, paragraphs, lists, tables, and form fields. The scanner "
            "checks whether the document contains any tags at all and whether "
            "a valid structure tree exists.\n",
            "#### How to Fix\n",
            "**Re-export from source (preferred):**",
            "1. Open the original Word, InDesign, or PowerPoint file",
            "2. File → Save As / Export → PDF",
            "3. Ensure **'Tagged PDF'** or **'Create Accessible PDF'** is checked",
            "4. Open the new PDF and verify tags in the Tags panel\n",
            "**In Adobe Acrobat Pro:**",
            "1. All Tools → Accessibility → AutoTag Document",
            "2. Review the Tags panel — fix any `<P>` elements that should be headings",
            "3. Run Accessibility Check (All Tools → Accessibility → Full Check) to verify",
            "4. File → Save As\n",
            "#### Why This Matters\n",
            "Tags are the foundation of PDF accessibility. "
            "Without tags, screen readers cannot determine document structure — headings, "
            "paragraphs, lists, tables, and form fields are all invisible. An untagged PDF "
            "is essentially a flat image to assistive technology.\n",
        ]
        changes = _render_applied_changes_md(fix_results, ["PDFUA.STRUCT.TAGGED", "PDFUA.STRUCT.NOTREE"])
        if changes:
            block.append(changes)
        sections.append("\n".join(block))
        fix_number += 1

    # ── Title ──
    title_files = _unique_files_for_rule(by_rule, "PDFUA.METADATA.TITLE") + \
                  _unique_files_for_rule(by_rule, "DOCX-META.TITLE") + \
                  _unique_files_for_rule(by_rule, "PPTX.META.TITLE") + \
                  _unique_files_for_rule(by_rule, "XLSX.META.TITLE") + \
                  _unique_files_for_rule(by_rule, "EPUB-E001")
    title_files = sorted(set(title_files))
    if title_files:
        n = len(title_files)
        pdf_title = bool(_unique_files_for_rule(by_rule, "PDFUA.METADATA.TITLE"))
        docx_title = bool(_unique_files_for_rule(by_rule, "DOCX-META.TITLE"))
        pptx_title = bool(_unique_files_for_rule(by_rule, "PPTX.META.TITLE"))
        xlsx_title = bool(_unique_files_for_rule(by_rule, "XLSX.META.TITLE"))
        epub_title = bool(_unique_files_for_rule(by_rule, "EPUB-E001"))

        active_title_rules = _active_rules(["PDFUA.METADATA.TITLE", "DOCX-META.TITLE",
                                             "PPTX.META.TITLE", "XLSX.META.TITLE", "EPUB-E001"], by_rule)
        block = [f"### Fix {fix_number} — Add a Document Title ({n} of {total} files)\n",
                 f"> 🔴 **Required** — {_wcag_md('2.4.2')}\n",
                 automation_summary_md(active_title_rules, n, total, remediation_applied=rem_applied),
                 "#### What This Checks\n",
                 "Every document must have a meaningful title set in its metadata "
                 f"(rules {', '.join(f'`{r}`' for r in active_title_rules)}). "
                 "The scanner reads the document properties and flags any file where "
                 "the title field is blank or set to a generic placeholder.\n",
                 "#### How to Fix\n"]
        if pdf_title:
            block += [
                "**In Adobe Acrobat Pro:**",
                "1. File → Properties",
                "2. Description tab → enter a meaningful title",
                "3. Initial View tab → set **Show: Document Title**",
                "4. Click OK → File → Save As\n",
            ]
        if docx_title:
            block += [
                "**In Microsoft Word:**",
                "1. File → Info → Properties (right panel)",
                "2. Enter title in the **Title** field",
                "3. Save\n",
            ]
        if pptx_title:
            block += [
                "**In Microsoft PowerPoint:**",
                "1. File → Info → Properties",
                "2. Enter title in the **Title** field",
                "3. Save\n",
            ]
        if xlsx_title:
            block += [
                "**In Microsoft Excel:**",
                "1. File → Info → Properties",
                "2. Enter title in the **Title** field",
                "3. Save\n",
            ]
        if epub_title:
            block += [
                "**In Sigil or Calibre (ePub):**",
                "1. Open the OPF file (content.opf)",
                "2. Add or edit `<dc:title>` in the `<metadata>` section",
                "3. Save\n",
            ]
        block += [
            "#### Why This Matters\n",
            "Screen readers announce the document title when opening a file. "
            "Without a title, users only hear the file name — which may be meaningless.\n",
            "> **Human review required after automation:** The automated fix tool sets "
            "a placeholder title derived from the file name (e.g. `TODO: Add descriptive "
            "document title`). You **must** replace this placeholder with a meaningful, "
            "human-written title that accurately describes the document's content.\n",
        ]
        changes = _render_applied_changes_md(fix_results, active_title_rules)
        if changes:
            block.append(changes)
        sections.append("\n".join(block))
        fix_number += 1

    # ── Language ──
    lang_files = _unique_files_for_rule(by_rule, "PDFUA.METADATA.LANG") + \
                 _unique_files_for_rule(by_rule, "DOCX-META.LANG") + \
                 _unique_files_for_rule(by_rule, "PPTX.META.LANG") + \
                 _unique_files_for_rule(by_rule, "EPUB-E003")
    lang_files = sorted(set(lang_files))
    if lang_files:
        n = len(lang_files)
        active_lang_rules = _active_rules(["PDFUA.METADATA.LANG", "DOCX-META.LANG",
                                              "PPTX.META.LANG", "EPUB-E003"], by_rule)
        block = [f"### Fix {fix_number} — Set the Document Language ({n} of {total} files)\n",
                 f"> 🔴 **Required** — {_wcag_md('3.1.1')}\n",
                 automation_summary_md(active_lang_rules, n, total, remediation_applied=rem_applied),
                 "#### What This Checks\n",
                 "Every document must declare its primary language in metadata "
                 f"(rules {', '.join(f'`{r}`' for r in active_lang_rules)}). "
                 "The scanner reads the language property and flags any file where "
                 "it is missing or empty.\n",
                 "#### How to Fix\n"]
        if _unique_files_for_rule(by_rule, "PDFUA.METADATA.LANG"):
            block += [
                "**In Adobe Acrobat Pro:**",
                "1. File → Properties → Advanced tab",
                "2. Reading Options → Language",
                "3. Enter `en` for English or `es` for Spanish",
                "4. Click OK → Save As\n",
            ]
        if _unique_files_for_rule(by_rule, "DOCX-META.LANG"):
            block += [
                "**In Microsoft Word:**",
                "1. Review → Language → Set Proofing Language",
                "2. Select the correct language → click OK",
                "3. Save\n",
            ]
        if _unique_files_for_rule(by_rule, "PPTX.META.LANG"):
            block += [
                "**In Microsoft PowerPoint:**",
                "1. Review → Language → Set Proofing Language",
                "2. Select the correct language → click OK",
                "3. Save\n",
            ]
        if _unique_files_for_rule(by_rule, "EPUB-E003"):
            block += [
                "**In Sigil or Calibre (ePub):**",
                "1. Open the OPF file (content.opf)",
                "2. Add or edit `<dc:language>en</dc:language>` in `<metadata>`",
                "3. Save\n",
            ]
        block += [
            "#### Why This Matters\n",
            "Screen readers use the language setting to choose the "
            "correct pronunciation engine. Wrong language = mispronounced or garbled text.\n",
            f"**Reference:** {_wcag_md('3.1.1')}\n",
        ]
        changes = _render_applied_changes_md(fix_results, active_lang_rules)
        if changes:
            block.append(changes)
        sections.append("\n".join(block))
        fix_number += 1

    # ── Form fields in structure tree ──
    form_struct_files = sorted(set(
        _unique_files_for_rule(by_rule, "PDFUA.FORM.STRUCT") +
        _unique_files_for_rule(by_rule, "PDFBP.FORM.STRUCT")))
    if form_struct_files:
        n = len(form_struct_files)
        has_error = bool(_unique_files_for_rule(by_rule, "PDFUA.FORM.STRUCT"))
        badge = f'> 🔴 **Required** — {_wcag_md("1.3.1")} / PDF/UA section 6.6\n' if has_error else f'> 🟡 **Recommended** — {_wcag_md("1.3.1")}\n'
        block = [
            f"### Fix {fix_number} — Link Form Fields into the Structure Tree ({n} of {total} files)\n",
            badge,
            automation_summary_md(["PDFUA.FORM.STRUCT", "PDFBP.FORM.STRUCT"], n, total, remediation_applied=rem_applied),
            "#### What This Checks\n",
            "PDF/UA requires every interactive form field to be linked into the "
            "document's tag structure (rules `PDFUA.FORM.STRUCT`, `PDFBP.FORM.STRUCT`). "
            "The scanner inspects the tag tree and flags form widgets that are "
            "orphaned (not connected to any tag) or misplaced (nested under the "
            "wrong parent element).\n",
            "#### How to Fix\n",
            "**Re-export from source (preferred):**",
            "1. Open the original Word or InDesign file",
            "2. Ensure form fields use content controls (Word) or proper form objects (InDesign)",
            "3. Re-export to PDF with **Tagged PDF** enabled\n",
            "**In Adobe Acrobat Pro (manual repair):**",
            "1. Open the Tags panel (View → Show/Hide → Navigation Panes → Tags)",
            "2. Locate orphaned `<Form>` tags (often at the end of the tree under `/Document`)",
            "3. Cut each `<Form>` tag and paste it next to its corresponding label `<P>` element",
            "4. Verify by tabbing through the form with a screen reader",
            "5. File → Save As\n",
            "#### Why This Matters\n",
            "Form fields that are not linked into the tag tree are invisible "
            "to screen readers or announced out of context — users cannot tell what information to enter. "
            "Labels and fields become disconnected even if they appear side by side visually.\n",
            f"**Reference:** {_wcag_md('1.3.1')} | {REF_LINKS['webaim_forms']}\n",
        ]
        changes = _render_applied_changes_md(fix_results, ["PDFUA.FORM.STRUCT", "PDFBP.FORM.STRUCT"])
        if changes:
            block.append(changes)
        sections.append("\n".join(block))
        fix_number += 1

    # ── Form field tooltips ──
    tooltip_files = _unique_files_for_rule(by_rule, "PDFUA.FORM.TU")
    if tooltip_files:
        n = len(tooltip_files)
        block = [
            f"### Fix {fix_number} — Add Labels to Form Fields ({n} of {total} files)\n",
            f"> 🔴 **Required** — {_wcag_md('1.3.1')} / PDF/UA section 6.6\n",
            automation_summary_md(["PDFUA.FORM.TU"], n, total, remediation_applied=rem_applied),
            "#### What This Checks\n",
            "PDF/UA requires every form field to have a tooltip that acts as its "
            "accessible label (rule `PDFUA.FORM.TU`). The scanner inspects each "
            "form widget's `/TU` (tooltip) entry and flags any field where it "
            "is missing or empty.\n",
            "#### How to Fix\n",
            "**In Adobe Acrobat Pro:**",
            "1. All Tools → Prepare Form",
            "2. Right-click each unlabelled field → Properties",
            "3. Enter a descriptive label in the **Tooltip** field",
            "   - For required fields, add *(required)* at the end",
            "   - Example: *First name (required)*",
            "4. Save\n",
            "#### Why This Matters\n",
            "Screen readers read the Tooltip aloud as the field label. "
            "Without it, users hear only the field type — e.g. *'Text field'* — with no "
            "indication of what to enter.\n",
            f"**Reference:** {_wcag_md('4.1.2')} | {_wcag_md('3.3.2')} | {REF_LINKS['webaim_forms']}\n",
        ]
        changes = _render_applied_changes_md(fix_results, ["PDFUA.FORM.TU"])
        if changes:
            block.append(changes)
        sections.append("\n".join(block))
        fix_number += 1

    # ── Slide titles ──
    slide_title_files = _unique_files_for_rule(by_rule, "PPTX.SLIDE.TITLE")
    if slide_title_files:
        n = len(slide_title_files)
        block = [
            f"### Fix {fix_number} — Add Titles to All Slides ({n} of {total} files)\n",
            f"> 🔴 **Required** — {_wcag_md('2.4.2')}\n",
            automation_summary_md(["PPTX.SLIDE.TITLE"], n, total, remediation_applied=rem_applied),
            "#### What This Checks\n",
            "Every slide must have a unique, descriptive title (rule `PPTX.SLIDE.TITLE`). "
            "The scanner checks the title placeholder on each slide and flags slides "
            "where it is missing, empty, or hidden.\n",
            "#### How to Fix\n",
            "**In Microsoft PowerPoint:**",
            "1. Open the slide in Normal view",
            "2. Click the title placeholder at the top of the slide",
            "3. Type a meaningful, unique title",
            "4. Save\n",
            "#### Why This Matters\n",
            "Slide titles are how screen reader users navigate "
            "presentations. Untitled slides force users to listen through all content to "
            "find what they need.\n",
            f"**Reference:** {_wcag_md('2.4.2')} | {REF_LINKS['ms_pptx']}\n",
        ]
        changes = _render_applied_changes_md(fix_results, ["PPTX.SLIDE.TITLE"])
        if changes:
            block.append(changes)
        sections.append("\n".join(block))
        fix_number += 1

    # ── Alt text for images ──
    docx_alt = _unique_files_for_rule(by_rule, "DOCX-IMG.ALT")
    pptx_alt = _unique_files_for_rule(by_rule, "PPTX.IMG.ALT")
    xlsx_alt = _unique_files_for_rule(by_rule, "XLSX.IMG.ALT")
    epub_alt = _unique_files_for_rule(by_rule, "EPUB-E009")
    pdf_alt = _unique_files_for_rule(by_rule, "PDFUA.IMG.ALT")
    all_alt = sorted(set(docx_alt + pptx_alt + xlsx_alt + epub_alt + pdf_alt))
    if all_alt:
        n = len(all_alt)
        active_alt_rules = _active_rules(["DOCX-IMG.ALT", "PPTX.IMG.ALT", "XLSX.IMG.ALT",
                                           "EPUB-E009", "PDFUA.IMG.ALT"], by_rule)
        block = [f"### Fix {fix_number} — Add Alternative Text to Images ({n} of {total} files)\n",
                 f"> 🔴 **Required** — {_wcag_md('1.1.1')}\n",
                 automation_summary_md(active_alt_rules, n, total, remediation_applied=rem_applied),
                 "#### What This Checks\n",
                 "Every meaningful image must have alternative text that describes "
                 f"its content (rules {', '.join(f'`{r}`' for r in active_alt_rules)}). "
                 "The scanner inspects each image element and flags any where "
                 "alt text is missing, empty, or a generic placeholder like "
                 "'image1.png'.\n",
                 "#### How to Fix\n"]
        if pdf_alt:
            block += [
                "**In Adobe Acrobat Pro:**",
                "1. Open the Tags panel → locate `<Figure>` tags",
                "2. Right-click → Properties → enter alt text in the **Alternate Text** field",
                "3. For decorative images, set alt text to a single space or mark as artifact",
                "4. Save As\n",
            ]
        if docx_alt:
            block += [
                "**In Microsoft Word:**",
                "1. Right-click an image → Edit Alt Text",
                "2. Enter a description of what the image shows and why it matters",
                "3. If the image is purely decorative, check **Mark as decorative**",
                "4. Repeat for all images → Save\n",
            ]
        if pptx_alt:
            block += [
                "**In Microsoft PowerPoint:**",
                "1. Right-click an image → Edit Alt Text",
                "2. Enter a meaningful description",
                "3. If decorative, check **Mark as decorative**",
                "4. Repeat for all images → Save\n",
            ]
        if xlsx_alt:
            block += [
                "**In Microsoft Excel:**",
                "1. Right-click an image or chart → Edit Alt Text",
                "2. Enter a meaningful description",
                "3. If decorative, check **Mark as decorative**",
                "4. Save\n",
            ]
        if epub_alt:
            block += [
                "**In Sigil or Calibre (ePub):**",
                "1. Open the XHTML content file containing the image",
                "2. Add or edit the `alt` attribute on each `<img>` tag",
                "3. Save\n",
            ]
        block += [
            "#### Why This Matters\n",
            "Blind and low-vision users hear alt text read aloud "
            "instead of seeing the image. Generic or missing alt text leaves them without "
            "the information the image conveys.\n",
            f"**Reference:** {_wcag_md('1.1.1')} | {REF_LINKS['webaim_alt']}\n",
        ]
        changes = _render_applied_changes_md(fix_results, active_alt_rules)
        if changes:
            block.append(changes)
        sections.append("\n".join(block))
        fix_number += 1

    # ── Table headers ──
    table_files = _unique_files_for_rule(by_rule, "PDFUA.TABLE.HEADERS") + \
                  _unique_files_for_rule(by_rule, "DOCX-TABLE.HEADERS") + \
                  _unique_files_for_rule(by_rule, "XLSX.TABLE.HEADER") + \
                  _unique_files_for_rule(by_rule, "PPTX.TABLE.HEADER")
    table_files = sorted(set(table_files))
    if table_files:
        n = len(table_files)
        pdf_t = _unique_files_for_rule(by_rule, "PDFUA.TABLE.HEADERS")
        docx_t = _unique_files_for_rule(by_rule, "DOCX-TABLE.HEADERS")
        xlsx_t = _unique_files_for_rule(by_rule, "XLSX.TABLE.HEADER")
        pptx_t = _unique_files_for_rule(by_rule, "PPTX.TABLE.HEADER")
        active_table_rules = _active_rules(["PDFUA.TABLE.HEADERS", "DOCX-TABLE.HEADERS",
                                               "XLSX.TABLE.HEADER", "PPTX.TABLE.HEADER"], by_rule)
        block = [f"### Fix {fix_number} — Mark Table Header Rows ({n} of {total} files)\n",
                 f"> 🔴 **Required** — {_wcag_md('1.3.1')}\n",
                 automation_summary_md(active_table_rules, n, total, remediation_applied=rem_applied),
                 "#### What This Checks\n",
                 "Data tables must identify their header rows so screen readers "
                 "can announce column names as users move between cells "
                 f"(rules {', '.join(f'`{r}`' for r in active_table_rules)}). "
                 "The scanner inspects table structure and flags tables "
                 "where the first row is not marked as a header.\n",
                 "#### How to Fix\n"]
        if pdf_t:
            block += [
                "**In Adobe Acrobat Pro:**",
                "In the Tags panel, tag header cells as `/TH` (not `/TD`). "
                "Right-click the cell tag → Properties → Type → TH.\n",
            ]
        if docx_t:
            block += [
                "**In Microsoft Word:**",
                "Click in the header row → Table Design tab → check **Header Row**. "
                "Also ensure the row uses a 'Table Header' or bold style.\n",
            ]
        if xlsx_t:
            block += [
                "**In Microsoft Excel:**",
                "Click inside the data range → Insert → Table → check **My table has headers**. "
                "Or right-click the Table → Table Properties → ensure Header Row is on.\n",
            ]
        if pptx_t:
            block += [
                "**In Microsoft PowerPoint:**",
                "Click the table → Table Design tab → check **Header Row**.\n",
            ]
        block += [
            "#### Why This Matters\n",
            "Screen readers announce column headers as users "
            "move between cells. Without headers, every cell sounds identical — e.g. "
            "*'Row 3, Column 2: Smith'* with no context.\n",
            f"**Reference:** {_wcag_md('1.3.1')} | {REF_LINKS['webaim_tables']}\n",
        ]
        changes = _render_applied_changes_md(fix_results, active_table_rules)
        if changes:
            block.append(changes)
        sections.append("\n".join(block))
        fix_number += 1

    # ── DisplayDocTitle / Tab order ──
    doc_title_files = _unique_files_for_rule(by_rule, "PDFBP.DISPLAY.DOCTITLE")
    tab_order_files = _unique_files_for_rule(by_rule, "PDFBP.NAV.TABORDER")
    if doc_title_files or tab_order_files:
        all_f2 = sorted(set(doc_title_files + tab_order_files))
        n = len(all_f2)
        block = [f"### Fix {fix_number} — Enable Title Display and Correct Tab Order ({n} of {total} files)\n",
                 "> 🟡 **Recommended** — improves usability but not a WCAG conformance failure\n",
                 automation_summary_md(["PDFBP.DISPLAY.DOCTITLE", "PDFBP.NAV.TABORDER"], n, total, remediation_applied=rem_applied),
                 "#### What This Checks\n",
                 "Two best-practice settings improve the user experience in PDF viewers: "
                 "showing the document title in the title bar instead of the file name "
                 "(rule `PDFBP.DISPLAY.DOCTITLE`), and setting tab order to follow the "
                 "document structure (rule `PDFBP.NAV.TABORDER`). "
                 "These are not WCAG conformance failures but significantly improve "
                 "usability for all users.\n",
                 "#### How to Fix\n"]
        if doc_title_files:
            block += [
                "**Display Doc Title (in Adobe Acrobat Pro):**",
                "1. File → Properties → Initial View",
                "2. *Show:* → select **Document Title**",
                "3. Save As\n",
            ]
        if tab_order_files:
            block += [
                "**Tab Order (in Adobe Acrobat Pro):**",
                "1. Open Page Thumbnails panel",
                "2. Right-click a page → Page Properties → Tab Order",
                "3. Select **Use Document Structure**",
                "4. Repeat for all pages → Save As\n",
            ]
        changes = _render_applied_changes_md(fix_results, ["PDFBP.DISPLAY.DOCTITLE", "PDFBP.NAV.TABORDER"])
        if changes:
            block.append(changes)
        sections.append("\n".join(block))
        fix_number += 1

    if not sections:
        return ""

    # Build tool note based on which document types are present
    tool_lines = []
    if "pdf" in types:
        tool_lines.append("> - **PDF files:** Adobe Acrobat Professional\n")
    if "docx" in types:
        tool_lines.append("> - **Word files (.docx):** Microsoft Word\n")
    if "xlsx" in types:
        tool_lines.append("> - **Excel files (.xlsx):** Microsoft Excel\n")
    if "pptx" in types:
        tool_lines.append("> - **PowerPoint files (.pptx):** Microsoft PowerPoint\n")
    if "epub" in types:
        tool_lines.append("> - **ePub files:** Sigil or Calibre\n")
    tool_note = ""
    if tool_lines:
        tool_note = ("> **Recommended tools for remediation:**\n"
                     + "".join(tool_lines) + "\n")

    # Add toolkit automation note if fix_tiers is available
    auto_note = ""
    if _HAS_FIX_TIERS:
        auto_note = (
            "> **Toolkit automation:** Fixes marked with "
            "\U0001f7e2 can be applied automatically by running "
            "`python tools/scan_all.py <target> --fix`. "
            "Fixes marked with \U0001f7e1 require your review after the toolkit "
            "applies them. Fixes marked with \U0001f7e0 must be completed manually.\n\n"
        )

    header = ("## Start Here: Quick Fixes (Do These First)\n\n"
              "These are the most common issues found across your documents. "
              "Each fix includes step-by-step instructions for the appropriate tool.\n\n"
              + tool_note
              + auto_note
              + "---\n\n")

    # Wrap each fix section in an accordion
    accordion_sections = []
    for sec in sections:
        sec_lines = sec.split("\n")
        # Extract the ### heading as the summary
        heading = sec_lines[0].lstrip("# ").strip() if sec_lines else "Fix"
        body = "\n".join(sec_lines[1:])
        accordion_sections.append(
            f"<details>\n<summary><strong>{heading}</strong></summary>\n{body}\n</details>"
        )
    return header + "\n\n".join(accordion_sections) + "\n---\n"


def _render_next_steps(audit: dict) -> str:
    """Bridging section between quick fixes and detailed file-by-file review.

    Guides users to continue past the quick wins into the deeper audit.
    """
    total = audit["summary"]["total_files"]
    return (
        "## What Comes Next: File-by-File Review\n\n"
        "> **Do not stop here.** The quick fixes above address the most common "
        "issues found across multiple files. However, each document may have "
        "unique accessibility issues that require individual attention.\n\n"
        "Automated scanning catches structural problems, but some issues "
        "\u2014 like reading order, meaningful alt text quality, and logical "
        "heading flow \u2014 require human judgment.\n\n"
        f"The sections below break down findings across all {total} files "
        "so you can work through them systematically:\n\n"
        "| Section | What You Will Find |\n"
        "|---------|-----------------------|\n"
        "| **Manual Review Required** | Issues that need a human reviewer with a screen reader |\n"
        "| **Additional Improvements** | Best-practice enhancements beyond strict compliance |\n"
        "| **Summary of Findings** | Every unique issue with severity and file count |\n"
        "| **Priority Action Plan** | Suggested order of work by impact and effort |\n"
        "| **Appendix A** | Complete per-file finding inventory |\n\n"
        "> \U0001f4a1 **Tip:** Work through one file at a time. Complete the quick fixes "
        "first, then move to file-specific issues. Re-scan after fixing to verify "
        "your changes.\n\n---\n"
    )


def _render_manual_review(by_rule: dict, audit: dict, all_f: list) -> str:
    """
    ⚠️ Manual Review Required section.
    Reading order is ALWAYS the first subsection — it is the most impactful
    issue that automated scanning cannot fully detect.
    """
    total = audit["summary"]["total_files"]
    types = _present_types(audit)
    # Build format-appropriate tool list for intro
    review_tools = []
    if "pdf" in types:
        review_tools.append("Adobe Acrobat Pro")
    if "pptx" in types:
        review_tools.append("the PowerPoint Selection Pane")
    review_tools.append("a screen reader such as NVDA or JAWS")
    tool_list = ", ".join(review_tools)
    sections = ["## ⚠️ Manual Review Required\n\n"
                "The following issues **cannot be fully verified by automated scanning**. "
                f"They require a human reviewer — typically using {tool_list}.\n"]

    # ════════════════════════════════════════════════════════════════════════
    # 1. READING ORDER  ← ALWAYS FIRST — most impactful, most commonly wrong
    # ════════════════════════════════════════════════════════════════════════
    ro_findings = [f for f in all_f if f.get("rule", "") in READING_ORDER_RULES]
    pdf_ro_findings = [f for f in ro_findings if f.get("_type") == "pdf"]
    ppt_ro_findings = [f for f in ro_findings if f.get("_type") == "pptx"]

    # Collect automatic detections with outcome fields
    detected_outcomes = []
    for fn in ro_findings:
        outcome = fn.get("outcome", "")
        rule = fn.get("rule", "")
        sev = fn.get("severity", "Info")
        if outcome and rule not in {"PDFQ.ORDER.MANUAL", "PPTX.ORDER.VERIFY"}:
            detected_outcomes.append((rule, sev, fn.get("_file", ""), outcome))

    sections.append(
        "### 📋 Reading Order\n\n"
        "**Priority: Critical — affects every screen reader and Braille display user**\n\n"
        "Reading order is the sequence in which assistive technology reads the content of a "
        "document — and it may be **completely different** from the visual order on screen. "
        "Multi-column layouts, sidebars, form fields, and complex tables are the most "
        "common sources of reading order problems.\n\n"
        "When reading order is wrong, screen reader users hear content in a confusing or "
        "misleading sequence — from mildly disorienting to completely unusable.\n\n"
        f"**Reference:** {_wcag_md('1.3.2')} | {REF_LINKS['acrobat_a11y']}\n"
    )

    # Outcome → experience table
    sections.append(
        "#### What Goes Wrong — Impact on Screen Reader Users\n\n"
        "| Situation | What the screen reader user experiences |\n"
        "|-----------|-------------------------------------------|\n"
        "| Form field labels appear **after** their fields | Hears *\"Checkbox, unchecked\"* with no context for what the checkbox represents |\n"
        "| Two-column layout — columns in wrong order | Hears all of column 2 first, then all of column 1 — content is fragmented |\n"
        "| Headers and footers not marked as Artifacts | Page header is repeated at the start of every page's content |\n"
        "| Submit button appears before final questions | *\"Submit\"* is announced before the user has reached the last form field |\n"
        "| Images out of reading sequence | Photo is described in the wrong narrative context — association lost |\n"
        "| Caption separated from its Figure | Image alt text heard, then paragraphs of unrelated text, then the caption |\n"
    )

    # Automated detections
    if detected_outcomes:
        sections.append("\n#### What Was Detected Automatically\n\n"
                        "| File | Rule | Severity | Likely Experience |\n"
                        "|------|------|----------|-------------------|\n")
        for rule, sev, fname, outcome in detected_outcomes:
            emoji = SEVERITY_EMOJI.get(sev, "")
            sections.append(f"| {fname} | `{rule}` | {emoji} {sev} | {outcome} |")
        sections.append("")

    # Verification instructions
    pdf_files = [f for f in audit.get("files", []) if f["type"] == "pdf"]
    ppt_files = [f for f in audit.get("files", []) if f["type"] == "pptx"]

    if pdf_files:
        sections.append(
            "\n#### How to Verify Reading Order — PDF (Adobe Acrobat Pro)\n\n"
            "1. Open the PDF in **Adobe Acrobat Pro**\n"
            "2. Go to **All Tools → Accessibility → Reading Order**\n"
            "3. Click **Show page content groups** in the Reading Order dialog\n"
            "4. Numbered grey boxes appear on the page — each number is the order "
            "in which a screen reader will read that content group\n"
            "5. Verify the sequence matches the **intended logical reading order**\n"
            "6. Pay special attention to:\n"
            "   - Form labels and their fields (label must come **before** its field)\n"
            "   - Multi-column text (left column complete before right column begins)\n"
            "   - Headers, footers, and page numbers (should be marked as **Artifacts**)\n"
            "   - Tables — header row should be read before data rows\n\n"
            "**To fix problems found:**\n"
            "- Drag the numbered boxes to re-sequence content groups, **or**\n"
            "- Use the **Tags panel** to reorder tags (more precise), **or**\n"
            "- Return to the source file (Word, InDesign) and re-export with correct order\n\n"
            "**Alternative — test with a live screen reader:**\n"
            "NVDA: Press **Insert + Down Arrow** for continuous reading.  \n"
            "JAWS: Press **Insert + Down Arrow**.  \n"
            "Listen to the entire document and note where the sequence feels wrong.\n"
        )

    if ppt_files:
        sections.append(
            "\n#### How to Verify Reading Order — PowerPoint\n\n"
            "1. Open the presentation in **PowerPoint** (desktop app)\n"
            "2. Go to **Home → Arrange → Selection Pane** (or View → Selection Pane)\n"
            "3. The **bottom item in the list is read FIRST** by assistive technology\n"
            "4. The slide **title placeholder must be at the bottom** of the list\n"
            "5. Verify all other content shapes are in the intended reading sequence "
            "(reading bottom to top in the pane)\n\n"
            "**To fix:**  \n"
            "Drag items up/down in the Selection Pane to reorder them.  \n"
            "The title should be the last item (bottom of pane) so it is read first.\n\n"
            "**Alternative — test with Narrator:**\n"
            "Open the presentation in Slide Show, enable Windows Narrator (Win+Ctrl+Enter), "
            "and Tab through the slide content to verify order.\n"
        )

    sections.append("\n---\n")

    # ════════════════════════════════════════════════════════════════════════
    # 2. COLOUR CONTRAST
    # ════════════════════════════════════════════════════════════════════════
    color_files = _unique_files_for_rule(by_rule, "XLSX.COLOR.ONLY")
    sections.append(
        "### 🎨 Colour Contrast and Colour-Only Information\n\n"
        "**Priority: High — affects low-vision and colour-blind users**\n\n"
        "Automated tools cannot detect all contrast failures or situations where "
        "colour is the only way to convey information (WCAG 1.4.1, 1.4.3).\n\n"
        f"**Reference:** {_wcag_md('1.4.1')} | {_wcag_md('1.4.3')}\n\n"
        "**What to check:**\n"
        "- All text has a contrast ratio of at least **4.5:1** against its background "
        "(3:1 for large text ≥ 18pt or 14pt bold)\n"
        "- Information is not conveyed by colour alone — e.g. red text for errors "
        "must also include a visible label or icon\n"
        "- Charts and graphs use patterns or labels in addition to colours\n\n"
        "**How to check contrast:**\n"
        "1. Install the **Colour Contrast Analyser** (free, TPGi)\n"
        "2. Pick the foreground and background colours with the eyedropper\n"
        "3. Confirm the ratio meets the threshold for the text size\n\n"
        "**Online tool:** [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)\n"
    )
    if color_files:
        sections.append(
            f"⚠️ **Automated check flagged colour-only use in: {', '.join(color_files)}**  \n"
            "These files use cell fill colour to differentiate data without a text or symbol alternative. "
            "Add a text label, symbol, or pattern to each colour-coded cell.\n"
        )
    sections.append("\n---\n")

    # ════════════════════════════════════════════════════════════════════════
    # 3. PDF ACCESSIBILITY CHECKER (always recommended)
    # ════════════════════════════════════════════════════════════════════════
    if pdf_files:
        sections.append(
            "### ✅ Run the Built-in PDF Accessibility Checker\n\n"
            "**Priority: Required before distributing any PDF**\n\n"
            "After applying all automated fixes, run Acrobat Pro's built-in checker "
            "for a final validation:\n\n"
            "1. Open the PDF in **Adobe Acrobat Pro**\n"
            "2. Go to **All Tools → Accessibility**\n"
            "3. Select **Accessibility Check**\n"
            "4. Click **Start Checking**\n"
            "5. Expand each category in the results panel\n"
            "6. Right-click flagged items to fix or view guidance\n\n"
            "**Pay special attention to:**\n"
            "- Reading order\n"
            "- Form field labels\n"
            "- Language setting\n"
            "- Document title\n"
            "- Colour contrast warnings\n\n"
            "Re-run the checker after each fix until no critical issues remain.\n\n"
            "---\n"
        )

    return "\n".join(sections)


def _render_additional_improvements(by_rule: dict, audit: dict) -> str:
    total = audit["summary"]["total_files"]
    items = []

    # Bookmarks / navigation
    pdf_files = [f for f in audit.get("files", []) if f["type"] == "pdf"]
    if pdf_files:
        items.append(
            "### Optional: Add Bookmarks to Longer PDF Documents\n\n"
            "For PDFs with multiple sections or pages, bookmarks allow users to "
            "navigate directly to a section without reading linearly:\n\n"
            "1. View → Show/Hide → Navigation Panes → Bookmarks\n"
            "2. Options menu → **New Bookmarks from Structure**\n"
            "3. Confirm the bookmark hierarchy looks correct\n"
            "4. Save As\n\n"
            "**Benefit:** Screen reader users and keyboard-only users can jump "
            "between sections quickly using the Bookmarks panel.\n\n"
            f"**Reference:** {_wcag_md('2.4.5')} | {REF_LINKS['acrobat_a11y']}\n"
        )

    # Speaker notes in PPT
    ppt_notes_files = _unique_files_for_rule(by_rule, "PPTX.SLIDE.NOTES")
    if ppt_notes_files:
        n = len(ppt_notes_files)
        items.append(
            f"### Add Speaker Notes to PowerPoint Slides ({n} of {total} files)\n\n"
            "Slides without speaker notes may be missing context that is only "
            "conveyed visually in the presentation. Consider adding notes that "
            "describe what is on each slide — these are accessible to screen reader "
            "users reading the file outside a presentation context.\n\n"
            "**PowerPoint:** View → Notes to open the Notes pane below each slide.\n"
        )

    # PDF/UA identifier
    pdfua_files = _unique_files_for_rule(by_rule, "PDFQ.METADATA.PDFUA")
    if pdfua_files:
        items.append(
            "### Optional: Add PDF/UA Conformance Identifier\n\n"
            "This step is only needed for **formal compliance documentation** (e.g. "
            "government publishing, Section 508 procurement).\n\n"
            "1. All Tools → Accessibility → Run Accessibility Check\n"
            "2. Look for the **Add PDF/UA Identifier** option after the check\n"
            "3. If not available, use third-party tools such as PAC 2024 (PDF Accessibility Checker)\n\n"
            "**Note:** The identifier is a metadata marker only — it does not fix issues. "
            "The document must be genuinely conformant before adding it.\n"
        )

    # Heading structure (Word/PPTX)
    heading_files = _unique_files_for_rule(by_rule, "DOCX-STRUCT.HEADINGS") + \
                    _unique_files_for_rule(by_rule, "DOCX-STRUCT.HEADINGSKIP") + \
                    _unique_files_for_rule(by_rule, "PDFBP.HEADING.SKIP")
    heading_files = sorted(set(heading_files))
    if heading_files:
        n = len(heading_files)
        has_word = bool(_unique_files_for_rule(by_rule, "DOCX-STRUCT.HEADINGS") +
                        _unique_files_for_rule(by_rule, "DOCX-STRUCT.HEADINGSKIP"))
        has_pdf = bool(_unique_files_for_rule(by_rule, "PDFBP.HEADING.SKIP"))
        heading_block = [
            f"### Improve Heading Structure ({n} of {total} files)\n\n"
            "Heading levels should not skip — going from Heading 1 directly to "
            "Heading 3 confuses screen reader users navigating by headings.\n\n"
        ]
        if has_word:
            heading_block.append(
                "**Word:** Use the Styles pane to apply Heading 1, 2, 3 in sequence.  \n"
                "**Test:** In Word, use View → Navigation Pane to see your heading structure "
                "at a glance.\n"
            )
        if has_pdf:
            heading_block.append(
                "**PDF:** Review the Tags panel to ensure `<H1>`, `<H2>`, `<H3>` levels are sequential.  \n"
            )
        heading_block.append(
            f"\n**Reference:** {_wcag_md('1.3.1')}\n"
        )
        items.append("".join(heading_block))

    # Sheet names (Excel)
    sheet_files = _unique_files_for_rule(by_rule, "XLSX.NAV.SHEET_NAMES")
    if sheet_files:
        n = len(sheet_files)
        items.append(
            f"### Rename Default Sheet Tabs in Excel ({n} of {total} files)\n\n"
            "Generic names like *Sheet1* or *Sheet2* give no context to screen reader "
            "users navigating between sheets:\n\n"
            "Double-click each sheet tab and enter a descriptive name that "
            "reflects the sheet's content (e.g. *January Sales*, *Summary*, *Instructions*).\n"
        )

    # Duplicate link text
    link_files = _unique_files_for_rule(by_rule, "DOCX-LINK.DESCRIPTIVE") + \
                 _unique_files_for_rule(by_rule, "PPTX.LINKS.TEXT") + \
                 _unique_files_for_rule(by_rule, "XLSX.LINKS.TEXT")
    link_files = sorted(set(link_files))
    if link_files:
        n = len(link_files)
        items.append(
            f"### Improve Hyperlink Text ({n} of {total} files)\n\n"
            "Hyperlinks with text like *'click here'*, *'read more'*, or a raw URL "
            "are not useful to screen reader users who browse links out of context:\n\n"
            "Replace with descriptive text that says **where the link goes** "
            f"— e.g. *'Download the 2024 Annual Report'* instead of *'click here'*.\n\n"
            f"**Reference:** {_wcag_md('2.4.4')} | {REF_LINKS['webaim_links']}\n"
        )

    if not items:
        return ""

    header = "## Additional Improvements\n\n"
    return header + "\n---\n\n".join(items) + "\n---\n"


def _render_summary_table(by_rule: dict, audit: dict, all_f: list) -> str:
    """Table of unique issues with file counts."""
    total = audit["summary"]["total_files"]
    rows = []
    seen_rules = set()

    # Sort by severity, then by number of affected files (highest impact first)
    sev_order = {"Error": 0, "Warning": 1, "Info": 2}
    # Pre-compute file counts for sort stability
    rule_file_count = {rule: len(_unique_files_for_rule(by_rule, rule)) for rule in by_rule}
    for fn in sorted(all_f, key=lambda x: (sev_order.get(x.get("severity", "Info"), 99), -rule_file_count.get(x.get("rule", ""), 0), x.get("rule", ""))):
        rule = fn.get("rule", "")
        if rule in seen_rules:
            continue
        seen_rules.add(rule)
        ref = RULE_REFERENCE.get(rule, {})
        desc = ref[4] if ref else fn.get("message", rule)[:80]
        sev = fn.get("severity", "Info")
        emoji = SEVERITY_EMOJI.get(sev, "")
        affected = _unique_files_for_rule(by_rule, rule)
        rows.append(f"| {emoji} {sev} | {desc} | {len(affected)} of {total} |")

    if not rows:
        return ""

    header = (
        "## Summary of Findings\n\n"
        "| Severity | Issue | Affected Files |\n"
        "|----------|-------|----------------|\n"
    )
    return header + "\n".join(rows) + "\n\n---\n"


def _render_priority_plan(by_rule: dict, audit: dict, all_f: list) -> str:
    total = audit["summary"]["total_files"]
    errors = sorted({fn["rule"] for fn in all_f if fn.get("severity") == "Error"},
                     key=lambda r: (-len(_unique_files_for_rule(by_rule, r)), r))
    warnings = sorted({fn["rule"] for fn in all_f if fn.get("severity") == "Warning"},
                       key=lambda r: (-len(_unique_files_for_rule(by_rule, r)), r))
    infos = sorted({fn["rule"] for fn in all_f if fn.get("severity") == "Info"},
                    key=lambda r: (-len(_unique_files_for_rule(by_rule, r)), r))

    lines = ["## Priority Action Plan\n"]

    if errors:
        lines.append("### 🔴 High Priority — Fix Before Distribution\n")
        for rule in errors:
            ref = RULE_REFERENCE.get(rule, {})
            desc = ref[4] if ref else rule
            n = len(_unique_files_for_rule(by_rule, rule))
            lines.append(f"- {desc} ({n} of {total} files)")
        lines.append("- **Run Accessibility Check on all files (required before publishing)**\n")

    if warnings:
        lines.append("### 🟡 Medium Priority — Fix Soon\n")
        for rule in warnings:
            ref = RULE_REFERENCE.get(rule, {})
            desc = ref[4] if ref else rule
            n = len(_unique_files_for_rule(by_rule, rule))
            lines.append(f"- {desc} ({n} of {total} files)")
        lines.append("")

    types = _present_types(audit)
    lines.append("### 📋 Manual Review Required\n")
    ro_parts = []
    if "pdf" in types:
        ro_parts.append("PDF: Acrobat Reading Order tool")
    if "pptx" in types:
        ro_parts.append("PPT: Selection Pane")
    if ro_parts:
        lines.append(f"- **Verify reading order** in all files ({'; '.join(ro_parts)})")
    else:
        lines.append("- **Verify reading order** in all files")
    lines.append("- **Check colour contrast** for all body text and charts")
    lines.append("- **Test with a screen reader** (NVDA or JAWS) before final distribution")
    lines.append("")

    if infos:
        lines.append("### 🔵 Optional / Compliance Only\n")
        for rule in infos:
            ref = RULE_REFERENCE.get(rule, {})
            desc = ref[4] if ref else rule
            n = len(_unique_files_for_rule(by_rule, rule))
            lines.append(f"- {desc} ({n} of {total} files)")
        lines.append("")

    lines.append("---\n")
    return "\n".join(lines)


def _render_whats_working(all_f: list, audit: dict) -> str:
    error_rules = {fn["rule"] for fn in all_f if fn.get("severity") == "Error"}
    items = []

    pdf_files = [f for f in audit.get("files", []) if f["type"] == "pdf"]
    if pdf_files and "PDFUA.STRUCT.NOTREE" not in error_rules and "PDFUA.STRUCT.TAGGED" not in error_rules:
        items.append("PDF documents use proper tagging — the structural foundation is in place")
    if pdf_files and "PDFUA.FORM.TU" not in error_rules:
        items.append("All PDF form fields have accessible labels (Tooltip / alternate name)")
    if "DOCX-IMG.ALT" not in error_rules and "PPTX.IMG.ALT" not in error_rules:
        items.append("Images include alternative text in supported document types")
    if "PDFUA.METADATA.TITLE" not in error_rules and "DOCX-META.TITLE" not in error_rules:
        items.append("Document titles are set correctly")
    if "PDFUA.METADATA.LANG" not in error_rules and "DOCX-META.LANG" not in error_rules:
        items.append("Document languages are set correctly")

    if not items:
        items.append("The foundation is in place — the fixes needed are well-understood and achievable")

    lines = ["## What's Already Working Well\n\n",
             "### Strengths\n\n",
             "All documents reviewed:\n"]
    for item in items:
        lines.append(f"- {item}")
    lines.append("\n---\n")
    return "\n".join(lines)


def _render_time_estimate(by_rule: dict, audit: dict) -> str:
    total = audit["summary"]["total_files"]
    rows = []

    if _unique_files_for_rule(by_rule, "PDFUA.METADATA.LANG") or \
       _unique_files_for_rule(by_rule, "DOCX-META.LANG"):
        n = len(set(_unique_files_for_rule(by_rule, "PDFUA.METADATA.LANG") +
                    _unique_files_for_rule(by_rule, "DOCX-META.LANG")))
        rows.append(f"| Fix language settings | {n} × 2 min ≈ {n*2} minutes |")

    if _unique_files_for_rule(by_rule, "PDFUA.METADATA.TITLE") or \
       _unique_files_for_rule(by_rule, "DOCX-META.TITLE"):
        n = len(set(_unique_files_for_rule(by_rule, "PDFUA.METADATA.TITLE") +
                    _unique_files_for_rule(by_rule, "DOCX-META.TITLE") +
                    _unique_files_for_rule(by_rule, "PPTX.META.TITLE") +
                    _unique_files_for_rule(by_rule, "XLSX.META.TITLE")))
        rows.append(f"| Add document titles | {n} × 3 min ≈ {n*3} minutes |")

    if _unique_files_for_rule(by_rule, "PDFUA.FORM.TU"):
        n = len(_unique_files_for_rule(by_rule, "PDFUA.FORM.TU"))
        rows.append(f"| Fix form field labels | {n} file(s) ≈ 10–20 minutes |")

    if _unique_files_for_rule(by_rule, "PPTX.SLIDE.TITLE"):
        n = len(_unique_files_for_rule(by_rule, "PPTX.SLIDE.TITLE"))
        rows.append(f"| Add slide titles | {n} file(s) ≈ 5–10 minutes |")

    rows.append(f"| Manual reading order review | All {total} files ≈ 10 min each |")
    rows.append(f"| Run accessibility checks | All {total} files ≈ 5 min each |")

    if not rows:
        return ""

    return (
        "## Estimated Time to Resolve Issues\n\n"
        "| Task | Estimate |\n"
        "|------|----------|\n"
        + "\n".join(rows)
        + "\n\n---\n"
    )


def _render_final_assessment(audit: dict) -> str:
    s = audit["summary"]
    grade = s["grade"]
    score = s["score"]

    if grade == "A":
        status = "Excellent — meets or exceeds most accessibility requirements"
        effort = "Minimal"
        outlook = "Documents are ready for distribution with minor verification steps."
    elif grade == "B":
        status = "Good foundation — minor issues need attention"
        effort = "Low"
        outlook = ("With a small amount of cleanup and final validation, "
                   "all documents can reach a high level of accessibility and usability.")
    elif grade == "C":
        status = "Adequate foundation, moderate fixes required"
        effort = "Moderate"
        outlook = "Addressing the errors and warnings listed above will bring the documents to a strong level of accessibility."
    else:
        status = "Significant barriers found — remediation needed before publishing"
        effort = "High"
        outlook = "The issues found should be resolved before these documents are distributed to the public."

    return (
        f"## Final Assessment\n\n"
        f"| | |\n"
        f"|---|---|\n"
        f"| **Overall Grade** | {grade} |\n"
        f"| **Score** | {score}/100 |\n"
        f"| **Status** | {status} |\n"
        f"| **Remediation Effort** | {effort} |\n\n"
        f"{outlook}\n\n"
        f"---\n\n"
        f"*Based on: WCAG 2.1 AA, PDF/UA (ISO 14289-1), Matterhorn Protocol, "
        f"Section 508, and WebAIM best practices.*\n"
    )


# ---------------------------------------------------------------------------
# Remediation Results (optional — present only after fix-verify cycle)
# ---------------------------------------------------------------------------

def _render_remediation_results(audit: dict) -> str:
    """Render remediation results section if fix data is present in the audit."""
    remediation = audit.get("remediation")
    if not remediation or not remediation.get("enabled"):
        return ""

    # Collect per-file remediation data from the files list
    files = []
    for fe in audit.get("files", []):
        rem = fe.get("remediation", {})
        if not rem.get("applied"):
            continue
        files.append({
            "file": fe["file"],
            "score_before": rem.get("before", {}).get("score", "N/A"),
            "score_after": rem.get("after", {}).get("score", "N/A"),
            "grade_before": rem.get("before", {}).get("grade", "?"),
            "grade_after": rem.get("after", {}).get("grade", "?"),
            "resolved": rem.get("fix_summary", {}).get("fixed", 0),
            "skipped": rem.get("fix_summary", {}).get("skipped", 0),
            "needs_human": rem.get("fix_summary", {}).get("needs_human", 0),
            "remaining": rem.get("after", {}).get("errors", 0) + rem.get("after", {}).get("warnings", 0),
            "fixes": rem.get("fix_result", []),
        })

    if not files:
        return ""

    lines = [
        "## Remediation Results\n",
        f"Automated fixes (Tier {remediation.get('max_tier', 1)}) were applied "
        f"to {len(files)} file(s) via the scan-fix-verify loop.\n",
        "| Document | Before | After | Change | Fixed | Remaining | Needs Human |",
        "|----------|--------|-------|--------|-------|-----------|-------------|",
    ]

    total_fixed = 0
    total_remaining = 0
    total_human = 0

    for entry in files:
        fname = entry["file"]
        before = entry["score_before"]
        after = entry["score_after"]
        fixed = entry["resolved"]
        remaining = entry["remaining"]
        needs_human = entry["needs_human"]

        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            delta = after - before
            change_str = f"+{delta}" if delta > 0 else str(delta) if delta < 0 else "0"
        else:
            change_str = "N/A"

        human_str = f"**{needs_human}**" if needs_human > 0 else "0"
        lines.append(f"| {fname} | {before} ({entry['grade_before']}) | {after} ({entry['grade_after']}) | {change_str} | {fixed} | {remaining} | {human_str} |")

        total_fixed += fixed
        total_remaining += remaining
        total_human += needs_human

    lines.append("")
    lines.append(f"**Totals**: {total_fixed} issues fixed, "
                 f"{total_remaining} remaining, {total_human} need human review\n")

    if remediation.get("score_improvement", 0) > 0:
        lines.append(f"> **Score improvement**: Average score went from "
                     f"{remediation['before_avg_score']} to {remediation['after_avg_score']} "
                     f"(+{remediation['score_improvement']} points)\n")

    # Per-file fix details
    for entry in files:
        fixes = entry.get("fixes", [])
        if not fixes:
            continue
        fname = entry["file"]
        lines.append(f"### {fname}\n")
        for fix in fixes:
            status = fix.get("status", "?")
            rule = fix.get("rule", "?")
            detail = fix.get("detail", fix.get("reason", ""))
            icon = {"fixed": "+", "skipped": "-", "failed": "X",
                    "needs-human": "?", "unknown": "??"}.get(status, "?")
            lines.append(f"- [{icon}] **{rule}** ({status}): {detail}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Technical Appendices
# ---------------------------------------------------------------------------

def _md_score_grade(score: int) -> str:
    """Return letter grade for a score."""
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"


def _render_alt_text_analysis_md(file_entry: dict) -> str:
    """Render alt text analysis as a collapsible details block (GFM)."""
    ata = file_entry.get("alt_text_analysis")
    if not ata or not ata.get("images"):
        return ""

    images = ata["images"]
    models_used = ata.get("models_used", [])
    model_label = ", ".join(m.split("/")[-1] for m in models_used) if models_used else "unknown"

    lines = [
        f"\n<details>\n<summary>Alt Text Analysis -- {len(images)} image(s), "
        f"{len(models_used)} model(s) ({model_label})</summary>\n"
    ]

    for img in images:
        location = img.get("location", "Unknown")
        page = img.get("page")
        page_label = f" (page {page})" if page else ""
        existing = img.get("existing_alt")
        analysis = img.get("analysis", {})
        existing_score = analysis.get("existing")
        alternatives = analysis.get("alternatives", [])
        recommendation = analysis.get("recommendation", "")

        lines.append(f"\n#### {location}{page_label}\n")

        # ── Current alt text ──
        lines.append("**Current alt text**\n")
        if existing is not None:
            disp = existing if existing else "(empty)"
            if existing_score:
                sc = existing_score["score"]
                g = _md_score_grade(sc)
                lines.append(f"- **Score:** {sc}/100 ({g})")
            lines.append(f"- **Text:** {disp}")
            if existing_score and existing_score.get("flags"):
                for flag in existing_score["flags"]:
                    sev = flag.get("severity", "info")
                    icon = {"error": "X", "warning": "!", "info": "i"}.get(sev, "-")
                    lines.append(f"- [{icon}] {flag['message']}")
            lines.append("")
        else:
            lines.append("- (none)\n")

        # ── Generated alternatives ──
        if alternatives:
            lines.append("**Generated alternatives** (ranked by quality score)\n")
            for alt in alternatives:
                sc = alt["score"]
                g = _md_score_grade(sc)
                model_short = alt.get("model", "").split("/")[-1]
                rank = alt.get("rank", 0)
                text = alt.get("text", "").replace("\n", " ")
                lines.append(f"{rank}. **{model_short}** -- {sc}/100 ({g})")
                lines.append(f"   > {text}")
                if alt.get("flags"):
                    for flag in alt["flags"]:
                        sev = flag.get("severity", "info")
                        icon = {"error": "X", "warning": "!", "info": "i"}.get(sev, "-")
                        lines.append(f"   - [{icon}] {flag['message']}")
                lines.append("")

        # ── Recommendation ──
        if recommendation:
            lines.append(f"> **Recommendation:** {recommendation}\n")

    lines.append("\n</details>\n")
    return "\n".join(lines)


def _render_appendix_a(audit: dict) -> str:
    """Appendix A — Per-file finding inventory."""
    lines = ["## Appendix A — Per-File Finding Inventory\n\n"
             "Complete list of every finding for every file scanned.\n"]

    sev_order = {"Error": 0, "Warning": 1, "Info": 2}

    for file_entry in audit.get("files", []):
        fname = file_entry["file"]
        score = file_entry["score"]
        grade = file_entry["grade"]
        findings = sorted(
            file_entry.get("findings", []),
            key=lambda x: (sev_order.get(x.get("severity", "Info"), 99), x.get("rule", ""))
        )
        lines.append(f"### {fname}  \nScore: {score}/100 · Grade: {grade}\n")

        rem = file_entry.get("remediation", {})
        if rem.get("applied"):
            fixed_name = rem.get("fixed_file", "")
            fixed_part = f" (`{fixed_name}`)" if fixed_name else ""
            lines.append(
                f"> **Automated remediation applied.**  A fixed copy is available{fixed_part}. "
                f"Cross-check the fixed file against the original to verify all changes. "
                f"See [Remediation Results](#remediation-results) for before/after scoring.\n")

        if not findings:
            lines.append("*No findings — all checks passed.*\n")
            continue
        lines.append("| Severity | Rule | Issue | Fix |\n"
                     "|----------|------|-------|-----|\n")
        for fn in findings:
            sev = fn.get("severity", "Info")
            emoji = SEVERITY_EMOJI.get(sev, "")
            rule = fn.get("rule", "")
            msg = fn.get("message", "").replace("|", "\\|").replace("\n", " ")
            fix = fn.get("fix", "").replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {emoji} {sev} | `{rule}` | {msg} | {fix} |")
        lines.append("")

        # Reading order outcomes (if any)
        ro_fn = [f for f in findings if f.get("rule", "") in READING_ORDER_RULES and f.get("outcome")]
        if ro_fn:
            lines.append("**Reading order — screen reader user impact:**\n")
            for fn in ro_fn:
                rule = fn.get("rule", "")
                outcome = fn.get("outcome", "")
                lines.append(f"> `{rule}`: {outcome}\n")

        # Alt text analysis (if data available for this file)
        alt_md = _render_alt_text_analysis_md(file_entry)
        if alt_md:
            lines.append(alt_md)

        lines.append("")

    lines.append("---\n")
    return "\n".join(lines)


def _render_appendix_b(all_f: list) -> str:
    """Appendix B — Rule reference table."""
    seen = set()
    rows = []
    sev_order = {"Error": 0, "Warning": 1, "Info": 2}

    all_rules = sorted(
        {fn.get("rule", "") for fn in all_f if fn.get("rule")},
        key=lambda r: (sev_order.get(
            RULE_REFERENCE.get(r, ("", "", "Info"))[2], 99), r)
    )

    for rule in all_rules:
        if rule in seen:
            continue
        seen.add(rule)
        ref = RULE_REFERENCE.get(rule, ("—", "—", "—", "—", rule))
        standard, wcag, sev, matterhorn, desc = ref
        emoji = SEVERITY_EMOJI.get(sev, "")
        wcag_cell = _wcag_md(wcag.replace("WCAG ", "")) if wcag.startswith("WCAG ") else wcag
        rows.append(f"| `{rule}` | {emoji} {sev} | {wcag_cell} | {matterhorn} | {standard} | {desc} |")

    if not rows:
        return ""

    return (
        "## Appendix B — Rule Reference\n\n"
        "| Rule ID | Severity | WCAG | Matterhorn | Standard | Description |\n"
        "|---------|----------|------|------------|----------|-------------|\n"
        + "\n".join(rows)
        + "\n\n---\n"
    )


def _render_appendix_c(audit: dict) -> str:
    """Appendix C — Standards referenced (format-conditional)."""
    types = _present_types(audit)

    # Always included
    rows = [
        "| [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/) | Web Content Accessibility Guidelines — the international baseline | [w3.org](https://www.w3.org/TR/WCAG22/) |",
        "| [Section 508](https://www.section508.gov/) | US federal accessibility requirements for electronic documents | [section508.gov](https://www.section508.gov/) |",
        "| [WebAIM](https://webaim.org/) | Practical accessibility guidance and evaluation resources | [webaim.org](https://webaim.org/) |",
        "| [EN 301 549](https://www.etsi.org/deliver/etsi_en/301500_302000/301549/) | European accessibility standard referencing WCAG 2.2 | [etsi.org](https://www.etsi.org/deliver/etsi_en/301500_302000/301549/) |",
    ]

    # PDF-specific
    if "pdf" in types:
        rows.extend([
            "| [PDF/UA (ISO 14289-1)](https://www.iso.org/standard/64599.html) | Universal Accessibility standard for PDF documents | [iso.org](https://www.iso.org/standard/64599.html) |",
            "| [PDF/UA in a Nutshell](https://pdfa.org/resource/pdfua-in-a-nutshell/) | Free overview of PDF/UA requirements (PDF Association) | [pdfa.org](https://pdfa.org/resource/pdfua-in-a-nutshell/) |",
            "| [Matterhorn Protocol](https://pdfa.org/resource/the-matterhorn-protocol/) | 136 failure conditions for PDF/UA conformance testing | [pdfa.org](https://pdfa.org/resource/the-matterhorn-protocol/) |",
            "| [WCAG Techniques for PDF](https://www.w3.org/WAI/WCAG22/Techniques/#pdf) | W3C technique documents for PDF accessibility | [w3.org](https://www.w3.org/WAI/WCAG22/Techniques/#pdf) |",
        ])

    # Office-specific (DOCX, XLSX, PPTX)
    if types & {"docx", "xlsx", "pptx"}:
        rows.append(
            "| [Microsoft Office Accessibility](https://support.microsoft.com/en-us/office/make-your-content-accessible-to-everyone-ecab0fcf-d143-4fe8-a2ff-6cd596bddc6d) | Microsoft's guide to creating accessible Office documents | [support.microsoft.com](https://support.microsoft.com/en-us/office/make-your-content-accessible-to-everyone-ecab0fcf-d143-4fe8-a2ff-6cd596bddc6d) |"
        )
    if "docx" in types:
        rows.append(
            "| [Accessible Word Documents](https://support.microsoft.com/en-us/office/make-your-word-documents-accessible-to-people-with-disabilities-d9bf3683-87ac-47ea-b91a-78dcacb3c66d) | Create accessible Word documents (Microsoft) | [support.microsoft.com](https://support.microsoft.com/en-us/office/make-your-word-documents-accessible-to-people-with-disabilities-d9bf3683-87ac-47ea-b91a-78dcacb3c66d) |"
        )
    if "xlsx" in types:
        rows.append(
            "| [Accessible Excel Workbooks](https://support.microsoft.com/en-us/office/make-your-excel-documents-accessible-to-people-with-disabilities-6cc05fc5-1314-48b5-8eb3-683e49b3e593) | Create accessible Excel workbooks (Microsoft) | [support.microsoft.com](https://support.microsoft.com/en-us/office/make-your-excel-documents-accessible-to-people-with-disabilities-6cc05fc5-1314-48b5-8eb3-683e49b3e593) |"
        )
    if "pptx" in types:
        rows.append(
            "| [Accessible PowerPoint Presentations](https://support.microsoft.com/en-us/office/make-your-powerpoint-presentations-accessible-to-people-with-disabilities-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25) | Create accessible PowerPoint presentations (Microsoft) | [support.microsoft.com](https://support.microsoft.com/en-us/office/make-your-powerpoint-presentations-accessible-to-people-with-disabilities-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25) |"
        )

    # EPUB-specific
    if "epub" in types:
        rows.extend([
            "| [EPUB Accessibility 1.1](https://www.w3.org/TR/epub-a11y-11/) | W3C accessibility requirements for EPUB publications | [w3.org](https://www.w3.org/TR/epub-a11y-11/) |",
            "| [EPUB Accessibility Techniques 1.1](https://www.w3.org/TR/epub-a11y-tech-11/) | Techniques for meeting EPUB Accessibility requirements | [w3.org](https://www.w3.org/TR/epub-a11y-tech-11/) |",
        ])

    # Markdown-specific
    if "md" in types:
        rows.append(
            "| [markdownlint Rules](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md) | Markdown linting rules including accessibility-relevant checks | [github.com](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md) |"
        )

    return (
        "## Appendix C — Standards and References\n\n"
        "| Standard | Description | Link |\n"
        "|----------|-------------|------|\n"
        + "\n".join(rows)
        + "\n\n---\n"
    )


def _render_appendix_d(audit: dict) -> str:
    """Appendix D — Tool versions and methodology (format-conditional)."""
    types = _present_types(audit)

    # Only detect versions for libraries actually used in this scan
    tool_rows = []
    if "pdf" in types:
        try:
            import pikepdf
            pikepdf_ver = pikepdf.__version__
        except Exception:
            pikepdf_ver = "not installed"
        try:
            import pypdf
            pypdf_ver = pypdf.__version__
        except Exception:
            pypdf_ver = "not installed"
        tool_rows.append(f"| pikepdf | {pikepdf_ver} | PDF tag tree, form fields, content stream analysis |")
        tool_rows.append(f"| pypdf | {pypdf_ver} | Widget annotation orphan detection |")
    if "xlsx" in types:
        try:
            import openpyxl
            openpyxl_ver = openpyxl.__version__
        except Exception:
            openpyxl_ver = "not installed"
        tool_rows.append(f"| openpyxl | {openpyxl_ver} | Excel workbook accessibility scanning |")
    if "pptx" in types:
        try:
            import pptx
            pptx_ver = pptx.__version__
        except Exception:
            pptx_ver = "not installed"
        tool_rows.append(f"| python-pptx | {pptx_ver} | PowerPoint accessibility and reading order scanning |")
    if "docx" in types:
        try:
            import docx
            docx_ver = docx.__version__
        except Exception:
            try:
                import docx as d
                docx_ver = "installed"
            except Exception:
                docx_ver = "not installed"
        tool_rows.append(f"| python-docx | {docx_ver} | Word document accessibility scanning |")

    lines = [
        "## Appendix D — Tool Versions and Methodology\n",
        "### Scanner Versions\n",
        "| Tool | Version | Purpose |",
        "|------|---------|----------|",
    ]
    lines.extend(tool_rows)

    # Methodology — only describe formats present in the scan
    lines.append("\n### Methodology\n")
    lines.append(
        "This report was generated by static analysis of document structure — no browser rendering "
        "or screen reader emulation is performed. The scanners inspect:\n"
    )
    if "pdf" in types:
        lines.append("- **PDF:** Tag tree structure, AcroForm fields, metadata, content stream MCID sequences")
    if "docx" in types:
        lines.append("- **Word (.docx):** OOXML paragraph styles, image inline elements, table XML, hyperlink runs")
    if "xlsx" in types:
        lines.append("- **Excel (.xlsx):** Workbook properties, sheet management, Table objects, cell fill detection")
    if "pptx" in types:
        lines.append("- **PowerPoint (.pptx):** Slide XML shape order (= AT reading order), placeholder types, alt text XML")

    # Reading order method — only for formats that have it
    if "pdf" in types or "pptx" in types:
        lines.append("\n### Reading Order Analysis Method\n")
    if "pdf" in types:
        lines.append(
            "**PDF:** The MCID (Marked Content Identifier) sequence is extracted from both the structure "
            "tree (which defines AT reading order) and the content stream (which defines paint/visual order). "
            "Pages where more than 25% of element pairs are in a different sequence are flagged as potential "
            "reading order problems. Figure-to-Caption adjacency is also checked in the tag tree.\n"
        )
    if "pptx" in types:
        lines.append(
            "**PowerPoint:** Shape elements are extracted in XML document order, which is the order "
            "assistive technology reads them (bottom-up in the Selection Pane). Title placeholder position "
            "is verified, and slide dimensions are used to detect two-column layouts.\n"
        )

    # Limitations — only mention relevant ones
    lines.append("### Limitations\n")
    if "pdf" in types:
        lines.append(
            "- PDF reading order analysis is heuristic — false positives are possible for "
            "complex but correctly ordered layouts"
        )
    lines.append("- Colour contrast is not analysed (requires pixel-level image rendering)")
    if "pdf" in types:
        lines.append(
            "- Scanned image PDFs (no real text) will not be detected as untagged if they "
            "use OCR layers"
        )
    if "docx" in types or "xlsx" in types:
        lines.append("- Complex table structures in Word and Excel may not be fully characterized")
    lines.append("- All reading order findings require manual human verification")
    lines.append("\n---\n")

    return "\n".join(lines)


def _render_appendix_e(audit: dict) -> str:
    """Appendix E — Glossary (format-conditional)."""
    types = _present_types(audit)

    # Core terms always included
    terms = [
        ("Alt text", "A text description of an image, read aloud by screen readers in place of the image"),
        ("AT", "Assistive Technology — screen readers, Braille displays, switch controls"),
        ("BCP 47", "The IETF language tag standard (e.g. `en-US`, `es`, `fr-CA`)"),
        ("Braille display", "A hardware device that converts on-screen text to raised Braille dots"),
        ("JAWS", "Job Access With Speech — the most widely used commercial screen reader (Windows)"),
        ("Narrator", "The built-in Windows screen reader"),
        ("NVDA", "NonVisual Desktop Access — a free, open-source screen reader for Windows"),
        ("Reading order", "The sequence in which assistive technology reads document content"),
        ("Screen reader", "Software that converts on-screen text to speech or Braille output"),
        ("VoiceOver", "The built-in macOS and iOS screen reader"),
        ("WCAG", "Web Content Accessibility Guidelines — the international accessibility standard"),
    ]

    # PDF-specific terms
    if "pdf" in types:
        terms.extend([
            ("AcroForm", "The PDF interactive form system — contains all form field definitions"),
            ("Artifact", "A page element (header, footer, decorative line) that should be ignored by screen readers"),
            ("Content stream", "The PDF layer that defines what is drawn on the page (paint order)"),
            ("MCID", "Marked Content Identifier — links tag tree structure elements to content stream content"),
            ("Matterhorn Protocol", "A PDF/UA testing framework with 136 specific failure conditions"),
            ("PDF/UA", "ISO 14289-1 — the Universal Accessibility standard for PDF documents"),
            ("RoleMap", "A PDF tag dictionary that maps custom tag names to standard PDF/UA roles"),
            ("Tab order", "The sequence in which the Tab key moves through form fields"),
            ("Tag tree", "The PDF structure tree — defines the logical document structure for AT"),
            ("TH / TD", "PDF tag types for table header cells (TH) and data cells (TD)"),
            ("Tooltip", "The PDF form field property (/TU) that screen readers read as the field label"),
            ("Widget annotation", "The PDF rendering object for a form field on a page"),
        ])

    # PowerPoint-specific terms
    if "pptx" in types:
        terms.append(("Selection Pane", "A PowerPoint panel showing all shapes on a slide in AT reading order"))

    # Sort alphabetically by term name
    terms.sort(key=lambda t: t[0].lower())

    rows = "\n".join(f"| **{t}** | {d} |" for t, d in terms)
    return (
        "## Appendix E — Glossary\n\n"
        "| Term | Definition |\n"
        "|------|------------|\n"
        f"{rows}\n"
    )


# ---------------------------------------------------------------------------
# Main report builder
# ---------------------------------------------------------------------------

def _wrap_accordion(content: str, summary: str, *, open: bool = False) -> str:
    """Wrap a Markdown section in a <details>/<summary> accordion."""
    if not content or not content.strip():
        return ""
    open_attr = " open" if open else ""
    # Strip the leading ## heading if it matches the summary text
    lines = content.split("\n")
    # Remove the first line if it's a heading (## or ### style)
    body_lines = []
    skipped_heading = False
    for line in lines:
        if not skipped_heading and line.startswith("## "):
            skipped_heading = True
            continue
        body_lines.append(line)
    body = "\n".join(body_lines)
    return f"<details{open_attr}>\n<summary><strong>{summary}</strong></summary>\n{body}\n</details>\n"


def generate_report(audit: dict) -> str:
    all_f = _all_findings(audit)
    by_rule = _findings_by_rule(all_f)

    # Render raw sections
    manual_review = _render_manual_review(by_rule, audit, all_f)
    additional = _render_additional_improvements(by_rule, audit)
    summary_table = _render_summary_table(by_rule, audit, all_f)
    priority_plan = _render_priority_plan(by_rule, audit, all_f)
    whats_working = _render_whats_working(all_f, audit)
    time_estimate = _render_time_estimate(by_rule, audit)
    final_assessment = _render_final_assessment(audit)
    remediation = _render_remediation_results(audit)
    appendix_a = _render_appendix_a(audit)
    appendix_b = _render_appendix_b(all_f)
    appendix_c = _render_appendix_c(audit)
    appendix_d = _render_appendix_d(audit)
    appendix_e = _render_appendix_e(audit)

    sections = [
        _render_header(audit),
        _render_executive_summary(audit, by_rule, all_f),
        _render_quick_fixes(by_rule, audit),
        _render_next_steps(audit),
        _wrap_accordion(manual_review, "Manual Review Required", open=True),
        _wrap_accordion(additional, "Additional Improvements"),
        _wrap_accordion(summary_table, "Summary of Findings"),
        _wrap_accordion(priority_plan, "Priority Action Plan", open=True),
        _wrap_accordion(whats_working, "What's Already Working Well"),
        _wrap_accordion(time_estimate, "Estimated Time to Resolve Issues"),
        final_assessment,  # Keep open -- it's the conclusion
        _wrap_accordion(remediation, "Remediation Results") if remediation else "",
        "\n---\n\n# Technical Appendices\n",
        "_The sections below are for technical reviewers, accessibility auditors, and "
        "anyone who needs to understand the detailed methodology and complete findings._\n\n---\n",
        _wrap_accordion(appendix_a, "Appendix A -- Per-File Finding Inventory"),
        _wrap_accordion(appendix_b, "Appendix B -- Rule Reference"),
        _wrap_accordion(appendix_c, "Appendix C -- Standards and References"),
        _wrap_accordion(appendix_d, "Appendix D -- Tool Versions and Methodology"),
        _wrap_accordion(appendix_e, "Appendix E -- Glossary"),
    ]

    return "\n".join(s for s in sections if s)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate a Markdown accessibility audit report from scan_results.json"
    )
    parser.add_argument("results", help="Path to scan_results.json from scan_all.py")
    parser.add_argument(
        "--output", default="ACCESSIBILITY-AUDIT.md",
        help="Output Markdown file (default: ACCESSIBILITY-AUDIT.md)"
    )
    args = parser.parse_args()

    results_path = Path(args.results)
    if not results_path.exists():
        sys.exit(f"ERROR: File not found: {results_path}")

    audit = json.loads(results_path.read_text(encoding="utf-8"))
    report = generate_report(audit)

    out = Path(args.output)
    out.write_text(report, encoding="utf-8")
    print(f"Report written to: {out}")


if __name__ == "__main__":
    main()
