"""
mcp_server.py — Document Accessibility MCP Server
===================================================
Exposes the scanning toolkit as Model Context Protocol (MCP) tools
that AI agents (Copilot, Claude, etc.) can call directly.

Tools registered:
  Scanning:
    scan_document        — Scan any supported file, auto-routing by extension
    scan_word            — Scan a Word (.docx) document
    scan_excel           — Scan an Excel (.xlsx) workbook
    scan_powerpoint      — Scan a PowerPoint (.pptx) presentation
    scan_markdown_doc    — Scan a Markdown (.md) file
    scan_epub_document   — Scan an ePub (.epub) document
    scan_pdf_metadata    — Extract PDF metadata and check accessibility
    scan_pdf_tags        — Analyze PDF tag structure
    scan_pdf_forms       — Scan PDF form field accessibility
    scan_pdf_full        — All PDF scanners combined
    scan_folder          — Scan all supported documents in a folder
    list_supported_rules — List all accessibility rules by format
    get_scan_result_json — Raw JSON scan results for processing

  Remediation:
    fix_word_document    — Auto-fix Word accessibility issues
    fix_excel_workbook   — Auto-fix Excel accessibility issues
    fix_powerpoint_pres  — Auto-fix PowerPoint accessibility issues
    fix_pdf_document     — Auto-fix PDF accessibility issues
    fix_epub_document    — Auto-fix ePub accessibility issues
    fix_document         — Auto-fix any file, routing by extension
    verify_fix           — Compare before/after scans to verify fixes

  Alt Text Generation:
    generate_alt_text        — Generate alt text for a single image
    generate_alt_text_batch  — Generate alt text for all images in a document
    list_alt_text_models     — List available vision models
    list_alt_text_profiles   — List available alt text profiles

Transport: stdio (launched by VS Code or other MCP hosts)

Usage:
    python tools/mcp_server.py

This file is PERMANENT — do not delete.
"""

import sys
import json
from pathlib import Path

# Ensure the tools directory is importable
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from mcp.server.fastmcp import FastMCP


# ---------------------------------------------------------------------------
# Path validation helper
# ---------------------------------------------------------------------------

def _validate_file_path(file_path: str) -> Path | None:
    """Validate and resolve a file path, blocking directory traversal."""
    try:
        path = Path(file_path).resolve()
    except (OSError, ValueError):
        return None
    # Block paths containing null bytes or suspicious traversal patterns
    if "\x00" in file_path:
        return None
    return path


def _validate_dir_path(dir_path: str) -> Path | None:
    """Validate and resolve a directory path."""
    try:
        path = Path(dir_path).resolve()
    except (OSError, ValueError):
        return None
    if "\x00" in dir_path:
        return None
    if not path.is_dir():
        return None
    return path

# ---------------------------------------------------------------------------
# Import scanners with graceful degradation
# ---------------------------------------------------------------------------

_scanners = {}

try:
    from scan_metadata import extract_metadata
    _scanners["metadata"] = extract_metadata
except ImportError:
    pass

try:
    from scan_tags import scan_tags as _scan_tags_impl
    _scanners["tags"] = _scan_tags_impl
except ImportError:
    pass

try:
    from scan_forms import scan_forms as _scan_forms_impl
    _scanners["forms"] = _scan_forms_impl
except ImportError:
    pass

try:
    from scan_word import scan_word as _scan_word_impl
    _scanners["word"] = _scan_word_impl
except ImportError:
    pass

try:
    from scan_excel import scan_excel as _scan_excel_impl
    _scanners["excel"] = _scan_excel_impl
except ImportError:
    pass

try:
    from scan_pptx import scan_pptx as _scan_pptx_impl
    _scanners["pptx"] = _scan_pptx_impl
except ImportError:
    pass

try:
    from scan_epub import scan_epub as _scan_epub_impl
    _scanners["epub"] = _scan_epub_impl
except ImportError:
    pass

try:
    from scan_markdown import scan_markdown as _scan_markdown_impl
    _scanners["markdown"] = _scan_markdown_impl
except ImportError:
    pass

try:
    from scan_all import run_audit, _score_file
except ImportError:
    run_audit = None
    _score_file = None

# ---------------------------------------------------------------------------
# Import fixers with graceful degradation
# ---------------------------------------------------------------------------

_fixers = {}

try:
    from fix_word import fix_word as _fix_word_impl
    _fixers["word"] = _fix_word_impl
except ImportError:
    pass

try:
    from fix_excel import fix_excel as _fix_excel_impl
    _fixers["excel"] = _fix_excel_impl
except ImportError:
    pass

try:
    from fix_pptx import fix_pptx as _fix_pptx_impl
    _fixers["pptx"] = _fix_pptx_impl
except ImportError:
    pass

try:
    from fix_pdf import fix_pdf as _fix_pdf_impl
    _fixers["pdf"] = _fix_pdf_impl
except ImportError:
    pass

try:
    from fix_epub import fix_epub as _fix_epub_impl
    _fixers["epub"] = _fix_epub_impl
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Import alt text generator with graceful degradation
# ---------------------------------------------------------------------------

_alt_text_available = False

try:
    from alt_text.client import generate_for_image, generate_for_document, ExtractedImage
    from alt_text.models import VISION_MODELS, validate_models, list_models
    from alt_text.profiles import list_profiles as _list_alt_profiles, resolve_profile
    from alt_text.config import load_config as _load_alt_config, merge_config
    from alt_text.formats import apply_format
    _alt_text_available = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Helper: serialize results for MCP (ensure JSON-safe)
# ---------------------------------------------------------------------------

def _safe_json(obj: object) -> object:
    """Convert scan results to JSON-serializable form."""
    return json.loads(json.dumps(obj, default=str))


def _format_scan_result(result: dict) -> str:
    """Format a scan result dict into readable text for AI consumption."""
    lines = []
    f_name = result.get("file", "unknown")
    findings = result.get("findings", [])
    errors = result.get("errors", [])

    errs = sum(1 for f in findings if f.get("severity") == "Error")
    warns = sum(1 for f in findings if f.get("severity") == "Warning")
    infos = sum(1 for f in findings if f.get("severity") == "Info")

    lines.append(f"## {f_name}")
    lines.append(f"Findings: {errs} errors, {warns} warnings, {infos} info")
    lines.append("")

    if errors:
        lines.append("### Scan Errors")
        for e in errors:
            lines.append(f"- {e}")
        lines.append("")

    for sev in ("Error", "Warning", "Info"):
        sev_findings = [f for f in findings if f.get("severity") == sev]
        if sev_findings:
            icon = {"Error": "X", "Warning": "!", "Info": "i"}[sev]
            lines.append(f"### {sev}s ({len(sev_findings)})")
            for f in sev_findings:
                rule = f.get("rule", "?")
                wcag = f.get("wcag", "")
                msg = f.get("message", "")
                fix = f.get("fix", "")
                wcag_str = f" [WCAG {wcag}]" if wcag else ""
                lines.append(f"- [{icon}] **{rule}**{wcag_str}: {msg}")
                if fix:
                    lines.append(f"  - Fix: {fix}")
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Document Accessibility Scanner",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Tool: scan_document
# ---------------------------------------------------------------------------

