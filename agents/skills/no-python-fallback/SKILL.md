# No-Python Fallback Skill

When Python is not installed (or MCP tools are unavailable), agents gracefully degrade instead of failing silently. This skill defines the detection procedure, per-format fallback strategies, and manual checklists that let agents provide maximum value without any Python dependency.

## Environment Detection

Run this probe at the start of every audit workflow. A single failed terminal command is enough to classify the environment.

```text
Probe command (run in terminal):
  python --version

Possible outcomes:
  A. Command succeeds  -> Python is installed.  Try to call any MCP scan tool.
     - MCP tool succeeds  -> FULL MODE.  Use MCP tools normally.
     - MCP tool fails     -> DEGRADED MODE.  Python exists but dependencies missing.
  B. Command fails      -> NO-PYTHON MODE.  Skip all MCP tools.
```

After the probe, set an internal label for the rest of the session:

| Label | Meaning |
|-------|---------|
| `full` | Python + MCP tools work. Use them for everything. |
| `degraded` | Python exists but `pip install -r requirements.txt` has not been run. Offer to install, then retry. In the meantime, use fallback strategies below. |
| `no-python` | No Python at all. Use fallback strategies below for every format. |

## Offer to Install (Degraded Mode Only)

If Python exists but MCP tools fail, tell the user:

> It looks like the scanning libraries are not installed yet. Would you like me to run `pip install -r requirements.txt` in the `tools/` folder to enable full automated scanning? In the meantime, I can still provide a manual audit walkthrough.

If the user agrees, run the install and re-probe. If they decline, continue in fallback mode.

---

## Fallback Strategy by Format

### Markdown (.md) -- Direct-Scan Fallback

Markdown is plain text. Copilot can read it with `read_file` and apply every check directly. **No value is lost.**

**Procedure:**
1. Read the entire file with `read_file`.
2. Walk through all 9 accessibility domains manually:

| Domain | What to check |
|--------|--------------|
| **Links** | Ambiguous text ("click here", "here", "read more", "link", "more info"). Links should describe their destination. |
| **Alt text** | Every `![...]()` image must have descriptive alt text between the brackets. Empty `![]()` is a fail. |
| **Headings** | Must start at `#` (H1), never skip levels (H1 to H3), and have only one H1 per file. |
| **Tables** | Every table must have a header row. Consider adding a description sentence before the table. |
| **Emoji** | Remove emoji entirely or replace with English text in parentheses. Screen readers announce emoji names inconsistently. |
| **Diagrams** | Mermaid code blocks and ASCII art must be replaced with or supplemented by a full text description. |
| **Em-dashes** | Replace `---` or `--` with the word "to" or a comma/semicolon. Screen readers may skip or mispronounce dashes. |
| **Anchors** | Verify that `[text](#anchor)` links point to headings or IDs that actually exist in the file. |
| **Plain language** | Sentences should average under 25 words. Avoid jargon where possible. |

3. Report findings inline using the same severity model as the MCP scanner (error / warning / tip).

### Word (.docx) -- Guidance Mode

Copilot cannot open `.docx` binary files without Python libraries. Instead, walk the user through Microsoft Word's built-in Accessibility Checker.

**Procedure:**
1. Tell the user: "I cannot read Word files directly without Python. Let me guide you through Word's built-in Accessibility Checker instead."
2. Provide these steps:

#### Running the Accessibility Checker
1. Open the document in Microsoft Word.
2. Go to **File** > **Check for Issues** > **Check Accessibility**.
   (Or: **Review** tab > **Check Accessibility** in newer versions.)
3. The Accessibility pane opens on the right showing Errors, Warnings, and Tips.
4. Click each finding to jump to the issue and read the "Why Fix" explanation.

#### Manual Checklist (15 rules)
After running the checker, also verify these items that the checker may miss:

| Check | How to verify |
|-------|--------------|
| Document title set | File > Properties > Title field is not blank |
| Language set | Review > Language > Set Proofing Language matches content language |
| Heading hierarchy | Navigation Pane (View > Navigation Pane) shows H1 > H2 > H3 without skips |
| Alt text on images | Right-click each image > Edit Alt Text -- should be descriptive |
| Alt text on SmartArt | Right-click SmartArt > Edit Alt Text |
| Table header rows | Table Properties > Row tab > "Repeat as header row" is checked |
| No merged cells | Check all tables for irregular cell spans |
| Hyperlink text | No raw URLs or "click here" -- links should describe destination |
| Color-only emphasis | Information is not conveyed by color alone (also use bold, underline, or text) |
| Reading order | Use Selection Pane (Home > Select > Selection Pane) to verify order |
| No blank paragraphs | Don't use blank lines for spacing -- use paragraph spacing instead |
| List formatting | Bulleted/numbered content uses Word's list styles, not manual dashes |
| No text boxes | Avoid floating text boxes -- they may be skipped by screen readers |
| Watermarks | If present, ensure they don't obscure content |
| Bookmarks for long docs | Table of Contents and heading bookmarks for documents over 5 pages |

