"""
fix_tiers.py — Automation Tier Classification for Fix Tools
============================================================
Maps scanner rule IDs to their automation capability tier:

  Tier 1 — SAFE TO AUTOMATE
      Metadata and structural flags that the toolkit can apply with
      high confidence and no content judgment required.
      Run with ``--fix`` and the toolkit applies these automatically.

  Tier 2 — ASSISTED (needs human review)
      The toolkit can start the fix (e.g. set first-row-as-header,
      insert placeholder alt text) but the result must be reviewed.
      A human must verify the output is correct.

  Tier 3 — MANUAL ONLY
      Requires content understanding or a specialised tool like
      Adobe Acrobat Pro. The toolkit cannot safely attempt these.

Each entry maps a scanner rule ID to:
  - tier:   1, 2, or 3
  - tool:   which fix_*.py module handles it (None for Tier 3)
  - label:  short human-readable tier label
  - note:   one-line explanation of what the tool does / why it's manual

Used by report_md.py, report_html.py, and scan_all.py.

This file is PERMANENT — do not delete.
"""

# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------

TIER_LABELS = {
    1: "Automated Fix Available",
    2: "Assisted Fix (Review Required)",
    3: "Manual Fix Required",
}

TIER_EMOJI = {
    1: "\U0001f7e2",   # green circle
    2: "\U0001f7e1",   # yellow circle
    3: "\U0001f7e0",   # orange circle
}

TIER_CSS_CLASS = {
    1: "badge-auto",
    2: "badge-assisted",
    3: "badge-manual",
}


# ---------------------------------------------------------------------------
# Rule → Tier mapping
# ---------------------------------------------------------------------------

