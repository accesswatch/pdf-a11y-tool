"""
report_html.py — HTML Accessibility Audit Report Generator
==========================================================
Reads scan_results.json (from scan_all.py) and produces a self-contained,
accessible HTML report matching the design language of the handcrafted
PDF-ACCESSIBILITY-AUDIT-FULL.html:

  - Blue gradient banner with score cards
  - Score badges (A-F) and pills (Error/Warning/Info)
  - Callout boxes (note, warn, error, good)
  - Sprint boxes with numbered step lists
  - Table of Contents navigation
  - All sections: exec summary → quick fixes → manual review → additional
    improvements → summary table → priority plan → what's working → time
    estimates → final assessment → Technical Appendices A–E

Usage:
    python tools/report_html.py scan_results.json [--output REPORT.html]

This file is PERMANENT — do not delete.
"""

import sys
import json
import argparse
import datetime
from html import escape as esc
from pathlib import Path

# Import shared data from report_md.py (same directory)
from report_md import (
    RULE_REFERENCE,
    READING_ORDER_RULES,
    WCAG_LINKS,
    REF_LINKS,
    _wcag_html,
    _ref_html,
    _present_types,
    _all_findings,
    _findings_by_rule,
    _count_by_severity,
    _unique_files_for_rule,
    _active_rules,
)

try:
    from fix_tiers import automation_summary_html
    _HAS_FIX_TIERS = True
except ImportError:
    _HAS_FIX_TIERS = False
    def automation_summary_html(rule_ids, affected_count=0, total_count=0, remediation_applied=False):  # noqa: E302
        return ""


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _h(text: str) -> str:
    """HTML-escape text."""
    return esc(str(text), quote=True)


def _pill(severity: str) -> str:
    cls = {"Error": "pill-error", "Warning": "pill-warn", "Info": "pill-tip"}.get(severity, "pill-tip")
    return f'<span class="pill {cls}">{_h(severity)}</span>'


def _badge(grade: str) -> str:
    cls = {"A": "badge-a", "B": "badge-b", "C": "badge-c", "D": "badge-d", "F": "badge-f"}.get(grade, "badge-f")
    return f'<span class="score-badge {cls}">{_h(grade)}</span>'


def _icon_ok(text: str) -> str:
    return f'<span class="icon-ok">{_h(text)}</span>'


def _icon_fail(text: str) -> str:
    return f'<span class="icon-fail">{_h(text)}</span>'


def _plural(n: int, singular: str, plural: str | None = None) -> str:
    return f"{n} {singular if n == 1 else (plural or singular + 's')}"