@mcp.tool()
def scan_document(file_path: str) -> str:
    """Scan any supported document for accessibility issues.

    Automatically routes to the correct scanner based on file extension.
    Supports: .pdf, .docx, .xlsx, .pptx, .epub, .md

    Args:
        file_path: Absolute path to the document file.

    Returns:
        Formatted accessibility findings with rule IDs, WCAG criteria,
        messages, and fix instructions.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"
    if not path.is_file():
        return f"Error: Not a file: {file_path}"

    ext = path.suffix.lower()

    if ext == ".docx":
        return scan_word(file_path)
    elif ext == ".xlsx":
        return scan_excel(file_path)
    elif ext == ".pptx":
        return scan_powerpoint(file_path)
    elif ext == ".pdf":
        return scan_pdf_full(file_path)
    elif ext == ".epub":
        return scan_epub_document(file_path)
    elif ext == ".md":
        return scan_markdown_doc(file_path)
    else:
        return f"Error: Unsupported file type '{ext}'. Supported: .pdf, .docx, .xlsx, .pptx, .epub, .md"


# ---------------------------------------------------------------------------
# Tool: scan_word
# ---------------------------------------------------------------------------

@mcp.tool()
def scan_word(file_path: str) -> str:
    """Scan a Word (.docx) document for accessibility issues.

    Checks: document title, language, heading structure, heading level skips,
    inline and floating image alt text, table headers, merged cells, nested tables,
    hyperlink text quality, list semantics (manual vs styled), empty paragraphs,
    table of contents, tracked changes, header/footer content, footnotes/endnotes.

    Args:
        file_path: Absolute path to the .docx file.

    Returns:
        Formatted accessibility findings with rule IDs, WCAG criteria, and fixes.
    """
    if "word" not in _scanners:
        return "Error: scan_word.py scanner not available. Ensure python-docx is installed."

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    result = _scanners["word"](path)
    return _format_scan_result(result)


# ---------------------------------------------------------------------------
# Tool: scan_excel
# ---------------------------------------------------------------------------

@mcp.tool()
def scan_excel(file_path: str) -> str:
    """Scan an Excel (.xlsx) workbook for accessibility issues.

    Checks: workbook title, sheet names (generic/duplicate), freeze panes,
    named tables with headers, merged cells, empty spacing rows, hyperlink text,
    color-only information, chart alt text, image alt text, hidden rows/columns/sheets,
    protected sheets, data validation input messages.

    Args:
        file_path: Absolute path to the .xlsx file.

    Returns:
        Formatted accessibility findings with rule IDs, WCAG criteria, and fixes.
    """
    if "excel" not in _scanners:
        return "Error: scan_excel.py scanner not available. Ensure openpyxl is installed."

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    result = _scanners["excel"](path)
    return _format_scan_result(result)


# ---------------------------------------------------------------------------
# Tool: scan_powerpoint
# ---------------------------------------------------------------------------

@mcp.tool()
def scan_powerpoint(file_path: str) -> str:
    """Scan a PowerPoint (.pptx) presentation for accessibility issues.

    Checks: presentation title, language, slide titles (missing/duplicate),
    speaker notes, reading order (title-first, pre-title text, column detection),
    image/chart alt text quality, table headers, embedded media captions,
    section names, hyperlink text, grouped shapes alt text, auto-advance
    transitions, excessive animations.

    Args:
        file_path: Absolute path to the .pptx file.

    Returns:
        Formatted accessibility findings with rule IDs, WCAG criteria, and fixes.
    """
    if "pptx" not in _scanners:
        return "Error: scan_pptx.py scanner not available. Ensure python-pptx is installed."

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    result = _scanners["pptx"](path)
    return _format_scan_result(result)


# ---------------------------------------------------------------------------
# Tool: scan_markdown
# ---------------------------------------------------------------------------

@mcp.tool()
def scan_markdown_doc(file_path: str) -> str:
    """Scan a Markdown (.md) file for accessibility issues.

    Checks: ambiguous link text, bare URL links, download file type disclosure,
    missing/generic image alt text, heading hierarchy (skips, multiple H1, no H1),
    table descriptions and empty header cells, emoji in headings, consecutive emoji,
    Mermaid diagrams and ASCII art without text descriptions.

    Args:
        file_path: Absolute path to the .md file.

    Returns:
        Formatted accessibility findings with rule IDs, WCAG criteria, and fixes.
    """
    if "markdown" not in _scanners:
        return "Error: scan_markdown.py scanner not available."

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    result = _scanners["markdown"](path)
    return _format_scan_result(result)


# ---------------------------------------------------------------------------
# Tool: scan_epub_document
# ---------------------------------------------------------------------------

@mcp.tool()
def scan_epub_document(file_path: str) -> str:
    """Scan an ePub (.epub) document for accessibility issues.

    Checks: document title, unique identifier, language, accessibility metadata,
    navigation document (TOC, page-list, landmarks), spine reading order,
    image alt text, heading hierarchy, table headers, ambiguous link text,
    fixed-layout detection, and best-practice metadata (author, description).

    Args:
        file_path: Absolute path to the .epub file.

    Returns:
        Formatted accessibility findings with rule IDs, WCAG criteria, and fixes.
    """
    if "epub" not in _scanners:
        return "Error: scan_epub.py scanner not available. Ensure lxml is installed."

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    result = _scanners["epub"](path)
    return _format_scan_result(result)


# ---------------------------------------------------------------------------
# Tool: scan_pdf_metadata
# ---------------------------------------------------------------------------

@mcp.tool()
def scan_pdf_metadata(file_path: str) -> str:
    """Extract and check PDF metadata for accessibility compliance.

    Checks: document title, language (catalog and XMP), DisplayDocTitle setting,
    tagged PDF (MarkInfo/Marked), PDF/UA identifier in XMP metadata.

    Args:
        file_path: Absolute path to the .pdf file.

    Returns:
        Metadata values and accessibility findings.
    """
    if "metadata" not in _scanners:
        return "Error: scan_metadata.py scanner not available. Ensure pikepdf is installed."

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    result = _scanners["metadata"](path)
    lines = [f"## PDF Metadata: {path.name}", ""]

    # Show extracted metadata values
    for key in ("title", "language", "tagged", "display_doc_title", "pdfua_identifier"):
        val = result.get(key, "N/A")
        lines.append(f"- **{key}**: {val}")
    lines.append("")

    # Show findings
    findings = result.get("findings", [])
    if findings:
        lines.append(f"### Findings ({len(findings)})")
        for f in findings:
            rule = f.get("rule", "?")
            sev = f.get("severity", "?")
            msg = f.get("message", "")
            fix = f.get("fix", "")
            lines.append(f"- [{sev}] **{rule}**: {msg}")
            if fix:
                lines.append(f"  - Fix: {fix}")
    else:
        lines.append("No metadata issues found.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: scan_pdf_tags
# ---------------------------------------------------------------------------

@mcp.tool()
def scan_pdf_tags(file_path: str) -> str:
    """Analyze PDF tag structure tree for accessibility issues.

    Checks: structure tree presence, form tag placement (inline vs orphaned),
    list continuity and split lists, role map and non-standard tags,
    heading hierarchy and skipped levels, table structure (TH/TD/THead/TBody),
    figure-caption adjacency, reading order (MCID inversion rate).

    Args:
        file_path: Absolute path to the .pdf file.

    Returns:
        Tag structure analysis and accessibility findings.
    """
    if "tags" not in _scanners:
        return "Error: scan_tags.py scanner not available. Ensure pikepdf is installed."

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    result = _scanners["tags"](path)

    lines = [f"## PDF Tag Structure: {path.name}", ""]

    if result.get("struct_tree_present"):
        lines.append("Structure tree: Present")
        tag_counts = result.get("tag_counts", {})
        if tag_counts:
            top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:15]
            lines.append(f"Tag counts (top 15): {dict(top_tags)}")
    else:
        lines.append("Structure tree: **NOT PRESENT** — document has no tags")
    lines.append("")

    findings = result.get("findings", [])
    if findings:
        for f in findings:
            sev = f.get("severity", "?")
            rule = f.get("rule", "?")
            msg = f.get("message", "")
            fix = f.get("fix", "")
            lines.append(f"- [{sev}] **{rule}**: {msg}")
            if fix:
                lines.append(f"  - Fix: {fix}")
    else:
        lines.append("No tag structure issues found.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: scan_pdf_forms
# ---------------------------------------------------------------------------

@mcp.tool()
def scan_pdf_forms(file_path: str) -> str:
    """Scan PDF form fields for accessibility issues.

    Checks: field tooltips (TU), required field labeling, push button tooltips,
    radio group tooltip consistency, structure tree linkage, orphan widgets,
    tab order per page, missing AcroForm.

    Args:
        file_path: Absolute path to the .pdf file.

    Returns:
        Form field analysis and accessibility findings.
    """
    if "forms" not in _scanners:
        return "Error: scan_forms.py scanner not available. Ensure pikepdf is installed."

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    result = _scanners["forms"](path)

    lines = [f"## PDF Form Fields: {path.name}", ""]
    field_count = result.get("field_count", 0)
    lines.append(f"Total form fields: {field_count}")
    lines.append("")

    findings = result.get("findings", [])
    if findings:
        for f in findings:
            sev = f.get("severity", "?")
            rule = f.get("rule", "?")
            msg = f.get("message", "")
            fix = f.get("fix", "")
            lines.append(f"- [{sev}] **{rule}**: {msg}")
            if fix:
                lines.append(f"  - Fix: {fix}")
    else:
        if field_count == 0:
            lines.append("No form fields detected in this PDF.")
        else:
            lines.append("No form accessibility issues found.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: scan_pdf_full
# ---------------------------------------------------------------------------

@mcp.tool()
def scan_pdf_full(file_path: str) -> str:
    """Run all PDF scanners (metadata + tags + forms) on a single PDF file.

    This is the comprehensive PDF scan that combines metadata extraction,
    tag structure analysis, and form field inspection into one result.

    Args:
        file_path: Absolute path to the .pdf file.

    Returns:
        Combined accessibility findings from all PDF scanners.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    lines = [f"# Full PDF Scan: {path.name}", ""]
    total_findings = []

    if "metadata" in _scanners:
        result = _scanners["metadata"](path)
        lines.append("## Metadata")
        for key in ("title", "language", "tagged", "display_doc_title"):
            lines.append(f"- {key}: {result.get(key, 'N/A')}")
        total_findings.extend(result.get("findings", []))
        lines.append("")

    if "tags" in _scanners:
        result = _scanners["tags"](path)
        lines.append("## Tag Structure")
        lines.append(f"- Present: {result.get('struct_tree_present', False)}")
        total_findings.extend(result.get("findings", []))
        lines.append("")

    if "forms" in _scanners:
        result = _scanners["forms"](path)
        lines.append("## Form Fields")
        lines.append(f"- Count: {result.get('field_count', 0)}")
        total_findings.extend(result.get("findings", []))
        lines.append("")

    # Score
    if _score_file and total_findings:
        score, grade = _score_file(total_findings)
        lines.append(f"## Score: {score}/100 (Grade {grade})")
        lines.append("")

    # All findings
    if total_findings:
        errs = sum(1 for f in total_findings if f.get("severity") == "Error")
        warns = sum(1 for f in total_findings if f.get("severity") == "Warning")
        lines.append(f"## Findings ({errs} errors, {warns} warnings)")
        for f in total_findings:
            sev = f.get("severity", "?")
            rule = f.get("rule", "?")
            wcag = f.get("wcag", "")
            msg = f.get("message", "")
            fix = f.get("fix", "")
            wcag_str = f" [WCAG {wcag}]" if wcag else ""
            lines.append(f"- [{sev}] **{rule}**{wcag_str}: {msg}")
            if fix:
                lines.append(f"  - Fix: {fix}")
    else:
        lines.append("No issues found.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: scan_folder
# ---------------------------------------------------------------------------

@mcp.tool()
def scan_folder(folder_path: str, file_types: str = "",
               output_json: str = "") -> str:
    """Scan all supported documents in a folder for accessibility issues.

    Recursively finds .pdf, .docx, .xlsx, .pptx, .epub, and .md files and runs
    the appropriate scanner on each. Returns an aggregate score and grade
    plus per-file summaries. Optionally writes full results to JSON.

    Args:
        folder_path: Absolute path to the folder to scan.
        file_types: Space-separated list of types to scan (e.g. 'pdf',
                    'word excel', 'powerpoint'). Empty string scans all.
        output_json: Optional path to write full JSON results.

    Returns:
        Summary of findings across all documents with scores and grades.
    """
    if run_audit is None:
        return "Error: scan_all.py not available."

    path = Path(folder_path)
    if not path.exists():
        return f"Error: Folder not found: {folder_path}"
    if not path.is_dir():
        return f"Error: Not a directory: {folder_path}"

    type_list = file_types.split() if file_types.strip() else None
    audit = run_audit(path, verbose=False, file_types=type_list)
    if not audit:
        return "No supported files found in the folder."

    # Write JSON if requested
    if output_json:
        out = Path(output_json)
        out.write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")

    # Format summary
    summary = audit.get("summary", {})
    lines = [
        "# Folder Accessibility Audit",
        f"**Path**: {folder_path}",
        f"**Date**: {audit.get('scan_date', 'N/A')}",
        f"**Files scanned**: {summary.get('total_files', 0)}",
        f"**Overall score**: {summary.get('score', 0)}/100 (Grade {summary.get('grade', '?')})",
        f"**Totals**: {summary.get('errors', 0)} errors, "
        f"{summary.get('warnings', 0)} warnings, {summary.get('info', 0)} info",
        "",
        "## By Format",
    ]
    for fmt, count in summary.get("by_type", {}).items():
        if count > 0:
            lines.append(f"- {fmt.upper()}: {count} file(s)")
    lines.append("")

    # Per-file summaries
    lines.append("## Per-File Results")
    for f in audit.get("files", []):
        errs = sum(1 for fi in f.get("findings", []) if fi.get("severity") == "Error")
        warns = sum(1 for fi in f.get("findings", []) if fi.get("severity") == "Warning")
        grade = f.get("grade", "?")
        score = f.get("score", 0)
        skipped = f.get("skipped", False)
        if skipped:
            lines.append(f"- **{f['file']}**: SKIPPED — {f.get('skip_reason', 'unknown')}")
        else:
            lines.append(f"- **{f['file']}**: {score}/100 ({grade}) — {errs} errors, {warns} warnings")

    if output_json:
        lines.append(f"\nFull JSON results written to: {output_json}")

    # Generate final dual-audience reports alongside the JSON
    report_dir = Path(output_json).parent if output_json else path
    try:
        from report_md import generate_report as _gen_md
        md_path = report_dir / "ACCESSIBILITY-AUDIT.md"
        md_path.write_text(_gen_md(audit), encoding="utf-8")
        lines.append(f"\nMarkdown report written to: {md_path}")
    except Exception as exc:
        lines.append(f"\nWarning: Markdown report generation failed: {exc}")
    try:
        from report_html import generate_report as _gen_html
        html_path = report_dir / "ACCESSIBILITY-AUDIT.html"
        html_path.write_text(_gen_html(audit), encoding="utf-8")
        lines.append(f"HTML report written to: {html_path}")
    except Exception as exc:
        lines.append(f"Warning: HTML report generation failed: {exc}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: list_supported_rules
# ---------------------------------------------------------------------------

_RULE_CATALOG = {
    "PDF Metadata": [
        ("PDFUA.METADATA.TITLE", "Error", "2.4.2", "Document title not set"),
        ("PDFUA.METADATA.LANG", "Error", "3.1.1", "Document language not set"),
        ("PDFBP.DISPLAY.DOCTITLE", "Warning", "2.4.2", "DisplayDocTitle not enabled"),
        ("PDFUA.STRUCT.TAGGED", "Error", "1.3.1", "Document not tagged"),
        ("PDFQ.METADATA.PDFUA", "Info", "—", "PDF/UA identifier not present"),
    ],
    "PDF Tags": [
        ("PDFUA.STRUCT.NOTREE", "Error", "1.3.1", "No structure tree root"),
        ("PDFUA.FORM.STRUCT", "Error", "1.3.2", "Form elements orphaned in tag tree"),
        ("PDFBP.LIST.CONTINUATION", "Warning", "1.3.1", "List split across pages"),
        ("PDFBP.STRUCT.NONSTANDARD", "Warning", "1.3.1", "Non-standard tags without role mapping"),
        ("PDFBP.STRUCT.HEADINGSKIP", "Warning", "1.3.1", "Heading level skipped"),
        ("PDFBP.STRUCT.TABLEHEADERS", "Warning", "1.3.1", "Table missing TH elements"),
    ],
    "PDF Forms": [
        ("PDFUA.FORM.TU", "Error", "1.3.1", "Form field missing tooltip"),
        ("PDFBP.FORMS.REQUIRED_LABEL", "Warning", "3.3.2", "Required field not indicated in tooltip"),
        ("PDFBP.FORMS.BUTTON_TOOLTIP", "Warning", "4.1.2", "Push button missing tooltip"),
        ("PDFBP.NAV.TABORDER", "Warning", "2.4.3", "Tab order not set to structure"),
    ],
    "Word (DOCX)": [
        ("DOCX-META.TITLE", "Error", "2.4.2", "Document title not set"),
        ("DOCX-META.LANG", "Error", "3.1.1", "Document language not set"),
        ("DOCX-STRUCT.HEADINGS", "Warning", "1.3.1", "No heading styles used"),
        ("DOCX-STRUCT.HEADINGSKIP", "Warning", "1.3.1", "Heading level skipped"),
        ("DOCX-IMG.ALT", "Error", "1.1.1", "Inline image missing alt text"),
        ("DOCX-IMG.ALT_QUALITY", "Warning", "1.1.1", "Placeholder or generic alt text on image"),
        ("DOCX-IMG.ALT_FLOAT", "Error", "1.1.1", "Floating image missing alt text"),
        ("DOCX-TABLE.HEADERS", "Warning", "1.3.1", "Table missing header row"),
        ("DOCX-TABLE.MERGE", "Warning", "1.3.1", "Merged cells detected"),
        ("DOCX-TABLE.NESTED", "Error", "1.3.1", "Nested table detected"),
        ("DOCX-LINK.DESCRIPTIVE", "Warning", "2.4.4", "Non-descriptive link text"),
        ("DOCX-LIST.SEMANTIC", "Warning", "1.3.1", "Manual lists without list styles"),
        ("DOCX-STRUCT.TOC", "Warning", "2.4.5", "No table of contents in long document"),
        ("DOCX-REVIEW.TRACKED", "Warning", "1.3.1", "Unresolved tracked changes"),
        ("DOCX-STRUCT.EMPTYPARA", "Info", "1.3.1", "Excessive empty paragraphs used for spacing"),
        ("DOCX-STRUCT.HDRFTR", "Info", "1.3.2", "Info-bearing header/footer content"),
        ("DOCX-STRUCT.FOOTNOTES", "Info", "2.4.1", "Heavy footnote/endnote usage"),
    ],
    "Excel (XLSX)": [
        ("XLSX.META.TITLE", "Error", "2.4.2", "Workbook title not set"),
        ("XLSX.NAV.SHEET_NAMES", "Warning", "2.4.6", "Generic sheet names"),
        ("XLSX.NAV.SHEET_DUP", "Warning", "2.4.6", "Duplicate sheet names"),
        ("XLSX.NAV.FREEZE_PANES", "Warning", "1.3.1", "No frozen panes"),
        ("XLSX.TABLE.NAMED", "Warning", "1.3.1", "No named Table objects"),
        ("XLSX.TABLE.HEADER", "Error", "1.3.1", "Table header row disabled"),
        ("XLSX.LAYOUT.MERGED", "Warning", "1.3.2", "Merged cells detected"),
        ("XLSX.LAYOUT.SPACING", "Warning", "1.3.2", "Empty spacing rows"),
        ("XLSX.LINKS.TEXT", "Warning", "2.4.4", "Non-descriptive hyperlink text"),
        ("XLSX.COLOR.ONLY", "Info", "1.4.1", "Color may be sole differentiator"),
        ("XLSX.CHART.ALT", "Error", "1.1.1", "Chart missing alt text"),
        ("XLSX.IMG.ALT", "Error", "1.1.1", "Image missing alt text"),
        ("XLSX.LAYOUT.HIDDEN", "Warning", "1.3.1", "Hidden rows/columns/sheets"),
        ("XLSX.PROTECT.SHEET", "Info", "2.1.1", "Protected sheet"),
        ("XLSX.DATA.VALIDATION", "Warning", "3.3.2", "Data validation without input message"),
    ],
    "PowerPoint (PPTX)": [
        ("PPTX.META.TITLE", "Error", "2.4.2", "Presentation title not set"),
        ("PPTX.META.LANG", "Error", "3.1.1", "Presentation language not set"),
        ("PPTX.SLIDE.TITLE", "Error", "2.4.2", "Slide missing title"),
        ("PPTX.SLIDE.TITLE_DUP", "Warning", "2.4.6", "Duplicate slide titles"),
        ("PPTX.SLIDE.NOTES", "Warning", "—", "Visual slide without speaker notes"),
        ("PPTX.ORDER.TITLE_FIRST", "Warning", "1.3.2", "Title not first in reading order"),
        ("PPTX.ORDER.COLUMNS", "Warning", "1.3.2", "Multi-column layout detected"),
        ("PPTX.ORDER.VERIFY", "Info", "1.3.2", "Reading order manual verification needed"),
        ("PPTX.IMG.ALT", "Error", "1.1.1", "Image/chart missing alt text"),
        ("PPTX.IMG.ALT_QUALITY", "Warning", "1.1.1", "Placeholder or generic alt text on image/chart"),
        ("PPTX.TABLE.HEADER", "Warning", "1.3.1", "Table missing header row"),
        ("PPTX.MEDIA.CAPTIONS", "Warning", "1.2.2", "Media without captions/transcript"),
        ("PPTX.SECTION.NAME", "Warning", "2.4.6", "Generic section name"),
        ("PPTX.SECTION.DUP", "Warning", "2.4.6", "Duplicate section names"),
        ("PPTX.LINKS.TEXT", "Warning", "2.4.4", "Non-descriptive hyperlink text"),
        ("PPTX.GROUP.ALT", "Error", "1.1.1", "Grouped shape missing alt text"),
        ("PPTX.TRANSITION.AUTO", "Warning", "2.2.1", "Auto-advance transition"),
        ("PPTX.ANIM.EXCESSIVE", "Info", "2.3.3", "Excessive animations"),
    ],
    "ePub (EPUB)": [
        ("EPUB-E001", "Error", "2.4.2", "Document title (dc:title) missing"),
        ("EPUB-E002", "Error", "—", "Unique identifier (dc:identifier) missing"),
        ("EPUB-E003", "Error", "3.1.1", "Document language (dc:language) missing"),
        ("EPUB-E004", "Error", "2.4.5", "Table of contents (nav toc / NCX) missing"),
        ("EPUB-E005", "Error", "1.1.1", "Image/SVG/MathML missing alt text"),
        ("EPUB-E006", "Error", "1.3.2", "Spine reading order issue"),
        ("EPUB-E007", "Error", "—", "Accessibility metadata missing"),
        ("EPUB-W001", "Warning", "—", "Navigation page-list absent"),
        ("EPUB-W002", "Warning", "2.4.1", "Navigation landmarks absent"),
        ("EPUB-W003", "Warning", "2.4.6", "Heading level skipped in content"),
        ("EPUB-W004", "Warning", "1.3.1", "Table missing header elements"),
        ("EPUB-W005", "Warning", "2.4.4", "Ambiguous link text"),
        ("EPUB-W006", "Warning", "1.4.1", "Fixed-layout ePub detected"),
        ("EPUB-T001", "Info", "—", "Accessibility summary is brief"),
        ("EPUB-T002", "Info", "—", "Author (dc:creator) missing"),
        ("EPUB-T003", "Info", "—", "Description (dc:description) missing"),
    ],
    "Markdown (MD)": [
        ("MD-A11Y.LINK.AMBIGUOUS", "Error", "2.4.4", "Ambiguous link text"),
        ("MD-A11Y.LINK.BARE_URL", "Warning", "2.4.4", "URL used as link text"),
        ("MD-A11Y.LINK.FILETYPE", "Warning", "2.4.4", "Download link missing file type"),
        ("MD-A11Y.IMG.ALT_MISSING", "Error", "1.1.1", "Image missing alt text"),
        ("MD-A11Y.IMG.ALT_QUALITY", "Warning", "1.1.1", "Generic or filename alt text"),
        ("MD-A11Y.HEADING.MULTIPLE_H1", "Warning", "1.3.1", "Multiple H1 headings"),
        ("MD-A11Y.HEADING.SKIP", "Error", "1.3.1", "Heading level skipped"),
        ("MD-A11Y.HEADING.NO_H1", "Warning", "1.3.1", "No H1 heading in document"),
        ("MD-A11Y.TABLE.NO_DESC", "Warning", "1.3.1", "Table without preceding description"),
        ("MD-A11Y.TABLE.EMPTY_HEADER", "Warning", "1.3.1", "Empty table header cell"),
        ("MD-A11Y.EMOJI.HEADING", "Warning", "1.3.3", "Emoji in heading"),
        ("MD-A11Y.EMOJI.CONSECUTIVE", "Info", "1.3.3", "Consecutive emoji sequence"),
        ("MD-A11Y.DIAGRAM.MERMAID", "Error", "1.1.1", "Mermaid diagram without text description"),
        ("MD-A11Y.DIAGRAM.ASCII", "Warning", "1.1.1", "ASCII diagram without text description"),
    ],
}


@mcp.tool()
def list_supported_rules(format_filter: str = "") -> str:
    """List all accessibility rules supported by the scanning toolkit.

    Returns rule IDs, default severities, WCAG criteria, and descriptions
    organized by document format. Use this to understand what the scanners check.

    Args:
        format_filter: Optional filter — 'pdf', 'docx'/'word', 'xlsx'/'excel',
                       'pptx'/'powerpoint', or empty for all.

    Returns:
        Table of all supported accessibility rules.
    """
    filter_lower = format_filter.lower().strip()
    filter_map = {
        "pdf": ["PDF Metadata", "PDF Tags", "PDF Forms"],
        "docx": ["Word (DOCX)"],
        "word": ["Word (DOCX)"],
        "xlsx": ["Excel (XLSX)"],
        "excel": ["Excel (XLSX)"],
        "pptx": ["PowerPoint (PPTX)"],
        "powerpoint": ["PowerPoint (PPTX)"],
        "epub": ["ePub (EPUB)"],
        "md": ["Markdown (MD)"],
        "markdown": ["Markdown (MD)"],
    }

    categories = filter_map.get(filter_lower, list(_RULE_CATALOG.keys()))

    lines = ["# Supported Accessibility Rules", ""]
    total = 0
    for cat in categories:
        rules = _RULE_CATALOG.get(cat, [])
        if not rules:
            continue
        lines.append(f"## {cat} ({len(rules)} rules)")
        lines.append("")
        lines.append("| Rule ID | Severity | WCAG | Description |")
        lines.append("|---------|----------|------|-------------|")
        for rule_id, severity, wcag, desc in rules:
            lines.append(f"| {rule_id} | {severity} | {wcag} | {desc} |")
            total += 1
        lines.append("")

    lines.append(f"**Total rules**: {total}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_scan_result_json
# ---------------------------------------------------------------------------

@mcp.tool()
def get_scan_result_json(file_path: str) -> str:
    """Get raw JSON scan results for a document (for programmatic processing).

    Returns the complete scanner output as a JSON string including all
    metadata, tag counts, form field details, and findings arrays.

    Args:
        file_path: Absolute path to the document file.

    Returns:
        JSON string with complete scan results.
    """
    path = Path(file_path)
    if not path.exists():
        return json.dumps({"error": f"File not found: {file_path}"})

    ext = path.suffix.lower()
    results = {}

    if ext == ".pdf":
        if "metadata" in _scanners:
            results["metadata"] = _safe_json(_scanners["metadata"](path))
        if "tags" in _scanners:
            results["tags"] = _safe_json(_scanners["tags"](path))
        if "forms" in _scanners:
            results["forms"] = _safe_json(_scanners["forms"](path))
    elif ext == ".docx" and "word" in _scanners:
        results["word"] = _safe_json(_scanners["word"](path))
    elif ext == ".xlsx" and "excel" in _scanners:
        results["excel"] = _safe_json(_scanners["excel"](path))
    elif ext == ".pptx" and "pptx" in _scanners:
        results["pptx"] = _safe_json(_scanners["pptx"](path))
    elif ext == ".epub" and "epub" in _scanners:
        results["epub"] = _safe_json(_scanners["epub"](path))
    else:
        return json.dumps({"error": f"Unsupported or unavailable scanner for: {ext}"})

    # Compute score
    all_findings = []
    for scanner_result in results.values():
        all_findings.extend(scanner_result.get("findings", []))
    if _score_file:
        score, grade = _score_file(all_findings)
        results["score"] = score
        results["grade"] = grade

    return json.dumps(results, indent=2, default=str)


# ---------------------------------------------------------------------------
# Tool: merge_scan_results
# ---------------------------------------------------------------------------

try:
    from merge_results import merge_scan_results as _merge_scan_results
    _HAS_MERGE = True
except ImportError:
    _HAS_MERGE = False


@mcp.tool()
def merge_scan_results(json_paths: str, output_path: str = "",
                       report_name: str = "ACCESSIBILITY-AUDIT",
                       cleanup: bool = False) -> str:
    """Merge multiple scan-result JSON files into one unified audit.

    Use after scanning files individually (e.g. to avoid subfolder recursion
    or to run separate batches).  Produces a merged JSON, and optionally
    generates the Markdown and HTML reports.

    Args:
        json_paths: Comma-separated absolute paths to scan-result JSON files,
                    or a glob pattern (e.g. "documents/temp_*.json").
        output_path: Where to write the merged JSON.  Empty = scan_results.json
                     next to the first input file.
        report_name: Base filename for reports (default: ACCESSIBILITY-AUDIT).
                     E.g. "PDF-ACCESSIBILITY-AUDIT" for PDF-only audits.
        cleanup: If true, delete the input JSON files after a successful merge.

    Returns:
        Summary of the merged audit with overall score and report paths.
    """
    if not _HAS_MERGE:
        return "Error: merge_results.py not available."

    import glob as _glob

    # Resolve input paths — support comma-separated list or single glob
    raw = json_paths.strip()
    if "," in raw:
        items = [Path(p.strip()) for p in raw.split(",") if p.strip()]
    else:
        expanded = _glob.glob(raw)
        items = [Path(p) for p in sorted(expanded)] if expanded else [Path(raw)]

    paths = [p.resolve() for p in items]
    missing = [p for p in paths if not p.exists()]
    if missing:
        return f"Error: File(s) not found: {', '.join(str(m) for m in missing)}"
    if not paths:
        return "Error: No input files resolved."

    audit = _merge_scan_results(paths)
    s = audit["summary"]

    # Write merged JSON
    if output_path:
        out = Path(output_path).resolve()
    else:
        out = paths[0].parent / "scan_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(audit, indent=2, default=str, ensure_ascii=False),
                   encoding="utf-8")

    # Generate reports
    report_dir = out.parent
    lines = [
        f"Merged {len(paths)} file(s) → {s['total_files']} documents",
        f"Overall: {s['score']}/100 Grade {s['grade']} | "
        f"{s['errors']}E {s['warnings']}W {s['info']}I",
        f"Merged JSON: {out}",
    ]

    try:
        from report_md import generate_report as _gen_md
        md_path = report_dir / f"{report_name}.md"
        md_path.write_text(_gen_md(audit), encoding="utf-8")
        lines.append(f"Markdown report: {md_path}")
    except Exception as exc:
        lines.append(f"Warning: Markdown report generation failed: {exc}")

    try:
        from report_html import generate_report as _gen_html
        html_path = report_dir / f"{report_name}.html"
        html_path.write_text(_gen_html(audit), encoding="utf-8")
        lines.append(f"HTML report: {html_path}")
    except Exception as exc:
        lines.append(f"Warning: HTML report generation failed: {exc}")

    alt_count = sum(1 for fe in audit["files"] if fe.get("alt_text_analysis"))
    if alt_count:
        lines.append(f"Files with alt text analysis: {alt_count}/{s['total_files']}")

    if cleanup:
        for p in paths:
            p.unlink()
        lines.append(f"Cleaned up {len(paths)} input file(s)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: fix_word_document
# ---------------------------------------------------------------------------

@mcp.tool()
def fix_word_document(file_path: str, rules: str = "", title: str = "",
                      author: str = "", language: str = "en-US") -> str:
    """Auto-fix accessibility issues in a Word (.docx) document.

    Creates a backup, applies fixes, and saves to <name>-fixed.docx.
    Auto-fixable rules: DOCX-META.TITLE, DOCX-META.LANG, DOCX-META.AUTHOR,
    DOCX-TABLE.HEADERS, DOCX-IMG.ALT.

    Args:
        file_path: Absolute path to the .docx file.
        rules: Comma-separated rule IDs to fix (empty = fix all).
        title: Custom document title. Empty = placeholder.
        author: Custom author name. Empty = placeholder.
        language: BCP 47 language tag. Default: en-US.

    Returns:
        Summary of fixes applied, skipped, and needing human action.
    """
    if "word" not in _fixers:
        return "Error: fix_word.py not available. Ensure python-docx is installed."

    rule_list = [r.strip() for r in rules.split(",") if r.strip()] or None
    result = _fixers["word"](Path(file_path), rules=rule_list, title=title,
                             author=author, lang=language)
    if "error" in result:
        return f"Error: {result['error']}"

    return _format_fix_result(result)


# ---------------------------------------------------------------------------
# Tool: fix_excel_workbook
# ---------------------------------------------------------------------------

@mcp.tool()
def fix_excel_workbook(file_path: str, rules: str = "", title: str = "",
                       author: str = "") -> str:
    """Auto-fix accessibility issues in an Excel (.xlsx) workbook.

    Creates a backup, applies fixes, and saves to <name>-fixed.xlsx.
    Auto-fixable rules: XLSX-META.TITLE, XLSX-META.AUTHOR,
    XLSX-TABLE.PRINT_TITLES, XLSX-IMG.ALT, XLSX-SHEET.NAME (reports only).

    Args:
        file_path: Absolute path to the .xlsx file.
        rules: Comma-separated rule IDs to fix (empty = fix all).
        title: Custom workbook title. Empty = placeholder.
        author: Custom author name. Empty = placeholder.

    Returns:
        Summary of fixes applied, skipped, and needing human action.
    """
    if "excel" not in _fixers:
        return "Error: fix_excel.py not available. Ensure openpyxl is installed."

    rule_list = [r.strip() for r in rules.split(",") if r.strip()] or None
    result = _fixers["excel"](Path(file_path), rules=rule_list, title=title,
                              author=author)
    if "error" in result:
        return f"Error: {result['error']}"

    return _format_fix_result(result)


# ---------------------------------------------------------------------------
# Tool: fix_powerpoint_pres
# ---------------------------------------------------------------------------

@mcp.tool()
def fix_powerpoint_pres(file_path: str, rules: str = "", title: str = "",
                        author: str = "") -> str:
    """Auto-fix accessibility issues in a PowerPoint (.pptx) presentation.

    Creates a backup, applies fixes, and saves to <name>-fixed.pptx.
    Auto-fixable rules: PPTX-META.TITLE, PPTX-META.AUTHOR,
    PPTX-SLIDE.TITLE, PPTX-SLIDE.TITLE_UNIQUE, PPTX-IMG.ALT.

    Args:
        file_path: Absolute path to the .pptx file.
        rules: Comma-separated rule IDs to fix (empty = fix all).
        title: Custom presentation title. Empty = placeholder.
        author: Custom author name. Empty = placeholder.

    Returns:
        Summary of fixes applied, skipped, and needing human action.
    """
    if "pptx" not in _fixers:
        return "Error: fix_pptx.py not available. Ensure python-pptx is installed."

    rule_list = [r.strip() for r in rules.split(",") if r.strip()] or None
    result = _fixers["pptx"](Path(file_path), rules=rule_list, title=title,
                             author=author)
    if "error" in result:
        return f"Error: {result['error']}"

    return _format_fix_result(result)


# ---------------------------------------------------------------------------
# Tool: fix_pdf_document
# ---------------------------------------------------------------------------

@mcp.tool()
def fix_pdf_document(file_path: str, rules: str = "", title: str = "",
                     language: str = "en-US") -> str:
    """Auto-fix accessibility issues in a PDF document.

    Creates a backup, applies fixes, and saves to <name>-fixed.pdf.
    Auto-fixable rules: PDFUA.METADATA.TITLE, PDFUA.METADATA.DISPLAY_TITLE,
    PDFUA.METADATA.LANG, PDFUA.NAV.TAB_ORDER, PDFUA.METADATA.PDFUA_ID,
    PDFUA.STRUCTURE.MARKED.

    Note: Structural fixes (full tagging, reading order, table headers)
    require Adobe Acrobat Pro and cannot be automated via pikepdf.

    Args:
        file_path: Absolute path to the .pdf file.
        rules: Comma-separated rule IDs to fix (empty = fix all).
        title: Custom document title. Empty = placeholder.
        language: BCP 47 language tag. Default: en-US.

    Returns:
        Summary of fixes applied, skipped, and needing human action.
    """
    if "pdf" not in _fixers:
        return "Error: fix_pdf.py not available. Ensure pikepdf is installed."

    rule_list = [r.strip() for r in rules.split(",") if r.strip()] or None
    result = _fixers["pdf"](Path(file_path), rules=rule_list, title=title,
                            lang=language)
    if "error" in result:
        return f"Error: {result['error']}"

    return _format_fix_result(result)


# ---------------------------------------------------------------------------
# Tool: fix_epub_document
# ---------------------------------------------------------------------------

@mcp.tool()
def fix_epub_document(file_path: str, rules: str = "", title: str = "",
                      language: str = "en") -> str:
    """Auto-fix accessibility issues in an ePub (.epub) document.

    Creates a backup, applies fixes, and saves to <name>-fixed.epub.
    Auto-fixable rules: EPUB-E001 (title), EPUB-E003 (language),
    EPUB-E007 (accessibility metadata), EPUB-E005 (alt text placeholder),
    EPUB-T002 (author).

    Note: Navigation structure (EPUB-E004), spine reordering (EPUB-E006),
    and heading fixes (EPUB-W003) require manual editing.

    Args:
        file_path: Absolute path to the .epub file.
        rules: Comma-separated rule IDs to fix (empty = fix all).
        title: Custom document title. Empty = placeholder.
        language: BCP 47 language tag. Default: en.

    Returns:
        Summary of fixes applied, skipped, and needing human action.
    """
    if "epub" not in _fixers:
        return "Error: fix_epub.py not available. Ensure lxml is installed."

    rule_list = [r.strip() for r in rules.split(",") if r.strip()] or None
    result = _fixers["epub"](Path(file_path), rules=rule_list, title=title,
                             lang=language)
    if "error" in result:
        return f"Error: {result['error']}"

    return _format_fix_result(result)


# ---------------------------------------------------------------------------
# Tool: fix_document
# ---------------------------------------------------------------------------

@mcp.tool()
def fix_document(file_path: str, rules: str = "", title: str = "",
                 author: str = "", language: str = "en-US") -> str:
    """Auto-fix accessibility issues in any supported document.

    Automatically routes to the correct fixer based on file extension.
    Supports: .pdf, .docx, .xlsx, .pptx, .epub

    Args:
        file_path: Absolute path to the document file.
        rules: Comma-separated rule IDs to fix (empty = fix all).
        title: Custom document title. Empty = placeholder.
        author: Custom author name. Empty = placeholder.
        language: BCP 47 language tag. Default: en-US.

    Returns:
        Summary of fixes applied, skipped, and needing human action.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    ext = path.suffix.lower()
    if ext == ".docx":
        return fix_word_document(file_path, rules, title, author, language)
    elif ext == ".xlsx":
        return fix_excel_workbook(file_path, rules, title, author)
    elif ext == ".pptx":
        return fix_powerpoint_pres(file_path, rules, title, author)
    elif ext == ".pdf":
        return fix_pdf_document(file_path, rules, title, language)
    elif ext == ".epub":
        return fix_epub_document(file_path, rules, title, language)
    else:
        return f"Error: Unsupported file type '{ext}'. Supported: .pdf, .docx, .xlsx, .pptx, .epub"


# ---------------------------------------------------------------------------
# Tool: verify_fix
# ---------------------------------------------------------------------------

@mcp.tool()
def verify_fix(original_path: str, fixed_path: str) -> str:
    """Compare before/after scans to verify accessibility fixes.

    Scans both the original and fixed files, then reports what improved,
    what regressed, and what remains unfixed. Use after applying fixes
    to confirm they worked.

    Args:
        original_path: Absolute path to the original (pre-fix) document.
        fixed_path: Absolute path to the fixed document.

    Returns:
        Delta report showing fixed, new, and remaining issues.
    """
    orig = Path(original_path)
    fixed = Path(fixed_path)

    if not orig.exists():
        return f"Error: Original file not found: {original_path}"
    if not fixed.exists():
        return f"Error: Fixed file not found: {fixed_path}"

    # Get JSON scan results for both
    orig_json = json.loads(get_scan_result_json(original_path))
    fixed_json = json.loads(get_scan_result_json(fixed_path))

    if "error" in orig_json:
        return f"Error scanning original: {orig_json['error']}"
    if "error" in fixed_json:
        return f"Error scanning fixed: {fixed_json['error']}"

    # Collect all findings as rule sets
    def _extract_rules(scan_result: dict) -> dict[str, list]:
        """Extract findings grouped by rule ID."""
        rules = {}
        for scanner_result in scan_result.values():
            if not isinstance(scanner_result, dict):
                continue
            for f in scanner_result.get("findings", []):
                rule = f.get("rule", "unknown")
                rules.setdefault(rule, []).append(f)
        return rules

    orig_rules = _extract_rules(orig_json)
    fixed_rules = _extract_rules(fixed_json)

    all_rule_ids = sorted(set(list(orig_rules.keys()) + list(fixed_rules.keys())))

    resolved = []
    remaining = []
    regressions = []

    for rule_id in all_rule_ids:
        orig_count = len(orig_rules.get(rule_id, []))
        fixed_count = len(fixed_rules.get(rule_id, []))

        if orig_count > 0 and fixed_count == 0:
            resolved.append((rule_id, orig_count))
        elif orig_count == 0 and fixed_count > 0:
            regressions.append((rule_id, fixed_count))
        elif fixed_count > 0:
            if fixed_count < orig_count:
                resolved.append((rule_id, orig_count - fixed_count))
                remaining.append((rule_id, fixed_count))
            else:
                remaining.append((rule_id, fixed_count))
                if fixed_count > orig_count:
                    regressions.append((rule_id, fixed_count - orig_count))

    # Scores
    orig_score = orig_json.get("score", "N/A")
    orig_grade = orig_json.get("grade", "?")
    fixed_score = fixed_json.get("score", "N/A")
    fixed_grade = fixed_json.get("grade", "?")

    lines = [
        "# Fix Verification Report",
        "",
        f"**Original**: {orig.name} — {orig_score}/100 ({orig_grade})",
        f"**Fixed**: {fixed.name} — {fixed_score}/100 ({fixed_grade})",
        "",
    ]

    if isinstance(orig_score, (int, float)) and isinstance(fixed_score, (int, float)):
        delta = fixed_score - orig_score
        direction = "improved" if delta > 0 else "declined" if delta < 0 else "unchanged"
        lines.append(f"**Score change**: {'+' if delta > 0 else ''}{delta} ({direction})")
        lines.append("")

    if resolved:
        lines.append(f"## Resolved ({sum(c for _, c in resolved)} findings)")
        for rule_id, count in resolved:
            lines.append(f"- {rule_id}: {count} fixed")
        lines.append("")

    if regressions:
        lines.append(f"## REGRESSIONS ({sum(c for _, c in regressions)} new findings)")
        for rule_id, count in regressions:
            lines.append(f"- {rule_id}: {count} NEW")
        lines.append("")

    if remaining:
        lines.append(f"## Remaining ({sum(c for _, c in remaining)} findings)")
        for rule_id, count in remaining:
            lines.append(f"- {rule_id}: {count} still present")
        lines.append("")

    if not resolved and not regressions:
        lines.append("No changes detected between original and fixed files.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helper: format fix results
# ---------------------------------------------------------------------------

def _format_fix_result(result: dict) -> str:
    """Format a fix result dict into readable text for AI consumption."""
    lines = []
    lines.append(f"## Fix Results: {Path(result['file']).name}")
    lines.append(f"**Output**: {result['output']}")
    lines.append(f"**Backup**: {result['backup']}")
    lines.append("")

    summary = result.get("summary", {})
    lines.append(f"**Fixed**: {summary.get('fixed', 0)} | "
                 f"**Skipped**: {summary.get('skipped', 0)} | "
                 f"**Failed**: {summary.get('failed', 0)} | "
                 f"**Needs Human**: {summary.get('needs_human', 0)}")
    lines.append("")

    for fix in result.get("fixes", []):
        status = fix.get("status", "?")
        rule = fix.get("rule", "?")
        icon = {"fixed": "+", "skipped": "-", "failed": "X",
                "needs-human": "?", "unknown": "??"}.get(status, "?")
        detail = fix.get("detail", fix.get("reason", ""))
        lines.append(f"[{icon}] **{rule}** ({status}): {detail}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Alt Text Generation Tools (4)
# ---------------------------------------------------------------------------

@mcp.tool()
def generate_alt_text(
    file_path: str,
    image_index: int = 0,
    model: str = "openai/gpt-4.1",
    profile: str = "auto",
    output_format: str = "native",
    language: str = "en",
    context: str = "",
    max_alt_length: int = 125,
) -> str:
    """Generate alt text for a single image in a document.

    Extracts the specified image from a document (PDF, Word, Excel,
    PowerPoint, or ePub), sends it to a vision-capable LLM via
    GitHub Models API, and returns structured alternative text.

    Args:
        file_path: Absolute path to the document.
        image_index: 0-based index of the image to process.
        model: Vision model ID (e.g. "openai/gpt-4.1").
        profile: Alt text profile (auto, informative, data, etc.).
        output_format: Output format (native, html, markdown, json, plain).
        language: BCP 47 language tag for the alt text.
        context: Additional document context for the LLM.
        max_alt_length: Maximum characters for concise alt text.

    Returns:
        Generated alt text in the requested format.
    """
    if not _alt_text_available:
        return ("Error: Alt text generator not available. "
                "Install required packages: pip install httpx PyMuPDF")

    path = _validate_file_path(file_path)
    if path is None or not path.exists():
        return f"Error: File not found: {file_path}"

    try:
        config = _load_alt_config()
        config = merge_config(config,
                              models=[model], profile=profile,
                              language=language, context=context,
                              max_alt_length=max_alt_length,
                              output_format=output_format)

        report = generate_for_document(path, config=config, models=[model], profile=profile)

        if not report.images:
            return f"No images found in {Path(file_path).name}"

        if image_index >= len(report.images):
            return (f"Image index {image_index} out of range. "
                    f"Document has {len(report.images)} image(s) (0-indexed).")

        img_options = report.images[image_index]
        if not img_options.options:
            errors = "; ".join(e.message for e in img_options.errors)
            return f"Failed to generate alt text: {errors}"

        result = img_options.options[0]
        formatted = apply_format(
            output_format, result.concise_alt, result.detailed_description,
            model=model, profile=profile, source_format=report.source_format,
            page_number=result.page_number, image_index=image_index,
        )
        if isinstance(formatted, dict):
            return json.dumps(formatted, indent=2)
        return str(formatted)

    except Exception as exc:
        return f"Error generating alt text: {exc}"


@mcp.tool()
def generate_alt_text_batch(
    file_path: str,
    models: str = "openai/gpt-4.1",
    profile: str = "auto",
    output_format: str = "json",
    language: str = "en",
    context: str = "",
) -> str:
    """Generate alt text for ALL images in a document.

    Extracts every image from the document and generates alt text
    for each one. Supports PDF, Word, Excel, PowerPoint, and ePub.

    Args:
        file_path: Absolute path to the document.
        models: Comma-separated model IDs for comparison.
        profile: Alt text profile (auto, informative, data, etc.).
        output_format: Output format (native, html, markdown, json, plain).
        language: BCP 47 language tag.
        context: Additional document context.

    Returns:
        Full alt text report for all images.
    """
    if not _alt_text_available:
        return ("Error: Alt text generator not available. "
                "Install required packages: pip install httpx PyMuPDF")

    path = _validate_file_path(file_path)
    if path is None or not path.exists():
        return f"Error: File not found: {file_path}"

    try:
        model_list = [m.strip() for m in models.split(",") if m.strip()]
        config = _load_alt_config()
        config = merge_config(config,
                              models=model_list, profile=profile,
                              language=language, context=context,
                              output_format=output_format)

        report = generate_for_document(path, config=config, models=model_list, profile=profile)

        lines = [
            f"# Alt Text Report: {Path(file_path).name}",
            f"**Format**: {report.source_format} | **Images**: {report.total_images}",
            f"**Models**: {', '.join(model_list)} | **Profile**: {profile}",
            "",
        ]

        for i, img_opt in enumerate(report.images):
            lines.append(f"## Image {i}: {img_opt.location}")
            if img_opt.existing_alt:
                lines.append(f"**Existing alt**: {img_opt.existing_alt}")
            lines.append("")

            for opt in img_opt.options:
                lines.append(f"### Model: {opt.model}")
                lines.append(f"**Alt**: {opt.concise_alt}")
                if opt.detailed_description:
                    lines.append(f"**Description**: {opt.detailed_description}")
                lines.append("")

            for err in img_opt.errors:
                lines.append(f"**Error** ({err.model}): [{err.error_type}] {err.message}")
            lines.append("")

        if report.errors:
            lines.append("## Errors")
            for e in report.errors:
                lines.append(f"- {e}")

        return "\n".join(lines)

    except Exception as exc:
        return f"Error generating alt text batch: {exc}"


@mcp.tool()
def list_alt_text_models() -> str:
    """List all available vision models for alt text generation.

    Returns model IDs, descriptions, cost tiers, and recommended flags.
    """
    if not _alt_text_available:
        return ("Error: Alt text generator not available. "
                "Install required packages: pip install httpx PyMuPDF")

    models = list_models()
    lines = ["# Available Vision Models", ""]
    for model_id, info in models.items():
        rec = " (recommended)" if info.get("recommended") else ""
        lines.append(
            f"- **{model_id}**: {info['name']} -- {info['description']}{rec}"
        )
        lines.append(f"  Cost: {info['cost']} | Rate tier: {info['tier']}")
    return "\n".join(lines)


@mcp.tool()
def list_alt_text_profiles() -> str:
    """List available alt text profiles for image description.

    Profiles control the style and strategy of generated alt text.
    """
    if not _alt_text_available:
        return ("Error: Alt text generator not available. "
                "Install required packages: pip install httpx PyMuPDF")

    try:
        config = _load_alt_config()
        profiles = _list_alt_profiles(config.custom_profiles)
    except Exception:
        from alt_text.profiles import BUILT_IN_PROFILES
        profiles = {n: {"description": p["description"], "type": "built-in"}
                    for n, p in BUILT_IN_PROFILES.items()}

    lines = ["# Available Alt Text Profiles", ""]
    for name, info in profiles.items():
        ptype = info.get("type", "built-in")
        lines.append(f"- **{name}** ({ptype}): {info['description']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
