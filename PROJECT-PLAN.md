# PDF Accessibility Tool -- Project Plan

A wxPython desktop application for PDF accessibility remediation, form building, and auto-tagging.

Prepared April 1, 2026

---

## Table of Contents

- [Project Overview](#project-overview)
- [Goals and Non-Goals](#goals-and-non-goals)
- [Target Users](#target-users)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Phase 1: Project Skeleton and Core PDF Engine](#phase-1-project-skeleton-and-core-pdf-engine)
- [Phase 2: Accessibility Checker](#phase-2-accessibility-checker)
- [Phase 3: Structure Tree and Full Tag Editor](#phase-3-structure-tree-and-full-tag-editor)
- [Phase 3.5: Screen Reader Preview](#phase-35-screen-reader-preview)
- [Phase 4: Alt Text Editor for Images](#phase-4-alt-text-editor-for-images)
- [Phase 5: Form Field Editor for Existing Fields](#phase-5-form-field-editor-for-existing-fields)
- [Phase 6: Form Builder for New Fields](#phase-6-form-builder-for-new-fields)
- [Phase 7: Table Header Editor](#phase-7-table-header-editor)
- [Phase 8: Document Properties and Metadata](#phase-8-document-properties-and-metadata)
- [Phase 9: Content Stream Tagging](#phase-9-content-stream-tagging)
- [Phase 10: Auto-Tagger](#phase-10-auto-tagger)
- [Phase 11: Tool Accessibility](#phase-11-tool-accessibility)
- [Phase 12: Packaging and Distribution](#phase-12-packaging-and-distribution)
- [Phase 13: Adaptive Learning System](#phase-13-adaptive-learning-system)
- [Phase 14: AI-Assisted Remediation and Agentic Integration](#phase-14-ai-assisted-remediation-and-agentic-integration)
- [File Inventory](#file-inventory)
- [Dependencies](#dependencies)
- [Phase Dependencies Map](#phase-dependencies-map)
- [Verification and Testing Strategy](#verification-and-testing-strategy)
- [Risk Register](#risk-register)
- [Decisions Log](#decisions-log)
- [UI Experience](#ui-experience)
- [Reference Resources](#reference-resources)

---

## Project Overview

Build a fully accessible wxPython desktop application that:

1. **Checks** PDFs for accessibility issues against PDF/UA and WCAG 2.2
2. **Edits** the full tag tree: change tag types, reparent, reorder, set attributes
3. **Manages** reading order for the entire PDF structure
4. **Builds** accessible forms with full control over field types, properties, and tab order
5. **Remediates** existing form fields (tooltips, names, required flags)
6. **Edits** alt text on images with a dedicated browsing panel
7. **Fixes** table headers with scope and association editing
8. **Tags** untagged content by manipulating content streams (BMC/EMC markers)
9. **Auto-tags** untagged PDFs using heuristic and ML-based detection
10. **Previews** the screen reader experience with a linearized text view of the tag tree in reading order
11. **Reports** findings with severity scoring, WCAG mapping, and CSV/Markdown export
12. **Packages** as a standalone Windows application via PyInstaller
13. **AI-Assisted Remediation** generates alt text via vision LLMs, provides AI-powered remediation guidance, and exposes an MCP server for agentic workflows in VS Code Copilot

The tool supports **two paths**:

- **Desktop path**: The wxPython GUI works fully offline with all 29+ built-in checks, guided remediation, and manual editing. No cloud dependency.
- **Agentic path**: When configured with a GitHub token, the tool uses vision LLMs via GitHub Models API for alt text generation, quality scoring, and remediation guidance. An MCP server exposes all scanning and fixing capabilities to VS Code Copilot agents.

Both paths share the same scanner engine, rule definitions, and fix tier classification. The tool itself must be fully operable with NVDA and JAWS screen readers, keyboard only, and in Windows High Contrast mode.

---

## Goals and Non-Goals

### Goals

- Full structure tree editing at the PDF object level
- Reading order management for every element in the document
- Property-driven form builder equally accessible to sighted and screen reader users
- Automated accessibility checking with and without veraPDF
- Alt text editing with image thumbnails
- Table header scope and association editing
- Content stream tagging (add BMC/EMC markers to untagged content)
- Heuristic auto-tagger for untagged PDFs with user review workflow
- Screen reader preview: linearized text view of the document as a screen reader would encounter it
- Markdown and CSV audit report generation
- NVDA and JAWS compatibility for the tool itself
- Open-source dependencies only (MPL-2.0, Apache-2.0, MIT, BSD)
- Single-exe distribution via PyInstaller

### Non-Goals (Out of Scope)

- OCR for scanned document images (recommend Adobe Acrobat for this)
- PDF/A conversion or conformance
- Digital signature application or verification
- Drag-and-drop visual form layout (property-driven approach chosen for accessibility)
- Web-based or browser-based interface
- macOS or Linux support in initial release (wxPython supports them, but testing is Windows-first)

---

## Target Users

- Small accessibility remediation teams (2 to 10 people)
- Document accessibility reviewers and QA staff
- Content creators who produce accessible PDFs from Word or other sources
- Government and higher education accessibility coordinators

Screen reader users (NVDA and JAWS) are first-class users of the tool itself.

---

## Technology Stack

| Component | Technology | License | Purpose |
|-----------|-----------|---------|---------|
| PDF manipulation | pikepdf 9.x or later | MPL-2.0 | Read/write PDF objects, structure tree, forms, metadata |
| PDF rendering | pypdfium2 4.x or later | Apache-2.0 / BSD | Render PDF pages to bitmaps for the page view panel |
| Desktop GUI | wxPython 4.2 or later | wxWindows Library Licence (LGPL-like) | Accessible native Windows UI with AUI panel management |
| Image processing | Pillow 10.x or later | MIT-like (HPND) | Bridge between pypdfium2 bitmaps and wx.Bitmap; image thumbnails |
| Config paths | platformdirs 4.x or later | MIT | Cross-platform user config and data directories |
| PDF/UA validation | veraPDF 1.26 or later | MPL-2.0 | Full PDF/UA conformance checking via CLI (optional, requires Java) |
| Auto-tagger ML | scikit-learn or similar | BSD-3-Clause | Text classification for heading, paragraph, list detection |
| Packaging | PyInstaller 6.x or later | GPL (build tool only, not bundled) | One-folder Windows exe distribution |
| AI alt text | tools/alt_text package | MIT (internal) | Vision-LLM alt text generation via GitHub Models API (opt-in) |
| AI communication | httpx 0.27+ | BSD-3-Clause | HTTP client for GitHub Models API calls |
| MCP server | FastMCP (mcp 1.x) | MIT | Model Context Protocol server for VS Code Copilot agent integration |
| PDF extraction | PyMuPDF 1.24+ | AGPL-3.0 | Image extraction from PDFs for AI alt text (agents extra only) |
| Office scanning | python-docx, openpyxl, python-pptx | MIT/MIT/MIT | Office document accessibility scanning (agents extra only) |

> **Note on PyMuPDF license**: PyMuPDF (AGPL-3.0) is used only for image extraction in the agents optional extra. It is not bundled in the standalone desktop distribution and is not required for core functionality.

### Why These Choices

- **pikepdf over pdfrw**: pikepdf has active development, a richer object model for raw PDF dictionary access, and is MPL-2.0 licensed.
- **pypdfium2 over PyMuPDF**: PyMuPDF is AGPL-licensed which restricts distribution. pypdfium2 wraps Google's PDFium engine under Apache-2.0.
- **wxPython over Qt/Tkinter**: Best native screen reader support on Windows via MSAA/UIA. AUI framework provides dockable panels. Mature accessibility story with `wx.Accessible` overrides.
- **veraPDF as optional**: Built-in checks cover the most common issues. Full PDF/UA validation requires Java, so veraPDF is a recommended but not required dependency.

---

## Architecture

### Layer Diagram

```
Application Layer
    main_frame.py ................... Main window, AUI panel management
    page_view_panel.py .............. Page bitmap display with overlays
    tag_tree_panel.py ............... Tag tree editor (wx.TreeCtrl)
    reading_order_panel.py .......... Reading order list with reorder
    alt_text_panel.py ............... Image browser and alt text editor
    table_editor_panel.py ........... Table header scope editor
    issues_panel.py ................. Accessibility findings list
    fields_list_panel.py ............ Form fields list and tab order
    field_properties_panel.py ....... Form field property editor
    field_placement.py .............. New field creation interface
    doc_properties_panel.py ......... Document metadata editor
    auto_tag_wizard.py .............. Auto-tagger review wizard
    sr_preview_panel.py ............. Screen reader preview (linearized text)

Core Engine Layer
    document.py ..................... PDF open/save, undo/redo command stack
    renderer.py ..................... pypdfium2 page rendering with caching
    struct_tree.py .................. Structure tree wrapper (critical module)
    tag_types.py .................... Standard PDF 2.0 tag type definitions
    content_parser.py ............... Content stream parser for marked content
    auto_tagger.py .................. Heuristic + ML auto-tagging engine
    sr_linearizer.py ................ Structure tree to screen reader text
    form_model.py ................... Form field read/write
    field_factory.py ................ New field creation and appearance streams
    table_model.py .................. Table structure grid model
    blank_pdf.py .................... New tagged PDF creation
    image_extractor.py .............. Image discovery and thumbnail generation
    validator.py .................... veraPDF integration (optional)
    builtin_checks.py ............... Built-in accessibility checks
    report.py ....................... Audit report generation
    preferences.py .................. User settings persistence

External Tools (optional)
    veraPDF CLI ..................... PDF/UA validation (requires Java)

AI Bridge Layer (optional, agents extra)
    ai_bridge.py .................... Connects desktop UI to AI capabilities

Agentic Toolkit Layer (optional, MCP server)
    tools/mcp_server.py ............. FastMCP server with 21+ tools for Copilot
    tools/scan_*.py ................. Scanners (PDF, Word, Excel, PowerPoint, ePub, Markdown)
    tools/fix_*.py .................. Fixers (PDF, Word, Excel, PowerPoint, ePub)
    tools/fix_tiers.py .............. Rule-to-tier classification (automated/assisted/manual)
    tools/report_md.py .............. Markdown audit report generator
    tools/report_html.py ............ HTML audit report generator
    tools/merge_results.py .......... Multi-document result aggregation
    tools/alt_text/ ................. Vision-LLM alt text package
        client.py ................... GitHub Models API client
        models.py ................... 10 vision model registry
        prompt.py ................... Layered prompt assembly
        profiles.py ................. 8 profiles (auto, informative, decorative, etc.)
        scorer.py ................... Alt text quality scoring (0-100)
        config.py ................... Configuration dataclass
        auth.py ..................... GitHub token resolution
        extractor_pdf.py ............ PDF image extraction (PyMuPDF)
        extractor_docx.py ........... Word image extraction
        extractor_xlsx.py ........... Excel image extraction
        extractor_pptx.py ........... PowerPoint image extraction
        extractor_epub.py ........... ePub image extraction
        parser.py ................... LLM response parser
        formats.py .................. Output format adapters
```

### Design Principles

1. **Command pattern for all edits**: Every user action that modifies the PDF creates a reversible Command object. The undo/redo stack holds all commands. This protects against corruption by making every change reversible.

2. **Structure tree as the single source of truth**: All panels (tag tree, reading order, alt text, table editor) read from and write to the same in-memory `StructTree` model. Changes in one panel are immediately reflected in all others.

3. **Rendering is read-only**: pypdfium2 renders pages for display only. Page content is never modified through the renderer. All modifications go through pikepdf's object model.

4. **Accessibility is not a phase**: Every panel is designed for screen reader and keyboard access from the start. Phase 11 (Tool Accessibility) is a final audit and polish pass, not the first time accessibility is considered.

5. **veraPDF is optional**: The tool works without Java installed. Built-in checks cover the 80-percent case. A first-run wizard detects veraPDF or lets the user skip it.

---

## Phase 1: Project Skeleton and Core PDF Engine

**Goal**: Establish project structure, PDF open/save, page rendering, and the main UI shell.

### Step 1.1: Project Structure

Create the repository layout:

```
pdf-a11y-tool/
    pyproject.toml
    README.md
    LICENSE
    pdf-a11y-tool.spec          (PyInstaller build spec)
    src/
        pdf_a11y/
            __init__.py
            __main__.py         (entry point: python -m pdf_a11y)
            app.py              (wx.App subclass, startup)
            core/
                __init__.py
                document.py
                renderer.py
                struct_tree.py
                tag_types.py
                content_parser.py
                auto_tagger.py
                sr_linearizer.py
                form_model.py
                field_factory.py
                table_model.py
                blank_pdf.py
                image_extractor.py
                validator.py
                builtin_checks.py
                report.py
                preferences.py
            ui/
                __init__.py
                main_frame.py
                page_view_panel.py
                tag_tree_panel.py
                reading_order_panel.py
                alt_text_panel.py
                table_editor_panel.py
                issues_panel.py
                fields_list_panel.py
                field_properties_panel.py
                field_placement.py
                doc_properties_panel.py
                auto_tag_wizard.py
                sr_preview_panel.py
    tests/
        __init__.py
        conftest.py
        test_document.py
        test_struct_tree.py
        test_form_model.py
        test_field_factory.py
        test_table_model.py
        test_validator.py
        test_builtin_checks.py
        test_report.py
        test_content_parser.py
        test_auto_tagger.py
        test_sr_linearizer.py
        fixtures/
            tagged.pdf          (known-good tagged PDF for testing)
            untagged.pdf        (untagged PDF for auto-tagger testing)
            form.pdf            (PDF with form fields)
            tables.pdf          (PDF with complex tables)
            images.pdf          (PDF with figures and alt text)
            bad.pdf             (PDF with many accessibility issues)
    docs/
        keyboard-shortcuts.md
        user-guide.md
```

`pyproject.toml` configuration:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pdf-a11y-tool"
version = "0.1.0"
description = "Accessible PDF remediation, form building, and auto-tagging tool"
requires-python = ">=3.11"
license = "MIT"
dependencies = [
    "pikepdf>=9.0",
    "pypdfium2>=4.0",
    "wxPython>=4.2",
    "Pillow>=10.0",
    "platformdirs>=4.0",
    "scikit-learn>=1.4",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.6",
    "mypy>=1.11",
    "pyinstaller>=6.0",
]

[project.scripts]
pdf-a11y-tool = "pdf_a11y.__main__:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true
```

### Step 1.2: PDF Document Model

`core/document.py` -- the central model that all panels interact with.

Responsibilities:

- Open a PDF file via `pikepdf.open()`, hold the `pikepdf.Pdf` object
- Save / Save As via `pikepdf.Pdf.save()`
- Page enumeration: count, get page by index, get page dimensions
- Metadata access: title, author, subject, language (read/write)
- Undo/redo stack using the Command pattern:
  - `Command` base class with `execute()` and `undo()` methods
  - `CommandStack` with `push()`, `undo()`, `redo()`, `can_undo`, `can_redo`
  - Every modification to the PDF creates a `Command` subclass instance
  - Commands are grouped for compound operations (e.g., "add form field" creates both an AcroForm entry and a structure element)
- Dirty flag: tracks whether unsaved changes exist
- Event notification: wx event broadcast when document changes (panels subscribe)

### Step 1.3: Page Renderer

`core/renderer.py` -- renders PDF pages to wx.Bitmap for display.

Responsibilities:

- Render a single page at a given DPI (default 150 for screen, configurable)
- Return a `wx.Bitmap` suitable for display in a `wx.StaticBitmap` or custom panel
- Zoom support: 50 percent to 400 percent in steps
- Page cache: LRU cache of rendered bitmaps (configurable size, default 10 pages)
- Background rendering: render on a worker thread, deliver result via `wx.CallAfter()`
- Coordinate mapping: convert between page points (PDF coordinates) and screen pixels at current zoom

### Step 1.4: Main Application Shell

`ui/main_frame.py` -- the primary window.

Layout (AUI-managed dockable panels):

```
+-------------------------------------------------------+
| Menu Bar                                              |
+-------------------------------------------------------+
| Toolbar: Open | Save | Check | Undo | Redo | Zoom    |
+------------------+------------------------------------+
| Tag Tree Panel   | Page View Panel                    |
| (left, 300px)    | (center, fills remaining space)    |
|                  |                                    |
|                  |                                    |
|                  |                                    |
+------------------+-----------------+------------------+
| Reading Order    | Properties Panel                   |
| Panel            | (field props, doc props, or        |
| (bottom-left)    |  element attributes depending on   |
|                  |  selection context)                 |
+------------------+-----------------+------------------+
| Issues / Fields / Alt Text / Table Editor / SR Preview (tabbed) |
| (bottom, full width)                                            |
+-------------------------------------------------------+
| Status Bar: Page 1 of 12 | 3 errors, 2 warnings | Zoom: 100% |
+-------------------------------------------------------+
```

Menus:

- **File**: New Blank PDF, Open (Ctrl+O), Save (Ctrl+S), Save As (Ctrl+Shift+S), Recent Files, Exit (Alt+F4)
- **Edit**: Undo (Ctrl+Z), Redo (Ctrl+Y), Preferences
- **View**: Toggle panels (Tag Tree, Reading Order, Issues, Fields, Alt Text, Tables, SR Preview), Toggle Reading Order Overlay (Ctrl+Shift+O), Screen Reader Preview (Ctrl+Shift+R), Zoom In (Ctrl+=), Zoom Out (Ctrl+-), Fit Page (Ctrl+0)
- **Check**: Run Full Check (F5), Run Built-in Checks Only, Run veraPDF Only, Export Report
- **Tags**: Change Type submenu, Add Child Element, Delete Element, Set Alt Text, Set Language, Auto-Tag Document
- **Forms**: Add Text Field, Add Checkbox, Add Radio Group, Add Dropdown, Add Button, Field Properties
- **Tools**: Generate Bookmarks from Headings, Set Document Title, Set Document Language, veraPDF Setup
- **Help**: Keyboard Shortcuts (Ctrl+/), User Guide, About

Keyboard navigation:

- F6 cycles focus between panels (Tag Tree, Page View, Properties, Bottom tabs)
- Ctrl+Tab cycles tabs in the bottom panel (Issues, Fields, Alt Text, Tables, SR Preview)
- All menu items have accelerator keys
- Toolbar buttons have keyboard equivalents

Accessibility:

- All panels have `SetName()` with descriptive labels
- Menu items have accessible descriptions
- Status bar updates announced via `wx.Accessible` or `wx.Bell` for significant changes
- Focus is managed: opening a dialog traps focus, closing returns to previous

**Phase 1 depends on**: Nothing. This is the foundation.

---

## Phase 2: Accessibility Checker

**Goal**: Scan a PDF and report all accessibility issues with severity, WCAG mapping, and actionable guidance.

### Step 2.1: veraPDF Integration

`core/validator.py`

Responsibilities:

- Detect veraPDF installation: check preferences, then scan PATH and common install locations (`C:\Program Files\veraPDF`, `C:\veraPDF`)
- Run veraPDF CLI via `subprocess.run()` with arguments: `--format xml --profile ua1` (PDF/UA-1 profile)
- Parse XML output into a list of `Finding` dataclass objects:
  ```python
  @dataclass
  class Finding:
      rule_id: str          # e.g., "PDFUA.TITLE"
      severity: str         # "error", "warning", "tip"
      wcag: str             # e.g., "2.4.2"
      description: str      # human-readable explanation
      page: int | None      # page number if applicable
      element: str | None   # element identifier if applicable
      confidence: str       # "high", "medium", "low"
      remediation: str      # keyboard-first fix using PDF Accessibility Tool
      acrobat_remediation: str  # equivalent fix using Adobe Acrobat Pro
  ```
- Map veraPDF rule IDs to internal PDFUA/PDFBP rule IDs and WCAG 2.2 success criteria
- Timeout handling: default 60 seconds, configurable. Kill process and report timeout on failure
- Error recovery: if veraPDF crashes or returns invalid XML, report the error as a finding

### Step 2.2: Built-in Checks

`core/builtin_checks.py`

Checks that run without veraPDF (pure pikepdf inspection):

| Check | Rule ID | WCAG | Severity |
|-------|---------|------|----------|
| Missing document title | PDFUA.TITLE | 2.4.2 | Error |
| Missing document language | PDFUA.LANG | 3.1.1 | Error |
| Invalid BCP 47 language code | PDFBP.LANG_VALID | 3.1.1 | Error |
| PDF is not tagged (no StructTreeRoot) | PDFUA.TAGGED | 1.3.1 | Error |
| Image (Figure) without alt text | PDFUA.IMG.ALT | 1.1.1 | Error |
| Figure alt text exceeds 250 characters | PDFBP.ALT_LENGTH | 1.1.1 | Warning |
| Figure alt text is filename or placeholder (e.g., DSC_0042.jpg, image1) | PDFBP.ALT_QUALITY | 1.1.1 | Warning |
| Form field without tooltip (TU) | PDFUA.FORMS | 4.1.2 | Error |
| Form field without name (T) | PDFUA.FORMS | 4.1.2 | Error |
| Duplicate form field names (non-radio) | PDFBP.FORMS.DUPLICATE_NAMES | 4.1.2 | Error |
| Radio button group with only 1 option | PDFBP.FORMS.RADIO_GROUP | 4.1.2 | Warning |
| Generic/non-descriptive form field tooltip | PDFBP.FORMS.TOOLTIP_QUALITY | 4.1.2 | Warning |
| Missing bookmarks (no Outlines) | PDFUA.BOOKMARKS | 2.4.1 | Warning |
| Empty structure tree (tagged but no elements) | PDFUA.TAGGED | 1.3.1 | Error |
| Heading hierarchy gap (H1 then H3, no H2) | PDFUA.HEADINGS | 2.4.6 | Warning |
| Table without header cells (no TH elements) | PDFBP.TABLE_HEADERS | 1.3.1 | Warning |
| TH cell without Scope attribute | PDFBP.TABLE_SCOPE | 1.3.1 | Warning |
| DisplayDocTitle not set | PDFBP.DISPLAY_TITLE | 2.4.2 | Warning |
| No headings at all (tagged document with zero H1-H6 tags) | PDFBP.NO_HEADINGS | 2.4.6 | Warning |
| Non-standard tag (e.g., InlineShape) without alt text or artifact marking | PDFBP.NONSTD_NO_ALT | 1.1.1 | Warning |
| Empty content tags (P, Span, etc. with no children -- screen readers say "blank") | PDFBP.EMPTY_TAGS | 1.3.1 | Warning |
| List structure invalid (L without LI, or LI without LBody) | PDFBP.LIST_STRUCT | 1.3.1 | Warning |
| Caption tag not adjacent to its Figure | PDFBP.FIGURE_CAPTION | 1.1.1 | Tip |
| Art tags present (often indicate messy structure needing cleanup) | PDFBP.ART_TAGS | 1.3.1 | Tip |
| Excessive Sect nesting (>3 levels, common in PowerPoint exports) | PDFBP.SECT_NESTING | 1.3.1 | Tip |
| Flat structure (all elements are direct children of Document, no /Sect grouping) | PDFBP.FLAT_STRUCTURE | 1.3.1 | Tip |
| Non-descriptive link text ("click here", "read more", raw URLs) | PDFBP.LINK_TEXT | 2.4.4 | Warning |
| Tab order not set to structure order (/Tabs /S) | PDFBP.NAV.TABORDER | 2.4.3 | Warning |
| Scanned/image-only PDF with no extractable text | PDFBP.TEXT.EXTRACTABLE | 1.1.1 | Error |
| Underscore fill lines in tagged content (screen readers read each underscore aloud) | PDFBP.UNDERSCORE_FILL | 1.3.1 | Warning |
| Form fields detached from labels in reading order (all fields grouped at end of structure) | PDFBP.FORMS_DETACHED | 1.3.2 | Error |
| Suspicious reading order (structure order differs greatly from visual position) | PDFBP.READING_ORDER | 1.3.2 | Tip |
| Orphaned form tag (AcroForm field with no matching /Form structure element) | PDFBP.ORPHAN_FIELD | 4.1.2 | Error |
| Form field not adjacent to its label in reading order | PDFBP.FIELD_LABEL_ORDER | 1.3.1 | Warning |
| Likely decorative element not marked as artifact (InlineShape, thin rule, repeated header/footer) | PDFBP.DECORATIVE_NOT_ARTIFACT | 1.1.1 | Warning |
| Insufficient color contrast (text foreground vs background below 4.5:1 or 3:1 for large text) | PDFBP.CONTRAST | 1.4.3 | Warning |

Each check returns zero or more `Finding` objects using the same dataclass as veraPDF findings.

#### Built-in Color Contrast Checker (PDFBP.CONTRAST)

This check uses pypdfium2 rendering to detect insufficient color contrast without requiring veraPDF or Java. No AI or Copilot SDK is needed -- this is pixel-level color analysis.

Algorithm:

1. For each page, render the page at 150 DPI using pypdfium2.
2. For each text-bearing structure element (P, H1-H6, Span, LI, TH, TD, Link, etc.), determine its bounding box from the structure tree's content region mapping.
3. Sample foreground pixel colors: render the page region and identify the dominant non-background color in the text area (using the rendered bitmap, not content stream color operators, which avoids the complexity of parsing color spaces).
4. Sample background pixel colors: sample pixels immediately surrounding the text bounding box to determine the background color.
5. Calculate the WCAG 2.2 relative luminance contrast ratio using the standard formula:
   ```
   L = 0.2126 * R + 0.7152 * G + 0.0722 * B  (after sRGB linearization)
   ratio = (L1 + 0.05) / (L2 + 0.05)  where L1 is the lighter luminance
   ```
6. Classify text as "large" (14pt bold or 18pt+) or "normal" based on font size from the content stream.
7. Flag findings where the ratio is below 4.5:1 (normal text) or 3:1 (large text).
8. Each finding includes the measured ratio, the sampled foreground and background hex colors, and the element's text preview, so the user knows exactly what to look at.

**Performance**: This check is slower than the other built-in checks because it requires page rendering. It runs in a background thread and reports progress: "Checking contrast... page 3 of 12." The user can skip this check via a checkbox in the Run Check dialog.

**Limitations**: Pixel sampling is an approximation. Gradients, textured backgrounds, and overlapping content can produce false positives. The check reports confidence: "high" for solid-color text on solid-color background, "medium" for text on images or gradients. Users are advised to verify medium-confidence findings visually or with a dedicated contrast tool.

#### Orphaned Form Tag Check (PDFBP.ORPHAN_FIELD)

Detects AcroForm fields that have no corresponding /Form structure element in the tag tree:

1. Walk the structure tree and collect all StructElem nodes with tag /Form. Record the widget annotation each links to.
2. Walk the AcroForm /Fields array and collect all field dictionaries.
3. Any field in AcroForm but not linked from a /Form StructElem is "orphaned" -- screen readers cannot discover it via the tag tree.
4. Also detects the reverse: /Form StructElem nodes that reference annotations not present in AcroForm (dead references).

The "Fix Now" action (see Guided Remediation) creates a /Form StructElem and links it to the orphaned field, or offers to delete dead references.

#### Form Field Label Order Check (PDFBP.FIELD_LABEL_ORDER)

Detects form fields that are not adjacent to their labels in reading order:

1. For each /Form element, identify its likely label (previous sibling /P, or /P within 24 points visual proximity).
2. If the /Form element is more than 1 sibling away from its label, flag it.
3. The finding includes both the field name and the label text, so the user can verify the association.

The "Align Fields to Labels" action in the Reading Order panel fixes these in batch.

#### Decorative Element Detection (PDFBP.DECORATIVE_NOT_ARTIFACT)

Auto-detects elements that are likely decorative and should be marked as artifacts:

1. **Non-standard tags with no alt text**: InlineShape, Textbox, and other Word-generated tags that are visual-only.
2. **Thin horizontal rules**: Content regions whose rendered height is less than 3 points and width spans more than 50% of the page. These are typically decorative separators.
3. **Repeated headers/footers**: Text elements that appear in the same position on 3+ consecutive pages with identical or near-identical content (page numbers, document titles, confidentiality notices).
4. **Underscore runs**: Text content consisting entirely of underscore characters ("_____") used as visual fill lines in forms -- these are meaningless to screen readers and should be artifacts.

The "Mark All Decorative as Artifacts" batch action in the Tag Tree panel fixes all detected decorative elements in one action.

#### Underscore Fill Line Detection (PDFBP.UNDERSCORE_FILL)

Detects text content that consists primarily of underscore characters used as visual fill lines in form labels. These are a holdover from print-era forms (e.g., "Name ___________________________") and create two accessibility problems:

1. **Screen readers read each underscore aloud**: NVDA and JAWS announce "underscore underscore underscore underscore..." for each character, which is disorienting and time-consuming.
2. **Redundant with form fields**: If the PDF already has a form field overlaid on the underscore line, the underscores serve no purpose for assistive technology -- the form field's tooltip provides the label.

Algorithm:

1. Walk the structure tree and identify all text-bearing /P elements.
2. For each /P element, extract its text content via MCID-to-content-stream mapping (or pypdfium2 text extraction within the element's bounding box).
3. Count underscore characters in the extracted text. If underscores make up more than 30% of the total characters and the text contains at least 10 consecutive underscores, flag it.
4. Cross-reference with AcroForm fields: if a form field's bounding box overlaps the underscore region, the finding severity is "warning" (the underscore is redundant). If no form field exists, severity is "tip" (underscores may be the only input method in a print form).
5. Each finding includes the text preview (truncated to 60 characters), the underscore percentage, and whether a form field overlaps.

The "Fix Now" action for this check offers:
- **Mark underscores as artifact** (preserves the label text, removes only the underscore portion): for elements where the label text is meaningful but the underscores are noise.
- **Mark entire element as artifact** (removes the whole P tag): for elements that are fully redundant with an overlapping form field.
- **Skip**: leave unchanged.

The batch action "Clean All Underscore Fills" processes all flagged elements at once, using the form-field-overlap heuristic to auto-decide: if a form field overlaps, mark underscores as artifact; if no overlap, mark as tip for manual review.

This check is a strong example of why the tool must adapt to arbitrary PDF documents. Microsoft Word, Google Docs, LibreOffice, and InDesign all produce different underscore patterns. The heuristic (30% threshold, 10-character minimum) was derived from scanning real-world government and university forms and works across these generators.

#### Form Fields Detached from Labels (PDFBP.FORMS_DETACHED)

Detects form fields that are grouped together at the end (or beginning) of the document structure, completely separated from their label content. This is a severe reading order problem:

1. Count the total number of /Form structure elements and their positions in the depth-first reading order.
2. Count the total number of text-bearing structure elements (/P, /H1-H6, /Span, etc.).
3. If more than 50% of /Form elements appear in a contiguous block at the end (or beginning) of the reading order, with no text-bearing elements interleaved, flag as error.
4. The finding reports: "N of M form fields are grouped at reading order positions X-Y, after all page content. Screen readers encounter all text first, then all fields, making it impossible to associate fields with their labels."
5. Cross-reference: for each form field in the block, identify its likely label (by tooltip text matching a nearby /P element's text content). Report label-field distances.

This check catches the most common reading order defect in Word-generated PDFs: Microsoft Word's PDF export appends all form fields as direct children of /Document after all content, regardless of their visual position on the page.

The "Fix Now" action for this check runs the Auto-Sort Reading Order on the form field block, interleaving fields with their likely labels based on visual position. The user previews the proposed order before applying.

### Step 2.3: Issues Panel

`ui/issues_panel.py`

- `wx.dataview.DataViewListCtrl` with columns: Severity (icon + text), Rule ID, WCAG, Description, Page, Element
- Column headers are sortable (click to sort, screen reader announces sort state)
- Filter bar: dropdown for severity (All, Errors, Warnings, Tips) and text search
- Activating a row (Enter or double-click) navigates the page view to the relevant page and selects the element in the tag tree panel
- Row context menu: "Go to Element", "Learn More" (opens WCAG quick reference URL in browser), "Dismiss" (mark as reviewed, does not fix), "Fix Now" (applies the most common automatic fix for this issue, see Guided Remediation below)
- Status line at bottom: "12 errors, 5 warnings, 3 tips (20 total)"
- Accessible: column headers announced, cell content readable by SR, filter state announced

### Step 2.3a: Guided Remediation (Fix Now)

When the user presses **Enter** or selects "Fix Now" from the context menu on an issue, the tool applies a one-action fix where possible. This directly addresses the pain point of users who cannot follow multi-step remediation instructions.

**Automatic fixes (no dialog needed):**

| Finding | Fix Applied |
|---------|-------------|
| PDFUA.TITLE | Opens the Title text input dialog (one field, pre-focused) |
| PDFUA.LANG | Opens the Language picker dialog (one dropdown, pre-focused) |
| PDFBP.DISPLAY_TITLE | Sets DisplayDocTitle to true. No dialog. Announced: "Fixed: Display Document Title enabled." |
| PDFUA.BOOKMARKS | Runs "Generate Bookmarks from Headings" automatically if headings exist. If no headings, announces: "Cannot generate bookmarks -- add headings first." |
| PDFBP.NONSTD_NO_ALT | Opens a targeted dialog: "This InlineShape appears decorative. [Mark as Artifact] [Set Alt Text] [Skip]" with Mark as Artifact as the default focused button. |
| PDFBP.ORPHAN_FIELD | Opens a dialog: "Form field 'Name' has no structure element. [Create /Form tag and link] [Delete orphaned field] [Skip]" |
| PDFBP.DECORATIVE_NOT_ARTIFACT | Marks the element as artifact immediately. Announced: "Marked as artifact." Undoable with Ctrl+Z. |
| PDFBP.TABLE_SCOPE | Opens a simplified Scope picker: "Set scope for this header cell: [Row] [Column] [Both] [Skip]" with auto-detection of likely scope based on position (first row = Column, first column = Row). |
| PDFBP.FIELD_LABEL_ORDER | Automatically moves the form field to be adjacent to its detected label. Announced: "Moved field after its label in reading order." Undoable. |
| PDFBP.CONTRAST | Navigates to the element on the page view and opens the contrast details dialog showing the measured ratio, affected text, and suggested color alternatives. No auto-fix (color changes require content stream editing). |
| PDFBP.UNDERSCORE_FILL | Opens a targeted dialog: "This text contains N underscores (redundant with form field). [Mark underscores as artifact] [Mark entire element as artifact] [Skip]" with auto-detection of form field overlap. |
| PDFBP.FORMS_DETACHED | Runs Auto-Sort Reading Order on the detached block. Opens the preview dialog showing proposed interleaved order. User confirms with Enter or cancels with Escape. |

**Batch Fix All**: A "Fix All Auto-Fixable" button at the top of the Issues panel applies all automatic fixes in one pass. A confirmation dialog lists what will change. The entire batch is a single compound command (one Ctrl+Z undoes all). Screen reader announces: "Fixed 8 of 14 issues automatically. 6 remaining issues require manual review."

All automatic fixes are undoable. The tool never makes irreversible changes without explicit user confirmation.

### Step 2.4: Report Export

`core/report.py`

Two export formats, each generated **per audience** (PDF Accessibility Tool users and Adobe Acrobat Pro users):

**ReportAudience enum**:

- `TOOL` -- Remediation instructions reference PDF Accessibility Tool shortcuts and panels.
- `ACROBAT` -- Remediation instructions reference Adobe Acrobat Pro menus and dialogs.

The `ReportGenerator` class exposes:

- `generate(fmt, audience)` -- returns report text for one audience.
- `write(fmt, path, audience)` -- writes one report file.
- `write_all(fmt, output_dir, stem)` -- writes both audience reports at once (e.g., `AUDIT-tool.md` and `AUDIT-acrobat.md`).

**Markdown** (AUDIT-tool.md / AUDIT-acrobat.md):

- Audit Information: date, tool version, file name, remediation tool label, veraPDF version if used
- Executive Summary: totals by severity, overall score, grade, most common issue
- Findings by Page: grouped by page number with rule ID, WCAG, description, and remediation for the selected audience only
- Findings by Rule: cross-reference showing how many times each rule was triggered
- What Passed: categories with no findings
- Remediation Priority: ordered by impact (Immediate / Soon / When Possible), each item with audience-specific fix instructions
- Accessibility Scorecard: `Score = 100 - sum(weighted_findings)`, grades A through F

**CSV** (AUDIT-tool.csv / AUDIT-acrobat.csv):

- One row per finding: Rule ID, Severity, WCAG, Page, Element, Description, Remediation (audience-specific column header)
- Compatible with Excel, Google Sheets, and screen reader table navigation

**Separate Reports Design**:

Every finding carries two remediation paths (stored on the `Finding` dataclass), but each generated report includes **only** the instructions for its target audience:

1. **PDF Accessibility Tool report** (`remediation` field): Keyboard-first instructions using this application. All steps reference keyboard shortcuts (Alt+Enter, F2, Ctrl+X/V, Space, Tab, Enter) and avoid mouse-only language. No "click", "drag", or "hover" -- every action is operable via keyboard.
2. **Adobe Acrobat Pro report** (`acrobat_remediation` field): Equivalent steps for users who have Acrobat Pro. References Acrobat's Tags panel, Properties dialog (Ctrl+E), Accessibility tools, and standard workflows.

This separation keeps each report focused and avoids confusing users with instructions for a tool they may not have.

**Phase 2 depends on**: Phase 1 (document model and UI shell).

---

## Phase 3: Structure Tree and Full Tag Editor

**Goal**: Visualize and edit the complete PDF tag tree, manage reading order for every element in the document.

This is the most technically demanding phase. The structure tree wrapper is the single most critical custom module in the project.

### Step 3.1: Structure Tree Wrapper

`core/struct_tree.py`

The in-memory model that bridges pikepdf's raw PDF dictionaries and the UI panels.

Data model:

```python
@dataclass
class StructNode:
    """One node in the structure tree, corresponding to a PDF StructElem."""
    tag: str                    # /S value: "P", "H1", "Table", etc.
    page: int | None            # page index if this element has page content
    alt_text: str               # /Alt
    actual_text: str            # /ActualText
    expansion_text: str         # /E
    language: str               # /Lang
    attributes: dict            # /A attribute dictionary (Scope, Headers, etc.)
    mcids: list[int]            # marked content IDs linking to content stream
    children: list[StructNode]  # /K child elements (ordered -- this IS reading order)
    parent: StructNode | None   # /P parent reference
    pdf_obj: pikepdf.Object     # reference to the underlying pikepdf indirect object
    node_id: str                # unique ID for UI tracking
    remediation_status: str     # "unchecked", "action_needed", "done", "manual_done"
    last_finding_ids: list[str] # rule IDs of current findings for this element
```

Operations (all return Command objects for undo/redo):

| Operation | What It Does | Complexity |
|-----------|-------------|-----------|
| `change_tag(node, new_tag)` | Change `/S` on a StructElem (e.g., P to H2) | Low |
| `set_alt_text(node, text)` | Set `/Alt` attribute | Low |
| `set_actual_text(node, text)` | Set `/ActualText` attribute | Low |
| `set_expansion_text(node, text)` | Set `/E` attribute | Low |
| `set_language(node, lang)` | Set `/Lang` attribute (BCP 47 code) | Low |
| `set_attribute(node, key, value)` | Set arbitrary attribute in `/A` dict | Low |
| `reorder_children(parent, new_order)` | Rearrange `/K` array (changes reading order) | Medium |
| `move_up(node)` / `move_down(node)` | Swap with adjacent sibling in parent's `/K` | Medium |
| `reparent(node, new_parent, index)` | Move node to new parent, update `/P` refs, update both `/K` arrays | Medium |
| `add_child(parent, tag, index)` | Create new StructElem as child of parent | Medium |
| `delete(node)` | Remove from parent's `/K`, recurse children (option: reparent children to grandparent or delete all) | Medium |
| `rebuild_parent_tree()` | Recalculate `/ParentTree` from scratch after edits | High |

ParentTree management:

The `/ParentTree` is a number tree that maps (page_index, mcid) pairs to structure elements. After any structural edit, rather than trying to incrementally update `/ParentTree`, the tool rebuilds it entirely from a depth-first walk of the structure tree. This is safer (avoids sync bugs) at the cost of being slightly slower on very large documents.

### Step 3.2: Tag Types Reference

`core/tag_types.py`

Constant definitions for all standard structure element types from PDF 2.0 and PDF/UA:

```python
@dataclass
class TagType:
    name: str               # "P", "H1", "Table", etc.
    category: str           # "grouping", "block", "inline", "table", "illustration"
    description: str        # "Paragraph" -- for UI display and SR announcement
    allowed_children: list  # which tag types can be children
    allowed_parents: list   # which tag types can be parents
```

Categories and types:

**Grouping elements**: Document, Part, Sect, Div, Art, BlockQuote, Caption, TOC, TOCI, Index, NonStruct, Private

**Block-level elements**: H (generic heading), H1 through H6 (specific level headings), P (paragraph), L (list), LI (list item), Lbl (label), LBody (list body)

**Table elements**: Table, THead, TBody, TFoot, TR (row), TH (header cell), TD (data cell)

**Inline elements**: Span, Quote, Note, Reference, BibEntry, Code, Link, Annot

**Illustration elements**: Figure, Formula, Form

**Ruby and Warichu**: Ruby, RB, RT, RP, Warichu, WT, WP

**Role mapping**: The `/RoleMap` dictionary maps custom tag names to standard types. The tool reads this map and displays both the custom name and its standard role. The role map editor allows adding, editing, and removing custom mappings.

### Step 3.3: Tag Tree Panel

`ui/tag_tree_panel.py`

A wx.TreeCtrl filling the left panel of the application.

Display per node: `[icon] [status] TagName -- "content preview text..." (page N)`

- Icons differ by category (heading icon, paragraph icon, table icon, figure icon, form icon)
- Content preview is the first 40 characters of actual text or alt text
- Page number shown if the element has page content
- **Status indicator**: A colored dot or text prefix shows the remediation state of each node:
  - Green checkmark / "Done": All accessibility requirements met for this element
  - Yellow warning / "Action needed": One or more issues detected (links to specific findings)
  - No indicator: Element has not been checked yet or has no applicable rules
- Screen readers announce the status as part of the item name: "H1, Done, Introduction, page 1" or "Figure, Action needed, page 3, no alt text"

**Text-based tree summary**: Above the tree, a read-only text area shows a plain-text summary of the selected element and its context in the reading order:

```
Position: 5 of 47 (sibling 3 of 8 under Document)
Tag: /P (Paragraph)
Content: "This form is not necessary for asthma..."
Page: 1
Previous sibling: /Figure -- "UA Youth Protection logo" (page 1)
Next sibling: /InlineShape -- no alt text (page 1)
Parent: /Document
Children: none (leaf element)
Status: Done -- no issues
```

This summary gives screen reader users immediate spatial context without needing to expand/collapse tree nodes or count arrow presses. It answers: "Where am I? What is around me? What needs fixing?"

**Toolbar above the tree** (visible buttons with keyboard equivalents):

| Button | Label | Shortcut | Action |
|--------|-------|----------|--------|
| Up arrow | "Move Up" | Alt+Up | Move element earlier in sibling order (reading order) |
| Down arrow | "Move Down" | Alt+Down | Move element later in sibling order (reading order) |
| Left arrow | "Move Out" | Alt+Left | Reparent element to grandparent (move up one level) |
| Right arrow | "Move In" | Alt+Right | Reparent element as last child of previous sibling (nest deeper) |
| Lightbulb | "Next Action" | Ctrl+Shift+N | Show the recommended next remediation action (same as context menu, see below) |
| Checkmark | "Mark Done" | Ctrl+Shift+D | Manually mark element as remediated (overrides auto-detection) |

These buttons ensure that reordering and reparenting are discoverable for users who do not know the keyboard shortcuts. Each button is labeled and keyboard-focusable.

**Drag and drop** (sighted user convenience):

- Sighted users can drag a tree node and drop it onto another node to reparent, or between nodes to reorder.
- Drop targets are highlighted: blue line between nodes = insert as sibling, blue highlight on node = insert as child.
- A confirmation dialog appears after drop: "Move /P to be a child of /Sect? [OK] [Cancel]"
- Drag and drop is a convenience feature. Every drag-and-drop operation is also available through keyboard: Alt+Up/Down for reorder, Alt+Left/Right for reparent, Ctrl+X/V for arbitrary moves.
- Screen reader users are never required to use drag and drop. The toolbar buttons and keyboard shortcuts provide identical functionality.

Keyboard operations:

| Key | Action |
|-----|--------|
| Arrow keys | Navigate tree |
| Enter | Select element and show on page view |
| F2 | Rename / change tag type (opens dropdown) |
| Delete | Delete element (confirmation dialog) |
| Ctrl+X | Cut element (for reparenting) |
| Ctrl+V | Paste element as child of selected node |
| Alt+Up | Move element up within parent (reorder) |
| Alt+Down | Move element down within parent (reorder) |
| Alt+Left | Move element out to grandparent (reparent up one level) |
| Alt+Right | Move element in as child of previous sibling (reparent deeper) |
| Ctrl+Alt+A | Set alt text (opens edit dialog) |
| Ctrl+Alt+L | Set language (opens BCP 47 picker) |
| Ctrl+Shift+N | Show next recommended action for this element |
| Ctrl+Shift+D | Toggle manual "done" status on this element |

Context menu (right-click or Shift+F10):

- **Next Action** (top of menu, bold): Shows the most important remediation action for this element. This is context-sensitive -- the tool analyzes the element's current state and recommends the single most impactful next step. Examples:
  - For a /Figure with no alt text: "Next: Set alt text (Ctrl+Alt+A)"
  - For a /P that looks like a heading (bold, large font): "Next: Change tag to H2 (F2)"
  - For a /TH with no Scope: "Next: Set header scope (open Table Editor)"
  - For an /InlineShape (decorative): "Next: Mark as artifact (Delete > Artifact)"
  - For a /Form with no tooltip: "Next: Set tooltip in Field Properties"
  - For a /Table with no THead: "Next: Add THead wrapper (Table Editor)"
  - For an element with all issues resolved: "All done -- no remaining issues" (grayed out, informational)
- Separator
- Change Type (submenu with all standard types, grouped by category)
- Mark as Artifact (removes element from structure tree; content becomes invisible to screen readers -- use for decorative elements like horizontal rules, background images, and page numbers)
- Mark All Decorative as Artifacts (batch operation: auto-detects likely decorative elements -- InlineShapes, thin horizontal rules, repeated page headers/footers, underscores used as visual separators -- and marks them all as artifacts in one action; shows a confirmation list before applying; single compound command for undo)
- Set Alt Text
- Set Actual Text
- Set Language
- Add Child Element (submenu by type)
- Reparent To (target picker)
- Move Up / Move Down / Move Out / Move In
- Delete (with confirmation)
- Properties (open full attribute editor)
- Separator
- **Mark as Done** / **Mark as Needs Review**: Toggle the element's remediation status. "Mark as Done" sets the green checkmark. "Mark as Needs Review" clears it. This is useful when the user has fixed an issue outside the tool (e.g., in the source Word document) and wants to track progress.

**Next Action intelligence** -- how the tool determines the recommendation:

1. The tool runs the built-in checks against the single selected element (not a full document scan -- just the applicable checks for this element type).
2. If there are findings, the highest-severity finding becomes the "Next Action" recommendation. The recommendation text includes the specific fix and its keyboard shortcut.
3. If there are no findings from built-in checks, the tool applies heuristic recommendations:
   - /P elements with bold text and short length: "Consider changing to a heading tag"
   - /Form elements adjacent to unlabeled /P elements: "Consider grouping with label"
   - Elements with role-mapped custom tags: "Consider replacing with standard tag"
4. If there are no findings and no heuristic recommendations: "All done -- no remaining issues."
5. The recommendation is shown in three places simultaneously:
   - The context menu "Next Action" item
   - The text-based summary area above the tree
   - The status bar when the element is selected

**Completion tracking per element:**

Each StructNode in the in-memory model gets two additional fields:

```python
@dataclass
class StructNode:
    # ... existing fields ...
    remediation_status: str   # "unchecked", "action_needed", "done", "manual_done"
    last_finding_ids: list[str]  # rule IDs of current findings for this element
```

- `"unchecked"`: Element has not been analyzed yet (initial state).
- `"action_needed"`: At least one finding exists for this element. The status indicator shows yellow/warning.
- `"done"`: All findings have been resolved (auto-detected by re-running checks after edits). Green checkmark.
- `"manual_done"`: User manually marked as done via context menu or Ctrl+Shift+D. Green checkmark with "(manual)" suffix. This is useful for issues the tool cannot verify (e.g., content accuracy).

Status auto-updates: After any edit to an element (tag type change, alt text, scope, etc.), the tool silently re-runs applicable checks on that single element and updates its status. This provides immediate feedback: the user makes a change and the status indicator flips from yellow to green without having to run a full document check.

Accessibility:

- Tree items have accessible names: "H1, Done, Introduction, page 1" or "Figure, Action needed, no alt text, page 3"
- Collapse/expand state announced
- Context menu items are descriptive
- "Next Action" item announces the full recommendation text
- Status changes announced: "Status changed to Done" after a fix is applied
- Focus returns to tree after dialog closes

### Step 3.4: Reading Order Panel

`ui/reading_order_panel.py`

A flat wx.ListCtrl showing all structure elements in document reading order. This is a depth-first traversal of the tag tree's `/K` arrays.

Columns: Order Number, Page, Tag Type, Content Preview

Operations:

| Button / Key | Action |
|-------------|--------|
| Move Up (Alt+Up) | Move selected element earlier in reading order |
| Move Down (Alt+Down) | Move selected element later in reading order |
| Jump to Tag Tree (Enter) | Select this element in the tag tree panel |
| Multi-select (Shift+click or Shift+arrows) | Batch move operations |
| Sort by Visual Position (Ctrl+Shift+S) | Auto-sort all elements by visual position (see below) |
| Align Fields to Labels (Ctrl+Shift+F) | Move form fields adjacent to their labels (see below) |

Implementation:

- Changes in this panel call `reorder_children()` on the appropriate parent node in the structure tree
- If the user tries to move an element past a sibling boundary (into a different parent), the tool shows a reparent confirmation dialog
- Position number updates immediately after reorder
- Status line: "Element 5 of 47 -- H2 heading, page 2"

#### Auto-Sort Reading Order by Visual Position

This feature directly addresses the most common pain point: users struggling to manually fix reading order element by element. The tool uses pypdfium2 bounding box data to calculate the correct reading order automatically.

**Sort by Visual Position** (Ctrl+Shift+S or button above the list):

1. For each structure element with page content, the tool extracts the bounding box from the content stream (via MCID to content region mapping, using pypdfium2 rendering coordinates).
2. Elements are sorted per page using a top-to-bottom, left-to-right algorithm:
   - **Single-column detection**: Elements sorted by Y position (top first), then X position (left first) for elements on the same line (within a tolerance band of 12 points).
   - **Multi-column detection**: If the tool detects two or more vertical columns of content (consistent X-position clusters), it sorts left column top-to-bottom first, then right column top-to-bottom. This handles the common two-column PDF layout.
   - **Header/footer detection**: Elements in the top 72 points or bottom 72 points of the page are classified as header/footer and placed at the beginning/end of the page's reading order respectively, or marked as artifact candidates.
3. A preview dialog shows the proposed new order alongside the current order. The user reviews and confirms before applying.
4. The entire reorder is a single compound command (one Ctrl+Z undoes the whole sort).
5. Screen reader announces: "Reading order sorted by visual position. 47 elements reordered. Review the new order and press Ctrl+Z to undo if needed."

**Column detection algorithm** (pure Python, no AI):

```python
def detect_columns(bboxes: list[tuple[float, float, float, float]], 
                   page_width: float) -> list[list[int]]:
    """Cluster elements into columns by X-position.
    
    Returns list of columns, each column being a list of element indices
    sorted top-to-bottom.
    """
    # Extract left-edge X positions
    x_positions = [bbox[0] for bbox in bboxes]
    # Cluster X positions with a tolerance (e.g., 36 points = 0.5 inch)
    # If all X positions cluster into 1 group: single column
    # If 2 clusters: two-column layout
    # If 3+ clusters: multi-column or complex layout
```

This is a heuristic that works for 90%+ of typical government, education, and corporate PDFs. Edge cases (complex multi-column, Z-pattern layouts) fall back to the simple top-to-bottom sort with a "Review suggested" flag.

#### Align Form Fields to Labels in Reading Order

**Align Fields to Labels** (Ctrl+Shift+F or button above the list):

1. For each /Form element in the structure tree, the tool identifies its likely label:
   - Check the previous sibling: if it is a /P element with text content that matches or closely resembles the field's tooltip (/TU), it is the label.
   - Check by visual proximity: if a /P element is directly to the left of or directly above the form field's bounding box (within 24 points), it is the label candidate.
2. If the form field is not immediately after its label in the reading order, the tool moves it to be the next sibling after the label.
3. A preview dialog shows all proposed moves. The user reviews and confirms.
4. The entire operation is a single compound command.
5. Screen reader announces: "Aligned 15 form fields to their labels. 2 fields could not be matched -- review manually."

This directly addresses the pain point of form fields being in the wrong reading order relative to their labels, which causes screen readers to announce fields without context.

### Step 3.5: Page Overlay for Reading Order

Enhancement to `ui/page_view_panel.py`.

- Numbered rectangles drawn over the page bitmap at positions corresponding to each structure element's content region
- Color-coded by element type:
  - Blue: headings (H1 through H6)
  - Green: paragraphs and text blocks (P, Span, BlockQuote)
  - Orange: figures and illustrations (Figure)
  - Red: form fields (Form)
  - Purple: table elements (Table, TH, TD)
  - Gray: other structure elements
- Numbers correspond to reading order index
- Click/Tab to a numbered region: selects the element in both the tag tree and reading order panels
- High contrast mode: black outlines on white background with thick borders, large readable numbers
- Toggle visibility: Ctrl+Shift+O or View menu

**Phase 3 depends on**: Phase 1 (document model, renderer, UI shell).

---

## Phase 3.5: Screen Reader Preview

**Goal**: Let users -- especially screen reader users -- preview exactly how a screen reader would encounter the document, based on the tag tree structure. This is a linearized text rendering of the tag tree in reading order, not a visual page rendering.

This feature is critical for screen reader users who are remediating PDFs. Without it, they would need to save the PDF, open it in Acrobat Reader, and test with NVDA/JAWS after every change. The preview provides immediate feedback inside the tool.

### Step 3.6: Screen Reader Linearizer

`core/sr_linearizer.py`

Engine that walks the structure tree and produces a linearized text representation of what a screen reader would announce.

For each structure element, the linearizer generates an announcement string based on the tag type and content:

| Tag Type | Announcement Pattern | Example |
|----------|--------------------|---------|
| H1 through H6 | "Heading level N: text" | "Heading level 1: Annual Report 2026" |
| P | "text" (no role prefix for paragraphs, matching SR behavior) | "This report covers the fiscal year..." |
| Figure with alt | "Image: alt text" | "Image: Bar chart showing quarterly revenue" |
| Figure without alt | "WARNING Image: no alternative text" | "WARNING Image: no alternative text" |
| Link | "Link: text (URL)" | "Link: Company website" |
| L (list) | "List, N items" | "List, 5 items" |
| LI | "bullet: text" or "N: text" (numbered) | "bullet: First item" |
| Table | "Table with R rows and C columns" | "Table with 5 rows and 3 columns" |
| TH | "Column header: text" or "Row header: text" (based on Scope) | "Column header: Revenue" |
| TD | "text (headers: H1, H2)" for associated headers | "$1.2M (headers: Quarter, Revenue)" |
| Form (text field) | "Text field: tooltip (required)" | "Text field: Enter your name, required" |
| Form (checkbox) | "Checkbox: tooltip, not checked" | "Checkbox: I agree to terms, not checked" |
| Form (button) | "Button: label" | "Button: Submit" |
| BlockQuote | "Block quote: text" | "Block quote: To be or not to be..." |
| Code | "Code: text" | "Code: print(hello)" |
| Artifact | (skipped -- artifacts are invisible to screen readers) | |
| Span with lang | "Language change to fr: text" | "Language change to fr: Bonjour" |

Problem detection inline:

- Elements with no text content and no alt text: flagged as "WARNING empty element"
- Heading hierarchy gaps: flagged as "WARNING heading level skipped from H1 to H3"
- Form fields without tooltips: flagged as "WARNING form field has no accessible name"
- Table cells without header association in complex tables: flagged as "WARNING data cell has no header association"
- Figure without alt text: flagged as shown above

Output is a list of `SRLine` objects:

```python
@dataclass
class SRLine:
    text: str               # the announcement text
    struct_node: StructNode  # link back to the structure element
    page: int
    depth: int               # nesting depth for indentation
    element_type: str        # tag name
    has_warning: bool        # True if this line contains a problem
    warning_text: str        # description of the problem if any
```

### Step 3.7: Screen Reader Preview Panel

`ui/sr_preview_panel.py`

One of the tabbed panels in the bottom section. Shows the linearized screen reader output as navigable text.

Layout:

```
+------------------------------------------------------------------+
| Screen Reader Preview                          [Mode: v] [Refresh]|
+------------------------------------------------------------------+
| Heading level 1: Annual Report 2026                        (p.1) |
| This report covers the fiscal year ending December 2025... (p.1) |
| Heading level 2: Executive Summary                         (p.1) |
| The company achieved record growth in all segments...      (p.1) |
| Image: Bar chart showing quarterly revenue                 (p.1) |
| Heading level 2: Financial Results                         (p.2) |
| Table with 5 rows and 3 columns                            (p.2) |
|   Column header: Quarter                                   (p.2) |
|   Column header: Revenue                                   (p.2) |
|   Column header: Profit                                    (p.2) |
|   Q1 (headers: Quarter, Revenue)                           (p.2) |
|   ...                                                      |     |
| >> WARNING Image: no alternative text                      (p.3) |
| Text field: Enter your name, required                      (p.4) |
| Checkbox: I agree to terms, not checked                    (p.4) |
| Button: Submit                                             (p.4) |
+------------------------------------------------------------------+
| Line 1 of 87 | Page 1 | 2 warnings | Mode: Full Document        |
+------------------------------------------------------------------+
```

Navigation modes (selectable via the Mode dropdown):

| Mode | What It Shows | Simulates |
|------|-------------|----------|
| Full Document | All elements in reading order | Reading the document start to finish |
| Headings Only | Only H1 through H6 elements | Pressing H key in a screen reader to navigate by heading |
| Form Fields Only | Only form elements | Pressing F key to navigate by form field |
| Tables Only | Only table structures with header announcements | Pressing T key to navigate by table |
| Links Only | Only link elements | Pressing K key (NVDA) to navigate by link |
| Warnings Only | Only elements with accessibility problems | Quick view of all issues in reading order context |

Keyboard operations:

| Key | Action |
|-----|--------|
| Up/Down arrows | Navigate between lines |
| Enter | Select line and navigate to element in tag tree and page view |
| H | Jump to next heading (in Full Document mode) |
| Shift+H | Jump to previous heading |
| F | Jump to next form field |
| T | Jump to next table |
| K | Jump to next link |
| W | Jump to next warning |
| Ctrl+Shift+R | Refresh preview (after edits) |
| Ctrl+C | Copy selected line text to clipboard |
| Ctrl+Shift+C | Copy entire preview to clipboard (for external review) |

Accessibility features:

- Each line is a navigable item in a wx.ListBox or wx.dataview.DataViewListCtrl
- Lines have accessible names: full announcement text plus page number
- Warning lines are announced with "Warning" prefix
- Mode changes announced: "Switched to Headings Only mode, 8 headings found"
- Status bar: current position, total lines, warning count, active mode
- This panel is itself fully screen reader accessible -- a screen reader user navigating this panel hears exactly what another screen reader would announce when reading the finished PDF

Interaction with other panels:

- Selecting a line in the SR Preview selects the corresponding element in the tag tree panel
- Selecting a line navigates the page view to the correct page
- When the user edits the tag tree (changes a tag type, edits alt text, reorders elements), the SR Preview refreshes to reflect the change
- Warning lines in the SR Preview link to the corresponding finding in the Issues panel

Copy and export:

- "Copy to Clipboard" button: copies the entire linearized text (useful for pasting into a review document or email)
- "Export as Text" button: saves the linearized text to a `.txt` file (useful for sharing with team members who do not have the tool)

**Phase 3.5 depends on**: Phase 3 (structure tree wrapper, tag types). Benefits from Phase 5 (form field data for richer form announcements) and Phase 7 (table header data for header association announcements) but works without them -- fields and tables are announced with whatever data is available.

---

## Phase 4: Alt Text Editor for Images

**Goal**: Provide a dedicated panel for browsing all images in the document and editing their alt text.

### Step 4.1: Image Extractor

`core/image_extractor.py`

Responsibilities:

- Walk the structure tree to find all `Figure` elements
- For each Figure: extract the referenced image (trace MCID to content stream to XObject)
- Generate a thumbnail via pypdfium2 (render the page region) or Pillow (extract the raw image XObject)
- Detect untagged images: scan all pages for image XObjects not referenced by any StructElem
- Return a list of `ImageInfo` dataclass objects:
  ```python
  @dataclass
  class ImageInfo:
      struct_node: StructNode | None   # None if untagged
      page: int
      rect: tuple[float, float, float, float]  # position on page
      alt_text: str
      is_decorative: bool              # alt text == ""
      thumbnail: wx.Bitmap
      xobject_key: str                 # PDF object reference
  ```

### Step 4.2: Alt Text Panel

`ui/alt_text_panel.py`

One of the tabbed panels in the bottom section of the main window.

Layout:

```
+--------------------------------------------------+
| [Thumbnail] | Page: 3  Size: 200x150px           |
|             | Tag: Figure                         |
|             | Alt Text: [editable text field]     |
|             | [ ] Mark as decorative              |
|             | [Apply] [Previous] [Next]           |
+--------------------------------------------------+
| Status: Image 3 of 12 | 5 missing alt text       |
+--------------------------------------------------+
```

Features:

- Navigate images with Previous / Next buttons or arrow keys
- Edit alt text inline (multiline text field for long descriptions)
- "Mark as decorative" checkbox: sets alt text to empty string (signals the image is decorative per PDF/UA)
- Apply button commits the change through the structure tree wrapper (creates an undo-able command)
- "Flag all missing" button: filters to show only images without alt text
- Activating an image navigates the page view to its location
- Batch operation: "Copy filename as alt text" for images where the XObject has a name

Accessibility:

- Thumbnail has accessible description: "Image on page 3, 200 by 150 pixels, currently no alt text"
- Alt text edit field is labeled "Alternative text for image 3 of 12"
- Decorative checkbox is labeled "Mark this image as decorative (no alt text needed)"
- Navigation buttons announce: "Image 4 of 12, page 3, alt text: Company logo"

**Phase 4 depends on**: Phase 3 (structure tree wrapper for finding Figure elements and writing /Alt).

---

## Phase 5: Form Field Editor for Existing Fields

**Goal**: Edit properties of existing form fields and fix accessibility issues.

### Step 5.1: Form Field Model

`core/form_model.py`

Responsibilities:

- Enumerate all AcroForm fields via `pikepdf.Pdf.Root.AcroForm`
- For each field, read:
  - `/T` (field name)
  - `/TU` (tooltip / user-facing name for screen readers)
  - `/FT` (field type: Tx, Btn, Ch, Sig)
  - `/V` (current value)
  - `/DV` (default value)
  - `/Ff` (field flags: required=bit 2, read-only=bit 1, no-export=bit 3, etc.)
  - `/Rect` (position on page)
  - Widget annotation properties
  - `/Pg` (page reference)
- Translate flag bits into human-readable boolean properties (required, read_only, etc.)
- Write all properties back to the PDF via pikepdf
- Detect common issues: missing TU, missing T, suspicious flag combinations

### Step 5.2: Field Properties Panel

`ui/field_properties_panel.py`

Shown in the properties area when a form field is selected.

Fields (all labeled for screen readers):

- **Name** (/T): text input
- **Tooltip** (/TU): text input -- this is what screen readers announce
- **Type**: read-only display (Text, Checkbox, Radio, Dropdown, Button, Signature)
- **Default Value** (/DV): text input
- **Required**: checkbox
- **Read Only**: checkbox
- **No Export**: checkbox
- **Page**: read-only display
- **Position**: read-only display (x, y, width, height in points)

Apply button commits changes as a command (undoable).

### Step 5.3: Fields List Panel

`ui/fields_list_panel.py`

One of the tabbed panels in the bottom section.

wx.DataViewListCtrl with columns: Page, Name, Type, Tooltip, Required, Issues

- Sortable by any column
- Selecting a field navigates the page view and highlights the field rectangle
- Batch operations:
  - "Set tooltip from name": for all fields where TU is empty, copy T to TU
  - "Flag fields with issues": filter to show only fields missing tooltip or name
- Context menu: Edit Properties, Go to Page, Set Tooltip, Toggle Required

### Step 5.4: Tab Order Editor

Integrated into the fields list panel.

- "Tab Order" view mode: shows fields in their current tab order per page
- Page selector dropdown (choose which page to view)
- Move Up / Move Down buttons (Alt+Up / Alt+Down) reorder within the page
- Tab order mode dropdown: Structure (/S), Row (/R), Column (/C), Custom
  - Structure: order follows structure tree (best for accessibility)
  - Row: top-to-bottom, left-to-right
  - Column: left-to-right, top-to-bottom
  - Custom: explicit order via `/Annots` array reorder
- Tab order numbers shown on page view overlay (alongside reading order numbers, in a different color)
- Changes write back to the page's `/Tabs` entry and `/Annots` array

**Phase 5 depends on**: Phase 1.  Parallel with Phase 3.

---

## Phase 6: Form Builder for New Fields

**Goal**: Create new form fields on existing or blank PDFs via a fully accessible property-driven interface.

### Step 6.1: Blank PDF Generator

`core/blank_pdf.py`

Create a new, properly tagged PDF from scratch:

- Page size: Letter (default), A4, Legal, or custom dimensions
- Initial structure: `/StructTreeRoot` with a `Document` element
- Metadata: title (required, user enters), language (required, default en-US), author
- `/ViewerPreferences /DisplayDocTitle true`
- `/MarkInfo /Marked true`
- Result: a minimal but fully tagged, PDF/UA-ready document

### Step 6.2: Field Creation Engine

`core/field_factory.py`

Create a new form field and register it in the PDF:

**Supported field types:**

| Type | PDF /FT | Key Properties |
|------|---------|---------------|
| Text Field | Tx | Max length, multiline, password, comb |
| Checkbox | Btn (bit 16 clear) | Checked/unchecked default |
| Radio Group | Btn (bits 15-16) | Group name, option values |
| Dropdown | Ch | Option list, editable flag, default selection |
| List Box | Ch (bit 18 clear) | Option list, multi-select, default selection |
| Push Button | Btn (bit 17) | Label text, action (submit, reset, URL) |
| Signature | Sig | Placeholder only (signing is out of scope) |

**Creation sequence for each field:**

1. Create a `pikepdf.Dictionary` for the field object (/Type /Annot, /Subtype /Widget, /FT, /T, /TU, /Rect, /Ff, /V, /DV)
2. Generate an appearance stream (/AP /N) so the field renders visually. Use pikepdf's built-in appearance stream generator for text fields. For buttons and checkboxes, build minimal appearance streams with content stream operators
3. Add the widget annotation to the page's `/Annots` array
4. Register the field in the document's `/AcroForm /Fields` array (create AcroForm if it does not exist)
5. Create a `Form` structure element in the tag tree as a child of the appropriate parent
6. Link the structure element to the widget annotation
7. Update the page's `/Tabs` entry to include the new field in tab order
8. All steps wrapped in a single compound Command for undo/redo

### Step 6.3: Field Placement Interface

`ui/field_placement.py`

A dialog or panel for creating a new field. Pure property-driven layout (no drag-and-drop).

Layout:

```
+--------------------------------------------------+
| Add New Form Field                               |
+--------------------------------------------------+
| Field Type:     [Dropdown: Text Field     v]     |
| Name:           [____________________________]   |
| Tooltip:        [____________________________]   |
| Default Value:  [____________________________]   |
| Required:       [ ] Yes                          |
| Read Only:      [ ] Yes                          |
+--------------------------------------------------+
| Position on Page                                 |
| Page: [Spinner: 1   ] of 12                      |
| X:    [Spinner: 72  ] points from left           |
| Y:    [Spinner: 700 ] points from bottom         |
| Width:[Spinner: 200 ] points                     |
| Height:[Spinner: 24 ] points                     |
| [Place at Cursor] -- click page to set position  |
+--------------------------------------------------+
| Type-Specific Options                            |
| (changes based on selected field type)           |
| Max Length: [Spinner: 0   ] (0 = no limit)       |
| Multiline: [ ] Yes                               |
+--------------------------------------------------+
| [Preview on Page] [Add Field] [Cancel]           |
+--------------------------------------------------+
```

Type-specific option panels:

- **Text**: max length, multiline checkbox, password checkbox
- **Checkbox**: default checked checkbox
- **Radio Group**: group name text field, options list (Add/Remove/Reorder), default selection
- **Dropdown**: options list (Add/Remove/Reorder), editable checkbox (allow text entry), default selection
- **List Box**: options list, multi-select checkbox, default selection
- **Push Button**: button label, action dropdown (None, Submit, Reset, URL), URL field if URL action
- **Signature**: no additional options (placeholder field)

"Place at Cursor" mode:

- When activated, the page view enters placement mode
- Mouse users click the page to set X, Y coordinates
- Keyboard users use arrow keys to move a cursor, Enter to place
- Width and Height remain as entered in the spinners
- Position spinners update to reflect the placed coordinates

"Preview on Page" button:

- Draws a ghost rectangle on the page view at the specified position and size
- Visual confirmation before committing

"Add Field" button:

- Validates all required properties (name and tooltip must be non-empty)
- Creates the field via field_factory
- Shows confirmation in status bar
- Optionally stays open for adding more fields ("Add and Continue" vs "Add and Close")

### Step 6.4: Field Presets

Extensibility hook for future template support.

- Field configurations stored as JSON files in the user's config directory
- Each preset: field type, default name pattern, default tooltip pattern, default dimensions, type-specific options
- Ship built-in presets:
  - "Name Field": Text, 200x24, tooltip "Enter your full name"
  - "Email Field": Text, 200x24, tooltip "Enter your email address"
  - "Yes/No Radio": Radio group with "Yes" and "No" options
  - "Submit Button": Push button with submit action
  - "Date Field": Text, 100x24, tooltip "Enter date as MM/DD/YYYY"
- Users can save custom presets from the Add Field dialog
- Preset selector dropdown in the Add Field dialog pre-fills all properties
- Foundation for a full form template system in a future release

**Phase 6 depends on**: Phase 3 (structure tree wrapper), Phase 5 (form model).

---

## Phase 7: Table Header Editor

**Goal**: Edit table header cells, scope attributes, and cell-to-header associations.

### Step 7.1: Table Structure Model

`core/table_model.py`

Parse table elements from the structure tree into a grid model:

```python
@dataclass
class TableCell:
    struct_node: StructNode
    tag: str              # "TH" or "TD"
    row: int
    col: int
    row_span: int         # default 1
    col_span: int         # default 1
    scope: str | None     # "Row", "Column", "Both", or None
    headers: list[str]    # IDs of associated TH elements
    content_preview: str  # first 40 chars of text

@dataclass
class TableModel:
    struct_node: StructNode   # the Table element
    rows: int
    cols: int
    has_thead: bool
    has_tbody: bool
    has_tfoot: bool
    cells: list[list[TableCell | None]]  # row-major grid, None for spanned slots
```

Detection:

- Walk the Table StructElem's children: THead, TBody, TFoot, TR
- Within each TR: TH and TD elements
- Calculate row/column positions accounting for RowSpan and ColSpan attributes
- Detect issues:
  - TH cells without Scope attribute
  - TD cells not associated with any TH (missing Headers attribute in complex tables)
  - Tables without THead
  - Inconsistent row widths (different number of cells per row)

### Step 7.2: Table Editor Panel

`ui/table_editor_panel.py`

One of the tabbed panels in the bottom section. Activated when a Table element is selected in the tag tree.

Layout options (user toggleable):

**Grid view** (default): a wx.grid.Grid showing the table structure

- Each cell shows: [TH/TD] content preview
- TH cells highlighted in bold or with background color
- Select a cell to edit its properties in a side panel
- Keyboard navigation: arrow keys move between cells, Enter opens cell editor

**Properties view**: when a cell is selected

- Tag type: toggle button (TH / TD)
- Scope: dropdown (None, Row, Column, Both) -- only enabled for TH cells
- Headers: list of associated TH cell IDs -- for complex tables where simple scope is insufficient
- Content preview: read-only
- Apply commits changes

Operations:

| Action | What It Does |
|--------|-------------|
| Toggle TH/TD | Change a cell's tag type in the structure tree |
| Set Scope | Add Scope attribute to TH cell's /A dictionary |
| Set Headers | Associate TD cell with TH cells by ID |
| Add THead wrapper | Create THead element and reparent first row(s) into it |
| Add TBody wrapper | Create TBody element and reparent body rows into it |
| Add TFoot wrapper | Create TFoot element and reparent last row(s) into it |

### Step 7.3: Table Checker Integration

Additional built-in checks added to `builtin_checks.py`:

| Check | Rule ID | WCAG | Severity |
|-------|---------|------|----------|
| Table with no TH cells | PDFBP.TABLE_HEADERS | 1.3.1 | Warning |
| TH cell without Scope | PDFBP.TABLE_SCOPE | 1.3.1 | Warning |
| Complex table TD without Headers | PDFBP.TABLE_ASSOC | 1.3.1 | Warning |
| Table without THead | PDFBP.TABLE_THEAD | 1.3.1 | Tip |
| Inconsistent row width | PDFBP.TABLE_STRUCTURE | 1.3.1 | Warning |

Findings appear in the Issues panel. Activating a table-related finding switches to the Table Editor tab and highlights the relevant cell.

**Phase 7 depends on**: Phase 3 (structure tree wrapper).

---

## Phase 8: Document Properties and Metadata

**Goal**: Edit document-level accessibility properties.

### Step 8.1: Document Properties Panel

`ui/doc_properties_panel.py`

Shown in the properties area when no element is selected, or accessible via Tools menu.

Fields:

- **Title** (required for PDF/UA): text input, writes to both `/Info /Title` and XMP `dc:title`
- **Author**: text input
- **Subject**: text input
- **Language** (required for PDF/UA): BCP 47 language tag picker (dropdown with common codes: en, en-US, en-GB, fr, de, es, plus text entry for others), writes to `/Lang`
- **Display Document Title**: checkbox, writes to `/ViewerPreferences /DisplayDocTitle`
- **Tagged PDF**: read-only indicator (shows whether `/MarkInfo /Marked` is true)
- **Bookmarks**: count display, "Generate from Headings" button

"Generate Bookmarks from Headings" action:

- Walk the structure tree for H1 through H6 elements
- Create `/Outlines` dictionary and `/Outline` entries matching the heading hierarchy
- Each bookmark links to the page containing the heading
- Nested: H2 under H1, H3 under H2, etc.
- Overwrites existing bookmarks (with confirmation dialog)

**Phase 8 depends on**: Phase 1.  Parallel with other phases.

---

## Phase 9: Content Stream Tagging

**Goal**: Enable tagging of untagged content by reading and modifying PDF content streams.

This phase introduces content stream manipulation. It is separated from Phase 3 because content stream changes carry a higher risk of PDF corruption. Phase 3 edits only the structure tree (safe). Phase 9 edits content streams (requires careful engineering and extensive testing).

### Step 9.1: Content Stream Parser

`core/content_parser.py`

Responsibilities:

- Parse a page's content stream via `pikepdf.parse_content_stream(page)`
- Identify marked content sequences:
  - `BMC` / `EMC` (begin/end marked content)
  - `BDC` / `EMC` (begin/end marked content with properties dictionary)
- Extract MCID values from `BDC` property dictionaries
- Map each MCID to its structure element (via the structure tree wrapper)
- Identify untagged content: content stream operators that are NOT inside any BMC/EMC pair
- Identify artifact content: content inside `/Artifact BMC ... EMC`
- For each content region, calculate approximate bounding box from text positioning operators (Tm, Td, etc.) and graphics state

Data model:

```python
@dataclass
class ContentRegion:
    page: int
    start_index: int          # index in content stream instruction list
    end_index: int
    region_type: str          # "tagged", "untagged", "artifact"
    mcid: int | None          # MCID if tagged
    struct_node: StructNode | None
    approx_rect: tuple | None # approximate bounding box
    text_preview: str         # extracted text content if text operators present
    operators: list           # raw content stream instructions
```

### Step 9.2: Visual Content Tagger

Enhancement to `ui/page_view_panel.py` and new tagging workflow.

When the user activates "Tag Untagged Content" mode (from the Tags menu):

1. Content parser scans the current page
2. Untagged regions are highlighted on the page view:
   - Light red overlay for untagged content
   - Light gray overlay for artifact content
   - No overlay for already-tagged content
3. User selects an untagged region (click or keyboard navigation)
4. A dialog appears:
   - "Tag this content as:" dropdown (standard tag types)
   - "Parent element:" dropdown (existing structure elements)
   - "Mark as artifact" checkbox (alternative: declare this is decorative)
   - [Apply] [Skip] [Cancel]
5. On Apply:
   - Insert `BDC /P <</MCID N>> ... EMC` operators around the content in the content stream
   - Create a new StructElem with the chosen tag type
   - Link it to the parent element
   - Assign the MCID
   - Rebuild `/ParentTree`

### Step 9.3: Artifact Wrapping

Operations for managing artifact (decorative) content:

- **Mark as artifact**: wrap content in `/Artifact BMC ... EMC`. Remove any existing StructElem reference. Content becomes invisible to screen readers
- **Un-artifact**: remove `/Artifact BMC ... EMC` wrappers. Create a new StructElem and add to structure tree. Content becomes part of the reading order

Safety measures:

- Every content stream edit creates a backup of the original content stream in the Command object (for undo)
- After every content stream modification, run a validation pass: verify all BMC/EMC pairs are balanced, all MCIDs are unique per page, ParentTree is consistent
- If validation fails, automatic rollback and user notification

**Phase 9 depends on**: Phase 3 (structure tree wrapper).  This is high-risk and should be built after Phases 1 through 8 are stable.

---

## Phase 10: Auto-Tagger

**Goal**: Automatically detect and tag content in untagged PDFs using heuristics and machine learning, with a user review workflow.

This is the most ambitious phase. It builds on Phase 9 (content stream tagging) and adds automated detection. The auto-tagger proposes tags; the user reviews and approves them.

### Step 10.1: Content Feature Extraction

`core/auto_tagger.py` -- analysis module

For each untagged content region (identified by `content_parser.py`), extract features:

**Text features:**

- Font size (relative to page: largest, larger, normal, smaller, smallest)
- Font weight (bold detection via font name analysis: "Bold", "Bd", etc.)
- Font style (italic detection)
- Text length (character count)
- Line count
- All caps detection
- Starts with number/bullet detection (list item heuristic)
- Indentation level (X position relative to page margin)
- Vertical position on page (header/footer region detection)

**Spatial features:**

- Bounding box dimensions (width, height)
- Aspect ratio
- Position relative to other content regions (above, below, left, right)
- White space before and after (paragraph spacing heuristic)
- Column detection (is content in a multi-column layout?)

**Context features:**

- Previous region's detected type
- Next region's detected type
- Page number (first page may have title/header patterns)
- Number of similar-sized regions on the page

### Step 10.2: Heuristic Classifier

Rule-based classification as the first pass (no ML required):

| Heuristic | Detected Tag | Confidence |
|-----------|-------------|-----------|
| Largest font on page 1, centered | H1 | High |
| Larger font than body, bold | H2 through H6 (by relative size) | Medium |
| Normal font, multi-line, standard width | P | High |
| Starts with bullet or number, indented | LI within L | Medium |
| Rectangular area with no text, image XObject | Figure | High |
| Small font at page top, repeating across pages | Artifact (header) | Medium |
| Small font at page bottom, repeating across pages | Artifact (footer) | Medium |
| Page number pattern (digits only) at footer | Artifact | High |
| Horizontal line (thin rectangle or line operator) | Artifact (decorative rule) | Medium |
| Tabular layout (aligned columns of text) | Table candidate | Low |

The heuristic classifier runs fast (no external dependencies) and produces a confidence score for each detection. High-confidence detections can be auto-applied; medium and low require user review.

### Step 10.3: ML Classifier (Optional Enhancement)

A scikit-learn based classifier trained on features from Step 10.1.

Architecture:

- **Model**: Random Forest or Gradient Boosting classifier (scikit-learn)
- **Features**: numeric feature vector from Step 10.1 (approximately 20 features)
- **Labels**: standard tag types (H1-H6, P, L, LI, Figure, Table, Artifact, etc.)
- **Training data**: generated from the tool's own usage. Train on features extracted from well-tagged PDFs (known-good documents). The tool ships with a pre-trained model from a corpus of accessible PDFs.
- **Inference**: classify each untagged region, output tag type and confidence score
- **Fallback**: if scikit-learn is not installed, use heuristic classifier only

Model management:

- Ship a `default_model.pkl` with the application (pre-trained on a diverse PDF corpus)
- Users can retrain the model on their own documents: "Train on tagged PDFs" action in Tools menu
- Model stored in user's config directory via platformdirs
- Version tracking: model version stored in preferences; warn if model is outdated

### Step 10.4: Auto-Tag Wizard

`ui/auto_tag_wizard.py`

A step-by-step wizard dialog for auto-tagging an untagged PDF.

**Step 1: Analysis**

```
+-----------------------------------------------------+
| Auto-Tag Wizard -- Step 1 of 4: Analysis            |
+-----------------------------------------------------+
| Analyzing document...                               |
|                                                     |
| Pages: 12                                           |
| Untagged content regions found: 87                  |
| Image XObjects found: 5                             |
|                                                     |
| Classifier: [Heuristic only v] / [Heuristic + ML]  |
|                                                     |
| [Next] [Cancel]                                     |
+-----------------------------------------------------+
```

**Step 2: Review Proposals**

```
+-----------------------------------------------------+
| Auto-Tag Wizard -- Step 2 of 4: Review Proposals    |
+-----------------------------------------------------+
| Region | Page | Proposed Tag | Confidence | Action  |
|--------|------|-------------|-----------|---------|
| 1      | 1    | H1          | High      | [Accept]|
| 2      | 1    | P           | High      | [Accept]|
| 3      | 1    | H2          | Medium    | [Change]|
| 4      | 1    | Figure      | High      | [Accept]|
| 5      | 2    | P           | Low       | [Review]|
| ...    |      |             |           |         |
+-----------------------------------------------------+
| Auto-accept all High confidence: [x]                |
| [Accept All Shown] [Previous] [Next] [Cancel]       |
+-----------------------------------------------------+
```

Features:

- Sortable/filterable list of all proposed tags
- Each row: page, proposed tag type (editable dropdown), confidence level, action buttons
- "Accept" locks in the proposed tag
- "Change" opens a dropdown to select a different tag type
- "Review" navigates to the page view and highlights the region for visual inspection
- "Mark as Artifact" button for decorative content
- "Auto-accept all High confidence" checkbox: automatically accepts all high-confidence proposals
- Page view updates to show the proposed tags as colored overlays

**Step 3: Structure and Reading Order**

```
+-----------------------------------------------------+
| Auto-Tag Wizard -- Step 3 of 4: Structure           |
+-----------------------------------------------------+
| Proposed document structure:                        |
|                                                     |
| Document                                            |
|   H1: "Annual Report 2026"                          |
|   P: "Published by..."                              |
|   H2: "Executive Summary"                           |
|   P: "This report covers..."                        |
|   Figure: [image, page 1]                           |
|   H2: "Financial Results"                           |
|   Table: [5 rows x 3 cols, page 2]                  |
|   ...                                               |
|                                                     |
| [Reorder] [Reparent] [Previous] [Next] [Cancel]     |
+-----------------------------------------------------+
```

- Shows the proposed tag tree structure
- Users can reorder elements (Move Up/Down) and reparent before committing
- This is a preview of what the tree will look like after auto-tagging

**Step 4: Apply**

```
+-----------------------------------------------------+
| Auto-Tag Wizard -- Step 4 of 4: Apply               |
+-----------------------------------------------------+
| Ready to tag 87 content regions.                    |
|                                                     |
| Summary:                                            |
|   Headings: 8                                       |
|   Paragraphs: 42                                    |
|   List items: 15                                    |
|   Figures: 5                                        |
|   Tables: 2                                         |
|   Artifacts: 15                                     |
|                                                     |
| This will modify the PDF's structure tree and       |
| content streams. Changes can be undone (Ctrl+Z).    |
|                                                     |
| [Apply Tags] [Previous] [Cancel]                    |
+-----------------------------------------------------+
```

- Summary of all changes to be applied
- Warning that content streams will be modified
- Apply creates the full structure tree, inserts BMC/EMC markers, builds ParentTree
- The entire auto-tag operation is a single compound Command (one Ctrl+Z undoes everything)
- After apply, the tool runs built-in checks and reports any remaining issues

### Step 10.5: Incremental Tagging

For partially tagged PDFs (some content is tagged, some is not):

- Content parser identifies only untagged regions
- Auto-tagger classifies only untagged regions
- Proposed structure elements are inserted into the existing tag tree at appropriate positions (after the nearest tagged sibling)
- Existing tags are preserved
- User reviews proposals in context of the existing structure

### Step 10.6: Training Workflow

"Train on Tagged PDFs" action (Tools menu):

1. User selects one or more well-tagged PDF files (or a folder)
2. Tool extracts features from all tagged content regions in those files
3. Uses the existing structure tree as ground truth labels
4. Trains or fine-tunes the scikit-learn classifier
5. Saves the updated model to user's config directory
6. Reports training accuracy (cross-validation score)

This enables teams to improve auto-tagging accuracy over time as they remediate more documents.

**Phase 10 depends on**: Phase 9 (content stream tagging), Phase 3 (structure tree wrapper), Phase 2 (built-in checks for post-tagging validation).

---

## Phase 11: Tool Accessibility

**Goal**: Ensure the tool itself meets WCAG 2.2 AA for its own interface. This phase is a final audit and polish pass. Accessibility is built into every phase from the start, but this phase is the comprehensive verification.

### Step 11.1: Screen Reader Audit

Test every panel and dialog with NVDA and JAWS:

- All controls have accessible names via `SetName()` or `SetLabel()`
- All buttons have descriptive labels (not just icons)
- Focus order follows logical reading order in every panel
- Tree controls expose correct hierarchy and state (expanded/collapsed, level)
- List controls expose column headers and cell content
- Grid controls expose row/column headers and cell content
- Dialogs are modal with proper focus trapping
- Escape closes dialogs and returns focus to the previous element
- Status bar changes announced for significant events (check complete, file saved, error)
- Progress indicators announced (auto-tagger analysis progress)
- Comboboxes and dropdowns navigable with arrow keys, selection announced

### Step 11.2: Keyboard Navigation

All features reachable without a mouse.

Global shortcuts:

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open PDF |
| Ctrl+S | Save PDF |
| Ctrl+Shift+S | Save PDF As |
| Ctrl+N | New Blank PDF |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| F5 | Run Accessibility Check |
| F6 | Cycle panel focus |
| Ctrl+Tab | Cycle bottom panel tabs |
| Ctrl+Shift+O | Toggle reading order overlay |
| Ctrl+Shift+R | Screen reader preview (refresh and focus) |
| Ctrl+= | Zoom in |
| Ctrl+- | Zoom out |
| Ctrl+0 | Fit page |
| Ctrl+/ | Keyboard shortcuts reference |
| Ctrl+F | Find in document (text search) |
| Ctrl+G | Go to page |
| Alt+F4 | Exit |

Panel-specific shortcuts documented in the Keyboard Shortcuts reference dialog.

### Step 11.3: High Contrast and Scaling

- Detect Windows High Contrast mode via `wx.SystemSettings.GetColour()` and adapt all custom-drawn content (page overlays, grid highlights, status indicators)
- Reading order overlay in High Contrast: black rectangles with white numbers, thick 3px borders
- DPI-aware scaling: use `wx.Window.FromDIP()` for all custom sizing
- Page view zoom is independent of system DPI (both multiply)
- All text content in the UI respects system font size settings
- No information conveyed by color alone (all color-coded elements also have text labels or icons)

### Step 11.4: Preferences Dialog

`core/preferences.py`

Settings stored via platformdirs in the user's config directory as JSON:

```json
{
    "verapdf_path": "C:\\Program Files\\veraPDF\\verapdf.bat",
    "default_page_size": "letter",
    "recent_files": [],
    "auto_accept_high_confidence": false,
    "ml_model_path": null,
    "overlay_colors": "default",
    "page_cache_size": 10,
    "default_language": "en-US"
}
```

Preferences dialog: tabbed layout (General, Paths, Auto-Tagger, Display). All inputs labeled. Tab order is logical.

**Phase 11 runs in parallel** with all other phases. Accessibility is built in from Phase 1.

---

## Phase 12: Packaging and Distribution

**Goal**: Package the application for Windows distribution.

### Step 12.1: PyInstaller Build

`pdf-a11y-tool.spec` -- PyInstaller spec file:

- **Mode**: one-folder (COLLECT pattern), not one-file. One-folder starts faster and is easier to debug.
- **Include**: pikepdf, pypdfium2 (with PDFium DLL), wxPython, Pillow, scikit-learn, platformdirs, all app code, default ML model, field presets JSON files
- **Exclude**: test files, dev dependencies (ruff, mypy, pytest), build tools
- **Entry point**: `src/pdf_a11y/__main__.py`
- **Icon**: custom application icon (ICO format)
- **Name**: `pdf-a11y-tool.exe`
- **Console**: false (windowed mode)

Output: `dist/pdf-a11y-tool/` folder containing the exe and all dependencies.

Build command:

```bash
pyinstaller pdf-a11y-tool.spec
```

### Step 12.2: veraPDF Setup Wizard

First-run dialog when the user opens the application for the first time (or when they try to run a veraPDF check without a configured path):

```
+-----------------------------------------------------+
| veraPDF Setup                                       |
+-----------------------------------------------------+
| veraPDF is an optional tool for full PDF/UA         |
| validation. It requires Java to be installed.       |
|                                                     |
| Status: [Not found / Found at C:\...\verapdf.bat]  |
|                                                     |
| [Auto-detect]  -- scans PATH and common locations   |
| [Browse...]    -- manually select verapdf.bat       |
| [Download]     -- opens verapdf.org in browser      |
|                                                     |
| [Skip]         -- use built-in checks only          |
| [Save]         -- save the detected/selected path   |
+-----------------------------------------------------+
```

Auto-detect locations:

- System PATH
- `C:\Program Files\veraPDF\`
- `C:\Program Files (x86)\veraPDF\`
- `C:\veraPDF\`
- `%LOCALAPPDATA%\veraPDF\`

### Step 12.3: Distribution

Initial release: zip archive containing the `pdf-a11y-tool/` folder. Extract and run `pdf-a11y-tool.exe`.

Future: Inno Setup installer with:

- Start Menu shortcut
- Desktop shortcut (optional)
- File association for `.pdf` files (optional)
- Uninstaller
- License acceptance dialog
- veraPDF and Java detection/installation integration

**Phase 12 depends on**: All prior phases complete for a full-featured release. Can do partial releases as phases complete.

---

## Phase 13: Adaptive Learning System

**Goal**: Enable the tool to learn from every PDF it scans, building a local knowledge base of accessibility patterns, common defects, and effective fixes. The system improves its detection accuracy, remediation suggestions, and auto-tagger confidence over time without requiring cloud connectivity or external AI services.

**Is AI self-learning possible?** Yes. The tool can absolutely learn and adapt using local machine learning and pattern accumulation. Here is how:

### Design Philosophy

The adaptive learning system operates on three principles:

1. **Learn locally, not in the cloud**: All learning data stays on the user's machine (or organization's shared drive). No data is sent to external services. This satisfies air-gapped government environments and FERPA/HIPAA-sensitive higher education contexts.
2. **Learn from user corrections**: When a user changes a tag type, adds alt text, fixes reading order, or marks something as an artifact, that correction is a training signal. The system records what the element looked like before the fix and what the user chose, building a local corpus of "problem -> solution" pairs.
3. **Learn from document patterns**: When the tool encounters a PDF from a specific source application (Word, InDesign, LibreOffice, Google Docs), it records the accessibility patterns typical of that generator. Over time, the tool develops per-generator profiles that front-load likely checks and suggest likely fixes.

### Step 13.1: Pattern Database

`core/pattern_db.py`

A SQLite database (via Python's built-in `sqlite3`) stored in the user's config directory (platformdirs):

```
~/.config/pdf-a11y-tool/patterns.db    (Linux/macOS)
%LOCALAPPDATA%\pdf-a11y-tool\patterns.db   (Windows)
```

Tables:

| Table | Purpose |
|-------|---------|
| `scan_history` | Record of every PDF scanned: filename hash (SHA-256, not the filename itself for privacy), page count, source application, creation date, finding counts by rule ID, overall score, scan timestamp |
| `corrections` | User corrections: rule ID, original element state (tag type, attributes, content preview), corrected state, source application, confidence of original detection, timestamp |
| `generator_profiles` | Per-source-application statistics: which rules fire most often, which auto-fixes are accepted vs rejected, average element counts by tag type |
| `element_features` | Feature vectors for tagged elements used to retrain the ML classifier: font size, weight, position, text length, content hash, assigned tag type, manually verified flag |
| `custom_rules` | User-defined pattern rules (see Step 13.4) |

Privacy: the database stores content hashes and previews (first 60 characters), never full document text. Users can clear the database at any time via Preferences > Learning > Clear All Data.

### Step 13.2: Learning from User Corrections

Every time the user makes a correction, the system records a training pair:

```python
@dataclass
class CorrectionRecord:
    rule_id: str                # Which check originally flagged this
    source_app: str             # PDF creator application
    element_tag_before: str     # Original tag type (e.g., "/P")
    element_tag_after: str      # Corrected tag type (e.g., "/H2")
    element_features: dict      # Font size, bold, position, text preview
    auto_fix_accepted: bool     # Did the user accept a suggested fix?
    auto_fix_type: str | None   # Which auto-fix was offered
    timestamp: str
```

Over time, these corrections feed back into:

1. **Auto-tagger retraining** (Phase 10): The ML classifier is periodically retrained on the combined default model + local corrections. This means the auto-tagger gets better at detecting headings, lists, artifacts, and other elements specific to the documents this user typically works with.

2. **Fix Now suggestion ranking**: If users consistently accept "Mark as artifact" for InlineShape elements from Word documents, the Fix Now dialog defaults to that choice instead of showing a neutral selection.

3. **Confidence calibration**: If the tool flags a pattern and users consistently dismiss it, the confidence for that pattern is lowered. If users consistently fix a pattern the tool didn't flag, the tool learns to flag it in the future.

### Step 13.3: Generator Profile Learning

The tool identifies the source application from PDF metadata (`/Creator`, `/Producer`) and builds a profile:

```
Generator: "Microsoft Word 2019"
Total documents scanned: 47
Most common findings:
  1. PDFBP.NO_HEADINGS (100% of documents)
  2. PDFBP.NONSTD_NO_ALT (89% - InlineShape tags)
  3. PDFBP.FORMS_DETACHED (76% - fields at end of structure)
  4. PDFBP.UNDERSCORE_FILL (64% - form fill lines)
  5. PDFBP.FLAT_STRUCTURE (100% - no /Sect grouping)
Typical P tag count per page: 25.3 (vs 8.1 for InDesign)
Auto-fix acceptance rate: 91% for DECORATIVE_NOT_ARTIFACT, 78% for FIELD_LABEL_ORDER
```

When scanning a new Word document, the tool:
- Pre-loads the Word profile and runs the most commonly triggered checks first
- Shows a "Common issues for Word documents" banner in the Issues panel
- Pre-selects likely fixes in the Fix Now dialogs
- Adjusts severity: if 76% of Word documents have detached form fields, the tool surfaces this prominently rather than burying it in a long list

### Step 13.4: User-Defined Pattern Rules

Advanced users can define custom rules that the tool evaluates on every scan:

```
Rule: "UA Forms - Missing Program Name"
Condition: Source application contains "Word"
           AND document title is empty
           AND form field count > 10
Action: Flag as Error with message "University forms require a document title"
```

Custom rules are stored in the `custom_rules` table and checked during the regular scan pass. They can also be exported as JSON and shared with team members, creating organizational-level accessibility standards.

### Step 13.5: Adaptive Scan Prioritization

The learning system reorders checks based on accumulated data:

1. **Source application priority**: If the tool has learned that Word documents always fail PDFBP.NO_HEADINGS and PDFBP.FORMS_DETACHED, those checks run first and their findings appear at the top of the Issues panel.
2. **Recurrence weighting**: Issues that appeared in previous scans of the same document (identified by content hash) and were not fixed are highlighted as "Recurring -- unfixed since [date]".
3. **User pattern priority**: If the user frequently works with university forms that have underscore fill lines, PDFBP.UNDERSCORE_FILL is elevated in severity from "warning" to "error" in their local profile.
4. **Diminishing alerts**: If the user has dismissed a particular finding type 10+ times with "not applicable", the tool stops showing it (with a "Hidden findings: 3" indicator at the bottom of the Issues panel and a "Show Hidden" button).

### Step 13.6: ML Model Retraining

The auto-tagger's ML model (Phase 10, Step 10.3) is retrained from local corrections:

1. **Trigger**: Automatic retraining after every 50 user corrections, or manual via Tools > Retrain Model.
2. **Data**: Combines the shipped `default_model.pkl` training data with local `element_features` and `corrections` data.
3. **Process**: Incremental training (warm start) on the combined dataset. Takes approximately 5 to 30 seconds depending on corpus size.
4. **Validation**: The tool runs a validation pass comparing the retrained model's predictions against the user's corrections. If accuracy drops (overfitting to a narrow document type), the tool warns and offers to keep the previous model.
5. **Storage**: Retrained model saved as `user_model.pkl` alongside `default_model.pkl`. Users can reset to the default model at any time.

### Step 13.7: Team Learning (Optional)

For organizations with multiple remediators:

1. **Export/Import**: Users can export their pattern database as a `.a11y-patterns.json` file and share it with team members.
2. **Merge**: The tool can merge pattern databases from multiple users, combining correction statistics and generator profiles. Merge resolves conflicts by taking the higher-confidence correction.
3. **Shared drive sync**: If the pattern database path is set to a shared network drive, multiple users can contribute to the same learning corpus (SQLite write-ahead logging handles concurrent access).
4. **Organizational rules**: Custom pattern rules (Step 13.4) can be bundled as a `.a11y-rules.json` file and distributed via a shared configuration directory.

### Step 13.8: Learning Dashboard

Preferences > Learning tab:

```
+-----------------------------------------------------+
| Learning Statistics                                  |
+-----------------------------------------------------+
| Documents scanned:           47                      |
| Corrections recorded:        312                     |
| Custom rules:                5                       |
| Model status:    Retrained (312 corrections)         |
| Last retrain:    April 2, 2026 14:35                 |
+-----------------------------------------------------+
| Top generator profiles:                              |
|   Microsoft Word 2019    (34 documents)              |
|   Adobe InDesign 2024    (8 documents)               |
|   Google Docs            (5 documents)               |
+-----------------------------------------------------+
| [Retrain Model Now]  [Export Data]  [Clear All Data] |
+-----------------------------------------------------+
```

All controls are keyboard-accessible: Tab moves between buttons and statistics sections, Enter activates buttons, statistics are announced as read-only text.

### Technology Choices

| Component | Technology | License |
|-----------|-----------|---------|
| Pattern database | sqlite3 (Python stdlib) | Public domain (SQLite) |
| ML retraining | scikit-learn (existing dependency) | BSD-3-Clause |
| Export format | JSON | N/A |
| Privacy | SHA-256 content hashes, 60-char previews, no full text | N/A |

### Why Not Cloud AI?

The adaptive learning system deliberately avoids cloud AI (OpenAI, Copilot, etc.) for core learning:

- **Offline operation**: Government and education users often work in air-gapped or restricted networks.
- **Privacy**: PDF documents may contain PII (names, DOB, medical information as in our sample form). Sending content to cloud APIs creates compliance risk.
- **Cost**: Per-API-call pricing makes scanning hundreds of documents expensive.
- **Latency**: Local SQLite lookups are instant; API calls add seconds per element.

Cloud AI is now implemented as an **opt-in add-on** in Phase 14 (AI-Assisted Remediation and Agentic Integration). The user explicitly chooses to send images to an AI service. All AI features require a GitHub token and are disabled by default. The core desktop tool continues to work fully offline.

**Phase 13 depends on**: Phase 2 (built-in checks), Phase 3 (structure tree), Phase 10 (auto-tagger ML). Can begin collecting data as soon as Phase 2 is implemented.

---

## Phase 14: AI-Assisted Remediation and Agentic Integration

**Goal**: Add opt-in AI capabilities that enhance the desktop tool and expose all scanning/fixing functionality to VS Code Copilot agents via an MCP server.

**Prerequisite**: Phase 2 (Accessibility Checker). Benefits from Phase 3 (Structure Tree) and Phase 4 (Alt Text Editor).

### Dual-Path Architecture

The project supports two complementary workflows:

| Path | Audience | Requirements | Key Features |
|------|----------|-------------|--------------|
| **Desktop** | Remediation teams, QA staff, content creators | Python 3.11+, `pip install pdf-a11y-tool` | wxPython GUI, 29+ built-in checks, guided Fix Now, offline operation |
| **Agentic** | Developers, CI pipelines, VS Code Copilot users | Python 3.11+, `pip install pdf-a11y-tool[agents]`, GitHub token | MCP server, 18 Copilot agents, vision-LLM alt text, batch scanning |

Both paths share the same scanner engine (`builtin_checks.py` and `tools/scan_*.py`), fix tier classification (`tools/fix_tiers.py`), and rule definitions. Fixes applied in one path are valid in the other.

### Step 14.1: AI Bridge Module

**File**: `src/pdf_a11y/core/ai_bridge.py`

A bridge connecting the desktop UI to the agentic toolkit's AI capabilities. Part of the core layer (no wx imports). All methods are synchronous and thread-safe, designed to be called from worker threads with `wx.CallAfter` for UI updates.

**Key classes**:

- `AiBridge` -- Main class. Lazy-loads `tools/alt_text` package. Methods: `generate_alt_text()`, `generate_alt_text_for_document()`, `get_remediation_guidance()`, `list_available_models()`, `list_available_profiles()`.
- `AltTextRequest` / `AltTextResponse` -- Dataclasses for image-to-alt-text requests with quality scoring.
- `RemediationRequest` / `RemediationResponse` -- Dataclasses for fix guidance with tier classification.
- `is_ai_available()` -- Checks if the alt_text package and GitHub token are configured.

**Design decisions**:

- Lazy imports: The `tools/` directory is added to `sys.path` at runtime. The desktop app works without the agents extra installed.
- No wx dependency: `ai_bridge.py` lives in `core/` and uses only stdlib and tools/ imports.
- Graceful degradation: Every method returns a response dataclass, never raises. Errors are captured in the `error` field.

### Step 14.2: MCP Server for Copilot Agents

**File**: `tools/mcp_server.py` (FastMCP via stdio transport)

Exposes 21+ tools to VS Code Copilot:

| Category | Tools | Purpose |
|----------|-------|---------|
| Scanning (11) | `scan_pdf`, `scan_word`, `scan_excel`, `scan_pptx`, `scan_epub`, `scan_markdown`, `scan_pdf_ua`, `scan_metadata`, `scan_tags`, `scan_forms`, `scan_all_documents` | Run accessibility checks on any supported document format |
| Analysis (3) | `list_rules`, `classify_fix_tier`, `merge_scan_results` | Inspect rule catalog, classify findings by fix tier, aggregate multi-doc results |
| Fixing (7) | `fix_pdf`, `fix_word`, `fix_excel`, `fix_pptx`, `fix_epub`, `generate_alt_text`, `batch_alt_text` | Apply automated fixes, generate AI alt text for images |

Configured in `.vscode/mcp.json` using stdio transport. Copilot agents invoke tools via the `doc-accessibility-scanner` MCP server.

### Step 14.3: Copilot Agent Definitions

**Directory**: `agents/`

18 agent definitions (`.agent.md` files) that work with VS Code Copilot:

| Agent | Role |
|-------|------|
| `document-accessibility-wizard` | Orchestrator: 7-phase audit workflow, delegates to specialists |
| `pdf-accessibility` | PDF scanner: 3 rule layers (PDF/UA, best practices, quality) |
| `pdf-remediator` | PDF fixer: 3-tier fixes with scan-fix-verify loop |
| `word-accessibility` | Word scanner: 15 checks with Microsoft rule mapping |
| `excel-accessibility` | Excel scanner: 14 checks for workbook accessibility |
| `powerpoint-accessibility` | PowerPoint scanner: 16 checks for presentation accessibility |
| `epub-accessibility` | ePub scanner: 16 checks for EPUB Accessibility 1.1 |
| `markdown-a11y-assistant` | Markdown audit wizard with severity scoring |
| `office-remediator` | Office fixer: 3-tier approach for Word/Excel/PowerPoint |
| `document-inventory` | File discovery and metadata extraction |
| `cross-document-analyzer` | Pattern detection across multiple document audits |

Plus scan config agents, CSV reporters, markdown scanner/fixer, and ePub config.

### Step 14.4: Alt Text Vision-LLM Package

**Directory**: `tools/alt_text/`

15-file Python package for generating alt text using vision-capable LLMs via GitHub Models API:

- **10 vision models**: GPT-4.1, GPT-4.1-mini, GPT-4o, GPT-4o-mini, Llama-4-Scout, Llama-4-Maverick, Phi-4-multimodal, Mistral-Small, Pixtral-Large, DeepSeek-V3
- **8 profiles**: auto, informative, data, decorative, functional, text, logo, complex
- **Quality scoring**: 0-100 score with flags for length, vagueness, filename patterns
- **Multi-format extraction**: PDF (PyMuPDF), Word (python-docx), Excel (openpyxl), PowerPoint (python-pptx), ePub (zipfile/lxml)

Authentication: GitHub token resolved from `GITHUB_TOKEN` environment variable or `gh auth token` CLI fallback.

### Step 14.5: Skills and Prompts

**Directory**: `agents/skills/` (8 skill directories)

Domain knowledge packages used by Copilot agents:

- `accessibility-rules` -- Cross-format rule reference with WCAG 2.2 mapping
- `document-scanning` -- Document discovery and inventory patterns
- `help-url-reference` -- Maps rule IDs to remediation help URLs
- `pdf-remediation` -- PDF fix patterns and tier classification
- `office-remediation` -- Office doc OOXML fix patterns
- `report-generation` -- Audit report formatting and scoring
- `markdown-accessibility` -- Markdown accessibility rule library
- `no-python-fallback` -- Guidance when Python scanners are unavailable

**Directory**: `.github/prompts/` (16 prompt files)

Pre-built workflows for common tasks: `audit-all-documents.prompt.md`, `auto-remediate.prompt.md`, `quick-document-check.prompt.md`, `verify-fixes.prompt.md`, etc.

**Phase 14 depends on**: Phase 2 (built-in checks). Enhanced by Phase 3 (structure tree), Phase 4 (alt text editor), Phase 13 (adaptive learning).

---

## File Inventory

### Source Files

| Path | Phase | Purpose |
|------|-------|---------|
| `pyproject.toml` | 1 | Project metadata and dependencies |
| `pdf-a11y-tool.spec` | 12 | PyInstaller build specification |
| `README.md` | 1 | Project overview and quick start |
| `LICENSE` | 1 | MIT license |
| `src/pdf_a11y/__init__.py` | 1 | Package init |
| `src/pdf_a11y/__main__.py` | 1 | Entry point |
| `src/pdf_a11y/app.py` | 1 | wx.App subclass and startup |
| `src/pdf_a11y/core/__init__.py` | 1 | Core package init |
| `src/pdf_a11y/core/document.py` | 1 | PDF open/save, undo/redo command stack |
| `src/pdf_a11y/core/renderer.py` | 1 | pypdfium2 page rendering with caching |
| `src/pdf_a11y/core/struct_tree.py` | 3 | Structure tree wrapper (critical module) |
| `src/pdf_a11y/core/tag_types.py` | 3 | Standard PDF 2.0 tag type definitions |
| `src/pdf_a11y/core/content_parser.py` | 9 | Content stream parser for marked content |
| `src/pdf_a11y/core/auto_tagger.py` | 10 | Heuristic and ML auto-tagging engine |
| `src/pdf_a11y/core/sr_linearizer.py` | 3.5 | Structure tree to screen reader announcement text |
| `src/pdf_a11y/core/form_model.py` | 5 | Form field read/write |
| `src/pdf_a11y/core/field_factory.py` | 6 | New field creation and appearance streams |
| `src/pdf_a11y/core/table_model.py` | 7 | Table structure grid model |
| `src/pdf_a11y/core/blank_pdf.py` | 6 | New tagged PDF creation |
| `src/pdf_a11y/core/image_extractor.py` | 4 | Image discovery and thumbnail generation |
| `src/pdf_a11y/core/validator.py` | 2 | veraPDF CLI integration |
| `src/pdf_a11y/core/builtin_checks.py` | 2 | Built-in accessibility checks |
| `src/pdf_a11y/core/report.py` | 2 | Audit report generation |
| `src/pdf_a11y/core/preferences.py` | 11 | User settings persistence |
| `src/pdf_a11y/core/ai_bridge.py` | 14 | AI bridge: connects desktop to vision-LLM toolkit |
| `src/pdf_a11y/ui/__init__.py` | 1 | UI package init |
| `src/pdf_a11y/ui/main_frame.py` | 1 | Main window with AUI panel management |
| `src/pdf_a11y/ui/page_view_panel.py` | 1 | Page bitmap display with overlays |
| `src/pdf_a11y/ui/tag_tree_panel.py` | 3 | Full tag tree editor |
| `src/pdf_a11y/ui/reading_order_panel.py` | 3 | Reading order list with reorder |
| `src/pdf_a11y/ui/alt_text_panel.py` | 4 | Image browser and alt text editor |
| `src/pdf_a11y/ui/table_editor_panel.py` | 7 | Table header scope editor |
| `src/pdf_a11y/ui/issues_panel.py` | 2 | Accessibility findings list |
| `src/pdf_a11y/ui/fields_list_panel.py` | 5 | Form fields list and tab order |
| `src/pdf_a11y/ui/field_properties_panel.py` | 5 | Form field property editor |
| `src/pdf_a11y/ui/field_placement.py` | 6 | New field creation interface |
| `src/pdf_a11y/ui/doc_properties_panel.py` | 8 | Document metadata editor |
| `src/pdf_a11y/ui/auto_tag_wizard.py` | 10 | Auto-tagger review wizard |
| `src/pdf_a11y/ui/sr_preview_panel.py` | 3.5 | Screen reader preview panel |

### Test Files

| Path | Tests For |
|------|-----------|
| `tests/conftest.py` | Shared fixtures (sample PDFs, temp directories) |
| `tests/test_document.py` | PDF open/save, undo/redo |
| `tests/test_struct_tree.py` | Structure tree read/write, reorder, reparent |
| `tests/test_form_model.py` | Form field enumeration and property editing |
| `tests/test_field_factory.py` | New field creation and appearance streams |
| `tests/test_table_model.py` | Table grid parsing and header editing |
| `tests/test_validator.py` | veraPDF integration (mocked subprocess) |
| `tests/test_builtin_checks.py` | Built-in check accuracy against known PDFs |
| `tests/test_report.py` | Report generation formatting and scoring |
| `tests/test_content_parser.py` | Content stream parsing and region detection |
| `tests/test_sr_linearizer.py` | Linearizer output for all tag types, warning detection |
| `tests/test_auto_tagger.py` | Heuristic and ML classifier accuracy |

### Test Fixtures

| Path | Description |
|------|-------------|
| `tests/fixtures/tagged.pdf` | Known-good tagged PDF for round-trip testing |
| `tests/fixtures/untagged.pdf` | Untagged PDF for auto-tagger testing |
| `tests/fixtures/form.pdf` | PDF with various form field types |
| `tests/fixtures/tables.pdf` | PDF with simple and complex tables |
| `tests/fixtures/images.pdf` | PDF with figures, some with alt text, some without |
| `tests/fixtures/bad.pdf` | PDF with many accessibility issues for checker testing |
| `tests/fixtures/scanned.pdf` | Image-only PDF (for testing scope limitations) |

### Agentic Toolkit Files (Phase 14)

| Path | Purpose |
|------|---------|
| `tools/mcp_server.py` | FastMCP server with 21+ tools for VS Code Copilot |
| `tools/scan_all.py` | Multi-format document scanner dispatcher |
| `tools/scan_metadata.py` | PDF metadata accessibility scanner |
| `tools/scan_tags.py` | PDF tag structure scanner |
| `tools/scan_forms.py` | PDF form field accessibility scanner |
| `tools/scan_word.py` | Word document accessibility scanner |
| `tools/scan_excel.py` | Excel workbook accessibility scanner |
| `tools/scan_pptx.py` | PowerPoint presentation accessibility scanner |
| `tools/scan_epub.py` | ePub document accessibility scanner |
| `tools/scan_markdown.py` | Markdown file accessibility scanner |
| `tools/fix_pdf.py` | Automated PDF fixes (title, language, tab order, etc.) |
| `tools/fix_word.py` | Word document fixes |
| `tools/fix_excel.py` | Excel workbook fixes |
| `tools/fix_pptx.py` | PowerPoint fixes |
| `tools/fix_epub.py` | ePub fixes |
| `tools/fix_tiers.py` | Rule-to-tier classification (Tier 1/2/3) |
| `tools/report_md.py` | Markdown audit report generator |
| `tools/report_html.py` | HTML audit report generator |
| `tools/merge_results.py` | Multi-document result aggregation |
| `tools/alt_text/client.py` | GitHub Models API client for vision LLMs |
| `tools/alt_text/models.py` | 10 vision model registry with defaults |
| `tools/alt_text/prompt.py` | Layered prompt assembly per profile |
| `tools/alt_text/profiles.py` | 8 built-in alt text generation profiles |
| `tools/alt_text/scorer.py` | Alt text quality scorer (0-100) |
| `tools/alt_text/config.py` | Configuration dataclass |
| `tools/alt_text/auth.py` | GitHub token resolution |
| `tools/alt_text/extractor_pdf.py` | PDF image extraction via PyMuPDF |
| `tools/alt_text/parser.py` | LLM response HTML parser |
| `tools/alt_text/formats.py` | Output format adapters |
| `agents/AGENTS.md` | Agent registry (18 agents) |
| `.vscode/mcp.json` | MCP server configuration |
| `.a11y-remediation-knowledge.json` | Remediation learning knowledge base |

### Documentation

| Path | Description |
|------|-------------|
| `docs/keyboard-shortcuts.md` | Complete keyboard shortcut reference |
| `docs/user-guide.md` | User guide covering all tool features |

---

## Dependencies

| Package | Min Version | License | Purpose | Required |
|---------|-------------|---------|---------|----------|
| pikepdf | 9.0 | MPL-2.0 | PDF read/write, structure tree, forms | Yes |
| pypdfium2 | 4.0 | Apache-2.0 / BSD | PDF page rendering | Yes |
| wxPython | 4.2 | wxWindows (LGPL-like) | Desktop GUI framework | Yes |
| Pillow | 10.0 | HPND (MIT-like) | Image processing bridge | Yes |
| platformdirs | 4.0 | MIT | Cross-platform config paths | Yes |
| scikit-learn | 1.4 | BSD-3-Clause | ML classifier for auto-tagger | Optional (heuristic fallback) |
| veraPDF | 1.26 | MPL-2.0 | PDF/UA validation CLI | Optional (requires Java) |
| PyInstaller | 6.0 | GPL (build only) | Packaging | Dev only |
| pytest | 8.0 | MIT | Testing | Dev only |
| ruff | 0.6 | MIT | Linting | Dev only |
| mypy | 1.11 | MIT | Type checking | Dev only |
| httpx | 0.27 | BSD-3-Clause | HTTP client for GitHub Models API | Agents extra |
| mcp (FastMCP) | 1.0 | MIT | MCP server for Copilot agent integration | Agents extra |
| PyMuPDF | 1.24 | AGPL-3.0 | Image extraction from PDFs for AI alt text | Agents extra |
| python-docx | 1.1 | MIT | Word document scanning and remediation | Agents extra |
| openpyxl | 3.1 | MIT | Excel workbook scanning and remediation | Agents extra |
| python-pptx | 1.0 | MIT | PowerPoint scanning and remediation | Agents extra |
| lxml | 5.0 | BSD | XML processing for ePub scanning | Agents extra |
| pypdf | 4.0 | BSD | PDF text extraction for AI context | Agents extra |

All runtime dependencies are open source with permissive licenses compatible with MIT distribution.

---

## Phase Dependencies Map

```
Phase 1: Skeleton and Core
  |
  +---> Phase 2: Accessibility Checker
  |
  +---> Phase 3: Tag Tree and Reading Order
  |       |
  |       +---> Phase 3.5: Screen Reader Preview
  |       |
  |       +---> Phase 4: Alt Text Editor
  |       |
  |       +---> Phase 7: Table Header Editor
  |       |
  |       +---> Phase 6: Form Builder (also needs Phase 5)
  |       |
  |       +---> Phase 9: Content Stream Tagging
  |               |
  |               +---> Phase 10: Auto-Tagger
  |
  +---> Phase 5: Form Field Editor
  |       |
  |       +---> Phase 6: Form Builder
  |
  +---> Phase 8: Document Properties
  |
  Phase 11: Tool Accessibility (parallel with all phases)
  |
  Phase 12: Packaging (after all phases for full release)
  |
  Phase 13: Adaptive Learning System (after Phase 2 + Phase 10)
  |
  Phase 14: AI-Assisted Remediation and Agentic Integration (after Phase 2)
             Shares scanner engine with desktop path.
             Enhanced by Phase 4 (alt text) and Phase 13 (learning).
```

Phases that can run in parallel:

- Phase 2, Phase 3, Phase 5, and Phase 8 can begin as soon as Phase 1 is complete
- Phase 3.5, Phase 4, and Phase 7 can begin as soon as Phase 3 is complete
- Phase 6 requires both Phase 3 and Phase 5
- Phase 9 requires Phase 3
- Phase 10 requires Phase 9

---

## Verification and Testing Strategy

### Unit Tests (automated, pytest)

| Test Area | What Is Tested | Expected Outcome |
|-----------|---------------|-----------------|
| Document round-trip | Open PDF, save without changes, compare | Output structure matches input |
| Structure tree read | Parse tag tree from known-good PDF | In-memory tree matches expected hierarchy |
| Structure tree write | Modify tree, save, reopen | Changes persisted correctly |
| Reorder siblings | Move element in /K array, save | New order reflected in saved PDF |
| Reparent element | Move element to new parent, save | Parent references correct, ParentTree valid |
| Form field read | Enumerate fields from form.pdf | All fields found with correct properties |
| Form field write | Edit tooltip, save, reopen | Tooltip value persisted |
| Field creation | Create text field on blank PDF | Field present in saved PDF with correct properties |
| Table model parse | Parse complex table | Grid model matches expected rows/columns/headers |
| Built-in checks | Run checks on bad.pdf | Expected findings match known issues |
| Report generation | Generate report from findings | Markdown format correct, scoring accurate |
| Content parser | Parse content stream from tagged PDF | MCIDs correctly identified and mapped |
| Auto-tagger heuristics | Run heuristics on untagged.pdf | Proposals are reasonable for known content |

### Integration Tests

| Test | Steps | Verification |
|------|-------|-------------|
| Full remediation workflow | Open bad.pdf, run checker, fix title, fix language, fix headings, save | Saved PDF passes all built-in checks |
| Form creation workflow | New blank PDF, add text field, checkbox, dropdown, save | Fields work in Acrobat Reader, SR reads tooltips |
| Table header workflow | Open tables.pdf, set TH scope, associate headers, save | PAC table check passes |
| Auto-tag workflow | Open untagged.pdf, run auto-tagger, accept proposals, save | Saved PDF has valid tag tree, passes basic checks |
| SR preview workflow | Open tagged.pdf, open SR Preview, navigate by heading, navigate by form field, edit alt text, verify preview updates | Preview accurately reflects tag tree; warnings match issues panel; navigation modes filter correctly |

### Manual Accessibility Tests

| Test | Tools | Success Criteria |
|------|-------|-----------------|
| NVDA full walkthrough | NVDA 2025.x, keyboard only | Complete full remediation task without mouse. All controls announced correctly. Focus management is logical. SR Preview panel itself is fully navigable and announces line content. |
| JAWS full walkthrough | JAWS 2025, keyboard only | Same tasks as NVDA walkthrough. All controls announced correctly. |
| High Contrast mode | Windows High Contrast (white on black) | All UI elements visible. Overlays readable. No information lost. |
| 200 percent DPI scaling | Windows Display Settings at 200% | No clipped content. No overlapping controls. All text readable. |
| Keyboard-only navigation | No screen reader, keyboard only | All features reachable. Tab order logical. Shortcuts work. |

### PDF Output Validation

All saved PDFs are validated with:

1. **Built-in checks** -- immediate feedback in the tool
2. **veraPDF** -- full PDF/UA conformance (if installed)
3. **Acrobat Reader** -- open and visually inspect (manual)
4. **Acrobat Pro Accessibility Checker** -- compare results (manual)
5. **PAC** -- secondary validation (manual)
6. **NVDA in Acrobat Reader** -- verify screen reader experience of saved documents (manual)

---

## Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | Structure tree manipulation corrupts PDF | Medium | High | Undo/redo for every operation. Rebuild ParentTree from scratch after edits. Comprehensive unit tests against a corpus of known-good PDFs. Always validate after save. |
| R2 | ParentTree goes out of sync with structure tree | Medium | High | Never update ParentTree incrementally. Rebuild entirely after any structural edit. Validate MCID consistency. |
| R3 | Content stream editing (Phase 9) corrupts page content | Medium | High | Backup original content stream in Command object. Validate BMC/EMC balance after every edit. Automatic rollback on validation failure. Extensive test corpus. |
| R4 | Auto-tagger (Phase 10) produces low-quality tags | Medium | Medium | Always require user review. Never auto-apply without confirmation. Show confidence scores. Allow one-click undo of entire auto-tag operation. Provide retraining workflow. |
| R5 | Appearance streams for new form fields render incorrectly | Medium | Medium | Test created forms in Acrobat Reader, Foxit Reader, Chrome PDF viewer, and Edge. Use pikepdf's built-in generator where possible. |
| R6 | wxPython accessibility gaps on Windows | Low | High | Test early and often with NVDA and JAWS. Use wx.Accessible overrides where native accessibility is insufficient. File wxPython upstream bugs. |
| R7 | veraPDF and Java are deployment friction | Low | Low | Make veraPDF entirely optional. Built-in checks cover 80 percent of common issues. Provide setup wizard. Document Java requirement clearly. |
| R8 | PyInstaller binary size is large | Low | Low | Use one-folder mode. Exclude unused DLLs. Compress with UPX if needed. Document expected size (approximately 100 to 200 MB). |
| R9 | scikit-learn adds significant binary size | Low | Low | Make ML classifier optional. Heuristic classifier works without it. Only include scikit-learn if user opts in during installation. |
| R10 | Complex tables with spans are difficult to parse | Medium | Medium | Start with simple tables (no spans). Add span support incrementally. Flag unparseable tables for manual review. |
| R11 | Form XObjects contain nested content streams | Medium | High | Phase 9 must recursively parse XObject content streams. Add specific test fixtures for PDFs with Form XObjects. |
| R12 | Untagged PDFs with unusual content stream structure | Medium | Medium | Auto-tagger falls back to heuristic-only mode if content stream parsing fails. Always let user override. |
| R13 | Color contrast pixel sampling produces false positives | Medium | Low | Report confidence level (high/medium). Flag gradient and image backgrounds as "medium confidence, verify manually." Never auto-fix contrast (requires content stream color changes). |
| R14 | Auto-sort reading order mishandles complex layouts | Medium | Medium | Always preview before applying. Never auto-apply without confirmation. Multi-column detection uses conservative clustering. Edge cases fall back to top-to-bottom sort with "Review suggested" flag. Single undo reverts entire sort. |
| R15 | Form field-to-label matching produces incorrect associations | Low | Medium | Preview all proposed moves before applying. Use both structural proximity (sibling order) and visual proximity (bounding box). Flag low-confidence matches for manual review. |
| R16 | GitHub Models API rate limits or outages break AI alt text | Medium | Low | AI features are opt-in. Desktop tool works fully offline. Queue and retry with exponential backoff. Cache generated alt text to avoid redundant API calls. |
| R17 | Vision LLM generates inaccurate or harmful alt text | Medium | Medium | Quality scorer flags vague, too-short, or filename-like alt text. User must review and approve all generated alt text before applying. Never auto-apply without confirmation. |
| R18 | GitHub token exposure in development | Low | High | Token resolved from environment variable or `gh auth token`. Never stored in config files or committed. `.gitignore` covers all token-related files. |
| R19 | MCP server protocol drift between FastMCP versions | Low | Medium | Pin mcp dependency to `>=1.0.0,<1.8.0`. Monitor for breaking changes. MCP interface is stdio-based, reducing transport risk. |

---

## Decisions Log

| Decision | Rationale | Alternatives Considered |
|----------|----------|----------------------|
| wxPython for GUI | Best native screen reader support on Windows via MSAA/UIA. AUI dockable panels. Mature accessibility with wx.Accessible. | Qt (PySide6): good but LGPL complexity. Tkinter: weak accessibility support. Web-based: adds browser dependency. |
| pikepdf for PDF manipulation | Active development, MPL-2.0 license, rich low-level API for raw PDF dictionary access. | pdfrw (MIT, lighter but less maintained). borb (AGPL, license problem). PyMuPDF (AGPL, license problem). |
| pypdfium2 for rendering | Apache-2.0 license, wraps Google's PDFium engine. | PyMuPDF (AGPL). pdf2image+Poppler (LGPL, external binary dependency). Ghostscript (AGPL). |
| Property-driven form builder (no drag-and-drop) | Equally accessible to sighted and screen reader users. Simpler to implement. Consistent with the tool's accessibility-first design. | Drag-and-drop with keyboard alternative: more complex, accessibility-as-afterthought risk. |
| veraPDF as optional dependency | Avoids Java requirement for all users. Built-in checks cover 80 percent of common issues. | Require veraPDF: blocks users without Java. Embed veraPDF: adds 100MB+ to package size. |
| Structure tree editing before content stream editing | Structure tree edits are safe (no corruption risk). Content stream editing is high-risk. Ship value early with safer operations. | Content stream editing from the start: higher risk of shipping buggy code. |
| Heuristic auto-tagger with optional ML | Heuristics work without external dependencies and are interpretable. ML improves accuracy but adds scikit-learn dependency. | ML-only: requires training data and adds dependency. Heuristic-only: lower accuracy for edge cases. |
| Rebuild ParentTree from scratch (not incremental) | Eliminates sync bugs between structure tree and ParentTree. Simpler to implement. Acceptable performance for typical document sizes. | Incremental ParentTree updates: faster but much higher bug risk. |
| No AI/Copilot SDK dependency for core analysis | All 29 built-in checks use pikepdf structure inspection, pypdfium2 rendering for contrast and text extraction, and heuristic algorithms for decorative detection, reading order sort, and label-field matching. No cloud API calls, no network dependency, no API keys. The tool works fully offline. AI features are available as an opt-in extra (Phase 14) for users who want vision-LLM alt text generation and agentic workflows. | Cloud-first: would limit offline users. No AI at all: would miss the opportunity for complex image description. |
| Dual-path architecture (desktop + agentic) | The same scanner engine, rule definitions, and fix tier classification power both the wxPython desktop GUI and the MCP server / VS Code Copilot agents. Users choose their preferred workflow without losing functionality. Desktop users get offline reliability; agentic users get AI-powered alt text and batch automation. | Desktop-only: misses developer workflow. Agent-only: excludes accessibility testers who prefer GUI tools. Separate codebases: maintenance burden, rule drift risk. |
| GitHub Models API for vision LLMs | Provides access to 10+ vision-capable models (GPT-4.1, Llama-4, Phi-4, etc.) through a single API endpoint with GitHub token authentication. Free tier available for open-source projects. | OpenAI direct: single vendor lock-in. Azure OpenAI: requires Azure subscription. Local models: insufficient quality for alt text generation. |
| MCP server over REST API | MCP (Model Context Protocol) integrates directly with VS Code Copilot via stdio transport. No port management, no CORS, no deployment. Works in any workspace that opens the repo. | REST API: requires separate server process, port allocation, CORS config. gRPC: overkill for tool invocation. |
| Guided Remediation (Fix Now) over documentation-only | Real user feedback showed that even detailed written instructions are insufficient for many users. One-action fixes (Fix Now button) eliminate the instruction-following barrier entirely. Every auto-fix is undoable. | Documentation-only: cheaper to build but fails users who struggle with multi-step procedures. Wizard-based: more guided but slower per issue. |
| Auto-Sort Reading Order by visual position | Manual reading order correction is the #1 time sink and error source in PDF remediation. Automated sort with review handles 90%+ of cases correctly. Column detection handles common two-column layouts. Edge cases fall back to manual. | Manual-only: leaves users to reorder elements one by one. Full AI layout analysis: overkill for rectangle-based column detection. |
| PyInstaller one-folder mode | Faster startup than one-file. Easier to debug. Files can be inspected. | One-file: single exe but slow startup (extracts to temp). NSIS/Inno installer: better UX but more build complexity (added as future option). |
| MIT license for the tool | Maximum permissibility. Compatible with all dependency licenses (MPL-2.0, Apache-2.0, BSD, LGPL). | MPL-2.0: would require source disclosure for modifications. GPL: too restrictive for team tools. |

---

## UI Experience

This section describes the complete user experience of the application from launch to close. Every control described here is a native wxPython widget. No WebView2, no embedded browser, no HTML rendering panels. This is a deliberate architectural constraint: WebView2 controls are not reliably accessible with all screen readers (JAWS in particular has inconsistent focus and virtual buffer behavior inside embedded WebView2), and mixing native controls with browser controls creates unpredictable focus order. The entire application is one unified native window.

### Design Constraints

| Constraint | Rationale |
|-----------|----------|
| All controls are native wxPython widgets | MSAA and UIA accessibility trees are well-defined for native controls. Screen readers have decades of support for Win32/WinForms controls that wxPython wraps. |
| No embedded HTML rendering | WebView2, CEF, and Chromium Embedded have accessibility gaps with JAWS, Narrator in older builds, and Dragon NaturallySpeaking. Focus trapping between native and web contexts is fragile. |
| No custom-drawn interactive controls | Custom-drawn text, buttons, or lists lose screen reader accessibility unless manually wired via IAccessible/UIA. We only custom-draw the page bitmap (read-only display) and overlays (supplementary visual information). |
| All information conveyed visually is also available non-visually | Color-coded overlays always have text labels. Icons always have text equivalents. Status changes are announced. |
| Every feature is reachable by keyboard alone | No feature requires mouse hover, drag, right-click-only, or gesture input as the sole interaction path. |

### Application Launch

When the user starts the application:

1. The main window appears with the title "PDF Accessibility Tool".
2. If this is the first launch, a veraPDF Setup dialog appears (modal). The user can auto-detect, browse, download, or skip. The dialog is fully keyboard-navigable: Tab moves between buttons, Enter activates, Escape skips.
3. After the setup dialog (or on subsequent launches), the main window is empty with a centered message: "Open a PDF file to begin (Ctrl+O) or create a new blank PDF (Ctrl+N)." This message is the accessible name of the central panel, so a screen reader announces it on focus.
4. The menu bar has focus. A screen reader user hears the menu bar and can press Alt to activate it, or Tab/F6 to move to the empty central area.

### Opening a PDF

Ctrl+O opens a standard Windows File Open dialog (native `wx.FileDialog`). After selecting a file:

1. A progress dialog appears: "Opening document-name.pdf..." with a progress bar. The dialog is announced by screen readers. For small PDFs this is instantaneous; for large PDFs (500+ pages) it may take several seconds.
2. The main window populates. Focus moves to the tag tree panel (left side). A screen reader announces: "Tag tree panel. Document, 47 elements."
3. The status bar updates: "Page 1 of 12, 0 errors, 0 warnings, Zoom 100%." This is a `wx.StatusBar` with three fields.
4. The page view renders page 1 as a bitmap in the center panel.

### Main Window Layout (What the User Encounters)

The window uses wxPython's AUI (Advanced User Interface) manager for dockable panels. Panels can be rearranged, but the default layout is:

**Top**: Menu bar, then toolbar.

**Left column, top**: Tag Tree panel (approximately 300 pixels wide, full height of the left column).

**Left column, bottom**: Reading Order panel.

**Center**: Page View panel (fills remaining horizontal space).

**Right of center**: Properties panel (context-sensitive: shows element attributes, field properties, or document properties depending on what is selected).

**Bottom (full width)**: Tabbed panel area with five tabs: Issues, Fields, Alt Text, Table Editor, SR Preview.

**Bottom edge**: Status bar.

F6 cycles focus between these regions in order: Tag Tree, Page View, Properties, Bottom Tabs, and back to Tag Tree. Within the bottom tabs, Ctrl+Tab cycles between the five tabs. Each panel has an accessible name set via `SetName()` so screen readers announce the panel name when focus arrives.

### The Menu Bar

All menus are native `wx.MenuBar` and `wx.Menu` objects. Every menu item has:

- A text label with an accelerator key underline (Alt+F for File, Alt+E for Edit, etc.)
- A keyboard shortcut where applicable (shown in the menu item text)
- An accessible description (set via the menu item help string, announced by screen readers on hover/focus)

Menu structure:

**File menu** (Alt+F):
- New Blank PDF (Ctrl+N): Opens the blank PDF creation dialog.
- Open (Ctrl+O): Standard file open dialog.
- Save (Ctrl+S): Saves to the current file. Grayed out if no changes.
- Save As (Ctrl+Shift+S): Save to a new file.
- Recent Files: Submenu with up to 10 recently opened files. Each item shows the file name and path.
- Separator.
- Exit (Alt+F4): Prompts to save if there are unsaved changes.

**Edit menu** (Alt+E):
- Undo (Ctrl+Z): Reverts the last command. Menu item text shows what will be undone: "Undo Change Tag Type" or "Undo Set Alt Text." Grayed out if nothing to undo.
- Redo (Ctrl+Y): Same pattern. Grayed out if nothing to redo.
- Separator.
- Preferences: Opens the Preferences dialog.

**View menu** (Alt+V):
- Toggle panels: Checkable menu items for each panel (Tag Tree, Reading Order, Issues, Fields, Alt Text, Tables, SR Preview). Checked items are visible; unchecking hides the panel. Screen readers announce the checked/unchecked state.
- Separator.
- Reading Order Overlay (Ctrl+Shift+O): Checkable. Toggles numbered rectangles on the page view.
- Screen Reader Preview (Ctrl+Shift+R): Switches focus to the SR Preview tab and refreshes it.
- Separator.
- Zoom In (Ctrl+=), Zoom Out (Ctrl+-), Fit Page (Ctrl+0).

**Check menu** (Alt+C):
- Run Full Check (F5): Runs both built-in checks and veraPDF (if configured). Shows progress dialog during the run. When complete, focus moves to the Issues panel and screen reader announces: "Check complete. 12 errors, 5 warnings, 3 tips found."
- Run Built-in Checks Only: Just the built-in checks.
- Run veraPDF Only: Just veraPDF. Grayed out if veraPDF is not configured.
- Separator.
- Export Report: Opens a Save dialog for Markdown or CSV export.

**Tags menu** (Alt+T):
- Change Type: Submenu with all standard tag types grouped by category (Grouping, Block, Inline, Table, Illustration). The currently selected element's current type is indicated. Selecting a new type changes it immediately (undoable).
- Add Child Element: Submenu by type. Adds a new child element under the selected node.
- Delete Element: Deletes with confirmation. Dialog offers "Delete children too" or "Move children to parent."
- Separator.
- Set Alt Text (Ctrl+Alt+A): Opens a text input dialog pre-filled with current alt text.
- Set Actual Text: Opens a text input dialog.
- Set Language (Ctrl+Alt+L): Opens a BCP 47 language picker dialog.
- Separator.
- Auto-Tag Document: Launches the Auto-Tag Wizard.

**Forms menu** (Alt+R):
- Add Text Field, Add Checkbox, Add Radio Group, Add Dropdown, Add Button: Each opens the Field Placement dialog pre-set to that field type.
- Separator.
- Field Properties: Opens the field properties panel for the selected field.

**Tools menu** (Alt+L):
- Generate Bookmarks from Headings: Generates PDF bookmarks matching the heading hierarchy.
- Set Document Title: Opens a text input dialog.
- Set Document Language: Opens a BCP 47 picker.
- Separator.
- veraPDF Setup: Opens the veraPDF configuration dialog.

**Help menu** (Alt+H):
- Keyboard Shortcuts (Ctrl+/): Opens a reference dialog listing all shortcuts. The dialog uses a `wx.ListCtrl` so screen readers can navigate the table.
- User Guide: Opens the user guide (a native `wx.html2.HtmlWindow` is intentionally NOT used; instead, the guide is opened as an external file in the system text viewer or default browser for the `.md` file).
- About: Standard about dialog with application name, version, license, and credits.

### The Toolbar

A `wx.ToolBar` below the menu bar. Each button is a native toolbar button with:

- A bitmap icon (for sighted users)
- A text label below or beside the icon (configurable in preferences: icons only, text only, or both)
- An accessible name matching the text label
- A tooltip matching the text label plus keyboard shortcut

Toolbar buttons left to right:

| Button | Label | Shortcut | State |
|--------|-------|----------|-------|
| Open | "Open PDF" | Ctrl+O | Always enabled |
| Save | "Save" | Ctrl+S | Enabled when dirty |
| Undo | "Undo" | Ctrl+Z | Enabled when undoable |
| Redo | "Redo" | Ctrl+Y | Enabled when redoable |
| Separator | | | |
| Check | "Run Accessibility Check" | F5 | Enabled when document open |
| Separator | | | |
| Zoom Out | "Zoom Out" | Ctrl+- | Enabled when document open |
| Zoom display | "100%" | (read-only) | Shows current zoom |
| Zoom In | "Zoom In" | Ctrl+= | Enabled when document open |
| Fit Page | "Fit Page" | Ctrl+0 | Enabled when document open |
| Separator | | | |
| Overlay | "Toggle Reading Order Overlay" | Ctrl+Shift+O | Toggleable, shows pressed state |

Screen reader users can navigate the toolbar with Left/Right arrow keys. Disabled buttons are announced as "grayed" or "unavailable."

### Tag Tree Panel (Left, Upper)

Accessible name: "Tag tree."

Control: `wx.TreeCtrl` -- a native Windows tree view control. This is one of the best-supported controls across all screen readers. NVDA, JAWS, and Narrator all have deep support for tree views including level announcements, expand/collapse state, and item count.

Each tree item displays: `[status] TagName -- "content preview..." (page N)`

A screen reader announces each item as: "H1, Done, Introduction, page 1, level 2, collapsed, 3 of 47." or "Figure, Action needed, no alt text, page 3, level 3, 5 of 8." The status ("Done" or "Action needed") is part of the accessible name so screen reader users always know which elements still need work. The level corresponds to the nesting depth. Expanded/collapsed state is automatic from `wx.TreeCtrl`. The item count ("3 of 47") is the position among siblings.

Tree item icons are visible to sighted users but do not convey information not already in the text. The tag name (H1, P, Table, Figure, etc.) tells the user what kind of element it is. The status indicator (green checkmark or yellow warning dot) is backed by the text status in the accessible name.

**Text-based element summary** (above the tree): A read-only `wx.TextCtrl` that updates whenever the tree selection changes. This gives screen reader users immediate spatial context:

```
Position: 5 of 47 (sibling 3 of 8 under Document)
Tag: /P (Paragraph)
Content: "This form is not necessary for asthma..."
Page: 1
Previous sibling: /Figure -- "UA Youth Protection logo" (page 1)
Next sibling: /InlineShape -- no alt text (page 1)
Parent: /Document
Children: none (leaf element)
Status: Done -- no issues
Next action: None -- all requirements met
```

A screen reader user can Tab to this summary area and read it with their review cursor. It answers: "Where am I in the tree? What is around me? What needs fixing?" This is critical because tree navigation with arrow keys gives you one node at a time. The summary gives you the full neighborhood at a glance.

**Toolbar above the tree**: A `wx.ToolBar` with visible buttons. Each button has an icon, text label, and keyboard shortcut. Buttons are Tabfocusable and operable with Enter or Space.

| Button | Icon | Label | Shortcut |
|--------|------|-------|----------|
| Up arrow | arrow-up | "Move Up" | Alt+Up |
| Down arrow | arrow-down | "Move Down" | Alt+Down |
| Left arrow | arrow-left | "Move Out" | Alt+Left |
| Right arrow | arrow-right | "Move In" | Alt+Right |
| Separator | | | |
| Lightbulb | lightbulb | "Next Action" | Ctrl+Shift+N |
| Checkmark | check | "Mark Done" | Ctrl+Shift+D |

These buttons make reordering and reparenting discoverable without memorizing shortcuts. Screen reader users navigating the toolbar hear: "Move Up button, Alt+Up. Move Down button, Alt+Down." and so on.

**Drag and drop** (sighted user convenience): Sighted users can drag a tree node and drop it onto another node to reparent, or between nodes to reorder. Drop targets are highlighted visually. A confirmation dialog appears after every drop. Drag and drop is strictly a convenience -- all operations are equally available through keyboard shortcuts and toolbar buttons. Screen reader users are never required to use drag and drop.

Operations available:

- **Arrow keys**: Navigate the tree (Up/Down between siblings and parent/child, Left collapses, Right expands).
- **Enter**: Navigates the page view to the page containing this element and scrolls/highlights it. Does not change focus -- the user stays in the tree.
- **F2**: Opens a dropdown overlay (a `wx.ComboBox` popup) listing all valid tag types for this position. The user selects a new type and presses Enter to apply, or Escape to cancel. This is announced: "Change tag type. Current type H1. Choose new type." The dropdown is filterable by typing.
- **Delete**: Opens a confirmation dialog: "Delete this element? [Delete element and children] [Move children to parent] [Mark as Artifact] [Cancel]". Focus returns to the next sibling after deletion.
- **Ctrl+X**: Cuts the element (for reparenting via Ctrl+V).
- **Ctrl+V**: Pastes the cut element as a child of the currently selected node. A dialog asks: "Insert as first child, last child, or after position N?" with a spinner.
- **Alt+Up / Alt+Down**: Moves the element up or down among its siblings (changes reading order). The tree redraws and focus stays on the moved item. Screen reader announces: "Moved up. Now position 2 of 5."
- **Alt+Left**: Moves the element out of its parent to become a sibling of the parent (reparent to grandparent). Screen reader announces: "Moved out. Now child of Document, position 4 of 12."
- **Alt+Right**: Moves the element into the previous sibling as its last child (nest one level deeper). Screen reader announces: "Moved in. Now child of Sect, position 3 of 3."
- **Ctrl+Alt+A**: Opens a simple text input dialog for alt text. Pre-filled with current value. Labeled: "Alternative text for Figure on page 3." Only enabled for Figure elements.
- **Ctrl+Alt+L**: Opens a language picker dialog. A `wx.ComboBox` with common BCP 47 codes (en, en-US, fr, de, es, etc.) and free-text entry. Labeled: "Language for this element. Current: en-US."
- **Ctrl+Shift+N**: Shows the "Next Action" hint -- the single most important remediation step for this element. Announced as a live region update so the screen reader reads it immediately. Also displayed in the summary area and status bar.
- **Ctrl+Shift+D**: Toggles the manual "Done" status. Screen reader announces: "Marked as done." or "Marked as needs review."
- **Shift+F10** or **Menu key**: Opens the context menu. The first item is always "Next Action" showing the recommended fix. The last section includes "Mark as Done" / "Mark as Needs Review."

When an element is selected, the Properties panel (right side) updates to show that element's attributes. This is a passive update -- focus stays in the tree. The text summary area above the tree also updates with the selected element's context.

### Page View Panel (Center)

Accessible name: "Page view, page N of M."

Control: A custom `wx.Panel` with a `wx.Bitmap` rendered by pypdfium2. This is the one area where custom drawing is used. The panel displays:

- The rendered page bitmap at the current zoom level.
- Optional reading order overlay: numbered rectangles drawn on top of the bitmap, color-coded by element type, with number labels.
- Optional form field rectangles: dotted outlines showing field positions.

This panel is primarily a visual aid. All actionable information is available in other panels (tag tree, reading order, issues). However, the panel is still keyboard-accessible:

- **Arrow keys** (when focused): Scroll the page view if the page is larger than the visible area.
- **Page Up / Page Down**: Navigate between pages. Screen reader announces: "Page 2 of 12."
- **Ctrl+G**: Go to Page dialog. A simple dialog with a page number spinner.
- **Zoom shortcuts**: Ctrl+=, Ctrl+-, Ctrl+0.
- **Tab** (when reading order overlay is on): Cycles through overlay regions. Each region has an accessible tooltip: "Region 5: H2 heading, page 2." This allows keyboard-only users to explore the page layout.

Critical design point: **The page view never holds exclusive information.** Everything visible in the page view is also available in the tag tree, reading order panel, or issues panel. A screen reader user who never looks at the page view can still perform all remediation tasks. The page view is supplementary visual confirmation, not a required interaction surface.

For sighted users, clicking an overlay region selects the corresponding element in the tag tree and reading order panels. This is a convenience shortcut equivalent to navigating the tree directly.

### Reading Order Panel (Left, Lower)

Accessible name: "Reading order."

Control: `wx.ListCtrl` in report mode (multi-column list). This is a native Windows list view, well-supported by all screen readers.

Columns: Order Number, Page, Tag Type, Content Preview.

A screen reader navigates this list with Up/Down arrows and announces: "Row 5. Order 5, Page 2, H2, Executive Summary." Column headers are sortable (click or keyboard: screen reader announces "Sorted by Page ascending").

Operations:

- **Enter**: Selects this element in the tag tree and navigates the page view.
- **Alt+Up / Alt+Down**: Reorders the selected element. This changes the actual reading order in the PDF structure tree. The list redraws and focus stays on the moved item. Screen reader announces: "Moved to position 4."
- **Shift+click or Shift+arrows**: Multi-select for batch moves.
- **Status line**: "Element 5 of 47 -- H2 heading, page 2." Updated on every selection change. This text is the accessible description of the panel, so screen readers can query it.

When the reading order changes here, the tag tree panel redraws to reflect the new sibling order (since reading order IS sibling order in the `/K` array).

### Properties Panel (Right of Center)

Accessible name: "Properties" (updates to "Element properties" or "Field properties" or "Document properties" based on context).

This is a context-sensitive panel. What it shows depends on what is selected elsewhere:

**When a structure element is selected in the tag tree:**

Control: A vertical `wx.Panel` with labeled form controls.

| Label | Control | Description |
|-------|---------|-------------|
| "Tag type" | `wx.StaticText` (read-only) | Current tag name |
| "Alt text" | `wx.TextCtrl` (multiline) | Editable alt text |
| "Actual text" | `wx.TextCtrl` | Editable actual text |
| "Expansion text" | `wx.TextCtrl` | Editable expansion text |
| "Language" | `wx.ComboBox` | BCP 47 code selector |
| "Page" | `wx.StaticText` (read-only) | Page number |
| "MCIDs" | `wx.StaticText` (read-only) | Marked content IDs |
| "Apply" | `wx.Button` | Commits changes |

Each label is programmatically associated with its control via `wx.StaticText` used as the label argument or via explicit `SetName()` on the control. A screen reader user Tabbing through this panel hears: "Alt text, edit, Image showing quarterly revenue chart, multiline."

**When a form field is selected (from the Fields panel or page view):**

The Properties panel shows the field properties editor (name, tooltip, type, flags, position). Same pattern: labeled native controls, Tab-navigable, Apply button.

**When nothing is selected:**

The Properties panel shows document-level properties (title, author, language, etc.).

### Bottom Tabbed Panel Area

Accessible name: "Work panels."

Control: `wx.Notebook` -- a native tabbed control. Ctrl+Tab and Ctrl+Shift+Tab cycle between tabs. Screen readers announce: "Issues tab, 1 of 5" when arriving at a tab.

Five tabs:

#### Tab 1: Issues

Accessible name: "Accessibility issues."

Control: `wx.dataview.DataViewListCtrl` -- a native data grid.

Columns: Severity (icon + text: "Error", "Warning", "Tip"), Rule ID, WCAG, Description, Page, Element.

Above the grid: a filter bar with:
- Severity filter: `wx.Choice` dropdown ("All", "Errors only", "Warnings only", "Tips only"). Labeled: "Filter by severity."
- Text search: `wx.SearchCtrl` (native search box with clear button). Labeled: "Search issues."

Filtering is immediate. Screen reader announces: "Filtered. 12 errors shown."

Grid navigation: Arrow keys move between cells. Screen reader announces column header and cell value: "Severity: Error. Rule ID: PDFUA.TITLE. WCAG: 2.4.2. Description: Document title is missing."

- **Enter** on a row: Navigates to the associated element in the tag tree and page view.
- **Context menu** (Shift+F10): "Go to Element", "Learn More" (opens WCAG reference in default browser), "Dismiss" (marks as reviewed without fixing).

Status line: "12 errors, 5 warnings, 3 tips (20 total)."

After an accessibility check (F5), this tab activates and focus moves to the first error row. Screen reader announces: "Check complete. Issues tab. Row 1 of 20. Severity: Error. Document title is missing."

#### Tab 2: Fields

Accessible name: "Form fields."

Control: `wx.dataview.DataViewListCtrl`.

Columns: Page, Name, Type, Tooltip, Required ("Yes"/"No"), Issues ("Missing tooltip", "Missing name", or blank).

Filter bar: Page filter dropdown, text search, "Show issues only" checkbox.

- **Enter** on a row: Selects the field; Properties panel switches to field properties; page view navigates to the field's page and highlights its rectangle.
- **Tab Order view**: A toggle button above the grid switches between "Field list" and "Tab order" modes. In Tab Order mode, the grid shows fields in their current tab order for the selected page, with a page selector dropdown. Alt+Up/Down reorders.

Batch operations (buttons above the grid):
- "Set tooltip from name": For all fields where TU is empty, copies T to TU. Confirmation dialog first. Single undo-able compound command.
- "Flag missing": Filters to show only fields with issues.

#### Tab 3: Alt Text

Accessible name: "Image alt text."

Control: A custom `wx.Panel` with native sub-controls.

Layout: Two areas side by side.

**Left**: Image thumbnail displayed in a `wx.StaticBitmap`. The bitmap has an accessible name describing the image: "Image thumbnail, page 3, 200 by 150 pixels." For screen reader users, the thumbnail is informational only; the meaningful content is the alt text field.

**Right**: A vertical form:
- "Image N of M" -- `wx.StaticText` (read-only counter).
- "Page" -- `wx.StaticText` (read-only page number).
- "Tag" -- `wx.StaticText` (read-only, e.g., "Figure").
- "Alternative text" -- `wx.TextCtrl` (multiline, labeled). This is the primary editing control.
- "Mark as decorative" -- `wx.CheckBox`. When checked, alt text is cleared (empty string = decorative per PDF/UA). When unchecked, the text field is editable.
- "Apply" -- `wx.Button`. Commits the change.
- "Previous" / "Next" -- `wx.Button` pair. Navigate between images.

Screen reader flow when arriving at this tab: "Image alt text tab. Image 3 of 12, page 3. Alternative text, edit, Company logo. Mark as decorative, checkbox, not checked. Apply button. Previous button. Next button."

The "Flag all missing" button above the form filters to show only images without alt text. Screen reader announces: "Filtered to 5 images missing alt text."

#### Tab 4: Table Editor

Accessible name: "Table header editor."

This tab activates and populates when a Table element is selected in the tag tree. Otherwise it shows: "Select a table element in the tag tree to edit headers."

Control: `wx.grid.Grid` -- a native grid control. This is the standard wxPython grid that exposes row and column headers to screen readers.

Each cell shows: "[TH] Revenue" or "[TD] $1.2M".

Screen reader navigation: Arrow keys move between cells. The screen reader announces: "Row 1, Column 2. Table header. Revenue." or "Row 3, Column 2. Table data. $1.2M."

When a cell is selected, a properties area below the grid shows:
- "Cell type" -- `wx.RadioButton` pair: "Header (TH)" and "Data (TD)". Selecting TH enables the Scope control.
- "Scope" -- `wx.Choice` dropdown: "None", "Row", "Column", "Both". Labeled: "Header scope." Only enabled for TH cells.
- "Headers" -- `wx.TextCtrl` showing associated header IDs. For complex tables. A "Pick headers" button opens a dialog listing all TH cells with checkboxes.
- "Apply" -- `wx.Button`.

Additional buttons:
- "Add THead wrapper" -- wraps the first row(s) in a THead element.
- "Add TBody wrapper" -- wraps body rows.
- "Add TFoot wrapper" -- wraps the last row(s).

These are structural changes to the tag tree, all undoable.

#### Tab 5: Screen Reader Preview

Accessible name: "Screen reader preview."

Control: `wx.ListBox` or `wx.dataview.DataViewListCtrl` -- a native list control.

This is the linearized view described in Phase 3.5. Each list item is one line of screen reader announcement text.

Above the list:
- "Mode" -- `wx.Choice` dropdown: "Full Document", "Headings Only", "Form Fields Only", "Tables Only", "Links Only", "Warnings Only". Labeled: "Preview mode."
- "Refresh" -- `wx.Button`. Refreshes the preview after edits.

Screen reader flow: "Screen reader preview tab. Mode, combo box, Full Document. Line 1 of 87. Heading level 1, Annual Report 2026, page 1."

Navigation:
- **Up/Down arrows**: Move between lines.
- **Enter**: Navigates to the corresponding element in the tag tree and page view. Focus stays in the preview.
- **H**: Jump to next heading line. Screen reader announces the line content.
- **Shift+H**: Jump to previous heading.
- **F**: Jump to next form field line.
- **T**: Jump to next table line.
- **K**: Jump to next link line.
- **W**: Jump to next warning line.

Warning lines are prefixed with "WARNING" and announced differently. Screen reader users hear: "Warning. Image, no alternative text, page 3."

Below the list: Status line -- "Line 5 of 87. Page 1. 2 warnings. Mode: Full Document."

Copy/export buttons:
- "Copy to Clipboard" -- copies the entire linearized text.
- "Export as Text" -- saves to a `.txt` file via a standard Save dialog.

### Status Bar

Control: `wx.StatusBar` with three fields.

Field 1: "Page 1 of 12" -- current page.
Field 2: "3 errors, 2 warnings" -- current issue count (updates after checks).
Field 3: "Zoom: 100%" -- current zoom level.

Screen readers can read the status bar by navigating to it (some screen readers use a specific shortcut; in NVDA, Insert+Page Down reads the status bar). Additionally, significant status changes are announced proactively via `wx.Accessible` event notifications:

- After a check completes: "Check complete. 12 errors, 5 warnings found."
- After save: "Saved successfully."
- After undo/redo: "Undone: change tag type" or "Redone: set alt text."
- After auto-tag: "Auto-tagging complete. 87 elements tagged."

These announcements use `wx.Accessible.NotifyEvent()` with `EVENT_OBJECT_NAMECHANGE` so screen readers pick them up as live updates without stealing focus.

### Dialogs

Every dialog in the application follows these rules:

1. **Modal**: Dialogs trap focus. Tab cycles only through the dialog's controls. Escape closes the dialog and returns focus to the element that opened it.
2. **Title bar**: Every dialog has a descriptive title announced by screen readers: "Set Alternative Text", "Add New Form Field", "Auto-Tag Wizard -- Step 2 of 4".
3. **Default button**: The primary action button (OK, Apply, Save) is the default and responds to Enter from most controls.
4. **Cancel**: Escape always works as Cancel.
5. **Labeled controls**: Every `wx.TextCtrl`, `wx.ComboBox`, `wx.CheckBox`, `wx.SpinCtrl`, and `wx.RadioButton` has a preceding `wx.StaticText` label that is programmatically associated.
6. **Tab order**: Follows visual layout (top to bottom, left to right) which also matches logical order.
7. **Error reporting**: If the user submits invalid data (e.g., empty required field), focus moves to the field with the error and a screen reader-accessible error message appears adjacent to the field.

Key dialogs:

**Preferences dialog**: `wx.Dialog` with `wx.Notebook` tabs: General, Paths, Auto-Tagger, Display. Each tab is a simple form. All inputs labeled.

**Keyboard Shortcuts dialog**: `wx.Dialog` with a `wx.ListCtrl` in report mode. Columns: Shortcut, Action, Context. Screen reader navigates rows: "Ctrl+O, Open PDF, Global."

**Confirmation dialogs**: `wx.MessageDialog` -- fully native, fully accessible. Used for: save before close, delete element, overwrite bookmarks, apply auto-tags.

**Text input dialogs**: Simple `wx.TextEntryDialog` for alt text, actual text, title, etc. Pre-filled with current value. Select-all on focus so the user can type to replace.

**Auto-Tag Wizard**: `wx.Dialog` with four sequential pages controlled by Back/Next buttons. Each page is a panel swapped into the dialog. Screen reader announces the step: "Auto-Tag Wizard, Step 1 of 4, Analysis."

### Common Workflows (Screen Reader User Perspective)

#### Workflow 1: Fix a missing document title

1. Open PDF (Ctrl+O). Screen reader: "Tag tree panel. Document, 47 elements."
2. Run check (F5). Screen reader: "Check complete. Issues tab. Row 1 of 20. Severity: Error. Document title is missing."
3. Press Enter on the finding. The Properties panel switches to document properties.
4. Tab to the Title field. Screen reader: "Title, edit, blank."
5. Type the title.
6. Tab to Apply. Press Enter. Screen reader: "Title set. 1 error resolved."

#### Workflow 2: Add alt text to images

1. Ctrl+Tab to the Alt Text tab. Screen reader: "Image alt text tab. Image 1 of 12."
2. Tab to the alt text field. Screen reader: "Alternative text, edit, blank."
3. Type the description.
4. Tab to Apply. Press Enter.
5. Press Next. Screen reader: "Image 2 of 12, page 1."
6. Repeat.

#### Workflow 3: Fix reading order

1. F6 to navigate to the Reading Order panel. Screen reader: "Reading order panel."
2. Arrow down to the misplaced element. Screen reader: "Row 8. Order 8, Page 2, P, This paragraph is misplaced."
3. Alt+Up to move it earlier. Screen reader: "Moved to position 7."
4. Repeat until correct.

#### Workflow 4: Change a tag type

1. In the tag tree, navigate to the element. Screen reader: "P, Some heading text, page 1, level 3."
2. Press F2. Screen reader: "Change tag type. Current type P. Choose new type, combo box."
3. Type "H2" or arrow to it. Press Enter. Screen reader: "Tag type changed to H2."
4. The tree item updates. SR Preview auto-refreshes.

#### Workflow 5: Verify work with Screen Reader Preview

1. Ctrl+Shift+R to open/refresh the SR Preview. Screen reader: "Screen reader preview tab. Line 1 of 87."
2. Press H to jump through headings. Screen reader reads each heading: "Heading level 1, Annual Report. Heading level 2, Executive Summary."
3. Press W to jump to warnings. Screen reader: "Warning. Image, no alternative text, page 3."
4. Press Enter on the warning. Focus moves to the tag tree at that Figure element.
5. Ctrl+Alt+A to set alt text. Fix it. Ctrl+Shift+R to refresh preview.
6. Press W again. Screen reader: "No more warnings." Work is verified.

#### Workflow 6: Build a form on a new PDF

1. Ctrl+N. "New Blank PDF" dialog. Screen reader: "Title, edit. Enter a document title."
2. Type title, set language, choose page size. Press Create.
3. Forms menu, Add Text Field. The Field Placement dialog opens.
4. Tab through: Name, Tooltip, Required checkbox, position spinners.
5. Press "Add Field." The field appears in the PDF.
6. Repeat for more fields.
7. Switch to Fields tab (Ctrl+Tab). Toggle to Tab Order view. Verify order with arrow keys. Alt+Up/Down to reorder.

### Focus Management Rules

These rules are enforced throughout the application:

1. **Opening a dialog**: Focus moves to the first interactive control in the dialog.
2. **Closing a dialog**: Focus returns to the control that triggered the dialog.
3. **Completing a check**: Focus moves to the Issues tab, first finding row.
4. **Deleting an element**: Focus moves to the next sibling (or parent if no siblings remain).
5. **Undo/Redo**: Focus stays where it is. The undo/redo operation silently updates the model and redraws affected panels.
6. **Navigating from one panel to another** (via Enter on a finding, reading order item, or SR preview line): Focus moves to the target panel and selects the relevant item. The user can return to the previous panel with F6.
7. **Tab key within a panel**: Moves between controls in that panel (edit fields, buttons, etc.).
8. **Tab key does NOT jump between panels**: F6 handles panel cycling. Tab stays within the current panel's controls. This prevents the common problem of Tab cycling through dozens of controls across all panels.

### No Hidden Interactions

Every feature in the application is reachable through at least two paths:

| Feature | Path 1 (Keyboard shortcut) | Path 2 (Menu/Toolbar) | Path 3 (Context menu) | Path 4 (Drag and drop) |
|---------|--------------------------|---------------------|---------------------|-----------------------|
| Open PDF | Ctrl+O | File, Open | -- | -- |
| Save | Ctrl+S | File, Save | -- | -- |
| Run check | F5 | Check, Run Full Check | -- | -- |
| Change tag type | F2 (in tree) | Tags, Change Type | Right-click, Change Type | -- |
| Set alt text | Ctrl+Alt+A | Tags, Set Alt Text | Right-click, Set Alt Text | -- |
| Move up in reading order | Alt+Up | Move Up toolbar button | Right-click, Move Up | -- |
| Move down in reading order | Alt+Down | Move Down toolbar button | Right-click, Move Down | -- |
| Move out (reparent up) | Alt+Left | Move Out toolbar button | Right-click, Move Out | Drag to new parent |
| Move in (reparent deeper) | Alt+Right | Move In toolbar button | Right-click, Move In | Drag onto sibling |
| Reorder by dragging | -- | -- | -- | Drag between nodes |
| Next action hint | Ctrl+Shift+N | Next Action toolbar button | Right-click, Next Action | -- |
| Mark as done | Ctrl+Shift+D | Mark Done toolbar button | Right-click, Mark as Done | -- |
| Delete element | Delete key | Tags, Delete Element | Right-click, Delete | -- |
| Undo | Ctrl+Z | Edit, Undo | -- | -- |
| Toggle overlay | Ctrl+Shift+O | View, Reading Order Overlay | -- | -- |
| SR Preview | Ctrl+Shift+R | View, Screen Reader Preview | -- | -- |

There are no features accessible only by mouse hover, only by drag-and-drop, or only by right-click. Drag and drop is a sighted-user convenience -- every drag-and-drop operation has a keyboard equivalent (Alt+Up/Down/Left/Right or Ctrl+X/V). Right-click and context menus are convenience shortcuts; every action in them is also available via the menu bar, toolbar buttons, or keyboard shortcuts.

---

## Reference Resources

### Standards

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) -- W3C Web Content Accessibility Guidelines
- [How to Meet WCAG Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/) -- filterable standards reference
- [PDF/UA (ISO 14289)](https://pdfa.org/resource/pdfua-flyer/) -- ISO standard for accessible PDF
- [Tagged PDF Q and A](https://pdfa.org/resource/tagged-pdf-q-a/) -- PDF Association technical reference

### Adobe Acrobat Resources

- [Acrobat Accessibility Series Overview](https://experienceleague.adobe.com/en/docs/document-cloud-learn/acrobat-learning/accessibility-tutorials/accessibility-overview)
- [Create and Verify PDF Accessibility](https://helpx.adobe.com/acrobat/using/create-verify-pdf-accessibility.html)
- [Complex Tables](https://experienceleague.adobe.com/en/docs/document-cloud-learn/acrobat-learning/accessibility-tutorials/complex-tables)
- [Scanned Documents](https://experienceleague.adobe.com/en/docs/document-cloud-learn/acrobat-learning/accessibility-tutorials/scanned-documents)

### Section 508 Training

- [PDF Testing and Remediation Series](https://www.section508.gov/training/pdfs/aed-cop-pdf01/)
- [Module 2: Testing a PDF](https://www.section508.gov/training/pdfs/aed-cop-pdf02/)
- [Module 3: Remediating PDFs](https://www.section508.gov/training/pdfs/aed-cop-pdf03/)
- [Module 4: Scanned Documents](https://www.section508.gov/training/pdfs/aed-cop-pdf04/)

### Source Document Authoring

- [Create an Accessible PDF from Word (Adobe)](https://experienceleague.adobe.com/en/docs/document-cloud-learn/acrobat-learning/accessibility-tutorials/create-accessible-from-word)
- [Make Word Documents Accessible (Microsoft)](https://support.microsoft.com/en-us/office/make-your-word-documents-accessible-to-people-with-disabilities-d9bf3683-87ac-47ea-b91a-78dcacb3c66d)
- [Create Accessible PDFs from Microsoft 365](https://support.microsoft.com/en-us/office/create-accessible-pdfs-064625e0-56ea-4e16-ad71-3aa33bb4b7ed)
- [Save as PDF in Office Desktop Apps](https://support.microsoft.com/en-us/office/save-or-convert-to-pdf-or-xps-in-office-desktop-apps-d85416c5-7d77-4fd6-a216-6f4bf7c7c110)
- [Accessibility Tools for Word (Microsoft)](https://support.microsoft.com/en-au/office/accessibility-tools-for-word-5fa2c21f-0ef4-4d4a-ae2d-451fb7003518)

### Tools

- [PAC Quickstart Guide](https://pac.pdf-accessibility.org/en/resources/quickstart-guide)
- [veraPDF](https://verapdf.org/) -- open-source PDF/UA validator
- [pikepdf Documentation](https://pikepdf.readthedocs.io/)
- [pypdfium2](https://github.com/nicegui/pypdfium2)
- [wxPython](https://www.wxpython.org/)

---

*Plan version 1.1 -- April 2, 2026*

*Revision 1.1 changes: Added 4 new built-in checks (PDFBP.ORPHAN_FIELD, PDFBP.FIELD_LABEL_ORDER, PDFBP.DECORATIVE_NOT_ARTIFACT, PDFBP.CONTRAST). Added Guided Remediation (Fix Now) to Issues Panel. Added Auto-Sort Reading Order by Visual Position. Added Align Form Fields to Labels. Added Batch Mark All Decorative as Artifacts. Added built-in color contrast checker using pypdfium2 rendering. Updated Decisions Log with Copilot SDK, Guided Remediation, and Auto-Sort decisions. Updated Risk Register with R13-R15. All additions driven by real end-user feedback on PDF remediation pain points.*