# ---------------------------------------------------------------------------
# Data helpers — imported from report_md.py (see import block above)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = r"""
:root {
  --pass: #22c55e; --fail: #ef4444; --warn: #f59e0b; --tip: #3b82f6;
  --grade-a: #22c55e; --grade-b: #3b82f6; --grade-c: #f59e0b;
  --grade-d: #f97316; --grade-f: #ef4444;
  --bg: #ffffff; --text: #1f2937; --muted: #6b7280;
  --border: #e5e7eb; --surface: #f9fafb;
}
*, *::before, *::after { box-sizing: border-box; }
body {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: var(--text); background: var(--bg); line-height: 1.6;
  max-width: 72rem; margin: 0 auto; padding: 0 1.5rem 3rem;
}
h1, h2, h3, h4 { margin-top: 2rem; }
h2 { border-bottom: 2px solid var(--border); padding-bottom: 0.5rem; }
a { color: var(--tip); text-decoration: underline; }
a:focus { outline: 3px solid var(--tip); outline-offset: 2px; }
code { background: #f1f5f9; padding: 0.15em 0.4em; border-radius: 4px; font-size: 0.9em; }
pre { background: #f1f5f9; padding: 1rem; border-radius: 6px; overflow-x: auto; font-size: 0.85rem; line-height: 1.5; }
table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
th, td { border: 1px solid var(--border); padding: 0.5rem 0.75rem; text-align: left; }
th { background: var(--surface); font-weight: 600; }
tr:nth-child(even) { background: var(--surface); }

/* Banner */
.report-banner {
  background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
  color: #fff; padding: 2rem; border-radius: 12px; margin: 1.5rem 0 2rem;
}
.report-banner h1 { color: #fff; margin: 0 0 0.5rem; border: none; font-size: 1.75rem; }
.report-banner p { margin: 0.25rem 0; opacity: 0.9; }

/* Score cards */
.score-cards { display: flex; gap: 1rem; flex-wrap: wrap; margin: 1.5rem 0; }
.score-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: 1rem 1.5rem; min-width: 140px; text-align: center;
}
.score-card .label { font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
.score-card .value { font-size: 2rem; font-weight: 700; margin: 0.25rem 0; }

/* Pills */
.pill {
  display: inline-block; padding: 0.15em 0.6em; border-radius: 999px;
  font-size: 0.8rem; font-weight: 600; white-space: nowrap;
}
.pill-error { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.pill-warn  { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }
.pill-tip   { background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }
.pill-ok    { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }

/* Score badges */
.score-badge {
  display: inline-block; padding: 0.2em 0.6em; border-radius: 6px;
  font-weight: 700; font-size: 0.9rem; color: #fff;
}
.badge-a { background: var(--grade-a); }
.badge-b { background: var(--grade-b); }
.badge-c { background: var(--grade-c); color: #1f2937; }
.badge-d { background: var(--grade-d); color: #1f2937; }
.badge-f { background: var(--grade-f); }

/* Callouts */
.callout {
  border-left: 4px solid var(--border); border-radius: 0 8px 8px 0;
  padding: 1rem 1.25rem; margin: 1rem 0; background: var(--surface);
}
.callout-title { font-weight: 700; margin-bottom: 0.5rem; }
.callout-note  { border-left-color: var(--tip); background: #eff6ff; }
.callout-warn  { border-left-color: var(--warn); background: #fffbeb; }
.callout-error { border-left-color: var(--fail); background: #fef2f2; }
.callout-good  { border-left-color: var(--pass); background: #f0fdf4; }

/* Sprint / fix boxes */
.sprint { border: 1px solid var(--border); border-radius: 8px; margin: 1.5rem 0; overflow: hidden; }
.sprint h3.sprint-header {
  background: var(--surface); padding: 0.75rem 1.25rem; margin: 0;
  font-size: 1.1rem; font-weight: 700; border-bottom: 1px solid var(--border);
}
.sprint-body { padding: 1rem 1.25rem; }
.sprint-body h4 { margin-top: 1.25rem; margin-bottom: 0.5rem; font-size: 1rem; }
.sprint-body h4:first-child { margin-top: 0; }

/* Compliance badges */
.badge { display: inline-block; font-size: 0.8rem; font-weight: 600; padding: 0.15rem 0.6rem; border-radius: 4px; margin-bottom: 0.5rem; }
.badge-required { background: #fef2f2; color: #991b1b; border: 1px solid #fca5a5; }
.badge-recommended { background: #fefce8; color: #854d0e; border: 1px solid #fde047; }

/* Automation tier badges */
.automation-badge { font-size: 0.85rem; padding: 0.5rem 0.75rem; border-radius: 6px; margin: 0.5rem 0; line-height: 1.4; }
.automation-badge code { font-size: 0.8rem; background: rgba(0,0,0,0.06); padding: 0.1rem 0.3rem; border-radius: 3px; }
.badge-auto { background: #f0fdf4; color: #166534; border: 1px solid #86efac; }
.badge-assisted { background: #fefce8; color: #854d0e; border: 1px solid #fde047; }
.badge-manual { background: #fff7ed; color: #9a3412; border: 1px solid #fdba74; }

/* Accordion drill-down */
details.drill-down { margin: 0.75rem 0; border: 1px solid var(--border); border-radius: 6px; }
details.drill-down summary { cursor: pointer; padding: 0.6rem 1rem; font-weight: 600; background: var(--surface); border-radius: 6px; }
details.drill-down summary:hover { background: #e5e7eb; }
details.drill-down[open] summary { border-bottom: 1px solid var(--border); border-radius: 6px 6px 0 0; }
details.drill-down .drill-body { padding: 0.75rem 1rem; }

/* Steps */
.steps { counter-reset: step; list-style: none; padding-left: 0; }
.steps li {
  counter-increment: step; padding: 0.5rem 0 0.5rem 2.5rem;
  position: relative; border-left: 2px solid var(--border); margin-left: 0.75rem;
}
.steps li::before {
  content: counter(step);
  position: absolute; left: -0.85rem; top: 0.4rem;
  width: 1.5rem; height: 1.5rem; border-radius: 50%;
  background: var(--tip); color: #fff; font-size: 0.8rem;
  font-weight: 700; display: flex; align-items: center; justify-content: center;
}
.steps li:last-child { border-left-color: transparent; }

/* File sections */
.file-section { border: 1px solid var(--border); border-radius: 8px; margin: 1rem 0; overflow: hidden; }
.file-header {
  display: flex; justify-content: space-between; align-items: center;
  background: var(--surface); padding: 0.75rem 1.25rem;
  border-bottom: 1px solid var(--border);
}
.file-name { font-weight: 600; }
h3.file-name { margin: 0; font-size: 1rem; border: none; }
.file-body { padding: 1rem 1.25rem; }

/* Icons */
.icon-ok  { color: var(--pass); }
.icon-fail { color: var(--fail); font-weight: 600; }

/* TOC */
.toc { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem 1.5rem; margin: 1.5rem 0; }
.toc h2 { margin-top: 0; border: none; font-size: 1.1rem; }
.toc ol { margin: 0.5rem 0; padding-left: 1.5rem; }
.toc li { margin: 0.25rem 0; }

/* Utilities */
.sr-only { position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; overflow: hidden; clip: rect(0,0,0,0); border: 0; }
.muted { color: var(--muted); font-size: 0.875rem; }
hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }

@media (max-width: 640px) {
  .score-cards { flex-direction: column; }
  .file-header { flex-direction: column; gap: 0.5rem; }
}

/* Alt text analysis */
.alt-analysis { margin: 1rem 0; }
.alt-image-card { border: 1px solid var(--border); border-radius: 6px; margin: 0.75rem 0; overflow: hidden; }
.alt-image-header { display: flex; justify-content: space-between; align-items: center; background: var(--surface); padding: 0.6rem 1rem; border-bottom: 1px solid var(--border); font-weight: 600; font-size: 0.95rem; }
.alt-option { display: block; padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; }
.alt-option:last-child { border-bottom: none; }
.alt-option-header { display: flex; gap: 0.6rem; align-items: center; margin-bottom: 0.4rem; }
.alt-score-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 2.5rem; height: 1.6rem; font-size: 0.8rem; font-weight: 700; border-radius: 4px; flex-shrink: 0; }
.alt-score-a { background: #dcfce7; color: #166534; }
.alt-score-b { background: #dbeafe; color: #1e40af; }
.alt-score-c { background: #fef9c3; color: #854d0e; }
.alt-score-d { background: #fed7aa; color: #9a3412; }
.alt-score-f { background: #fecaca; color: #991b1b; }
.alt-model { font-size: 0.8rem; color: var(--muted); }
.alt-rank { font-size: 0.8rem; color: var(--muted); margin-left: auto; }
.alt-text-content { font-size: 0.9rem; line-height: 1.5; padding: 0.4rem 0.6rem; background: #f9fafb; border-radius: 4px; border: 1px solid #f3f4f6; }
.alt-flags { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.5rem; }
.alt-flag { font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 3px; }
.alt-flag-error { background: #fef2f2; color: #991b1b; }
.alt-flag-warning { background: #fffbeb; color: #854d0e; }
.alt-flag-info { background: #eff6ff; color: #1e40af; }
.alt-recommendation { background: #f0f9ff; border-left: 3px solid var(--tip); padding: 0.6rem 0.85rem; margin: 0.75rem 1rem; font-size: 0.85rem; border-radius: 0 4px 4px 0; line-height: 1.5; }
.alt-section-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); font-weight: 600; padding: 0.6rem 1rem 0.2rem; border-top: 2px solid var(--border); margin-top: 0.25rem; }
"""


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_html_head(audit: dict) -> str:
    try:
        display_date = datetime.datetime.fromisoformat(
            audit.get("scan_date", "")).strftime("%B %d, %Y")
    except Exception:
        display_date = audit.get("scan_date", "")[:10]
    title = f"Accessibility Audit Report — {display_date}"
    return (
        f'<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        f'<meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{_h(title)}</title>\n'
        f'<style>{CSS}</style>\n'
        f'</head>\n<body>\n'
    )


def _render_banner(audit: dict) -> str:
    s = audit["summary"]
    try:
        display_date = datetime.datetime.fromisoformat(
            audit.get("scan_date", "")).strftime("%B %d, %Y")
    except Exception:
        display_date = audit.get("scan_date", "")[:10]

    type_labels = []
    ext_map = {"pdf": "PDF", "docx": "Word", "xlsx": "Excel", "pptx": "PowerPoint",
                "epub": "ePub", "md": "Markdown"}
    for t, n in s.get("by_type", {}).items():
        if n:
            type_labels.append(f"{n} {ext_map.get(t, t.upper())}")
    doc_desc = ", ".join(type_labels) if type_labels else f"{s['total_files']} documents"

    return (
        '<div class="report-banner">\n'
        '  <h1>Accessibility Audit Report</h1>\n'
        f'  <p>Generated: {_h(display_date)}</p>\n'
        f'  <p>{_h(doc_desc)} reviewed</p>\n'
        '</div>\n'
    )


def _render_score_cards(audit: dict, all_f: list) -> str:
    s = audit["summary"]
    counts = _count_by_severity(all_f)
    return (
        '<div class="score-cards">\n'
        '  <div class="score-card">\n'
        f'    <div class="label">Overall Score</div>\n'
        f'    <div class="value">{s["score"]}</div>\n'
        f'    <div>/ 100</div>\n'
        '  </div>\n'
        '  <div class="score-card">\n'
        f'    <div class="label">Grade</div>\n'
        f'    <div class="value">{_badge(s["grade"])}</div>\n'
        '  </div>\n'
        '  <div class="score-card">\n'
        f'    <div class="label">Files</div>\n'
        f'    <div class="value">{s["total_files"]}</div>\n'
        '  </div>\n'
        '  <div class="score-card">\n'
        f'    <div class="label">Errors</div>\n'
        f'    <div class="value" style="color:var(--fail)">{counts["Error"]}</div>\n'
        '  </div>\n'
        '  <div class="score-card">\n'
        f'    <div class="label">Warnings</div>\n'
        f'    <div class="value" style="color:var(--warn)">{counts["Warning"]}</div>\n'
        '  </div>\n'
        '  <div class="score-card">\n'
        f'    <div class="label">Info</div>\n'
        f'    <div class="value" style="color:var(--tip)">{counts["Info"]}</div>\n'
        '  </div>\n'
        '</div>\n'
    )


def _render_toc(sections_list: list[tuple[str, str]]) -> str:
    """Build a Table of Contents from (id, title) tuples."""
    items = "\n".join(
        f'    <li><a href="#{sid}">{_h(title)}</a></li>'
        for sid, title in sections_list
    )
    return (
        '<nav class="toc" aria-label="Table of Contents">\n'
        '  <h2>Contents</h2>\n'
        f'  <ol>\n{items}\n  </ol>\n'
        '</nav>\n'
    )


def _render_executive_summary(audit: dict, by_rule: dict, all_f: list) -> str:
    s = audit["summary"]
    errors = [r for r, d in by_rule.items()
              if any(fn.get("severity") == "Error" for fn in d["findings"])]

    lines = ['<section id="exec-summary">\n<h2>1. Executive Summary</h2>\n']

    if s["grade"] in ("A", "B"):
        lines.append(
            f'<p>The {_plural(s["total_files"], "document")} audited '
            f'score <strong>{s["score"]}/100 (Grade {_h(s["grade"])})</strong> — '
            'a solid foundation. Most important structural requirements are already met.</p>\n'
        )
    elif s["grade"] == "C":
        lines.append(
            f'<p>The {_plural(s["total_files"], "document")} audited '
            f'score <strong>{s["score"]}/100 (Grade {_h(s["grade"])})</strong>. '
            'There is a good structural foundation, but several issues need attention '
            'to meet accessibility standards fully.</p>\n'
        )
    else:
        lines.append(
            f'<p>The {_plural(s["total_files"], "document")} audited '
            f'score <strong>{s["score"]}/100 (Grade {_h(s["grade"])})</strong>. '
            'Significant accessibility barriers were found that should be addressed '
            'before distribution.</p>\n'
        )

    # Issue summary table
    if errors:
        # Sort by number of affected files (highest impact first)
        errors.sort(key=lambda r: -len(_unique_files_for_rule(by_rule, r)))
        lines.append('<h3>Main Issues Found</h3>\n<table>\n'
                     '<thead><tr><th>Issue</th><th>Severity</th><th>Affected Files</th></tr></thead>\n<tbody>\n')
        for rule in errors[:8]:
            ref = RULE_REFERENCE.get(rule, {})
            desc = ref[4] if ref else rule
            sev = ref[2] if ref else "Error"
            affected = _unique_files_for_rule(by_rule, rule)
            lines.append(f'<tr><td>{_h(desc)}</td><td>{_pill(sev)}</td>'
                         f'<td>{len(affected)} of {s["total_files"]}</td></tr>\n')
        lines.append('</tbody></table>\n')

    # What's working well (brief)
    working = []
    pdf_files = [f for f in audit.get("files", []) if f["type"] == "pdf"]
    error_rules = set(errors)
    if pdf_files and "PDFUA.STRUCT.NOTREE" not in error_rules and "PDFUA.STRUCT.TAGGED" not in error_rules:
        working.append("PDF documents are properly tagged")
    if pdf_files and "PDFUA.FORM.TU" not in error_rules:
        working.append("Form fields have accessible labels (tooltips)")

    if working:
        lines.append('<div class="callout callout-good">\n<div class="callout-title">What Is Already Working</div>\n<ul>\n')
        for w in working:
            lines.append(f'  <li>{_h(w)}</li>\n')
        lines.append('</ul>\n</div>\n')

    lines.append('</section>\n')
    return "".join(lines)


def _render_quick_fixes(by_rule: dict, audit: dict) -> str:
    s = audit["summary"]
    total = s["total_files"]
    types = _present_types(audit)
    rem_applied = audit.get("remediation", {}).get("enabled", False)
    sprints = []
    fix_number = 1

    def _badge(required: bool, text: str) -> str:
        cls = "badge-required" if required else "badge-recommended"
        return f'<span class="badge {cls}">{text}</span>'

    def _make_sprint(title: str, badge_html: str, what_checks: str,
                     steps_html: str, why_matters: str,
                     auto_badge: str = "") -> str:
        return (
            '<div class="sprint">\n'
            f'  <h3 class="sprint-header">{_h(title)}</h3>\n'
            f'  <div class="sprint-body">\n'
            f'    {badge_html}\n'
            f'    {auto_badge}'
            f'    <h4>What This Checks</h4>\n<p>{what_checks}</p>\n'
            f'    <details class="drill-down">\n'
            f'      <summary>How to Fix (step-by-step instructions)</summary>\n'
            f'      <div class="drill-body">\n{steps_html}\n      </div>\n'
            f'    </details>\n'
            f'    <h4>Why This Matters</h4>\n<p>{why_matters}</p>\n'
            f'  </div>\n'
            '</div>\n'
        )

    # ── Tagging ──
    tagged_files = sorted(set(
        _unique_files_for_rule(by_rule, "PDFUA.STRUCT.TAGGED") +
        _unique_files_for_rule(by_rule, "PDFUA.STRUCT.NOTREE")))
    if tagged_files:
        n = len(tagged_files)
        steps = (
            '<h4>Re-export from source (preferred)</h4>\n<ol class="steps">\n'
            '  <li>Open the original Word, InDesign, or PowerPoint file</li>\n'
            '  <li>File &rarr; Save As / Export &rarr; PDF</li>\n'
            '  <li>Ensure <strong>Tagged PDF</strong> or <strong>Create Accessible PDF</strong> is checked</li>\n'
            '  <li>Open the new PDF and verify tags in the Tags panel</li>\n</ol>\n'
            '<h4>In Adobe Acrobat Pro</h4>\n<ol class="steps">\n'
            '  <li>All Tools &rarr; Accessibility &rarr; AutoTag Document</li>\n'
            '  <li>Review the Tags panel &mdash; fix any <code>&lt;P&gt;</code> elements that should be headings</li>\n'
            '  <li>Run Accessibility Check (All Tools &rarr; Accessibility &rarr; Full Check) to verify</li>\n'
            '  <li>File &rarr; Save As</li>\n</ol>\n'
        )
        sprints.append(_make_sprint(
            f"Fix {fix_number} \u2014 Tag the Document for Accessibility ({n} of {total} files)",
            _badge(True, f"\U0001f534 Required \u2014 {_wcag_html('1.3.1')} / PDF/UA section 5.1"),
            "PDF/UA requires every PDF to contain a complete tag structure "
            "(rules <code>PDFUA.STRUCT.TAGGED</code> and <code>PDFUA.STRUCT.NOTREE</code>). "
            "Tags define the logical reading order and identify each element &mdash; "
            "headings, paragraphs, lists, tables, and form fields. The scanner "
            "checks whether the document contains any tags at all and whether "
            "a valid structure tree exists.",
            steps,
            "Tags are the foundation of PDF accessibility. "
            "Without tags, screen readers cannot determine document structure &mdash; headings, "
            "paragraphs, lists, tables, and form fields are all invisible. An untagged PDF "
            "is essentially a flat image to assistive technology."
            f'<br><strong>Reference:</strong> {_wcag_html("1.3.1")} | '
            f'{_ref_html("pdfua")} | {_ref_html("acrobat_a11y")}',
            auto_badge=automation_summary_html(["PDFUA.STRUCT.TAGGED", "PDFUA.STRUCT.NOTREE"], n, total, remediation_applied=rem_applied)
        ))
        fix_number += 1

    # ── Title ──
    title_rules = ["PDFUA.METADATA.TITLE", "DOCX-META.TITLE", "PPTX.META.TITLE",
                    "XLSX.META.TITLE", "EPUB-E001"]
    title_files = sorted(set(f for r in title_rules for f in _unique_files_for_rule(by_rule, r)))
    if title_files:
        n = len(title_files)
        pdf_title = bool(_unique_files_for_rule(by_rule, "PDFUA.METADATA.TITLE"))
        docx_title = bool(_unique_files_for_rule(by_rule, "DOCX-META.TITLE"))
        pptx_title = bool(_unique_files_for_rule(by_rule, "PPTX.META.TITLE"))
        xlsx_title = bool(_unique_files_for_rule(by_rule, "XLSX.META.TITLE"))
        epub_title = bool(_unique_files_for_rule(by_rule, "EPUB-E001"))
        active_title_rules = _active_rules(["PDFUA.METADATA.TITLE", "DOCX-META.TITLE", "PPTX.META.TITLE",
                                             "XLSX.META.TITLE", "EPUB-E001"], by_rule)
        body = []
        if pdf_title:
            body.append('<h4>In Adobe Acrobat Pro</h4>\n<ol class="steps">\n'
                        '  <li>File &rarr; Properties</li>\n'
                        '  <li>Description tab &rarr; enter a meaningful title</li>\n'
                        '  <li>Initial View tab &rarr; set <strong>Show: Document Title</strong></li>\n'
                        '  <li>Click OK &rarr; File &rarr; Save As</li>\n</ol>\n')
        if docx_title:
            body.append('<h4>In Microsoft Word</h4>\n<ol class="steps">\n'
                        '  <li>File &rarr; Info &rarr; Properties (right panel)</li>\n'
                        '  <li>Enter title in the <strong>Title</strong> field</li>\n'
                        '  <li>Save</li>\n</ol>\n')
        if pptx_title:
            body.append('<h4>In Microsoft PowerPoint</h4>\n<ol class="steps">\n'
                        '  <li>File &rarr; Info &rarr; Properties</li>\n'
                        '  <li>Enter title in the <strong>Title</strong> field</li>\n'
                        '  <li>Save</li>\n</ol>\n')
        if xlsx_title:
            body.append('<h4>In Microsoft Excel</h4>\n<ol class="steps">\n'
                        '  <li>File &rarr; Info &rarr; Properties</li>\n'
                        '  <li>Enter title in the <strong>Title</strong> field</li>\n'
                        '  <li>Save</li>\n</ol>\n')
        if epub_title:
            body.append('<h4>In Sigil or Calibre (ePub)</h4>\n<ol class="steps">\n'
                        '  <li>Open the OPF file (content.opf)</li>\n'
                        '  <li>Add or edit <code>&lt;dc:title&gt;</code> in the <code>&lt;metadata&gt;</code> section</li>\n'
                        '  <li>Save</li>\n</ol>\n')
        sprints.append(_make_sprint(
            f"Fix {fix_number} \u2014 Add a Document Title ({n} of {total} files)",
            _badge(True, f"\U0001f534 Required \u2014 {_wcag_html('2.4.2')}"),
            "Every document must have a meaningful title set in its metadata "
            f"(rules {', '.join(f'<code>{r}</code>' for r in active_title_rules)}). "
            "The scanner reads the document properties and flags any file where "
            "the title field is blank or set to a generic placeholder.",
            "".join(body),
            "Screen readers announce the document title when opening a file. "
            "Without a title, users only hear the file name &mdash; which may be meaningless."
            f'<br><strong>Reference:</strong> {_wcag_html("2.4.2")}'
            '<div class="callout" style="margin-top:0.75em;padding:0.6em 1em;'
            'border-left:4px solid #b58900;background:#fdf6e3;">'
            "<strong>Human review required after automation:</strong> "
            "The automated fix tool sets a placeholder title derived from the file name "
            "(e.g.&nbsp;<code>TODO: Add descriptive document title</code>). "
            "You <strong>must</strong> replace this placeholder with a meaningful, "
            "human-written title that accurately describes the document&rsquo;s content."
            "</div>",
            auto_badge=automation_summary_html(active_title_rules, n, total, remediation_applied=rem_applied)
        ))
        fix_number += 1

    # ── Language ──
    lang_rules = ["PDFUA.METADATA.LANG", "DOCX-META.LANG", "PPTX.META.LANG", "EPUB-E003"]
    lang_files = sorted(set(f for r in lang_rules for f in _unique_files_for_rule(by_rule, r)))
    if lang_files:
        n = len(lang_files)
        active_lang_rules = _active_rules(["PDFUA.METADATA.LANG", "DOCX-META.LANG", "PPTX.META.LANG", "EPUB-E003"], by_rule)
        body = []
        if _unique_files_for_rule(by_rule, "PDFUA.METADATA.LANG"):
            body.append('<h4>In Adobe Acrobat Pro</h4>\n<ol class="steps">\n'
                        '  <li>File &rarr; Properties &rarr; Advanced tab</li>\n'
                        '  <li>Reading Options &rarr; Language</li>\n'
                        '  <li>Enter <code>en</code> for English or <code>es</code> for Spanish</li>\n'
                        '  <li>Click OK &rarr; Save As</li>\n</ol>\n')
        if _unique_files_for_rule(by_rule, "DOCX-META.LANG"):
            body.append('<h4>In Microsoft Word</h4>\n<ol class="steps">\n'
                        '  <li>Review &rarr; Language &rarr; Set Proofing Language</li>\n'
                        '  <li>Select the correct language &rarr; click OK</li>\n'
                        '  <li>Save</li>\n</ol>\n')
        if _unique_files_for_rule(by_rule, "PPTX.META.LANG"):
            body.append('<h4>In Microsoft PowerPoint</h4>\n<ol class="steps">\n'
                        '  <li>Review &rarr; Language &rarr; Set Proofing Language</li>\n'
                        '  <li>Select the correct language &rarr; click OK</li>\n'
                        '  <li>Save</li>\n</ol>\n')
        if _unique_files_for_rule(by_rule, "EPUB-E003"):
            body.append('<h4>In Sigil or Calibre (ePub)</h4>\n<ol class="steps">\n'
                        '  <li>Open the OPF file (content.opf)</li>\n'
                        '  <li>Add or edit <code>&lt;dc:language&gt;en&lt;/dc:language&gt;</code> in <code>&lt;metadata&gt;</code></li>\n'
                        '  <li>Save</li>\n</ol>\n')
        sprints.append(_make_sprint(
            f"Fix {fix_number} \u2014 Set the Document Language ({n} of {total} files)",
            _badge(True, f"\U0001f534 Required \u2014 {_wcag_html('3.1.1')}"),
            "Every document must declare its primary language in metadata "
            f"(rules {', '.join(f'<code>{r}</code>' for r in active_lang_rules)}). "
            "The scanner reads the language property and flags any file where "
            "it is missing or empty.",
            "".join(body),
            "Screen readers use the language setting to choose the correct pronunciation engine. "
            "Wrong language = mispronounced or garbled text."
            f'<br><strong>Reference:</strong> {_wcag_html("3.1.1")}',
            auto_badge=automation_summary_html(active_lang_rules, n, total, remediation_applied=rem_applied)
        ))
        fix_number += 1

    # ── Form fields in structure tree ──
    form_struct_files = sorted(set(
        _unique_files_for_rule(by_rule, "PDFUA.FORM.STRUCT") +
        _unique_files_for_rule(by_rule, "PDFBP.FORM.STRUCT")))
    if form_struct_files:
        n = len(form_struct_files)
        has_error = bool(_unique_files_for_rule(by_rule, "PDFUA.FORM.STRUCT"))
        badge_text = (f"\U0001f534 Required \u2014 {_wcag_html('1.3.1')} / PDF/UA section 6.6"
                      if has_error else
                      f"\U0001f7e1 Recommended \u2014 {_wcag_html('1.3.1')}")
        steps = (
            '<h4>Re-export from source (preferred)</h4>\n<ol class="steps">\n'
            '  <li>Open the original Word or InDesign file</li>\n'
            '  <li>Ensure form fields use content controls (Word) or proper form objects (InDesign)</li>\n'
            '  <li>Re-export to PDF with <strong>Tagged PDF</strong> enabled</li>\n</ol>\n'
            '<h4>In Adobe Acrobat Pro (manual repair)</h4>\n<ol class="steps">\n'
            '  <li>Open the Tags panel (View &rarr; Show/Hide &rarr; Navigation Panes &rarr; Tags)</li>\n'
            '  <li>Locate orphaned <code>&lt;Form&gt;</code> tags (often at the end of the tree under <code>/Document</code>)</li>\n'
            '  <li>Cut each <code>&lt;Form&gt;</code> tag and paste it next to its corresponding label element</li>\n'
            '  <li>Verify by tabbing through the form with a screen reader</li>\n'
            '  <li>File &rarr; Save As</li>\n</ol>\n'
        )
        sprints.append(_make_sprint(
            f"Fix {fix_number} \u2014 Link Form Fields into the Structure Tree ({n} of {total} files)",
            _badge(has_error, badge_text),
            "PDF/UA requires every interactive form field to be linked into the "
            "document&rsquo;s tag structure (rules <code>PDFUA.FORM.STRUCT</code>, "
            "<code>PDFBP.FORM.STRUCT</code>). "
            "The scanner inspects the tag tree and flags form widgets that are "
            "orphaned (not connected to any tag) or misplaced (nested under the "
            "wrong parent element).",
            steps,
            "Form fields that are not linked into the tag tree are invisible "
            "to screen readers or announced out of context &mdash; users cannot tell "
            "what information to enter. Labels and fields become disconnected even if "
            "they appear side by side visually."
            f'<br><strong>Reference:</strong> {_wcag_html("1.3.1")} | {_ref_html("webaim_forms")}',
            auto_badge=automation_summary_html(["PDFUA.FORM.STRUCT", "PDFBP.FORM.STRUCT"], n, total, remediation_applied=rem_applied)
        ))
        fix_number += 1

    # ── Tooltips ──
    tooltip_files = _unique_files_for_rule(by_rule, "PDFUA.FORM.TU")
    if tooltip_files:
        n = len(tooltip_files)
        steps = (
            '<h4>In Adobe Acrobat Pro</h4>\n<ol class="steps">\n'
            '  <li>All Tools &rarr; Prepare Form</li>\n'
            '  <li>Right-click each unlabelled field &rarr; Properties</li>\n'
            '  <li>Enter a descriptive label in the <strong>Tooltip</strong> field '
            '(for required fields, add <em>(required)</em> at the end)</li>\n'
            '  <li>Save</li>\n</ol>\n'
        )
        sprints.append(_make_sprint(
            f"Fix {fix_number} \u2014 Add Labels to Form Fields ({n} of {total} files)",
            _badge(True, f"\U0001f534 Required \u2014 {_wcag_html('1.3.1')} / PDF/UA section 6.6"),
            "PDF/UA requires every form field to have a tooltip that acts as its "
            "accessible label (rule <code>PDFUA.FORM.TU</code>). The scanner inspects each "
            "form widget&rsquo;s <code>/TU</code> (tooltip) entry and flags any field where it "
            "is missing or empty.",
            steps,
            "Screen readers read the Tooltip aloud as the field label. Without it, "
            "users hear only the field type &mdash; e.g. &ldquo;Text field&rdquo; &mdash; with no "
            "indication of what to enter."
            f'<br><strong>Reference:</strong> {_wcag_html("4.1.2")} | {_wcag_html("3.3.2")} | {_ref_html("webaim_forms")}',
            auto_badge=automation_summary_html(["PDFUA.FORM.TU"], n, total, remediation_applied=rem_applied)
        ))
        fix_number += 1

    # ── Slide titles ──
    slide_title_files = _unique_files_for_rule(by_rule, "PPTX.SLIDE.TITLE")
    if slide_title_files:
        n = len(slide_title_files)
        steps = (
            '<h4>In Microsoft PowerPoint</h4>\n<ol class="steps">\n'
            '  <li>Open the slide in Normal view</li>\n'
            '  <li>Click the title placeholder at the top of the slide</li>\n'
            '  <li>Type a meaningful, unique title</li>\n'
            '  <li>Save</li>\n</ol>\n'
        )
        sprints.append(_make_sprint(
            f"Fix {fix_number} \u2014 Add Titles to All Slides ({n} of {total} files)",
            _badge(True, f"\U0001f534 Required \u2014 {_wcag_html('2.4.2')}"),
            "Every slide must have a unique, descriptive title (rule <code>PPTX.SLIDE.TITLE</code>). "
            "The scanner checks the title placeholder on each slide and flags slides "
            "where it is missing, empty, or hidden.",
            steps,
            "Slide titles are how screen reader users navigate presentations. "
            "Untitled slides force users to listen through all content to find what they need."
            f'<br><strong>Reference:</strong> {_wcag_html("2.4.2")}',
            auto_badge=automation_summary_html(["PPTX.SLIDE.TITLE"], n, total, remediation_applied=rem_applied)
        ))
        fix_number += 1

    # ── Alt text ──
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
        body = []
        if pdf_alt:
            body.append('<h4>In Adobe Acrobat Pro</h4>\n<ol class="steps">\n'
                        '  <li>Open the Tags panel &rarr; locate <code>&lt;Figure&gt;</code> tags</li>\n'
                        '  <li>Right-click &rarr; Properties &rarr; enter alt text in the <strong>Alternate Text</strong> field</li>\n'
                        '  <li>For decorative images, set alt text to a single space or mark as artifact</li>\n'
                        '  <li>Save As</li>\n</ol>\n')
        if docx_alt:
            body.append('<h4>In Microsoft Word</h4>\n<ol class="steps">\n'
                        '  <li>Right-click an image &rarr; Edit Alt Text</li>\n'
                        '  <li>Enter a description of what the image shows and why it matters</li>\n'
                        '  <li>If purely decorative, check <strong>Mark as decorative</strong></li>\n'
                        '  <li>Repeat for all images &rarr; Save</li>\n</ol>\n')
        if pptx_alt:
            body.append('<h4>In Microsoft PowerPoint</h4>\n<ol class="steps">\n'
                        '  <li>Right-click an image &rarr; Edit Alt Text</li>\n'
                        '  <li>Enter a meaningful description</li>\n'
                        '  <li>If decorative, check <strong>Mark as decorative</strong></li>\n'
                        '  <li>Repeat for all images &rarr; Save</li>\n</ol>\n')
        if xlsx_alt:
            body.append('<h4>In Microsoft Excel</h4>\n<ol class="steps">\n'
                        '  <li>Right-click an image or chart &rarr; Edit Alt Text</li>\n'
                        '  <li>Enter a meaningful description</li>\n'
                        '  <li>If decorative, check <strong>Mark as decorative</strong></li>\n'
                        '  <li>Save</li>\n</ol>\n')
        if epub_alt:
            body.append('<h4>In Sigil or Calibre (ePub)</h4>\n<ol class="steps">\n'
                        '  <li>Open the XHTML content file containing the image</li>\n'
                        '  <li>Add or edit the <code>alt</code> attribute on each <code>&lt;img&gt;</code> tag</li>\n'
                        '  <li>Save</li>\n</ol>\n')
        sprints.append(_make_sprint(
            f"Fix {fix_number} \u2014 Add Alternative Text to Images ({n} of {total} files)",
            _badge(True, f"\U0001f534 Required \u2014 {_wcag_html('1.1.1')}"),
            "Every meaningful image must have alternative text that describes "
            f"its content (rules {', '.join(f'<code>{r}</code>' for r in active_alt_rules)}). "
            "The scanner inspects each image element and flags any where "
            "alt text is missing, empty, or a generic placeholder.",
            "".join(body),
            "Blind and low-vision users hear alt text read aloud instead of seeing the image. "
            "Generic or missing alt text leaves them without the information the image conveys."
            f'<br><strong>Reference:</strong> {_wcag_html("1.1.1")} | {_ref_html("webaim_alt")}',
            auto_badge=automation_summary_html(active_alt_rules, n, total, remediation_applied=rem_applied)
        ))
        fix_number += 1

    # ── Table headers ──
    table_rules = ["PDFUA.TABLE.HEADERS", "DOCX-TABLE.HEADERS", "XLSX.TABLE.HEADER", "PPTX.TABLE.HEADER"]
    table_files = sorted(set(f for r in table_rules for f in _unique_files_for_rule(by_rule, r)))
    if table_files:
        n = len(table_files)
        active_table_rules = _active_rules(table_rules, by_rule)
        body = []
        if _unique_files_for_rule(by_rule, "PDFUA.TABLE.HEADERS"):
            body.append('<h4>In Adobe Acrobat Pro</h4>\n'
                        '<p>In the Tags panel, tag header cells as '
                        '<code>/TH</code> (not <code>/TD</code>). Right-click the cell tag &rarr; '
                        'Properties &rarr; Type &rarr; TH.</p>\n')
        if _unique_files_for_rule(by_rule, "DOCX-TABLE.HEADERS"):
            body.append('<h4>In Microsoft Word</h4>\n'
                        '<p>Click in the header row &rarr; Table Design tab &rarr; '
                        'check <strong>Header Row</strong>. Also ensure the row uses a '
                        '&ldquo;Table Header&rdquo; or bold style.</p>\n')
        if _unique_files_for_rule(by_rule, "XLSX.TABLE.HEADER"):
            body.append('<h4>In Microsoft Excel</h4>\n'
                        '<p>Click inside the data range &rarr; Insert &rarr; Table &rarr; '
                        'check <strong>My table has headers</strong>.</p>\n')
        if _unique_files_for_rule(by_rule, "PPTX.TABLE.HEADER"):
            body.append('<h4>In Microsoft PowerPoint</h4>\n'
                        '<p>Click the table &rarr; Table Design tab &rarr; '
                        'check <strong>Header Row</strong>.</p>\n')
        sprints.append(_make_sprint(
            f"Fix {fix_number} \u2014 Mark Table Header Rows ({n} of {total} files)",
            _badge(True, f"\U0001f534 Required \u2014 {_wcag_html('1.3.1')}"),
            "Data tables must identify their header rows so screen readers "
            "can announce column names as users move between cells "
            f"(rules {', '.join(f'<code>{r}</code>' for r in active_table_rules)}). "
            "The scanner inspects table structure and flags tables "
            "where the first row is not marked as a header.",
            "".join(body),
            "Screen readers announce column headers as users move between cells. "
            "Without headers, every cell sounds identical &mdash; "
            "e.g. &ldquo;Row 3, Column 2: Smith&rdquo; with no context."
            f'<br><strong>Reference:</strong> {_wcag_html("1.3.1")} | {_ref_html("webaim_tables")}',
            auto_badge=automation_summary_html(active_table_rules, n, total, remediation_applied=rem_applied)
        ))
        fix_number += 1

    # ── DisplayDocTitle / Tab order ──
    doc_title_files = _unique_files_for_rule(by_rule, "PDFBP.DISPLAY.DOCTITLE")
    tab_order_files = _unique_files_for_rule(by_rule, "PDFBP.NAV.TABORDER")
    if doc_title_files or tab_order_files:
        all_f2 = sorted(set(doc_title_files + tab_order_files))
        n = len(all_f2)
        body = []
        if doc_title_files:
            body.append('<h4>Display Doc Title (in Adobe Acrobat Pro)</h4>\n<ol class="steps">\n'
                        '  <li>File &rarr; Properties &rarr; Initial View</li>\n'
                        '  <li><em>Show:</em> &rarr; select <strong>Document Title</strong></li>\n'
                        '  <li>Save As</li>\n</ol>\n')
        if tab_order_files:
            body.append('<h4>Tab Order (in Adobe Acrobat Pro)</h4>\n<ol class="steps">\n'
                        '  <li>Open Page Thumbnails panel</li>\n'
                        '  <li>Right-click a page &rarr; Page Properties &rarr; Tab Order</li>\n'
                        '  <li>Select <strong>Use Document Structure</strong></li>\n'
                        '  <li>Repeat for all pages &rarr; Save As</li>\n</ol>\n')
        sprints.append(_make_sprint(
            f"Fix {fix_number} \u2014 Enable Title Display and Correct Tab Order ({n} of {total} files)",
            _badge(False, "\U0001f7e1 Recommended \u2014 improves usability but not a WCAG conformance failure"),
            "Two best-practice settings improve the user experience in PDF viewers: "
            "showing the document title in the title bar instead of the file name "
            "(rule <code>PDFBP.DISPLAY.DOCTITLE</code>), and setting tab order to follow the "
            "document structure (rule <code>PDFBP.NAV.TABORDER</code>). "
            "These are not WCAG conformance failures but significantly improve "
            "usability for all users.",
            "".join(body),
            "",
            auto_badge=automation_summary_html(["PDFBP.DISPLAY.DOCTITLE", "PDFBP.NAV.TABORDER"], n, total, remediation_applied=rem_applied)
        ))
        fix_number += 1

    if not sprints:
        return ""

    # Build tool note based on which document types are present
    tool_items = []
    if "pdf" in types:
        tool_items.append('<li><strong>PDF files:</strong> Adobe Acrobat Professional</li>')
    if "docx" in types:
        tool_items.append('<li><strong>Word files (.docx):</strong> Microsoft Word</li>')
    if "xlsx" in types:
        tool_items.append('<li><strong>Excel files (.xlsx):</strong> Microsoft Excel</li>')
    if "pptx" in types:
        tool_items.append('<li><strong>PowerPoint files (.pptx):</strong> Microsoft PowerPoint</li>')
    if "epub" in types:
        tool_items.append('<li><strong>ePub files:</strong> Sigil or Calibre</li>')
    tool_note = ""
    if tool_items:
        tool_note = ('<div class="callout callout-note">\n'
                     '<div class="callout-title">Recommended Tools for Remediation</div>\n'
                     '<ul>\n  ' + '\n  '.join(tool_items) + '\n</ul>\n</div>\n')

    auto_legend = (
        '<div class="callout callout-note">\n'
        '<div class="callout-title">Toolkit Automation</div>\n'
        '<p>Each fix block shows whether the DRC Accessibility Toolkit can help:</p>\n'
        '<ul>\n'
        '  <li><span class="automation-badge badge-auto">Safe to Automate</span> '
        '&mdash; fully automated, no human judgment needed (<code>--fix</code> flag)</li>\n'
        '  <li><span class="automation-badge badge-assisted">Assisted</span> '
        '&mdash; toolkit applies a partial fix; human review required</li>\n'
        '  <li><span class="automation-badge badge-manual">Manual</span> '
        '&mdash; requires human judgment or an external tool (e.g. Acrobat Pro)</li>\n'
        '</ul>\n</div>\n'
    )

    return (
        '<section id="quick-fixes">\n'
        '<h2>2. Start Here: Quick Fixes (Do These First)</h2>\n'
        '<p>These are the most common issues found across your documents. '
        'Each fix includes step-by-step instructions for the appropriate tool.</p>\n'
        + tool_note
        + auto_legend
        + "".join(sprints)
        + '</section>\n'
    )


def _render_manual_review(by_rule: dict, audit: dict, all_f: list) -> str:
    lines = [
        '<section id="manual-review">\n'
        '<h2>3. Manual Review Required</h2>\n'
        '<p>The following issues <strong>cannot be fully verified by automated scanning</strong>. '
        'They require a human reviewer using appropriate tools '
        'and a screen reader such as NVDA or JAWS.</p>\n'
    ]

    # ── Reading Order ──
    ro_findings = [f for f in all_f if f.get("rule", "") in READING_ORDER_RULES]
    detected_outcomes = []
    for fn in ro_findings:
        outcome = fn.get("outcome", "")
        rule = fn.get("rule", "")
        if outcome and rule not in {"PDFQ.ORDER.MANUAL", "PPTX.ORDER.VERIFY"}:
            detected_outcomes.append((rule, fn.get("severity", "Info"), fn.get("_file", ""), outcome))

    lines.append(
        '<h3>Reading Order</h3>\n'
        '<p><strong>Priority: Critical</strong> — affects every screen reader and Braille display user</p>\n'
        '<p>Reading order is the sequence in which assistive technology reads document content. '
        'It may be completely different from the visual order on screen. Multi-column layouts, '
        'sidebars, form fields, and complex tables are the most common sources of problems.</p>\n'
        f'<p><strong>Reference:</strong> {_wcag_html("1.3.2")} | {_ref_html("acrobat_a11y")}</p>\n'
    )

    # Impact table
    lines.append(
        '<h4>What Goes Wrong</h4>\n'
        '<table>\n<thead><tr><th>Situation</th><th>Screen reader user experience</th></tr></thead>\n<tbody>\n'
        '<tr><td>Form field labels appear after their fields</td>'
        '<td>Hears "Checkbox, unchecked" with no context</td></tr>\n'
        '<tr><td>Two-column layout in wrong order</td>'
        '<td>Hears all of column 2 first, then column 1</td></tr>\n'
        '<tr><td>Headers/footers not marked as Artifacts</td>'
        '<td>Page header repeated at start of every page</td></tr>\n'
        '<tr><td>Caption separated from Figure</td>'
        '<td>Image description heard in wrong narrative context</td></tr>\n'
        '</tbody></table>\n'
    )

    # Automated detections
    if detected_outcomes:
        lines.append(
            '<h4>What Was Detected Automatically</h4>\n'
            '<table>\n<thead><tr><th>File</th><th>Rule</th><th>Severity</th>'
            '<th>Likely Experience</th></tr></thead>\n<tbody>\n')
        for rule, sev, fname, outcome in detected_outcomes:
            short = outcome
            lines.append(
                f'<tr><td>{_h(fname)}</td><td><code>{_h(rule)}</code></td>'
                f'<td>{_pill(sev)}</td><td>{_h(short)}</td></tr>\n')
        lines.append('</tbody></table>\n')

    # Verification instructions
    pdf_files = [f for f in audit.get("files", []) if f["type"] == "pdf"]
    ppt_files = [f for f in audit.get("files", []) if f["type"] == "pptx"]

    if pdf_files:
        lines.append(
            '<h4>How to Verify — PDF (Adobe Acrobat Pro)</h4>\n'
            '<ol class="steps">\n'
            '  <li>Open the PDF in <strong>Adobe Acrobat Pro</strong></li>\n'
            '  <li>Go to <strong>All Tools &rarr; Accessibility &rarr; Reading Order</strong></li>\n'
            '  <li>Click <strong>Show page content groups</strong></li>\n'
            '  <li>Numbered grey boxes appear — each number is the order a screen reader reads that content</li>\n'
            '  <li>Verify the sequence matches the intended logical reading order</li>\n'
            '  <li>Pay special attention to: form labels before fields, multi-column text, and headers/footers</li>\n'
            '</ol>\n')

    if ppt_files:
        lines.append(
            '<h4>How to Verify — PowerPoint</h4>\n'
            '<ol class="steps">\n'
            '  <li>Open in <strong>PowerPoint</strong> (desktop app)</li>\n'
            '  <li>Go to <strong>Home &rarr; Arrange &rarr; Selection Pane</strong></li>\n'
            '  <li>The <strong>bottom item</strong> in the list is read <strong>FIRST</strong> by AT</li>\n'
            '  <li>Slide title placeholder must be at the <strong>bottom</strong> of the list</li>\n'
            '  <li>Drag items to reorder as needed</li>\n'
            '</ol>\n')

    # ── Colour Contrast ──
    color_files = _unique_files_for_rule(by_rule, "XLSX.COLOR.ONLY")
    lines.append(
        '<hr>\n<h3>Colour Contrast and Colour-Only Information</h3>\n'
        '<p><strong>Priority: High</strong> — affects low-vision and colour-blind users</p>\n'
        '<p>Automated tools cannot detect all contrast failures or situations where '
        'colour is the only way to convey information (WCAG 1.4.1, 1.4.3).</p>\n'
        '<p><strong>What to check:</strong></p>\n<ul>\n'
        '  <li>All text has a contrast ratio of at least <strong>4.5:1</strong> against its background '
        '(3:1 for large text)</li>\n'
        '  <li>Information is not conveyed by colour alone</li>\n'
        '  <li>Charts and graphs use patterns or labels in addition to colours</li>\n'
        '</ul>\n'
        '<p><strong>Online tool:</strong> <a href="https://webaim.org/resources/contrastchecker/">'
        'WebAIM Contrast Checker</a></p>\n'
        f'<p><strong>Reference:</strong> {_wcag_html("1.4.1")} | {_wcag_html("1.4.3")}</p>\n')

    if color_files:
        lines.append(
            '<div class="callout callout-warn">\n'
            f'<div class="callout-title">Automated check flagged colour-only use in: '
            f'{_h(", ".join(color_files))}</div>\n'
            'These files use cell fill colour to differentiate data without a text or symbol alternative.\n'
            '</div>\n')

    # ── PDF Accessibility Checker ──
    if pdf_files:
        lines.append(
            '<hr>\n<h3>Run the Built-in PDF Accessibility Checker</h3>\n'
            '<p><strong>Priority: Required before distributing any PDF</strong></p>\n'
            '<ol class="steps">\n'
            '  <li>Open the PDF in <strong>Adobe Acrobat Pro</strong></li>\n'
            '  <li>Go to <strong>All Tools &rarr; Accessibility</strong></li>\n'
            '  <li>Select <strong>Accessibility Check</strong></li>\n'
            '  <li>Click <strong>Start Checking</strong></li>\n'
            '  <li>Expand each category in the results panel</li>\n'
            '  <li>Right-click flagged items to fix or view guidance</li>\n'
            '</ol>\n')

    lines.append('</section>\n')
    return "".join(lines)


def _render_additional_improvements(by_rule: dict, audit: dict) -> str:
    total = audit["summary"]["total_files"]
    items = []

    pdf_files = [f for f in audit.get("files", []) if f["type"] == "pdf"]
    if pdf_files:
        items.append(
            '<h3>Optional: Add Bookmarks to Longer PDF Documents</h3>\n'
            '<ol class="steps">\n'
            '  <li>View &rarr; Show/Hide &rarr; Navigation Panes &rarr; Bookmarks</li>\n'
            '  <li>Options menu &rarr; <strong>New Bookmarks from Structure</strong></li>\n'
            '  <li>Confirm the bookmark hierarchy looks correct</li>\n'
            '  <li>Save As</li>\n</ol>\n'
            f'<p><strong>Reference:</strong> {_wcag_html("2.4.5")} | {_ref_html("acrobat_a11y")}</p>\n')

    ppt_notes = _unique_files_for_rule(by_rule, "PPTX.SLIDE.NOTES")
    if ppt_notes:
        n = len(ppt_notes)
        items.append(
            f'<h3>Add Speaker Notes to PowerPoint Slides ({n} of {total} files)</h3>\n'
            '<p>Slides without speaker notes may be missing context. '
            'Add notes that describe what is on each slide.</p>\n'
            '<p><strong>PowerPoint:</strong> View &rarr; Notes to open the Notes pane.</p>\n')

    pdfua = _unique_files_for_rule(by_rule, "PDFQ.METADATA.PDFUA")
    if pdfua:
        items.append(
            '<h3>Optional: Add PDF/UA Conformance Identifier</h3>\n'
            '<p>Only needed for formal compliance documentation (government publishing, Section 508 procurement).</p>\n'
            '<ol class="steps">\n'
            '  <li>All Tools &rarr; Accessibility &rarr; Run Accessibility Check</li>\n'
            '  <li>Look for the <strong>Add PDF/UA Identifier</strong> option</li>\n'
            '  <li>If unavailable, use PAC 2024 (PDF Accessibility Checker)</li>\n</ol>\n')

    heading_files = sorted(set(
        _unique_files_for_rule(by_rule, "DOCX-STRUCT.HEADINGS") +
        _unique_files_for_rule(by_rule, "DOCX-STRUCT.HEADINGSKIP") +
        _unique_files_for_rule(by_rule, "PDFBP.HEADING.SKIP")))
    if heading_files:
        n = len(heading_files)
        has_word = bool(_unique_files_for_rule(by_rule, "DOCX-STRUCT.HEADINGS") +
                        _unique_files_for_rule(by_rule, "DOCX-STRUCT.HEADINGSKIP"))
        has_pdf = bool(_unique_files_for_rule(by_rule, "PDFBP.HEADING.SKIP"))
        heading_parts = [
            f'<h3>Improve Heading Structure ({n} of {total} files)</h3>\n'
            '<p>Heading levels should not skip (e.g. Heading 1 directly to Heading 3).</p>\n'
        ]
        if has_word:
            heading_parts.append(
                '<p><strong>Word:</strong> Use the Styles pane to apply headings sequentially. '
                'Use View &rarr; Navigation Pane to see your heading structure at a glance.</p>\n')
        if has_pdf:
            heading_parts.append(
                '<p><strong>PDF:</strong> Review the Tags panel to ensure '
                '<code>&lt;H1&gt;</code>, <code>&lt;H2&gt;</code>, <code>&lt;H3&gt;</code> '
                'levels are sequential.</p>\n')
        heading_parts.append(
            f'<p><strong>Reference:</strong> {_wcag_html("1.3.1")}</p>\n')
        items.append("".join(heading_parts))

    sheet_files = _unique_files_for_rule(by_rule, "XLSX.NAV.SHEET_NAMES")
    if sheet_files:
        n = len(sheet_files)
        items.append(
            f'<h3>Rename Default Sheet Tabs in Excel ({n} of {total} files)</h3>\n'
            '<p>Generic names like <em>Sheet1</em> give no context to screen reader users. '
            'Double-click each sheet tab and enter a descriptive name.</p>\n')

    link_files = sorted(set(
        _unique_files_for_rule(by_rule, "DOCX-LINK.DESCRIPTIVE") +
        _unique_files_for_rule(by_rule, "PPTX.LINKS.TEXT") +
        _unique_files_for_rule(by_rule, "XLSX.LINKS.TEXT")))
    if link_files:
        n = len(link_files)
        items.append(
            f'<h3>Improve Hyperlink Text ({n} of {total} files)</h3>\n'
            '<p>Replace vague link text like "click here" or raw URLs with descriptive text '
            'that says where the link goes.</p>\n'
            f'<p><strong>Reference:</strong> {_wcag_html("2.4.4")} | {_ref_html("webaim_links")}</p>\n')

    if not items:
        return ""

    return (
        '<section id="improvements">\n'
        '<h2>4. Additional Improvements</h2>\n'
        + "\n<hr>\n".join(items)
        + '</section>\n'
    )


def _render_summary_table(by_rule: dict, audit: dict, all_f: list) -> str:
    total = audit["summary"]["total_files"]
    seen = set()
    rows = []
    sev_order = {"Error": 0, "Warning": 1, "Info": 2}
    # Pre-compute file counts for sort stability
    rule_file_count = {rule: len(_unique_files_for_rule(by_rule, rule)) for rule in by_rule}

    for fn in sorted(all_f, key=lambda x: (sev_order.get(x.get("severity", "Info"), 99), -rule_file_count.get(x.get("rule", ""), 0), x.get("rule", ""))):
        rule = fn.get("rule", "")
        if rule in seen:
            continue
        seen.add(rule)
        ref = RULE_REFERENCE.get(rule, {})
        desc = ref[4] if ref else fn.get("message", rule)[:80]
        sev = fn.get("severity", "Info")
        affected = _unique_files_for_rule(by_rule, rule)
        rows.append(f'<tr><td>{_pill(sev)}</td><td>{_h(desc)}</td>'
                     f'<td>{len(affected)} of {total}</td></tr>\n')

    if not rows:
        return ""

    return (
        '<section id="summary-table">\n'
        '<h2>5. Summary of Findings</h2>\n'
        '<table>\n<thead><tr><th>Severity</th><th>Issue</th><th>Affected Files</th></tr></thead>\n'
        '<tbody>\n' + "".join(rows) + '</tbody></table>\n'
        '</section>\n'
    )


def _render_per_file_table(audit: dict) -> str:
    lines = [
        '<section id="file-table">\n'
        '<h2>6. Per-Document Summary</h2>\n'
        '<table>\n<thead><tr><th>#</th><th>File</th><th>Type</th><th>Score</th>'
        '<th>Grade</th><th>Errors</th><th>Warnings</th></tr></thead>\n<tbody>\n'
    ]
    ext_map = {"pdf": "PDF", "docx": "Word", "xlsx": "Excel", "pptx": "PowerPoint",
                "epub": "ePub", "md": "Markdown"}
    for i, fe in enumerate(audit.get("files", []), 1):
        fname = fe["file"]
        ftype = ext_map.get(fe.get("type", ""), fe.get("type", ""))
        score = fe["score"]
        grade = fe["grade"]
        findings = fe.get("findings", [])
        errs = sum(1 for f in findings if f.get("severity") == "Error")
        warns = sum(1 for f in findings if f.get("severity") == "Warning")
        lines.append(
            f'<tr><td>{i}</td><td>{_h(fname)}</td><td>{_h(ftype)}</td>'
            f'<td><strong>{score}</strong></td><td>{_badge(grade)}</td>'
            f'<td>{errs}</td><td>{warns}</td></tr>\n')

    # Overall row
    s = audit["summary"]
    lines.append(
        f'<tr style="background:#f0fdf4;font-weight:700">'
        f'<td colspan="3">Overall Average</td>'
        f'<td><strong>{s["score"]}</strong></td><td>{_badge(s["grade"])}</td>'
        f'<td colspan="2">{s["errors"]} errors, {s["warnings"]} warnings</td></tr>\n')

    lines.append('</tbody></table>\n')
    lines.append('<p class="muted">Scoring: 90-100 = A, 80-89 = B, 70-79 = C, 60-69 = D, 0-59 = F</p>\n')
    lines.append('</section>\n')
    return "".join(lines)


def _render_priority_plan(by_rule: dict, audit: dict, all_f: list) -> str:
    total = audit["summary"]["total_files"]
    errors = sorted({fn["rule"] for fn in all_f if fn.get("severity") == "Error"},
                     key=lambda r: (-len(_unique_files_for_rule(by_rule, r)), r))
    warnings = sorted({fn["rule"] for fn in all_f if fn.get("severity") == "Warning"},
                       key=lambda r: (-len(_unique_files_for_rule(by_rule, r)), r))
    infos = sorted({fn["rule"] for fn in all_f if fn.get("severity") == "Info"},
                    key=lambda r: (-len(_unique_files_for_rule(by_rule, r)), r))

    lines = ['<section id="priority-plan">\n<h2>7. Priority Action Plan</h2>\n']

    if errors:
        lines.append('<h3>High Priority — Fix Before Distribution</h3>\n<ul>\n')
        for rule in errors:
            ref = RULE_REFERENCE.get(rule, {})
            desc = ref[4] if ref else rule
            n = len(_unique_files_for_rule(by_rule, rule))
            lines.append(f'  <li>{_pill("Error")} {_h(desc)} ({n} of {total} files)</li>\n')
        lines.append('  <li><strong>Run Accessibility Check on all files (required before publishing)</strong></li>\n')
        lines.append('</ul>\n')

    if warnings:
        lines.append('<h3>Medium Priority — Fix Soon</h3>\n<ul>\n')
        for rule in warnings:
            ref = RULE_REFERENCE.get(rule, {})
            desc = ref[4] if ref else rule
            n = len(_unique_files_for_rule(by_rule, rule))
            lines.append(f'  <li>{_pill("Warning")} {_h(desc)} ({n} of {total} files)</li>\n')
        lines.append('</ul>\n')

    types = _present_types(audit)
    ro_parts = []
    if "pdf" in types:
        ro_parts.append("PDF: Acrobat Reading Order tool")
    if "pptx" in types:
        ro_parts.append("PPT: Selection Pane")
    ro_detail = f' ({_h("; ".join(ro_parts))})' if ro_parts else ''
    lines.append(
        '<h3>Manual Review Required</h3>\n<ul>\n'
        f'  <li><strong>Verify reading order</strong> in all files{ro_detail}</li>\n'
        '  <li><strong>Check colour contrast</strong> for all body text and charts</li>\n'
        '  <li><strong>Test with a screen reader</strong> (NVDA or JAWS) before final distribution</li>\n'
        '</ul>\n')

    if infos:
        lines.append('<h3>Optional / Compliance Only</h3>\n<ul>\n')
        for rule in infos:
            ref = RULE_REFERENCE.get(rule, {})
            desc = ref[4] if ref else rule
            n = len(_unique_files_for_rule(by_rule, rule))
            lines.append(f'  <li>{_pill("Info")} {_h(desc)} ({n} of {total} files)</li>\n')
        lines.append('</ul>\n')

    lines.append('</section>\n')
    return "".join(lines)


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

    li = "\n".join(f'  <li>{_h(item)}</li>' for item in items)
    return (
        '<section id="whats-working">\n'
        '<h2>8. What\'s Already Working Well</h2>\n'
        '<div class="callout callout-good">\n'
        '<h3 class="callout-title">Strengths</h3>\n'
        f'<ul>\n{li}\n</ul>\n'
        '</div>\n'
        '</section>\n'
    )


def _render_time_estimate(by_rule: dict, audit: dict) -> str:
    total = audit["summary"]["total_files"]
    rows = []

    lang_files = set(
        _unique_files_for_rule(by_rule, "PDFUA.METADATA.LANG") +
        _unique_files_for_rule(by_rule, "DOCX-META.LANG"))
    if lang_files:
        n = len(lang_files)
        rows.append(f'<tr><td>Fix language settings</td><td>{n} x 2 min = ~{n*2} minutes</td></tr>\n')

    title_files = set(
        _unique_files_for_rule(by_rule, "PDFUA.METADATA.TITLE") +
        _unique_files_for_rule(by_rule, "DOCX-META.TITLE") +
        _unique_files_for_rule(by_rule, "PPTX.META.TITLE") +
        _unique_files_for_rule(by_rule, "XLSX.META.TITLE"))
    if title_files:
        n = len(title_files)
        rows.append(f'<tr><td>Add document titles</td><td>{n} x 3 min = ~{n*3} minutes</td></tr>\n')

    tu_files = _unique_files_for_rule(by_rule, "PDFUA.FORM.TU")
    if tu_files:
        n = len(tu_files)
        rows.append(f'<tr><td>Fix form field labels</td><td>{n} file(s) = ~10-20 minutes</td></tr>\n')

    slide_files = _unique_files_for_rule(by_rule, "PPTX.SLIDE.TITLE")
    if slide_files:
        n = len(slide_files)
        rows.append(f'<tr><td>Add slide titles</td><td>{n} file(s) = ~5-10 minutes</td></tr>\n')

    rows.append(f'<tr><td>Manual reading order review</td><td>All {total} files, ~10 min each</td></tr>\n')
    rows.append(f'<tr><td>Run accessibility checks</td><td>All {total} files, ~5 min each</td></tr>\n')

    return (
        '<section id="time-estimate">\n'
        '<h2>9. Estimated Time to Resolve Issues</h2>\n'
        '<table>\n<thead><tr><th>Task</th><th>Estimate</th></tr></thead>\n<tbody>\n'
        + "".join(rows) + '</tbody></table>\n'
        '</section>\n'
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
                   "all documents can reach a high level of accessibility.")
    elif grade == "C":
        status = "Adequate foundation, moderate fixes required"
        effort = "Moderate"
        outlook = "Addressing the errors and warnings listed above will bring the documents to a strong level of accessibility."
    else:
        status = "Significant barriers found — remediation needed before publishing"
        effort = "High"
        outlook = "The issues found should be resolved before these documents are distributed to the public."

    return (
        '<section id="final-assessment">\n'
        '<h2>10. Final Assessment</h2>\n'
        '<table>\n'
        f'<tr><th>Overall Grade</th><td>{_badge(grade)}</td></tr>\n'
        f'<tr><th>Score</th><td>{score}/100</td></tr>\n'
        f'<tr><th>Status</th><td>{_h(status)}</td></tr>\n'
        f'<tr><th>Remediation Effort</th><td>{_h(effort)}</td></tr>\n'
        '</table>\n'
        f'<p>{_h(outlook)}</p>\n'
        '<p class="muted"><em>Based on: WCAG 2.1 AA, PDF/UA (ISO 14289-1), '
        'Matterhorn Protocol, Section 508, and WebAIM best practices.</em></p>\n'
        '</section>\n'
    )


# ---------------------------------------------------------------------------
# Remediation Results (optional — present only after fix-verify cycle)
# ---------------------------------------------------------------------------

def _render_remediation_results(audit: dict) -> str:
    """Render remediation results section if fix data is present."""
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

    total_fixed = sum(e["resolved"] for e in files)
    total_remaining = sum(e["remaining"] for e in files)
    total_human = sum(e["needs_human"] for e in files)

    lines = [
        '<section id="remediation-results">\n',
        '<h2>Remediation Results</h2>\n',
        f'<p>Automated fixes (Tier {remediation.get("max_tier", 1)}) were applied '
        f'to {len(files)} file(s) via the scan-fix-verify loop.</p>\n',
        '<table>\n<thead><tr>'
        '<th>Document</th><th>Before</th><th>After</th><th>Change</th>'
        '<th>Fixed</th><th>Remaining</th><th>Needs Human</th>'
        '</tr></thead>\n<tbody>\n',
    ]

    for entry in files:
        fname = _h(entry["file"])
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

        human_str = f'<strong>{needs_human}</strong>' if needs_human > 0 else "0"
        lines.append(
            f'<tr><td>{fname}</td><td>{before} ({_h(entry["grade_before"])})</td>'
            f'<td>{after} ({_h(entry["grade_after"])})</td>'
            f'<td>{change_str}</td><td>{fixed}</td><td>{remaining}</td>'
            f'<td>{human_str}</td></tr>\n'
        )

    lines.append('</tbody></table>\n')
    lines.append(
        f'<p><strong>Totals</strong>: {total_fixed} issues fixed, '
        f'{total_remaining} remaining, {total_human} need human review</p>\n'
    )

    if remediation.get("score_improvement", 0) > 0:
        lines.append(
            f'<p class="success"><strong>Score improvement</strong>: Average score went from '
            f'{remediation["before_avg_score"]} to {remediation["after_avg_score"]} '
            f'(+{remediation["score_improvement"]} points)</p>\n'
        )

    # Per-file fix details
    for entry in files:
        fixes = entry.get("fixes", [])
        if not fixes:
            continue
        fname = _h(entry["file"])
        lines.append(f'<h3>{fname}</h3>\n<ul>\n')
        for fix in fixes:
            status = fix.get("status", "?")
            rule = _h(fix.get("rule", "?"))
            detail = _h(fix.get("detail", fix.get("reason", "")))
            icon = {"fixed": "+", "skipped": "-", "failed": "X",
                    "needs-human": "?", "unknown": "??"}.get(status, "?")
            lines.append(f'<li>[{icon}] <strong>{rule}</strong> ({_h(status)}): {detail}</li>\n')
        lines.append('</ul>\n')

    lines.append('</section>\n')
    return "".join(lines)


# ---------------------------------------------------------------------------
# Alt text analysis renderer (used in Appendix A per-file sections)
# ---------------------------------------------------------------------------

def _score_grade(score: int) -> str:
    """Return CSS class suffix for a score."""
    if score >= 90: return "a"
    if score >= 80: return "b"
    if score >= 70: return "c"
    if score >= 60: return "d"
    return "f"


def _render_alt_text_analysis(fe: dict) -> str:
    """Render the alt text analysis accordion for a single file entry."""
    ata = fe.get("alt_text_analysis")
    if not ata or not ata.get("images"):
        return ""

    images = ata["images"]
    models_used = ata.get("models_used", [])
    model_label = ", ".join(m.split("/")[-1] for m in models_used) if models_used else "unknown"

    lines = [
        '    <details class="drill-down">\n'
        f'    <summary>Alt Text Analysis -- {len(images)} image(s), '
        f'{len(models_used)} model(s) ({_h(model_label)})</summary>\n'
        '    <div class="drill-body alt-analysis">\n'
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

        lines.append(
            f'      <div class="alt-image-card">\n'
            f'        <div class="alt-image-header">\n'
            f'          <span>{_h(location)}{_h(page_label)}</span>\n'
        )

        # Show existing score badge in header if available
        if existing_score:
            sc = existing_score["score"]
            g = _score_grade(sc)
            lines.append(
                f'          <span class="alt-score-badge alt-score-{g}">{sc}</span>\n')
        lines.append('        </div>\n')

        # Existing alt text
        if existing is not None:
            lines.append('        <div class="alt-section-label">Current alt text</div>\n')
            lines.append('        <div class="alt-option">\n')
            lines.append('          <div class="alt-option-header">\n')
            if existing_score:
                sc = existing_score["score"]
                g = _score_grade(sc)
                lines.append(
                    f'            <span class="alt-score-badge alt-score-{g}">{sc}</span>\n')
            lines.append(f'            <span class="alt-model">(existing)</span>\n')
            lines.append('          </div>\n')
            lines.append(
                f'          <div class="alt-text-content">{_h(existing if existing else "(empty)")}</div>\n')
            if existing_score and existing_score.get("flags"):
                lines.append('          <div class="alt-flags">\n')
                for flag in existing_score["flags"]:
                    fc = flag.get("severity", "info")
                    lines.append(
                        f'            <span class="alt-flag alt-flag-{fc}">'
                        f'{_h(flag["message"])}</span>\n')
                lines.append('          </div>\n')
            lines.append('        </div>\n')
        else:
            lines.append(
                '        <div class="alt-section-label">No existing alt text</div>\n')

        # Model alternatives
        if alternatives:
            lines.append('        <div class="alt-section-label">Generated alternatives</div>\n')
            for alt in alternatives:
                sc = alt["score"]
                g = _score_grade(sc)
                model_short = alt.get("model", "").split("/")[-1]
                rank = alt.get("rank", 0)
                rank_label = f"#{rank}" if rank else ""
                lines.append('        <div class="alt-option">\n')
                lines.append('          <div class="alt-option-header">\n')
                lines.append(
                    f'            <span class="alt-score-badge alt-score-{g}">{sc}</span>\n'
                    f'            <span class="alt-model">{_h(model_short)}</span>\n'
                    f'            <span class="alt-rank">{_h(rank_label)}</span>\n')
                lines.append('          </div>\n')
                lines.append(
                    f'          <div class="alt-text-content">{_h(alt.get("text", ""))}</div>\n')
                if alt.get("flags"):
                    lines.append('          <div class="alt-flags">\n')
                    for flag in alt["flags"]:
                        fc = flag.get("severity", "info")
                        lines.append(
                            f'            <span class="alt-flag alt-flag-{fc}">'
                            f'{_h(flag["message"])}</span>\n')
                    lines.append('          </div>\n')
                lines.append('        </div>\n')

        # Recommendation
        if recommendation:
            lines.append(
                f'        <div class="alt-recommendation">{_h(recommendation)}</div>\n')

        lines.append('      </div>\n')

    lines.append('    </div>\n    </details>\n')
    return "".join(lines)


# ---------------------------------------------------------------------------
# Technical Appendices
# ---------------------------------------------------------------------------

def _render_appendix_a(audit: dict) -> str:
    sev_order = {"Error": 0, "Warning": 1, "Info": 2}
    lines = [
        '<section id="appendix-a">\n'
        '<h2>Appendix A — Per-File Finding Inventory</h2>\n'
        '<p>Complete list of every finding for every file scanned.</p>\n'
    ]

    for fe in audit.get("files", []):
        fname = fe["file"]
        score = fe["score"]
        grade = fe["grade"]
        findings = sorted(
            fe.get("findings", []),
            key=lambda x: (sev_order.get(x.get("severity", "Info"), 99), x.get("rule", "")))

        lines.append(
            '<div class="file-section">\n'
            '  <div class="file-header">\n'
            f'    <h3 class="file-name">{_h(fname)}</h3>\n'
            f'    <span>{_badge(grade)} {score}/100</span>\n'
            '  </div>\n'
            '  <div class="file-body">\n')

        rem = fe.get("remediation", {})
        if rem.get("applied"):
            fixed_name = rem.get("fixed_file", "")
            fixed_part = f" (<code>{_h(fixed_name)}</code>)" if fixed_name else ""
            lines.append(
                '    <div class="callout callout-ok">\n'
                '    <div class="callout-title">Automated remediation applied</div>\n'
                f'    <p>A fixed copy is available{fixed_part}. '
                f'Cross-check the fixed file against the original to verify all changes. '
                f'See <a href="#remediation-results">Remediation Results</a> for before/after scoring.</p>\n'
                '    </div>\n')

        if not findings:
            lines.append('    <p><em>No findings — all checks passed.</em></p>\n')
        else:
            lines.append(
                '    <table>\n'
                '    <thead><tr><th>Severity</th><th>Rule</th><th>Issue</th><th>Fix</th></tr></thead>\n'
                '    <tbody>\n')
            for fn in findings:
                sev = fn.get("severity", "Info")
                rule = fn.get("rule", "")
                msg = fn.get("message", "")
                fix = fn.get("fix", "")
                lines.append(
                    f'    <tr><td>{_pill(sev)}</td><td><code>{_h(rule)}</code></td>'
                    f'<td>{_h(msg)}</td><td>{_h(fix)}</td></tr>\n')
            lines.append('    </tbody></table>\n')

            # Reading order outcomes
            ro_fn = [f for f in findings if f.get("rule", "") in READING_ORDER_RULES and f.get("outcome")]
            if ro_fn:
                lines.append('    <div class="callout callout-warn">\n'
                             '    <div class="callout-title">Reading order — screen reader user impact</div>\n')
                for fn in ro_fn:
                    lines.append(f'    <p><code>{_h(fn.get("rule", ""))}</code>: {_h(fn.get("outcome", ""))}</p>\n')
                lines.append('    </div>\n')

        # Alt text analysis accordion (if data available for this file)
        alt_html = _render_alt_text_analysis(fe)
        if alt_html:
            lines.append(alt_html)

        lines.append('  </div>\n</div>\n')

    lines.append('</section>\n')
    return "".join(lines)


def _render_appendix_b(all_f: list) -> str:
    seen = set()
    rows = []
    sev_order = {"Error": 0, "Warning": 1, "Info": 2}

    all_rules = sorted(
        {fn.get("rule", "") for fn in all_f if fn.get("rule")},
        key=lambda r: (sev_order.get(
            RULE_REFERENCE.get(r, ("", "", "Info"))[2], 99), r))

    for rule in all_rules:
        if rule in seen:
            continue
        seen.add(rule)
        ref = RULE_REFERENCE.get(rule, ("—", "—", "—", "—", rule))
        standard, wcag, sev, matterhorn, desc = ref
        wcag_cell = _wcag_html(wcag.replace("WCAG ", "")) if wcag.startswith("WCAG ") else _h(wcag)
        rows.append(
            f'<tr><td><code>{_h(rule)}</code></td><td>{_pill(sev)}</td>'
            f'<td>{wcag_cell}</td><td>{_h(matterhorn)}</td>'
            f'<td>{_h(standard)}</td><td>{_h(desc)}</td></tr>\n')

    if not rows:
        return ""

    return (
        '<section id="appendix-b">\n'
        '<h2>Appendix B — Rule Reference</h2>\n'
        '<table>\n<thead><tr><th>Rule ID</th><th>Severity</th><th>WCAG</th>'
        '<th>Matterhorn</th><th>Standard</th><th>Description</th></tr></thead>\n'
        '<tbody>\n' + "".join(rows) + '</tbody></table>\n'
        '</section>\n'
    )


def _render_appendix_c(audit: dict) -> str:
    types = _present_types(audit)

    # Always included
    rows = [
        '<tr><td><a href="https://www.w3.org/TR/WCAG22/">WCAG 2.2 AA</a></td>'
        '<td>Web Content Accessibility Guidelines — the international baseline</td>'
        '<td><a href="https://www.w3.org/TR/WCAG22/">w3.org</a></td></tr>',
        '<tr><td><a href="https://www.section508.gov/">Section 508</a></td>'
        '<td>US federal accessibility requirements for electronic documents</td>'
        '<td><a href="https://www.section508.gov/">section508.gov</a></td></tr>',
        '<tr><td><a href="https://webaim.org/">WebAIM</a></td>'
        '<td>Practical accessibility guidance and evaluation resources</td>'
        '<td><a href="https://webaim.org/">webaim.org</a></td></tr>',
        '<tr><td><a href="https://www.etsi.org/deliver/etsi_en/301500_302000/301549/">EN 301 549</a></td>'
        '<td>European accessibility standard referencing WCAG 2.2</td>'
        '<td><a href="https://www.etsi.org/deliver/etsi_en/301500_302000/301549/">etsi.org</a></td></tr>',
    ]

    # PDF-specific
    if "pdf" in types:
        rows.extend([
            '<tr><td><a href="https://www.iso.org/standard/64599.html">PDF/UA (ISO 14289-1)</a></td>'
            '<td>Universal Accessibility standard for PDF documents</td>'
            '<td><a href="https://www.iso.org/standard/64599.html">iso.org</a></td></tr>',
            '<tr><td><a href="https://pdfa.org/resource/pdfua-in-a-nutshell/">PDF/UA in a Nutshell</a></td>'
            '<td>Free overview of PDF/UA requirements (PDF Association)</td>'
            '<td><a href="https://pdfa.org/resource/pdfua-in-a-nutshell/">pdfa.org</a></td></tr>',
            '<tr><td><a href="https://pdfa.org/resource/the-matterhorn-protocol/">Matterhorn Protocol</a></td>'
            '<td>136 failure conditions for PDF/UA conformance testing</td>'
            '<td><a href="https://pdfa.org/resource/the-matterhorn-protocol/">pdfa.org</a></td></tr>',
            '<tr><td><a href="https://www.w3.org/WAI/WCAG22/Techniques/#pdf">WCAG Techniques for PDF</a></td>'
            '<td>W3C technique documents for PDF accessibility</td>'
            '<td><a href="https://www.w3.org/WAI/WCAG22/Techniques/#pdf">w3.org</a></td></tr>',
        ])

    # Office-specific (DOCX, XLSX, PPTX)
    if types & {"docx", "xlsx", "pptx"}:
        rows.append(
            '<tr><td><a href="https://support.microsoft.com/en-us/office/make-your-content-accessible-to-everyone-ecab0fcf-d143-4fe8-a2ff-6cd596bddc6d">Microsoft Office Accessibility</a></td>'
            '<td>Microsoft&#x27;s guide to creating accessible Office documents</td>'
            '<td><a href="https://support.microsoft.com/en-us/office/make-your-content-accessible-to-everyone-ecab0fcf-d143-4fe8-a2ff-6cd596bddc6d">support.microsoft.com</a></td></tr>'
        )
    if "docx" in types:
        rows.append(
            '<tr><td><a href="https://support.microsoft.com/en-us/office/make-your-word-documents-accessible-to-people-with-disabilities-d9bf3683-87ac-47ea-b91a-78dcacb3c66d">Accessible Word Documents</a></td>'
            '<td>Create accessible Word documents (Microsoft)</td>'
            '<td><a href="https://support.microsoft.com/en-us/office/make-your-word-documents-accessible-to-people-with-disabilities-d9bf3683-87ac-47ea-b91a-78dcacb3c66d">support.microsoft.com</a></td></tr>'
        )
    if "xlsx" in types:
        rows.append(
            '<tr><td><a href="https://support.microsoft.com/en-us/office/make-your-excel-documents-accessible-to-people-with-disabilities-6cc05fc5-1314-48b5-8eb3-683e49b3e593">Accessible Excel Workbooks</a></td>'
            '<td>Create accessible Excel workbooks (Microsoft)</td>'
            '<td><a href="https://support.microsoft.com/en-us/office/make-your-excel-documents-accessible-to-people-with-disabilities-6cc05fc5-1314-48b5-8eb3-683e49b3e593">support.microsoft.com</a></td></tr>'
        )
    if "pptx" in types:
        rows.append(
            '<tr><td><a href="https://support.microsoft.com/en-us/office/make-your-powerpoint-presentations-accessible-to-people-with-disabilities-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25">Accessible PowerPoint Presentations</a></td>'
            '<td>Create accessible PowerPoint presentations (Microsoft)</td>'
            '<td><a href="https://support.microsoft.com/en-us/office/make-your-powerpoint-presentations-accessible-to-people-with-disabilities-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25">support.microsoft.com</a></td></tr>'
        )

    # EPUB-specific
    if "epub" in types:
        rows.extend([
            '<tr><td><a href="https://www.w3.org/TR/epub-a11y-11/">EPUB Accessibility 1.1</a></td>'
            '<td>W3C accessibility requirements for EPUB publications</td>'
            '<td><a href="https://www.w3.org/TR/epub-a11y-11/">w3.org</a></td></tr>',
            '<tr><td><a href="https://www.w3.org/TR/epub-a11y-tech-11/">EPUB Accessibility Techniques 1.1</a></td>'
            '<td>Techniques for meeting EPUB Accessibility requirements</td>'
            '<td><a href="https://www.w3.org/TR/epub-a11y-tech-11/">w3.org</a></td></tr>',
        ])

    # Markdown-specific
    if "md" in types:
        rows.append(
            '<tr><td><a href="https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md">markdownlint Rules</a></td>'
            '<td>Markdown linting rules including accessibility-relevant checks</td>'
            '<td><a href="https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md">github.com</a></td></tr>'
        )

    return (
        '<section id="appendix-c">\n'
        '<h2>Appendix C \u2014 Standards and References</h2>\n'
        '<table>\n<thead><tr><th>Standard</th><th>Description</th><th>Link</th></tr></thead>\n'
        '<tbody>\n'
        + '\n'.join(rows) + '\n'
        '</tbody></table>\n'
        '</section>\n'
    )


def _render_appendix_d(audit: dict) -> str:
    """Appendix D — Tool versions and methodology (format-conditional)."""
    types = _present_types(audit)

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
        tool_rows.append(f'<tr><td>{_h("pikepdf")}</td><td>{_h(pikepdf_ver)}</td><td>PDF tag tree, form fields, content stream analysis</td></tr>\n')
        tool_rows.append(f'<tr><td>{_h("pypdf")}</td><td>{_h(pypdf_ver)}</td><td>Widget annotation orphan detection</td></tr>\n')
    if "xlsx" in types:
        try:
            import openpyxl
            openpyxl_ver = openpyxl.__version__
        except Exception:
            openpyxl_ver = "not installed"
        tool_rows.append(f'<tr><td>{_h("openpyxl")}</td><td>{_h(openpyxl_ver)}</td><td>Excel workbook accessibility scanning</td></tr>\n')
    if "pptx" in types:
        try:
            import pptx
            pptx_ver = pptx.__version__
        except Exception:
            pptx_ver = "not installed"
        tool_rows.append(f'<tr><td>{_h("python-pptx")}</td><td>{_h(pptx_ver)}</td><td>PowerPoint accessibility and reading order scanning</td></tr>\n')
    if "docx" in types:
        try:
            import docx
            docx_ver = getattr(docx, "__version__", "installed")
        except Exception:
            docx_ver = "not installed"
        tool_rows.append(f'<tr><td>{_h("python-docx")}</td><td>{_h(docx_ver)}</td><td>Word document accessibility scanning</td></tr>\n')

    rows_html = "".join(tool_rows)

    # Methodology items — only describe formats present
    method_items = []
    if "pdf" in types:
        method_items.append('  <li><strong>PDF:</strong> Tag tree structure, AcroForm fields, metadata, content stream MCID sequences</li>\n')
    if "docx" in types:
        method_items.append('  <li><strong>Word (.docx):</strong> OOXML paragraph styles, image inline elements, table XML, hyperlink runs</li>\n')
    if "xlsx" in types:
        method_items.append('  <li><strong>Excel (.xlsx):</strong> Workbook properties, sheet management, Table objects, cell fill detection</li>\n')
    if "pptx" in types:
        method_items.append('  <li><strong>PowerPoint (.pptx):</strong> Slide XML shape order (= AT reading order), placeholder types, alt text XML</li>\n')

    # Limitations — only mention relevant ones
    limit_items = []
    if "pdf" in types:
        limit_items.append('  <li>PDF reading order analysis is heuristic — false positives are possible for complex layouts</li>\n')
    limit_items.append('  <li>Colour contrast is not analysed (requires pixel-level image rendering)</li>\n')
    if "pdf" in types:
        limit_items.append('  <li>Scanned image PDFs (no real text) may not be detected as untagged if they use OCR layers</li>\n')
    if "docx" in types or "xlsx" in types:
        limit_items.append('  <li>Complex table structures in Word and Excel may not be fully characterized</li>\n')
    limit_items.append('  <li>All reading order findings require manual human verification</li>\n')

    return (
        '<section id="appendix-d">\n'
        '<h2>Appendix D — Tool Versions and Methodology</h2>\n'
        '<h3>Scanner Versions</h3>\n'
        '<table>\n<thead><tr><th>Tool</th><th>Version</th><th>Purpose</th></tr></thead>\n'
        f'<tbody>\n{rows_html}</tbody></table>\n'
        '<h3>Methodology</h3>\n'
        '<p>This report was generated by static analysis of document structure — '
        'no browser rendering or screen reader emulation is performed. The scanners inspect:</p>\n'
        '<ul>\n' + "".join(method_items) + '</ul>\n'
        '<h3>Limitations</h3>\n'
        '<ul>\n' + "".join(limit_items) + '</ul>\n'
        '</section>\n'
    )


def _render_appendix_e(audit: dict) -> str:
    """Appendix E — Glossary (format-conditional)."""
    types = _present_types(audit)

    # Core terms always included
    terms = [
        ("Alt text", "A text description of an image, read aloud by screen readers in place of the image"),
        ("AT", "Assistive Technology — screen readers, Braille displays, switch controls"),
        ("BCP 47", "The IETF language tag standard (e.g. en-US, es, fr-CA)"),
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

    # Sort alphabetically
    terms.sort(key=lambda t: t[0].lower())

    rows = "".join(
        f'<tr><td><strong>{_h(t)}</strong></td><td>{_h(d)}</td></tr>\n'
        for t, d in terms
    )
    return (
        '<section id="appendix-e">\n'
        '<h2>Appendix E — Glossary</h2>\n'
        '<table>\n<thead><tr><th>Term</th><th>Definition</th></tr></thead>\n'
        f'<tbody>\n{rows}</tbody></table>\n'
        '</section>\n'
    )


# ---------------------------------------------------------------------------
# Main report builder
# ---------------------------------------------------------------------------

def generate_report(audit: dict) -> str:
    all_f = _all_findings(audit)
    by_rule = _findings_by_rule(all_f)

    # Build section list for TOC
    toc_items = [
        ("exec-summary", "Executive Summary"),
        ("quick-fixes", "Start Here: Quick Fixes"),
        ("manual-review", "Manual Review Required"),
        ("improvements", "Additional Improvements"),
        ("summary-table", "Summary of Findings"),
        ("file-table", "Per-Document Summary"),
        ("priority-plan", "Priority Action Plan"),
        ("whats-working", "What's Already Working Well"),
        ("time-estimate", "Estimated Time to Resolve"),
        ("final-assessment", "Final Assessment"),
    ]

    # Conditionally add remediation results to TOC if present
    if audit.get("remediation"):
        toc_items.append(("remediation-results", "Remediation Results"))

    toc_items.extend([
        ("appendix-a", "Appendix A — Per-File Finding Inventory"),
        ("appendix-b", "Appendix B — Rule Reference"),
        ("appendix-c", "Appendix C — Standards and References"),
        ("appendix-d", "Appendix D — Tool Versions and Methodology"),
        ("appendix-e", "Appendix E — Glossary"),
    ])

    parts = [
        _render_html_head(audit),
        _render_banner(audit),
        _render_score_cards(audit, all_f),
        _render_toc(toc_items),
        _render_executive_summary(audit, by_rule, all_f),
        _render_quick_fixes(by_rule, audit),
        _render_manual_review(by_rule, audit, all_f),
        _render_additional_improvements(by_rule, audit),
        _render_summary_table(by_rule, audit, all_f),
        _render_per_file_table(audit),
        _render_priority_plan(by_rule, audit, all_f),
        _render_whats_working(all_f, audit),
        _render_time_estimate(by_rule, audit),
        _render_final_assessment(audit),
        _render_remediation_results(audit),
        '<hr>\n<h2 id="technical-appendices">Technical Appendices</h2>\n'
        '<p class="muted">The sections below are for technical reviewers, accessibility auditors, '
        'and anyone who needs to understand the detailed methodology and complete findings.</p>\n<hr>\n',
        _render_appendix_a(audit),
        _render_appendix_b(all_f),
        _render_appendix_c(audit),
        _render_appendix_d(audit),
        _render_appendix_e(audit),
        '\n<hr>\n<p class="muted"><em>Report generated by the Document Accessibility Audit Toolkit.</em></p>\n',
        '</body>\n</html>\n',
    ]

    return "".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate an HTML accessibility audit report from scan_results.json"
    )
    parser.add_argument("results", help="Path to scan_results.json from scan_all.py")
    parser.add_argument(
        "--output", default="ACCESSIBILITY-AUDIT.html",
        help="Output HTML file (default: ACCESSIBILITY-AUDIT.html)"
    )
    args = parser.parse_args()

    results_path = Path(args.results)
    if not results_path.exists():
        sys.exit(f"ERROR: File not found: {results_path}")

    audit = json.loads(results_path.read_text(encoding="utf-8"))
    report = generate_report(audit)

    out = Path(args.output)
    out.write_text(report, encoding="utf-8")
    print(f"HTML report written to: {out}")


if __name__ == "__main__":
    main()