3. Ask the user to report what the Accessibility Checker found, then help interpret and prioritize.

### Excel (.xlsx) -- Guidance Mode

Same approach as Word -- walk the user through Excel's built-in Accessibility Checker.

**Procedure:**
1. Tell the user: "I cannot read Excel files directly without Python. Let me guide you through Excel's built-in Accessibility Checker instead."
2. Provide these steps:

#### Running the Accessibility Checker
1. Open the workbook in Microsoft Excel.
2. Go to **Review** tab > **Check Accessibility**.
3. The Accessibility pane lists findings per worksheet.

#### Manual Checklist (14 rules)
| Check | How to verify |
|-------|--------------|
| Workbook title set | File > Properties > Title field is not blank |
| Language set | File > Options > Language -- editing language matches content |
| Sheet names are descriptive | Right-click tab > Rename -- no "Sheet1", "Sheet2" defaults |
| Tables have headers | Select data range > Insert > Table > "My table has headers" checked |
| Named ranges for data | Formulas > Name Manager -- key ranges should have names |
| Alt text on charts | Right-click chart > Edit Alt Text |
| Alt text on images | Right-click image > Edit Alt Text |
| No merged cells | Find merged cells: Home > Find & Select > Go To Special > Formats |
| No blank rows/columns as separators | Data regions should not rely on blank rows for structure |
| Color-only data | Information is not conveyed by color alone |
| Hyperlink text | No raw URLs -- hyperlinks should have descriptive display text |
| No hidden sheets with data | Right-click sheet tabs > Unhide to check for hidden sheets |
| Tab order is logical | Tab through cells -- order should follow reading direction |
| Font size at least 11pt | Home tab > Font size for body text |

### PowerPoint (.pptx) -- Guidance Mode

**Procedure:**
1. Tell the user: "I cannot read PowerPoint files directly without Python. Let me guide you through PowerPoint's built-in Accessibility Checker instead."
2. Provide these steps:

#### Running the Accessibility Checker
1. Open the presentation in Microsoft PowerPoint.
2. Go to **Review** tab > **Check Accessibility**.
3. The Accessibility pane lists findings per slide.

#### Manual Checklist (16 rules)
| Check | How to verify |
|-------|--------------|
| Presentation title set | File > Properties > Title field is not blank |
| Language set | File > Options > Language matches content |
| Every slide has a unique title | View > Outline View -- every slide shows a title, no duplicates |
| Slide layouts (not blank) | Use built-in layouts, not blank slides with text boxes |
| Reading order correct | Home > Select > Selection Pane -- items read bottom-to-top in the list |
| Alt text on images | Right-click image > Edit Alt Text |
| Alt text on shapes/SmartArt | Right-click > Edit Alt Text (or mark as decorative) |
| Grouped shapes | Groups should have alt text on the group, not individual shapes |
| Table header rows | Click in table > Table Design > Header Row checkbox |
| No merged cells in tables | Inspect tables for irregular cell spans |
| Hyperlink text | No raw URLs or "click here" |
| Color contrast | Text should be readable against backgrounds |
| No auto-advancing transitions | Transitions tab > uncheck "After" timing |
| No essential audio-only content | Captions or transcripts for audio/video |
| Font size at least 18pt | Body text 18pt+, titles 24pt+ for readability |
| Sections for long presentations | Use PowerPoint sections for 10+ slide presentations |

### PDF -- Guidance Mode

PDFs require specialized libraries to parse. Walk the user through Adobe Acrobat Pro's accessibility tools or free alternatives.

**Procedure:**
1. Tell the user: "I cannot read PDF internal structure without Python. Let me guide you through PDF accessibility verification instead."
2. Determine what tools the user has available:
   - **Adobe Acrobat Pro**: Full accessibility checker and remediation
   - **Free readers (Acrobat Reader, Foxit, etc.)**: Limited to basic reading/reflow checks
   - **PAC 2024 (free)**: Full PDF/UA validation

#### Adobe Acrobat Pro Walkthrough
1. Open the PDF in Acrobat Pro.
2. Go to **All tools** > **Prepare for accessibility** (or **Tools** > **Accessibility** in older versions).
3. Run **Accessibility Check** (full check against PDF/UA and WCAG).
4. Review the results tree -- issues are grouped by category:
   - Document (title, language, tagged)
   - Page Content (figures, headings, tables)
   - Forms (tooltips, tab order)
   - Alternate Text
   - Tables (headers, regularity)
5. Right-click any failed item for fix options.

