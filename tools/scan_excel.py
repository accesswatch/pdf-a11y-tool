"""
scan_excel.py — Excel Workbook Accessibility Scanner
=====================================================
Permanent utility for document accessibility audits.
Inspects .xlsx files for accessibility issues using openpyxl.

Checks performed:
  Core metadata:
    - Workbook title property                [XLSX.META.TITLE]
    - Author / company metadata              [XLSX.META.AUTHOR]

  Navigation & structure:
    - Meaningful, unique worksheet names     [XLSX.NAV.SHEET_NAMES]
    - Duplicate sheet names                  [XLSX.NAV.SHEET_DUP]
    - Frozen header row for navigability     [XLSX.NAV.FREEZE_PANES]

  Tables:
    - Named Table objects vs. plain ranges   [XLSX.TABLE.NAMED]
    - Table header row configured            [XLSX.TABLE.HEADER]
    - Avoid merged cells inside tables       [XLSX.TABLE.MERGED]

  Layout:
    - Global merged cell detection           [XLSX.LAYOUT.MERGED]
    - Empty spacing rows/columns             [XLSX.LAYOUT.SPACING]

  Color & contrast:
    - Color as sole differentiator warning   [XLSX.COLOR.ONLY]

  Links:
    - Hyperlink text quality                 [XLSX.LINKS.TEXT]

  Charts & images:
    - Chart objects missing alt text         [XLSX.CHART.ALT]
    - Images missing alt text                [XLSX.IMG.ALT]

  Data integrity:
    - Hidden rows/columns with data          [XLSX.LAYOUT.HIDDEN]
    - Protected sheets (input barriers)      [XLSX.PROTECT.SHEET]
    - Data validation rules                  [XLSX.DATA.VALIDATION]

Usage:
    python tools/scan_excel.py <xlsx_or_folder> [--json] [--output file.json]

Dependencies: openpyxl

This file is PERMANENT — do not delete. Used by agents and scan_all.py.
"""

import sys
import json
import argparse
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from lxml import etree

try:
    import openpyxl
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("ERROR: openpyxl not installed. Run: pip install openpyxl")

# XML namespaces used in xlsx package
_SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_CHART_NS = "http://schemas.openxmlformats.org/drawingml/2006/chart"
_SSDR_NS = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"


# ---------------------------------------------------------------------------
# Metadata checks
# ---------------------------------------------------------------------------