FIX_TIERS: dict[str, dict] = {
    # ═══════════════════════════════════════════════════════════════════════
    # PDF  (fix_pdf.py)
    # ═══════════════════════════════════════════════════════════════════════
    "PDFUA.METADATA.TITLE": {
        "tier": 1, "tool": "fix_pdf",
        "note": "Sets the document title in PDF metadata.",
    },
    "PDFUA.METADATA.DISPLAY_TITLE": {
        "tier": 1, "tool": "fix_pdf",
        "note": "Enables DisplayDocTitle in ViewerPreferences.",
    },
    "PDFBP.DISPLAY.DOCTITLE": {
        "tier": 1, "tool": "fix_pdf",
        "note": "Enables DisplayDocTitle in ViewerPreferences.",
    },
    "PDFUA.METADATA.LANG": {
        "tier": 1, "tool": "fix_pdf",
        "note": "Sets the document language in the catalog.",
    },
    "PDFUA.NAV.TAB_ORDER": {
        "tier": 1, "tool": "fix_pdf",
        "note": "Sets page tab order to follow document structure.",
    },
    "PDFBP.NAV.TABORDER": {
        "tier": 1, "tool": "fix_pdf",
        "note": "Sets page tab order to follow document structure.",
    },
    "PDFUA.METADATA.PDFUA_ID": {
        "tier": 1, "tool": "fix_pdf",
        "note": "Adds the PDF/UA conformance identifier.",
    },
    "PDFQ.METADATA.PDFUA": {
        "tier": 1, "tool": "fix_pdf",
        "note": "Adds the PDF/UA conformance identifier.",
    },
    "PDFUA.STRUCTURE.MARKED": {
        "tier": 1, "tool": "fix_pdf",
        "note": "Sets the Marked flag in the MarkInfo dictionary.",
    },
    "PDFUA.FORM.TU": {
        "tier": 2, "tool": "fix_pdf",
        "note": "Copies field name to tooltip — review for clarity.",
    },
    "PDFUA.TABLE.HEADERS": {
        "tier": 3, "tool": None,
        "note": "Requires manual tagging of header cells in Acrobat Pro.",
    },
    "PDFBP.HEADING.SKIP": {
        "tier": 3, "tool": None,
        "note": "Heading level repair requires understanding document structure.",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Word  (fix_word.py)
    # ═══════════════════════════════════════════════════════════════════════
    "DOCX-META.TITLE": {
        "tier": 1, "tool": "fix_word",
        "note": "Sets the document title in core properties.",
    },
    "DOCX-META.LANG": {
        "tier": 1, "tool": "fix_word",
        "note": "Sets the document language.",
    },
    "DOCX-META.AUTHOR": {
        "tier": 1, "tool": "fix_word",
        "note": "Sets the author in core properties.",
    },
    "DOCX-TABLE.HEADERS": {
        "tier": 2, "tool": "fix_word",
        "note": "Marks first row as header — verify it is actually the header.",
    },
    "DOCX-IMG.ALT": {
        "tier": 3, "tool": None,
        "note": "Alt text requires describing image content — cannot be automated.",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Excel  (fix_excel.py)
    # ═══════════════════════════════════════════════════════════════════════
    "XLSX.META.TITLE": {
        "tier": 1, "tool": "fix_excel",
        "note": "Sets the workbook title in core properties.",
    },
    # Alias: XLSX-META.TITLE maps to same fix as XLSX.META.TITLE
    "XLSX-META.TITLE": {
        "tier": 1, "tool": "fix_excel",
        "note": "Alias for XLSX.META.TITLE — sets workbook title.",
    },
    "XLSX.META.AUTHOR": {
        "tier": 1, "tool": "fix_excel",
        "note": "Sets the author in core properties.",
    },
    # Alias: XLSX-META.AUTHOR maps to same fix as XLSX.META.AUTHOR
    "XLSX-META.AUTHOR": {
        "tier": 1, "tool": "fix_excel",
        "note": "Alias for XLSX.META.AUTHOR — sets workbook author.",
    },
    "XLSX-SHEET.NAME": {
        "tier": 3, "tool": None,
        "note": "Sheet names require human judgment for meaningful labels.",
    },
    "XLSX-TABLE.PRINT_TITLES": {
        "tier": 2, "tool": "fix_excel",
        "note": "Sets print titles to row 1 — verify it is the header row.",
    },
    "XLSX.TABLE.HEADER": {
        "tier": 2, "tool": "fix_excel",
        "note": "Sets print titles to row 1 — verify it is the header row.",
    },
    "XLSX-IMG.ALT": {
        "tier": 3, "tool": None,
        "note": "Alt text requires describing image content — cannot be automated.",
    },
    "XLSX.IMG.ALT": {
        "tier": 3, "tool": None,
        "note": "Alt text requires describing image content — cannot be automated.",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # PowerPoint  (fix_pptx.py)
    # ═══════════════════════════════════════════════════════════════════════
    "PPTX.META.TITLE": {
        "tier": 1, "tool": "fix_pptx",
        "note": "Sets the presentation title in core properties.",
    },
    # Alias: PPTX-META.TITLE maps to same fix as PPTX.META.TITLE
    "PPTX-META.TITLE": {
        "tier": 1, "tool": "fix_pptx",
        "note": "Alias for PPTX.META.TITLE — sets presentation title.",
    },
    "PPTX.META.AUTHOR": {
        "tier": 1, "tool": "fix_pptx",
        "note": "Sets the author in core properties.",
    },
    # Alias: PPTX-META.AUTHOR maps to same fix as PPTX.META.AUTHOR
    "PPTX-META.AUTHOR": {
        "tier": 1, "tool": "fix_pptx",
        "note": "Alias for PPTX.META.AUTHOR — sets presentation author.",
    },
    "PPTX-SLIDE.TITLE": {
        "tier": 2, "tool": "fix_pptx",
        "note": "Adds placeholder titles — you must write the actual titles.",
    },
    "PPTX.SLIDE.TITLE": {
        "tier": 2, "tool": "fix_pptx",
        "note": "Adds placeholder titles — you must write the actual titles.",
    },
    "PPTX-SLIDE.TITLE_UNIQUE": {
        "tier": 2, "tool": "fix_pptx",
        "note": "Appends numbers to duplicate titles — review for meaningfulness.",
    },
    "PPTX-IMG.ALT": {
        "tier": 3, "tool": None,
        "note": "Alt text requires describing image content — cannot be automated.",
    },
    "PPTX.IMG.ALT": {
        "tier": 3, "tool": None,
        "note": "Alt text requires describing image content — cannot be automated.",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # ePub  (fix_epub.py)
    # ═══════════════════════════════════════════════════════════════════════
    "EPUB-E001": {
        "tier": 1, "tool": "fix_epub",
        "note": "Sets the title in OPF metadata.",
    },
    "EPUB-E003": {
        "tier": 1, "tool": "fix_epub",
        "note": "Sets the language in OPF metadata.",
    },
    "EPUB-T002": {
        "tier": 1, "tool": "fix_epub",
        "note": "Sets the author in OPF metadata.",
    },
    "EPUB-E006": {
        "tier": 1, "tool": "fix_epub",
        "note": "Removes duplicate spine entries.",
    },
    "EPUB-E007": {
        "tier": 1, "tool": "fix_epub",
        "note": "Adds accessibility metadata to OPF.",
    },
    "EPUB-E004": {
        "tier": 2, "tool": "fix_epub",
        "note": "Generates a navigation document — review for completeness.",
    },
    "EPUB-E005": {
        "tier": 3, "tool": None,
        "note": "Alt text requires describing image content — cannot be automated.",
    },
    "EPUB-E009": {
        "tier": 3, "tool": None,
        "note": "Alt text requires describing image content — cannot be automated.",
    },
    "EPUB-W003": {
        "tier": 2, "tool": "fix_epub",
        "note": "Repairs heading hierarchy — review the result.",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_tier(rule_id: str) -> dict | None:
    """Return the tier info for a rule, or None if not classified."""
    return FIX_TIERS.get(rule_id)


# ---------------------------------------------------------------------------
# Dynamic tier upgrade for alt text rules
# ---------------------------------------------------------------------------

# Rules eligible for Tier 3 → Tier 2 upgrade when alt-text-generator is available
_ALT_TEXT_RULES = frozenset({
    "DOCX-IMG.ALT",
    "XLSX-IMG.ALT", "XLSX.IMG.ALT",
    "PPTX-IMG.ALT", "PPTX.IMG.ALT",
    "EPUB-E005", "EPUB-E009",
    "PDFUA.IMG.ALT",
})


def _is_alt_text_generator_available() -> bool:
    """Check whether the alt-text-generator package is importable."""
    try:
        from alt_text.client import generate_for_image  # noqa: F401
        from alt_text.auth import get_github_token
        get_github_token()
        return True
    except Exception:
        return False


def get_effective_tier(rule_id: str) -> dict | None:
    """Return the tier info with dynamic upgrade if alt-text-generator available.

    Alt text rules (Tier 3) are upgraded to Tier 2 when the alt-text-generator
    package is installed and a GitHub token is available.
    """
    base = FIX_TIERS.get(rule_id)
    if base is None:
        return None

    if rule_id in _ALT_TEXT_RULES and base["tier"] == 3:
        if _is_alt_text_generator_available():
            return {
                **base,
                "tier": 2,
                "tool": base.get("tool") or _rule_to_tool(rule_id),
                "note": "LLM-generated alt text (review required) — via alt-text-generator.",
            }

    return base


def _rule_to_tool(rule_id: str) -> str | None:
    """Infer the fix tool module from a rule ID prefix."""
    if rule_id.startswith("DOCX"):
        return "fix_word"
    if rule_id.startswith("XLSX"):
        return "fix_excel"
    if rule_id.startswith("PPTX"):
        return "fix_pptx"
    if rule_id.startswith("PDF"):
        return "fix_pdf"
    if rule_id.startswith("EPUB"):
        return "fix_epub"
    return None


# Scanner → fixer rule ID mapping (only entries where they differ)
_SCANNER_TO_FIXER: dict[str, str] = {
    "PDFBP.DISPLAY.DOCTITLE": "PDFUA.METADATA.DISPLAY_TITLE",
    "PDFBP.NAV.TABORDER":    "PDFUA.NAV.TAB_ORDER",
    "PDFQ.METADATA.PDFUA":   "PDFUA.METADATA.PDFUA_ID",
    "XLSX.META.TITLE":        "XLSX-META.TITLE",
    "XLSX.META.AUTHOR":       "XLSX-META.AUTHOR",
    "XLSX.TABLE.HEADER":      "XLSX-TABLE.PRINT_TITLES",
    "XLSX.IMG.ALT":           "XLSX-IMG.ALT",
    "PPTX.META.TITLE":        "PPTX-META.TITLE",
    "PPTX.META.AUTHOR":       "PPTX-META.AUTHOR",
    "PPTX.SLIDE.TITLE":       "PPTX-SLIDE.TITLE",
    "PPTX.IMG.ALT":            "PPTX-IMG.ALT",
    "EPUB-E009":               "EPUB-E005",
}

# Which fixer tool handles each file type
_TYPE_TO_TOOL: dict[str, str] = {
    "pdf":  "fix_pdf",
    "docx": "fix_word",
    "xlsx": "fix_excel",
    "pptx": "fix_pptx",
    "epub": "fix_epub",
}


def to_fixer_id(scanner_rule: str) -> str:
    """Convert a scanner rule ID to the fixer's rule ID."""
    return _SCANNER_TO_FIXER.get(scanner_rule, scanner_rule)


def get_fixable_rules(findings: list[dict], file_type: str,
                      max_tier: int = 1) -> list[str]:
    """Return fixer rule IDs from findings that are automatable up to *max_tier*.

    Args:
        findings: List of finding dicts from a scanner (each has a "rule" key).
        file_type: File type string ("pdf", "docx", "xlsx", "pptx", "epub").
        max_tier: Maximum tier to include (1 = safe only, 2 = safe + assisted).

    Returns:
        De-duplicated list of fixer rule IDs suitable for passing to the fix tool.
    """
    tool_name = _TYPE_TO_TOOL.get(file_type)
    if not tool_name:
        return []

    fixer_rules: list[str] = []
    seen: set[str] = set()
    for f in findings:
        scanner_id = f.get("rule", "")
        info = FIX_TIERS.get(scanner_id)
        if not info:
            continue
        if info["tier"] > max_tier:
            continue
        if info["tool"] != tool_name:
            continue
        fixer_id = to_fixer_id(scanner_id)
        if fixer_id not in seen:
            seen.add(fixer_id)
            fixer_rules.append(fixer_id)
    return fixer_rules


def tier_for_fix_block(rule_ids: list[str]) -> int:
    """Return the best (lowest) tier across a set of rules in a fix block.

    If any rule in the block has Tier 1, the block gets the green badge
    because at least some files can be auto-fixed. Returns 0 if no rules
    are classified.
    """
    tiers = [FIX_TIERS[r]["tier"] for r in rule_ids if r in FIX_TIERS]
    return min(tiers) if tiers else 0


def rules_by_tier(rule_ids: list[str]) -> dict[int, list[str]]:
    """Group a list of rule IDs by their automation tier."""
    grouped: dict[int, list[str]] = {1: [], 2: [], 3: []}
    for r in rule_ids:
        info = FIX_TIERS.get(r)
        if info:
            grouped[info["tier"]].append(r)
    return grouped


def automation_summary_md(rule_ids: list[str],
                         affected_count: int = 0,
                         total_count: int = 0,
                         remediation_applied: bool = False) -> str:
    """Return a Markdown automation-capability callout for a fix block.

    Shows which rules can be auto-fixed, assisted, or need manual work.
    When *affected_count* and *total_count* are provided, includes the
    count in the badge text.  When *remediation_applied* is True, Tier 1
    text reflects that fixes have already been applied.
    """
    grouped = rules_by_tier(rule_ids)
    t1 = grouped.get(1, [])
    t2 = grouped.get(2, [])
    t3 = grouped.get(3, [])

    count_str = ""
    if affected_count and total_count:
        count_str = f" Affects {affected_count} of {total_count} files."

    lines = []
    if t1:
        rules_str = ", ".join(f"`{r}`" for r in t1)
        if remediation_applied:
            lines.append(
                f"> {TIER_EMOJI[1]} **Automated Fixes Applied** — "
                f"Remediation has been run.{count_str} "
                f"Human verification is required — cross-check fixed files against originals for accuracy. "
                f"See [Remediation Results](#remediation-results) for before/after details. "
                f"Covers: {rules_str}")
        else:
            lines.append(
                f"> {TIER_EMOJI[1]} **Automated Fix Available** — "
                f"Run `scan_all.py --fix` to apply.{count_str} "
                f"Always verify automated fixes for accuracy. "
                f"Covers: {rules_str}")
    if t2:
        rules_str = ", ".join(f"`{r}`" for r in t2)
        lines.append(
            f"> {TIER_EMOJI[2]} **Assisted Fix (Review Required)** — "
            f"The toolkit can start this fix but you must review the result.{count_str} "
            f"Covers: {rules_str}")
    if t3:
        rules_str = ", ".join(f"`{r}`" for r in t3)
        lines.append(
            f"> {TIER_EMOJI[3]} **Manual Fix Required** — "
            f"This needs your judgment and the appropriate application.{count_str} "
            f"Covers: {rules_str}")
    return "\n>\n".join(lines) + "\n" if lines else ""


def automation_summary_html(rule_ids: list[str],
                           affected_count: int = 0,
                           total_count: int = 0,
                           remediation_applied: bool = False) -> str:
    """Return HTML automation-capability badges for a fix block."""
    grouped = rules_by_tier(rule_ids)
    t1 = grouped.get(1, [])
    t2 = grouped.get(2, [])
    t3 = grouped.get(3, [])

    count_str = ""
    if affected_count and total_count:
        count_str = f" Affects {affected_count} of {total_count} files."

    parts = []
    if t1:
        rules_str = ", ".join(f"<code>{r}</code>" for r in t1)
        if remediation_applied:
            parts.append(
                f'<div class="automation-badge {TIER_CSS_CLASS[1]}">'
                f'{TIER_EMOJI[1]} <strong>Automated Fixes Applied</strong> &mdash; '
                f'Remediation has been run.{count_str} '
                f'Human verification is required &mdash; cross-check fixed files against originals for accuracy. '
                f'See <a href="#remediation-results">Remediation Results</a> for before/after details. '
                f'Covers: {rules_str}</div>')
        else:
            parts.append(
                f'<div class="automation-badge {TIER_CSS_CLASS[1]}">'
                f'{TIER_EMOJI[1]} <strong>Automated Fix Available</strong> &mdash; '
                f'Run <code>scan_all.py --fix</code> to apply.{count_str} '
                f'Always verify automated fixes for accuracy. '
                f'Covers: {rules_str}</div>')
    if t2:
        rules_str = ", ".join(f"<code>{r}</code>" for r in t2)
        parts.append(
            f'<div class="automation-badge {TIER_CSS_CLASS[2]}">'
            f'{TIER_EMOJI[2]} <strong>Assisted Fix (Review Required)</strong> &mdash; '
            f'The toolkit can start this fix but you must review the result.{count_str} '
            f'Covers: {rules_str}</div>')
    if t3:
        rules_str = ", ".join(f"<code>{r}</code>" for r in t3)
        parts.append(
            f'<div class="automation-badge {TIER_CSS_CLASS[3]}">'
            f'{TIER_EMOJI[3]} <strong>Manual Fix Required</strong> &mdash; '
            f'This needs your judgment and the appropriate application.{count_str} '
            f'Covers: {rules_str}</div>')
    return "\n".join(parts) + "\n" if parts else ""