#### Manual Checklist (Key PDF/UA Requirements)
| Check | How to verify |
|-------|--------------|
| Tagged PDF | File > Properties > "Tagged PDF: Yes" |
| Document title set | File > Properties > Description > Title |
| Title displayed in title bar | File > Properties > Initial View > Show: Document Title |
| Language set | File > Properties > Advanced > Language |
| PDF/UA identifier | Acrobat Preflight > PDF/UA check (or PAC 2024) |
| Heading hierarchy | Tags panel shows H1 > H2 > H3 structure |
| Alt text on figures | Tags panel > Figure tags should have Alt text |
| Table headers | Tags panel > Table > THead with TH cells |
| Reading order | Order panel matches visual reading flow |
| Form field tooltips | Forms panel > each field has a Tooltip |
| Tab order follows document | Page Properties > Tab Order: Use Document Structure |
| Bookmarks for long PDFs | Bookmarks panel populated for 5+ page documents |
| No scanned-image-only pages | Select All Text (Ctrl+A) -- if no text selects, OCR is needed |
| Color contrast | Use PAC 2024 color contrast check or manual inspection |
| Link destinations | Hyperlinks should have descriptive text, not raw URLs |

#### PAC 2024 Walkthrough (Free Alternative)
1. Download PAC 2024 from [PDF Accessibility Checker](https://pac.pdf-accessibility.org/).
2. Open the PDF in PAC.
3. Click "Start Check" for full PDF/UA-1 and WCAG validation.
4. Review the results tree -- similar categories to Acrobat.

### EPUB (.epub) -- Partial Fallback

An EPUB is a ZIP archive containing XHTML, CSS, and OPF metadata. If the user extracts it, Copilot can read the internal files.

**Procedure:**
1. Tell the user: "I cannot scan EPUB files directly without Python. However, an EPUB is a ZIP file. If you extract it, I can read the XHTML and OPF files inside."
2. Guide extraction:
   - **Windows**: Rename `.epub` to `.zip`, then extract.
   - **macOS/Linux**: `unzip book.epub -d book_extracted/`
3. Once extracted, read and audit:
   - `content.opf` or `package.opf`: Check metadata (title, language, accessibility properties)
   - `toc.xhtml` or `toc.ncx`: Verify navigation structure
   - Individual XHTML chapter files: Check heading hierarchy, alt text, table headers, link text

#### Manual Checklist (If Extraction Is Not Possible)
Recommend the user run **Ace by DAISY** (free, cross-platform EPUB accessibility checker):
1. Install: `npm install -g @daisy/ace`
2. Run: `ace book.epub --outdir ace-report/`
3. Open `ace-report/report.html` in a browser.
4. Review findings by EPUB Accessibility 1.1 and WCAG mapping.

#### EPUB Manual Inspection Checklist
| Check | How to verify (in extracted EPUB or reading system) |
|-------|------------------------------------------------------|
| Title set in OPF | `<dc:title>` element in package.opf is not empty |
| Language set in OPF | `<dc:language>` element present (e.g., "en") |
| Accessibility metadata | `<meta property="schema:accessMode">` and related properties |
| Navigation document | `toc.xhtml` exists with `<nav epub:type="toc">` |
| Page list | `<nav epub:type="page-list">` if print page numbers exist |
| Landmarks | `<nav epub:type="landmarks">` with key sections |
| Reading order | Spine order in OPF matches logical reading sequence |
| Alt text on images | `<img alt="...">` in all XHTML files |
| Heading hierarchy | H1 > H2 > H3 in content files, no skipped levels |
| Table headers | `<th>` elements in data tables |
| Link text | No "click here" or raw URLs |
| Language on foreign text | `lang` attribute on inline foreign-language phrases |
| ARIA roles | `<section role="doc-chapter">` and similar DPUB-ARIA roles |
| Cover image alt text | Cover `<img>` has meaningful alt text |
| Decorative images | Decorative images use `alt=""` and `role="presentation"` |
| Media overlays | If audio narration exists, `<smil>` files are present |

---

## Report Format in Fallback Mode

Even without MCP tools, agents should produce a structured report. Use this template:

```markdown
# Document Accessibility Audit -- [Filename]

> **Audit mode**: Manual guidance (Python/MCP tools not available)
> **Date**: [date]
> **Auditor**: Copilot-assisted manual review

## Environment Note

Automated scanning was not available for this audit. Findings below are based on
[the built-in Accessibility Checker / manual inspection / Copilot direct-scan].
Install Python and the toolkit dependencies for automated scanning with severity
scoring and cross-document analysis.

## Summary

| Metric | Value |
|--------|-------|
| Format | [.docx / .xlsx / .pptx / .pdf / .epub / .md] |
| Audit method | [Accessibility Checker walkthrough / Copilot direct-scan / PAC 2024 / Ace by DAISY] |
| Issues found | [count or "see details below"] |

## Findings

### Errors (Must Fix)
[List each error with location and suggested fix]

### Warnings (Should Fix)
[List each warning with location and suggested fix]

### Tips (Consider)
[List each tip]

## Next Steps
- Install Python 3.13+ and run `pip install -r tools/requirements.txt` to enable automated scanning
- Re-run the audit with `@document-accessibility-wizard` for severity scoring, cross-document analysis, and CSV export
```

---

## Key Principle

**Something is always better than nothing.** A guided manual audit catches 70-80% of issues that automated scanning finds. The agent should never say "I can't help without Python" -- instead, it should switch to the appropriate fallback strategy for the format and provide maximum value with the tools available.
