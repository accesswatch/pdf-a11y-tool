# Document Accessibility Toolkit -- Agent Catalog

## No-Python Fallback

All agents work **with or without Python installed**. When MCP tools are unavailable, agents automatically switch to guidance mode:

| Format | Fallback | Value retained |
|--------|----------|---------------|
| Markdown | Direct-scan (Copilot reads file natively) | 100% -- no value lost |
| Word/Excel/PowerPoint | Guide user through built-in Accessibility Checker + manual checklist | 70-80% |
| PDF | Guide user through Acrobat Pro or PAC 2024 + manual checklist | 70-80% |
| EPUB | Guide user to extract ZIP and read XHTML/OPF, or use Ace by DAISY | 60-80% |

Install Python 3.13+ and `pip install -r tools/requirements.txt` to enable full automated scanning with severity scoring, cross-document analysis, and CSV export. See `agents/skills/no-python-fallback/SKILL.md` for the full fallback reference.

## Quick Start

| What you want to do | Agent to use |
|---------------------|-------------|
| Audit a folder of documents | `document-accessibility-wizard` |
| Scan a single Word file | `word-accessibility` |
| Scan a single Excel file | `excel-accessibility` |
| Scan a single PowerPoint file | `powerpoint-accessibility` |
| Scan a single PDF file | `pdf-accessibility` |
| Scan a single ePub file | `epub-accessibility` |
| Fix Office document issues | `office-remediator` |
| Fix PDF issues | `pdf-remediator` |
| Auto-fix via scan-fix-verify loop | `document-accessibility-wizard` (Phase 5) |
| Audit markdown documentation | `markdown-a11y-assistant` |
| Build a document inventory | `document-accessibility-wizard` (Phase 1) |
| Export findings to CSV | `document-accessibility-wizard` (Phase 6) |
| Configure Office scan rules | `document-accessibility-wizard` (Phase 0) |
| Configure PDF scan rules | `document-accessibility-wizard` (Phase 0) |
| Configure ePub scan rules | `document-accessibility-wizard` (Phase 0) |

## Agent Details

### document-accessibility-wizard (Orchestrator)

Interactive audit wizard. Start here for any multi-document workflow. Runs 7 phases: configuration (Phase 0), inventory (Phase 1), format scanning (Phases 2-3), cross-document analysis (Phase 4), automated remediation with scan-fix-verify loop (Phase 5), CSV/JSON export (Phase 6), and CI/CD integration (Phase 7). Delegates to 13 sub-agents, aggregates results via cross-document-analyzer, and generates the final markdown/HTML report.

- **Invocation**: `@document-accessibility-wizard audit this folder`
- **Outputs**: `DOCUMENT-ACCESSIBILITY-AUDIT.md`, `.html`
- **Sub-agents**: `document-inventory`, `word-accessibility`, `excel-accessibility`, `powerpoint-accessibility`, `pdf-accessibility`, `epub-accessibility`, `office-scan-config`, `pdf-scan-config`, `epub-scan-config`, `cross-document-analyzer`, `document-csv-reporter`, `office-remediator`, `pdf-remediator`
- **MCP scan tools**: `scan_folder`, `scan_document`, `scan_word`, `scan_excel`, `scan_powerpoint`, `scan_pdf_full`, `list_supported_rules`, `get_scan_result_json`
- **MCP fix tools**: `fix_document`, `fix_word_document`, `fix_excel_workbook`, `fix_powerpoint_pres`, `fix_pdf_document`, `verify_fix`

### word-accessibility

Scans `.docx` files for 15 accessibility checks (title, language, headings, alt text for inline and floating images, tables, lists, TOC, tracked changes, and more). WCAG 2.2 AA.

- **Invocation**: `@word-accessibility scan this Word file`
- **MCP tools used**: `scan_word`, `scan_document`, `get_scan_result_json`, `list_supported_rules`

### excel-accessibility

Scans `.xlsx` files for 14 accessibility checks (title, sheet names, tables, alt text, merged cells, color-only data, hidden data, protection, data validation). WCAG 2.2 AA.

- **Invocation**: `@excel-accessibility check this spreadsheet`
- **MCP tools used**: `scan_excel`, `scan_document`, `get_scan_result_json`, `list_supported_rules`

### powerpoint-accessibility

Scans `.pptx` files for 16 accessibility checks (title, language, slide titles, reading order, alt text, grouped shapes, transitions, animations, media captions). WCAG 2.2 AA.

- **Invocation**: `@powerpoint-accessibility audit this presentation`
- **MCP tools used**: `scan_powerpoint`, `scan_document`, `get_scan_result_json`, `list_supported_rules`

### pdf-accessibility

Scans PDFs against three rule layers: PDF/UA conformance (30 rules), best practices (22 rules), and quality/pipeline (4 rules). Matterhorn Protocol mapping. WCAG 2.2 AA.

- **Invocation**: `@pdf-accessibility scan this PDF`
- **MCP tools used**: `scan_pdf_full`, `scan_pdf_metadata`, `scan_pdf_tags`, `scan_pdf_forms`, `scan_document`, `get_scan_result_json`, `list_supported_rules`

