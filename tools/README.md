# Document Accessibility Tools

Persistent, reusable scanning and remediation utilities for document
accessibility audits. Supports PDF, Word (.docx), Excel (.xlsx),
PowerPoint (.pptx), ePub (.epub), and Markdown (.md). These scripts are
**never deleted** -- they live here permanently and are invoked by agents,
CI pipelines, MCP clients, or directly by staff.

## Requirements

```
pip install pikepdf pypdf python-docx openpyxl python-pptx lxml mcp ebooklib
```

All libraries are already installed on the audit workstation (Python 3.13).

## Scanners

| Script | Purpose | Run time |
|--------|---------|----------|
| `scan_metadata.py` | Extracts PDF title, language, DisplayDocTitle, XMP, PDF/UA identifier | ~1-2 s/file |
| `scan_tags.py` | Analyzes PDF tag tree -- form tags, list structure, role maps, tables | ~2-5 s/file |
| `scan_forms.py` | Inspects PDF AcroForm fields -- tooltips, tab order, field types | ~1-2 s/file |
| `scan_word.py` | Scans Word docs -- title, headings, images, tables, lists, TOC, tracked changes | ~1-3 s/file |
| `scan_excel.py` | Scans Excel workbooks -- title, sheets, tables, charts, images, hidden data | ~1-3 s/file |
| `scan_pptx.py` | Scans PowerPoint -- titles, reading order, alt text, tables, media, animations | ~2-4 s/file |
| `scan_epub.py` | Scans ePub -- metadata, language, nav, alt text, headings, tables (16 checks) | ~1-3 s/file |
| `scan_markdown.py` | Scans Markdown -- links, alt text, headings, tables, emoji, diagrams (14 checks) | ~1 s/file |
| `scan_all.py` | Multi-format orchestrator -- routes to correct scanner, scores each file | ~5-15 s/file |
| `merge_results.py` | Merge individual scan-result JSONs into one audit, regenerate reports | ~1 s |

## Fixers

| Script | Purpose |
|--------|---------|
| `fix_word.py` | Fix Word docs -- metadata, table headers, alt text placeholders |
| `fix_excel.py` | Fix Excel workbooks -- metadata, sheet names, alt text |
| `fix_pptx.py` | Fix PowerPoint -- metadata, slide titles, alt text |
| `fix_pdf.py` | Fix PDFs -- metadata, language, PDF/UA ID, marked content |
| `fix_epub.py` | Fix ePub -- metadata, language, accessibility metadata, alt text |

All fixers write to a new file (e.g., `report-fixed.docx`) and never modify
the original.

## Report Generators

| Script | Purpose | Run time |
|--------|---------|----------|
| `report_md.py` | Reads scan JSON, generates the front-facing Markdown report | ~1 s |
| `report_html.py` | Reads scan JSON, generates the HTML report | ~1 s |

## MCP Server (AI Tool Integration)

The MCP server (`mcp_server.py`) wraps all scanners and fixers as structured
tools that AI agents can call directly. It is registered in `.vscode/mcp.json`
for VS Code Copilot.

### Registered Tools (21)

#### Scanning Tools (11)

| Tool | Description |
|------|-------------|
| `scan_document` | Auto-route to correct scanner by file extension |
| `scan_word` | Scan a Word (.docx) document |
| `scan_excel` | Scan an Excel (.xlsx) workbook |
| `scan_powerpoint` | Scan a PowerPoint (.pptx) presentation |
| `scan_markdown_doc` | Scan a Markdown (.md) file |
| `scan_epub_document` | Scan an ePub (.epub) document |
| `scan_pdf_metadata` | Extract and check PDF metadata |
| `scan_pdf_tags` | Analyze PDF tag structure tree |
| `scan_pdf_forms` | Scan PDF form field accessibility |
| `scan_pdf_full` | Run all PDF scanners combined |
| `scan_folder` | Scan all documents in a folder recursively |

#### Analysis Tools (2)

| Tool | Description |
|------|-------------|
| `list_supported_rules` | List all rules by format |
| `get_scan_result_json` | Get raw JSON results for programmatic use |
| `merge_scan_results` | Merge multiple scan-result JSONs into one unified audit + reports |

#### Fix Tools (7)

| Tool | Description |
|------|-------------|
| `fix_document` | Auto-route to correct fixer by file extension |
| `fix_word_document` | Fix Word (.docx) metadata, tables, alt text |
| `fix_excel_workbook` | Fix Excel (.xlsx) metadata, sheet names, alt text |
| `fix_powerpoint_pres` | Fix PowerPoint (.pptx) metadata, slide titles, alt text |
| `fix_pdf_document` | Fix PDF metadata, language, PDF/UA ID, marked content |
| `fix_epub_document` | Fix ePub metadata, language, accessibility metadata, alt text |
| `verify_fix` | Compare before/after scans, report delta |

### Starting the MCP Server Manually

```bash
python tools/mcp_server.py
```

The server uses stdio transport -- it reads JSON-RPC messages on stdin and
writes responses to stdout. VS Code launches it automatically via mcp.json.

## CLI Usage

### Full audit of a folder

```bash
python tools/scan_all.py "s:/pdf" --output "s:/pdf/scan_results.json"
python tools/report_md.py  "s:/pdf/scan_results.json" --output "s:/pdf/PDF-ACCESSIBILITY-AUDIT-FULL.md"
python tools/report_html.py "s:/pdf/scan_results.json" --output "s:/pdf/PDF-ACCESSIBILITY-AUDIT-FULL.html"
```

### Single file (any format)

```bash
python tools/scan_all.py "document.pdf"
python tools/scan_all.py "report.docx"
python tools/scan_all.py "data.xlsx"
python tools/scan_all.py "slides.pptx"
python tools/scan_all.py "book.epub"
python tools/scan_all.py "README.md"
```

### Merge individual scan results

```bash
# Scan files individually (avoids subfolder recursion)
Get-ChildItem documents/*.pdf | ForEach-Object {
    python tools/scan_all.py $_.FullName --type pdf --json-only --output "documents/temp_$($_.BaseName).json"
}

# Merge all temp results and generate reports
python tools/merge_results.py documents/temp_*.json --report-name PDF-ACCESSIBILITY-AUDIT --cleanup
```

### Format-specific scan

```bash
python tools/scan_metadata.py "s:/pdf"
python tools/scan_word.py "report.docx"
python tools/scan_excel.py "data.xlsx"
python tools/scan_pptx.py "slides.pptx"
python tools/scan_epub.py "book.epub"
python tools/scan_markdown.py "README.md"
```

## Output Format

All scanners produce structured JSON with a consistent schema:

```json
{
  "file": "document.pdf",
  "findings": [
    {
      "rule": "PDFUA.METADATA.TITLE",
      "severity": "Error",
      "wcag": "2.4.2",
      "message": "Document title is not set",
      "fix": "Set the document title in File > Properties"
    }
  ],
  "score": 81,
  "grade": "B"
}
```

### Scoring

- Error: -10 points each (capped at -50)
- Warning: -3 points each (capped at -21)
- Info: 0 points (informational only)
- Base score: 100, floor: 0
- Grades: A (90+), B (80-89), C (70-79), D (60-69), F (below 60)

## Why These Files Are Permanent

The agents that produce accessibility reports use these scripts
as their analysis engine. Without them, agents must regenerate
equivalent code on every run -- wasting time and producing
inconsistent results. These scripts are the **ground truth scanner**.

Keep them in version control alongside the documents or in the agent repo.