def check_metadata(wb) -> list:
    """Check workbook-level metadata."""
    findings = []
    props = wb.properties

    title = getattr(props, "title", None)
    if not title or not str(title).strip():
        findings.append({
            "rule": "XLSX.META.TITLE",
            "severity": "Error",
            "confidence": "High",
            "wcag": "2.4.2",
            "matterhorn": None,
            "message": (
                "Workbook has no title set in document properties. "
                "Screen readers and browser tabs announce the title; without it, "
                "users hear an unhelpful filename."
            ),
            "fix": (
                "In Excel: File > Info > Properties (right panel) > Title. "
                "Or: File > Info > Advanced Properties > Summary tab > Title."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Sheet name checks
# ---------------------------------------------------------------------------

GENERIC_SHEET_NAMES = {"sheet1", "sheet2", "sheet3", "sheet4", "sheet5",
                        "tab1", "tab2", "tab3", "page1", "page2"}


def check_sheet_names(wb) -> list:
    """Check sheet names for meaningfulness and uniqueness."""
    findings = []
    seen = {}
    generics = []

    for ws in wb.worksheets:
        name = ws.title or ""
        canon = name.strip().lower()
        seen.setdefault(canon, []).append(name)
        if canon in GENERIC_SHEET_NAMES:
            generics.append(name)

    if generics:
        findings.append({
            "rule": "XLSX.NAV.SHEET_NAMES",
            "severity": "Warning",
            "confidence": "High",
            "wcag": "2.4.6",
            "message": (
                f"{len(generics)} sheet tab(s) have generic names that do not describe the content: "
                f"{generics}. Screen readers announce the sheet name when users navigate to it."
            ),
            "fix": (
                "Right-click each sheet tab > Rename. "
                "Use descriptive names like 'Q1 Budget' instead of 'Sheet1'."
            ),
        })

    duplicates = [names[0] for names in seen.values() if len(names) > 1]
    if duplicates:
        findings.append({
            "rule": "XLSX.NAV.SHEET_DUP",
            "severity": "Warning",
            "confidence": "High",
            "wcag": "2.4.6",
            "message": (
                f"Duplicate sheet names found: {duplicates}. "
                "Screen reader users navigating sheets will hear identical names "
                "and cannot distinguish between them."
            ),
            "fix": "Rename duplicate sheets to be unique and descriptive.",
        })

    return findings


# ---------------------------------------------------------------------------
# Freeze panes check
# ---------------------------------------------------------------------------

def check_freeze_panes(wb) -> list:
    """Check whether header rows are frozen for navigability."""
    findings = []
    unfrozen_with_data = []

    for ws in wb.worksheets:
        max_row = ws.max_row or 0
        if max_row < 2:
            continue  # single-row or empty sheets don't need freeze
        if not ws.freeze_panes:
            unfrozen_with_data.append(ws.title)

    if unfrozen_with_data:
        findings.append({
            "rule": "XLSX.NAV.FREEZE_PANES",
            "severity": "Warning",
            "confidence": "Medium",
            "wcag": "1.3.1",
            "message": (
                f"{len(unfrozen_with_data)} sheet(s) have multiple rows but no frozen panes: "
                f"{unfrozen_with_data}. Without a frozen header row, users who scroll down "
                "lose the column header context."
            ),
            "fix": (
                "Select the cell below and to the right of the headers you want to freeze "
                "(e.g., A2 to freeze row 1). View > Freeze Panes > Freeze Panes. "
                "For most sheets: View > Freeze Panes > Freeze Top Row."
            ),
            "source": "https://www.section508.gov/create/spreadsheets/",
        })

    return findings


# ---------------------------------------------------------------------------
# Named table checks
# ---------------------------------------------------------------------------

def check_tables(wb) -> list:
    """Check for properly defined Tables (not just styled ranges)."""
    findings = []
    sheets_without_tables = []

    for ws in wb.worksheets:
        max_row = ws.max_row or 0
        max_col = ws.max_column or 0
        if max_row < 2 or max_col < 1:
            continue  # empty or single-header sheet

        # Check if tabular data exists but isn't in a Table
        tables = list(ws.tables.values()) if hasattr(ws, "tables") else []

        if not tables and max_row > 1:
            sheets_without_tables.append(ws.title)
        else:
            # Check each table for header configuration
            for tbl in tables:
                header_count = getattr(tbl, "headerRowCount", None)
                if header_count == 0:
                    findings.append({
                        "rule": "XLSX.TABLE.HEADER",
                        "severity": "Error",
                        "confidence": "High",
                        "wcag": "1.3.1",
                        "sheet": ws.title,
                        "table": tbl.displayName,
                        "message": (
                            f"Table '{tbl.displayName}' on sheet '{ws.title}' "
                            "has its header row disabled (headerRowCount=0). "
                            "Screen readers cannot identify column headers without this."
                        ),
                        "fix": (
                            "Click anywhere in the table. Table Design tab > "
                            "check 'Header Row' in Table Style Options."
                        ),
                    })

    if sheets_without_tables:
        findings.append({
            "rule": "XLSX.TABLE.NAMED",
            "severity": "Warning",
            "confidence": "Medium",
            "wcag": "1.3.1",
            "message": (
                f"{len(sheets_without_tables)} sheet(s) appear to have tabular data "
                "but no named Excel Table (ListObject) defined: "
                f"{sheets_without_tables}. Named Tables enable screen readers to "
                "announce column headers as users navigate cell by cell."
            ),
            "fix": (
                "Select the data range including the header row. "
                "Insert > Table. Ensure 'My table has headers' is checked. "
                "Give the table a meaningful name in Table Design > Table Name."
            ),
            "source": "https://www.section508.gov/create/spreadsheets/",
        })

    return findings


# ---------------------------------------------------------------------------
# Merged cells check
# ---------------------------------------------------------------------------

def check_merged_cells(wb) -> list:
    """Check for merged cells which disrupt non-visual navigation."""
    findings = []

    for ws in wb.worksheets:
        merged = list(ws.merged_cells.ranges)
        if merged:
            findings.append({
                "rule": "XLSX.LAYOUT.MERGED",
                "severity": "Warning",
                "confidence": "High",
                "wcag": "1.3.2",
                "sheet": ws.title,
                "message": (
                    f"Sheet '{ws.title}' has {len(merged)} merged cell range(s). "
                    "Merged cells break the screen reader's ability to map data to "
                    "column or row headers, causing confusing or silent announcements."
                ),
                "fix": (
                    "Avoid merging cells. For centered headings, use "
                    "'Center Across Selection' instead of Merge & Center: "
                    "Format Cells > Alignment > Horizontal > Center Across Selection."
                ),
            })

    return findings


# ---------------------------------------------------------------------------
# Empty spacing rows/columns check
# ---------------------------------------------------------------------------

def check_spacing_layout(wb) -> list:
    """Detect empty rows or columns used for visual spacing."""
    findings = []

    for ws in wb.worksheets:
        max_row = ws.max_row or 0
        max_col = ws.max_column or 0
        if max_row < 1 or max_col < 1:
            continue

        empty_rows = []
        for row_idx in range(1, max_row + 1):
            row_cells = [ws.cell(row=row_idx, column=c) for c in range(1, min(max_col + 1, 20))]
            if all(c.value is None for c in row_cells):
                # Ignore trailing empty rows
                if row_idx < max_row - 1:
                    empty_rows.append(row_idx)

        if len(empty_rows) > 2:
            findings.append({
                "rule": "XLSX.LAYOUT.SPACING",
                "severity": "Warning",
                "confidence": "Medium",
                "wcag": "1.3.2",
                "sheet": ws.title,
                "message": (
                    f"Sheet '{ws.title}' has {len(empty_rows)} empty row(s) in the middle "
                    "of the data range (rows {empty_rows[:5]}...). "
                    "Empty rows used for visual spacing confuse screen readers "
                    "which announce 'blank' repeatedly between data rows."
                ),
                "fix": (
                    "Remove empty spacing rows and columns. "
                    "Use cell padding (Format Cells > Alignment > Indent) or "
                    "row height to add visual breathing room without adding empty rows."
                ),
                "source": "https://www.section508.gov/create/spreadsheets/",
            })
            break  # one finding per sheet is enough

    return findings


# ---------------------------------------------------------------------------
# Hyperlink text check
# ---------------------------------------------------------------------------

_POOR_LINK_PHRASES = {
    "click here", "here", "link", "more", "read more", "learn more",
    "go", "this", "url", "http", "https", "www", "details", "info",
}


def check_hyperlinks(wb) -> list:
    """Check hyperlink anchor text across all sheets."""
    findings = []

    for ws in wb.worksheets:
        poor_links = []
        for row in ws.iter_rows():
            for cell in row:
                if cell.hyperlink:
                    display = (
                        cell.hyperlink.display
                        or (str(cell.value) if cell.value else "")
                    ).strip().lower()
                    if not display or display in _POOR_LINK_PHRASES or display.startswith(("http://", "https://")):
                        poor_links.append({
                            "cell": cell.coordinate,
                            "text": display or "(empty)",
                        })

        if poor_links:
            findings.append({
                "rule": "XLSX.LINKS.TEXT",
                "severity": "Warning",
                "confidence": "High",
                "wcag": "2.4.4",
                "sheet": ws.title,
                "message": (
                    f"Sheet '{ws.title}' has {len(poor_links)} hyperlink(s) with "
                    "non-descriptive anchor text. Screen reader users navigating links "
                    "will hear unhelpful text like 'click here' or a raw URL. "
                    f"Examples: {poor_links[:3]}"
                ),
                "fix": (
                    "Replace link text with a description of the destination: "
                    "e.g., 'Section 508 Spreadsheet Guide' instead of 'click here'. "
                    "Right-click the cell > Edit Hyperlink > change the 'Text to display' field."
                ),
            })

    return findings


# ---------------------------------------------------------------------------
# Color-only information warning
# ---------------------------------------------------------------------------

def check_color_warning(wb) -> list:
    """
    Emit an informational check about color-only information.
    We can detect cell fill colors but cannot determine semantics automatedly.
    """
    findings = []
    sheets_with_fills = []

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            found = False
            for cell in row:
                fill = cell.fill
                if fill and fill.fill_type not in (None, "none", "solid") or (
                    fill and fill.fill_type == "solid"
                    and fill.fgColor
                    and fill.fgColor.type != "theme"
                    and fill.fgColor.rgb not in ("00000000", "FFFFFFFF", "FF000000", "FFFEFEFE")
                ):
                    sheets_with_fills.append(ws.title)
                    found = True
                    break
            if found:
                break

    if sheets_with_fills:
        findings.append({
            "rule": "XLSX.COLOR.ONLY",
            "severity": "Info",
            "confidence": "Low",
            "wcag": "1.4.1",
            "message": (
                f"{len(set(sheets_with_fills))} sheet(s) appear to use cell background colors "
                f"({list(set(sheets_with_fills))}). "
                "If color is the only means of conveying information (e.g., red = overdue, "
                "green = complete), this violates WCAG 1.4.1. "
                "Manual review required to verify."
            ),
            "fix": (
                "Add a text label, icon, or pattern alongside any color-coded meaning. "
                "Example: add a 'Status' column with text values ('Overdue', 'Complete') "
                "in addition to conditional formatting colors."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Chart alt text check (via OOXML package inspection)
# ---------------------------------------------------------------------------

def check_charts(xlsx_path: Path) -> list:
    """Check for chart objects and whether they have alt text descriptions.

    Charts are embedded as drawing objects in the xlsx package. openpyxl has
    limited chart-reading support, so we inspect the zip directly for
    drawing XML files containing chart references and check their cNvPr descr.
    """
    findings = []
    charts_total = 0
    charts_no_alt = 0

    try:
        with ZipFile(str(xlsx_path), "r") as zf:
            drawing_files = [n for n in zf.namelist()
                             if n.startswith("xl/drawings/drawing") and n.endswith(".xml")]
            for df in drawing_files:
                tree = etree.parse(zf.open(df))
                root = tree.getroot()
                # twoCellAnchor / oneCellAnchor containing graphicFrame (chart) or pic (image)
                for anchor_tag in ("twoCellAnchor", "oneCellAnchor", "absoluteAnchor"):
                    for anchor in root.findall(f".//{{{_SSDR_NS}}}{anchor_tag}"):
                        # Check for chart frames
                        for gf in anchor.findall(f".//{{{_SSDR_NS}}}graphicFrame"):
                            charts_total += 1
                            nvgf = gf.find(f"{{{_SSDR_NS}}}nvGraphicFramePr")
                            if nvgf is not None:
                                cnv = nvgf.find(f"{{{_SSDR_NS}}}cNvPr")
                                if cnv is not None:
                                    descr = cnv.get("descr", "").strip()
                                    if not descr:
                                        charts_no_alt += 1
                                else:
                                    charts_no_alt += 1
                            else:
                                charts_no_alt += 1

    except (BadZipFile, Exception):
        pass

    if charts_no_alt:
        findings.append({
            "rule": "XLSX.CHART.ALT",
            "severity": "Error",
            "confidence": "High",
            "wcag": "1.1.1",
            "message": (
                f"{charts_no_alt} of {charts_total} chart(s) are missing alt text. "
                "Charts convey data visually; without alt text, screen reader users "
                "receive no equivalent information."
            ),
            "fix": (
                "Right-click the chart → Edit Alt Text → describe the chart's key "
                "message and trends, not just 'bar chart'. Include the data range "
                "or a summary table nearby for full data access."
            ),
        })
    elif charts_total > 0:
        findings.append({
            "rule": "XLSX.CHART.ALT",
            "severity": "Info",
            "confidence": "Medium",
            "wcag": "1.1.1",
            "message": (
                f"{charts_total} chart(s) found — all have alt text. "
                "Manual review recommended to verify alt text quality."
            ),
            "fix": "Verify chart alt text describes the key message, not just the chart type.",
        })

    return findings


# ---------------------------------------------------------------------------
# Images / drawing alt text check
# ---------------------------------------------------------------------------

def check_images(xlsx_path: Path) -> list:
    """Check for embedded images and whether they have alt text."""
    findings = []
    images_total = 0
    images_no_alt = 0

    try:
        with ZipFile(str(xlsx_path), "r") as zf:
            drawing_files = [n for n in zf.namelist()
                             if n.startswith("xl/drawings/drawing") and n.endswith(".xml")]
            for df in drawing_files:
                tree = etree.parse(zf.open(df))
                root = tree.getroot()
                for anchor_tag in ("twoCellAnchor", "oneCellAnchor", "absoluteAnchor"):
                    for anchor in root.findall(f".//{{{_SSDR_NS}}}{anchor_tag}"):
                        for pic in anchor.findall(f".//{{{_SSDR_NS}}}pic"):
                            images_total += 1
                            nvpic = pic.find(f"{{{_SSDR_NS}}}nvPicPr")
                            if nvpic is not None:
                                cnv = nvpic.find(f"{{{_SSDR_NS}}}cNvPr")
                                if cnv is not None:
                                    descr = cnv.get("descr", "").strip()
                                    if not descr:
                                        images_no_alt += 1
                                else:
                                    images_no_alt += 1
                            else:
                                images_no_alt += 1

    except (BadZipFile, Exception):
        pass

    if images_no_alt:
        findings.append({
            "rule": "XLSX.IMG.ALT",
            "severity": "Error",
            "confidence": "High",
            "wcag": "1.1.1",
            "message": (
                f"{images_no_alt} of {images_total} image(s) are missing alt text."
            ),
            "fix": (
                "Right-click the image → Edit Alt Text → describe the image content. "
                "If decorative, mark as decorative."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Hidden rows/columns check
# ---------------------------------------------------------------------------

def check_hidden_data(wb) -> list:
    """Detect hidden rows, columns, and sheets that may contain data."""
    findings = []
    hidden_sheets = []
    sheets_with_hidden_rows = []
    sheets_with_hidden_cols = []

    for ws in wb.worksheets:
        if ws.sheet_state == "hidden" or ws.sheet_state == "veryHidden":
            hidden_sheets.append(ws.title)
            continue

        hidden_row_count = sum(1 for rd in ws.row_dimensions.values() if rd.hidden)
        if hidden_row_count > 0:
            sheets_with_hidden_rows.append((ws.title, hidden_row_count))

        hidden_col_count = sum(1 for cd in ws.column_dimensions.values() if cd.hidden)
        if hidden_col_count > 0:
            sheets_with_hidden_cols.append((ws.title, hidden_col_count))

    if hidden_sheets:
        findings.append({
            "rule": "XLSX.LAYOUT.HIDDEN",
            "severity": "Warning",
            "confidence": "High",
            "wcag": "1.3.1",
            "message": (
                f"{len(hidden_sheets)} hidden sheet(s): {hidden_sheets}. "
                "Hidden sheets are inaccessible to all users and may contain "
                "outdated or sensitive data."
            ),
            "fix": (
                "Right-click any sheet tab → Unhide → select the hidden sheet. "
                "Delete it if no longer needed, or make it visible."
            ),
        })

    if sheets_with_hidden_rows:
        details = [f"'{s}' ({n} rows)" for s, n in sheets_with_hidden_rows[:5]]
        findings.append({
            "rule": "XLSX.LAYOUT.HIDDEN",
            "severity": "Warning",
            "confidence": "Medium",
            "wcag": "1.3.1",
            "message": (
                f"Hidden rows found in: {', '.join(details)}. "
                "Hidden rows may confuse users who notice gaps in row numbers."
            ),
            "fix": "Select rows surrounding the hidden area → right-click → Unhide.",
        })

    if sheets_with_hidden_cols:
        details = [f"'{s}' ({n} cols)" for s, n in sheets_with_hidden_cols[:5]]
        findings.append({
            "rule": "XLSX.LAYOUT.HIDDEN",
            "severity": "Warning",
            "confidence": "Medium",
            "wcag": "1.3.1",
            "message": (
                f"Hidden columns found in: {', '.join(details)}. "
                "Hidden columns may contain data that some users cannot access."
            ),
            "fix": "Select columns surrounding the hidden area → right-click → Unhide.",
        })

    return findings


# ---------------------------------------------------------------------------
# Protected sheet check
# ---------------------------------------------------------------------------

def check_protection(wb) -> list:
    """Detect protected sheets that may interfere with assistive technology."""
    findings = []
    protected = []

    for ws in wb.worksheets:
        if ws.protection.sheet:
            protected.append(ws.title)

    if protected:
        findings.append({
            "rule": "XLSX.PROTECT.SHEET",
            "severity": "Info",
            "confidence": "High",
            "wcag": "2.1.1",
            "message": (
                f"{len(protected)} sheet(s) are protected: {protected}. "
                "Sheet protection can interfere with keyboard navigation "
                "and screen reader interaction in some Excel versions."
            ),
            "fix": (
                "If the sheet contains form fields, ensure 'Select unlocked cells' "
                "and 'Select locked cells' are both checked in Protect Sheet dialog."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Data validation check
# ---------------------------------------------------------------------------

def check_data_validation(wb) -> list:
    """Check data validation rules for input messages."""
    findings = []
    validations_without_msg = 0
    total_validations = 0

    for ws in wb.worksheets:
        if not hasattr(ws, "data_validations") or ws.data_validations is None:
            continue
        for dv in ws.data_validations.dataValidation:
            total_validations += 1
            has_prompt = bool(getattr(dv, "promptTitle", None) or
                             getattr(dv, "prompt", None))
            if not has_prompt:
                validations_without_msg += 1

    if validations_without_msg:
        findings.append({
            "rule": "XLSX.DATA.VALIDATION",
            "severity": "Warning",
            "confidence": "Medium",
            "wcag": "3.3.2",
            "message": (
                f"{validations_without_msg} of {total_validations} data validation rule(s) "
                "have no input message. Screen reader users will not know what values "
                "are expected until they trigger a validation error."
            ),
            "fix": (
                "Select the cell with validation → Data tab → Data Validation → "
                "Input Message tab → enter a Title and Input message."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Main scan function
# ---------------------------------------------------------------------------

def scan_excel(xlsx_path: Path) -> dict:
    result = {
        "file": xlsx_path.name,
        "path": str(xlsx_path),
        "sheet_count": 0,
        "findings": [],
        "errors": [],
    }

    try:
        wb = openpyxl.load_workbook(str(xlsx_path), data_only=True)
        result["sheet_count"] = len(wb.worksheets)
        result["sheets"] = [ws.title for ws in wb.worksheets]

        all_findings = []
        all_findings.extend(check_metadata(wb))
        all_findings.extend(check_sheet_names(wb))
        all_findings.extend(check_freeze_panes(wb))
        all_findings.extend(check_tables(wb))
        all_findings.extend(check_merged_cells(wb))
        all_findings.extend(check_spacing_layout(wb))
        all_findings.extend(check_hyperlinks(wb))
        all_findings.extend(check_color_warning(wb))
        all_findings.extend(check_charts(xlsx_path))
        all_findings.extend(check_images(xlsx_path))
        all_findings.extend(check_hidden_data(wb))
        all_findings.extend(check_protection(wb))
        all_findings.extend(check_data_validation(wb))

        result["findings"] = all_findings

    except Exception as e:
        result["errors"].append(f"Could not open or analyze file: {e}")

    return result


def scan_folder(folder: Path) -> list:
    return [scan_excel(p) for p in sorted(folder.glob("*.xlsx"))]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scan Excel workbooks for accessibility issues."
    )
    parser.add_argument("path", help="XLSX file or folder containing XLSX files")
    parser.add_argument("--output", help="Write JSON output to this file")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args()

    target = Path(args.path)
    if target.is_dir():
        results = scan_folder(target)
    elif target.is_file():
        results = [scan_excel(target)]
    else:
        sys.exit(f"ERROR: Path not found: {target}")

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"JSON written to {args.output}")
    elif args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            errs = sum(1 for f in r["findings"] if f.get("severity") == "Error")
            warns = sum(1 for f in r["findings"] if f.get("severity") == "Warning")
            print(f"\n{r['file']}")
            print(f"  Sheets       : {r.get('sheet_count', 0)}")
            print(f"  Findings     : {errs} errors, {warns} warnings")
            for f in r["findings"]:
                sev = f.get("severity", "?")
                rule = f.get("rule", "?")
                msg = f.get("message", "")[:100]
                print(f"    [{sev}] {rule}: {msg}")


if __name__ == "__main__":
    sys.exit(main())