### office-remediator

Fixes Word, Excel, and PowerPoint accessibility issues using a 3-tier approach: Tier 1 MCP tools for metadata/property fixes, Tier 2 Python scripts (python-docx, openpyxl, python-pptx) for structural fixes, and Tier 3 step-by-step Office UI instructions for complex/visual fixes. Implements the scan-fix-verify loop with up to 3 iterations and 5 anti-loop guards. Writes to `-fixed` copies. Logs outcomes to the learning system.

- **Invocation**: `@office-remediator fix the Word issues from the audit`
- **MCP fix tools**: `fix_word_document`, `fix_excel_workbook`, `fix_powerpoint_pres`, `fix_document`
- **MCP scan tools**: `scan_word`, `scan_excel`, `scan_powerpoint`, `verify_fix`
- **Learning system**: Reads/writes `.a11y-remediation-knowledge.json`

### pdf-remediator

Fixes PDF accessibility issues using a 3-tier approach: Tier 1 MCP tools for metadata fixes (title, language, PDF/UA ID, display title), Tier 2 scripts (pikepdf/qpdf/ghostscript) for structural fixes, and Tier 3 step-by-step Adobe Acrobat Pro instructions for complex tag/table/reading-order fixes. Implements the scan-fix-verify loop with up to 3 iterations. Writes to `-fixed` copies. Logs outcomes to the learning system.

- **Invocation**: `@pdf-remediator fix the PDF issues from the audit`
- **MCP fix tools**: `fix_pdf_document`, `fix_document`
- **MCP scan tools**: `scan_pdf_full`, `scan_pdf_metadata`, `scan_pdf_tags`, `scan_pdf_forms`, `verify_fix`
- **Learning system**: Reads/writes `.a11y-remediation-knowledge.json`

### epub-accessibility

Scans `.epub` files for EPUB Accessibility 1.1 conformance (WCAG 2.x mapping). Checks package metadata, navigation documents (TOC/NCX/page-list/landmarks), spine reading order, image alt text, heading hierarchy, table structure, link text, `schema.org` accessibility metadata, and language attributes. 16 rules across error/warning/tip severities.

- **Invocation**: `@epub-accessibility scan this epub`
- **Rule IDs**: `EPUB-E*` (errors), `EPUB-W*` (warnings), `EPUB-T*` (tips)
- **MCP tools used**: `scan_epub_document` (when available)

### epub-scan-config (Internal)

Not user-invocable. Manages `.a11y-epub-config.json` -- rule enable/disable, severity filters, and scan profiles for ePub audits. Invoked by the wizard during Phase 0 when `.epub` files are in scope.

### markdown-a11y-assistant

Interactive markdown accessibility audit wizard. Runs a guided, step-by-step WCAG audit of markdown documentation across 9 domains: descriptive links, alt text, heading hierarchy, tables, emoji, Mermaid/ASCII diagrams, em-dashes, anchor links, and plain language. Orchestrates markdown-scanner and markdown-fixer sub-agents.

- **Invocation**: `@markdown-a11y-assistant audit the markdown files`
- **Outputs**: `MARKDOWN-ACCESSIBILITY-AUDIT.md`
- **Sub-agents**: `markdown-scanner`, `markdown-fixer`, `markdown-csv-reporter`

### markdown-scanner (Internal)

Not user-invocable. Scans a single markdown file across all 9 accessibility domains. Returns structured findings with severity, line numbers, and auto-fix classification.

### markdown-fixer (Internal)

Not user-invocable. Applies auto-fixable changes (links, headings, emoji, em-dashes, tables, Mermaid replacement) and presents human-judgment items for approval.

### markdown-csv-reporter (Internal)

Not user-invocable. Exports markdown audit findings to CSV format with severity scoring, WCAG criteria mapping, and remediation guidance.

### document-inventory (Internal)

Not user-invocable. File discovery and inventory building for audit workflows. Scans folders for .docx, .xlsx, .pptx, .pdf, and .epub files. Supports delta detection via `git diff`, metadata extraction (title, author, language), and template grouping. Invoked by the wizard during Phase 1.

- **MCP tools used**: `scan_folder`, `scan_document`, `get_scan_result_json`

### document-csv-reporter (Internal)

Not user-invocable. Exports audit findings to three CSV files: FINDINGS (per-issue detail), SCORECARD (per-document summary), and REMEDIATION (prioritized fix plan with ROI scoring). Includes Microsoft Office and Adobe PDF help URLs, WCAG understanding document links, and native-tool-first fix guidance. Invoked by the wizard during Phase 6.

- **Outputs**: `DOCUMENT-ACCESSIBILITY-FINDINGS.csv`, `DOCUMENT-ACCESSIBILITY-SCORECARD.csv`, `DOCUMENT-ACCESSIBILITY-REMEDIATION.csv`
- **Skills used**: `help-url-reference`

### office-scan-config (Internal)

Not user-invocable. Manages `.a11y-office-config.json` -- per-type rule enable/disable, severity filters, and preset profiles (strict, moderate, minimal) for Word, Excel, and PowerPoint scanning. Invoked by the wizard during Phase 0 when Office files are in scope.

- **MCP tools used**: `list_supported_rules`

### pdf-scan-config (Internal)

Not user-invocable. Manages `.a11y-pdf-config.json` -- three rule layers (PDFUA conformance, PDFBP best practices, PDFQ pipeline), severity filters, and preset profiles. Invoked by the wizard during Phase 0 when PDF files are in scope.

- **MCP tools used**: `list_supported_rules`

### cross-document-analyzer (Internal)

Not user-invocable. Called by the wizard to detect cross-document patterns, compute severity scores (0-100, A-F grades), analyze shared templates, and track remediation progress.

- **MCP tools used**: `scan_folder`, `get_scan_result_json`, `list_supported_rules`

## Reusable Prompts

One-click workflows are available in `.github/prompts/`:

| Prompt file | What it does |
|-------------|-------------|
| `audit-all-documents.prompt.md` | Scan every document in the workspace root |
| `scan-single-document.prompt.md` | Scan one file (asks for path) |
| `quick-document-check.prompt.md` | Fast triage -- errors only, inline results |
| `scan-inventory.prompt.md` | Discover and inventory all documents in a folder |
| `export-document-csv.prompt.md` | Export audit findings to CSV with help URLs |
| `audit-epub.prompt.md` | Scan an ePub for EPUB Accessibility 1.1 |
| `config-office-scan.prompt.md` | Create/edit Office scan config (.a11y-office-config.json) |
| `config-pdf-scan.prompt.md` | Create/edit PDF scan config (.a11y-pdf-config.json) |
| `config-epub-scan.prompt.md` | Create/edit ePub scan config (.a11y-epub-config.json) |
| `list-rules.prompt.md` | Show the full rule catalog |
| `generate-fix-scripts.prompt.md` | Generate remediation scripts from audit findings |
| `compare-audit-results.prompt.md` | Re-scan and show what improved |

## MCP Server

Registered in `.vscode/mcp.json` as `doc-accessibility-scanner`. Runs via `python tools/mcp_server.py` (stdio transport). 20 tools total (13 scan + 7 fix). See [tools/README.md](tools/README.md) for setup.

### Scan Tools (13)

| Tool | Purpose |
|------|---------|
| `scan_document` | Auto-routes to the correct scanner by file extension |
| `scan_word` | Scan .docx -- 15 checks |
| `scan_excel` | Scan .xlsx -- 14 checks |
| `scan_powerpoint` | Scan .pptx -- 16 checks |
| `scan_markdown_doc` | Scan .md -- 14 checks |
| `scan_epub_document` | Scan .epub -- 16 checks |
| `scan_pdf_metadata` | PDF title, language, tagged status, PDF/UA ID |
| `scan_pdf_tags` | PDF structure tree, headings, tables, reading order |
| `scan_pdf_forms` | PDF form tooltips, tab order, radio groups |
| `scan_pdf_full` | Combined PDF scan with scoring |
| `scan_folder` | Recursive folder scan, all formats |
| `list_supported_rules` | Rule catalog, filterable by format |
| `get_scan_result_json` | Raw JSON for programmatic use |

### Fix Tools (7)

| Tool | Purpose |
|------|---------|
| `fix_document` | Auto-routes to the correct fixer by extension |
| `fix_word_document` | Fix .docx metadata, tables, alt text |
| `fix_excel_workbook` | Fix .xlsx metadata, sheet names, alt text |
| `fix_powerpoint_pres` | Fix .pptx metadata, slide titles, alt text |
| `fix_pdf_document` | Fix PDF metadata, language, PDF/UA ID, marked content |
| `fix_epub_document` | Fix .epub metadata, language, a11y metadata, alt text |
| `verify_fix` | Compare before/after scans, report delta |

## Learning System

The toolkit maintains `.a11y-remediation-knowledge.json` in the workspace root, tracking:

- **Per-rule statistics**: Success/failure counts, last outcome, avg fix time
- **Fix patterns**: Reusable template recipes indexed by rule ID
- **User preferences**: Preferred fix tiers, naming conventions
- **Session log**: Timestamped record of all fix attempts

Both remediator agents and the wizard's Phase 5 read/write this file to improve fix selection over time.

## Skills Reference

| Skill | Purpose |
|-------|---------|
| `accessibility-rules` | Rule ID catalog with WCAG 2.2 mapping |
| `document-scanning` | File discovery, delta detection, scan config |
| `report-generation` | Report structure, scoring formula, tone standard |
| `office-remediation` | python-docx/openpyxl/python-pptx code patterns |
| `pdf-remediation` | pikepdf/pypdf/qpdf/Ghostscript code patterns, Acrobat Pro manual steps |
| `markdown-accessibility` | Markdown rule library, emoji maps, diagram templates, anchor rules |
| `help-url-reference` | Microsoft Office, Adobe PDF, axe-core, and WCAG help URL mappings |
