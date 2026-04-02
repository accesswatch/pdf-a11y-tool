---
name: pdf-remediation
description: PDF accessibility remediation patterns using pikepdf, pypdf, qpdf, and Ghostscript. Covers metadata fixes (title, language, display title), structure fixes (marked content, tab order, PDF/UA identifier), and Adobe Acrobat Pro manual steps for tagging, reading order, table headers, alt text, and form tooltips.
---

# PDF Remediation Patterns Skill

API reference and code patterns for programmatically fixing accessibility issues in PDF documents.

---

## pikepdf Patterns (Primary Library)

### Set Document Title (Info Dict + XMP)

```python
import pikepdf

pdf = pikepdf.open("input.pdf")

# Info dict
pdf.docinfo["/Title"] = "Descriptive Document Title"

# XMP metadata (canonical source)
with pdf.open_metadata() as meta:
    meta["dc:title"] = "Descriptive Document Title"

pdf.save("output.pdf")
pdf.close()
```

### Set Display Document Title

```python
import pikepdf

pdf = pikepdf.open("input.pdf")
root = pdf.Root

if "/ViewerPreferences" not in root:
    root["/ViewerPreferences"] = pikepdf.Dictionary()
root["/ViewerPreferences"]["/DisplayDocTitle"] = True

pdf.save("output.pdf")
pdf.close()
```

### Set Document Language

```python
import pikepdf

pdf = pikepdf.open("input.pdf")
pdf.Root["/Lang"] = "en-US"  # BCP 47 language tag
pdf.save("output.pdf")
pdf.close()
```

### Set Tab Order to Structure Order

```python
import pikepdf

pdf = pikepdf.open("input.pdf")
for page in pdf.pages:
    if page.get("/Tabs") is None:
        page["/Tabs"] = pikepdf.Name("/S")  # Structure order
pdf.save("output.pdf")
pdf.close()
```

### Add PDF/UA-1 Identifier

```python
import pikepdf

pdf = pikepdf.open("input.pdf")
with pdf.open_metadata() as meta:
    meta["pdfuaid:part"] = "1"  # PDF/UA-1
pdf.save("output.pdf")
pdf.close()
```

### Set Marked Content Flag

```python
import pikepdf

pdf = pikepdf.open("input.pdf")
root = pdf.Root
if "/MarkInfo" not in root:
    root["/MarkInfo"] = pikepdf.Dictionary()
root["/MarkInfo"]["/Marked"] = True
# NOTE: This flag alone does not create tags.
# Full tagging requires Acrobat Pro or a tagging library.
pdf.save("output.pdf")
pdf.close()
```

### Read Existing Metadata

```python
import pikepdf

pdf = pikepdf.open("input.pdf")

# Info dict
title = str(pdf.docinfo.get("/Title", ""))
author = str(pdf.docinfo.get("/Author", ""))
lang = str(pdf.Root.get("/Lang", ""))

# XMP metadata
with pdf.open_metadata() as meta:
    xmp_title = meta.get("dc:title", "")
    xmp_creator = meta.get("dc:creator", "")
    pdfua_part = meta.get("pdfuaid:part", "")

# Structure info
is_tagged = bool(pdf.Root.get("/MarkInfo", {}).get("/Marked", False))
has_struct_tree = "/StructTreeRoot" in pdf.Root

pdf.close()
```

### Check and Fix Bookmark/Outline Presence

```python
import pikepdf

pdf = pikepdf.open("input.pdf")
has_outlines = "/Outlines" in pdf.Root
page_count = len(pdf.pages)

if not has_outlines and page_count > 4:
    print("WARNING: No bookmarks in multi-page PDF")
    # Bookmarks cannot be auto-generated without structure tree.
    # Requires Acrobat Pro or a tagging pipeline.

pdf.close()
```

---

## pypdf Patterns (Read-Only Analysis)

### Extract Structure Tree Info

```python
from pypdf import PdfReader

reader = PdfReader("input.pdf")

# Check for structure tree
catalog = reader.trailer["/Root"]
has_struct = "/StructTreeRoot" in catalog

# Count pages
page_count = len(reader.pages)

# Read metadata
meta = reader.metadata
title = meta.title if meta else None
author = meta.author if meta else None
```

### Enumerate Tagged Structure Elements

```python
from pypdf import PdfReader

reader = PdfReader("input.pdf")
root = reader.trailer["/Root"]

if "/StructTreeRoot" in root:
    struct = root["/StructTreeRoot"]
    kids = struct.get("/K", [])
    if not isinstance(kids, list):
        kids = [kids]
    for kid in kids:
        tag = str(kid.get("/S", ""))
        print(f"Top-level tag: {tag}")
```

### Extract Text for Reading Order Analysis

```python
from pypdf import PdfReader

reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages, 1):
    text = page.extract_text() or ""
    print(f"Page {i}: {len(text)} chars extracted")
```

---

## qpdf CLI Patterns

### Linearize PDF (Fast Web View)

```bash
qpdf --linearize input.pdf output.pdf
```

### Check PDF Structure

```bash
qpdf --check input.pdf
```

### Decrypt PDF (Remove Restrictions)

```bash
qpdf --decrypt input.pdf output.pdf
```

### Extract PDF as JSON (Structure Analysis)

```bash
qpdf --json input.pdf > structure.json
```

### Merge PDFs (Preserving Tags)

```bash
qpdf --empty --pages input1.pdf input2.pdf -- merged.pdf
# WARNING: Merging may break tag tree. Re-tag after merge.
```

---

## Ghostscript CLI Patterns

### Convert to PDF/A-2b

```bash
gs -dPDFA=2 -dBATCH -dNOPAUSE -dNOOUTERSAVE \
   -sColorConversionStrategy=UseDeviceIndependentColor \
   -sDEVICE=pdfwrite \
   -dPDFACompatibilityPolicy=1 \
   -sOutputFile=output-pdfa.pdf \
   input.pdf
```

### Re-distill PDF (Fix Corrupted Structure)

```bash
gs -dBATCH -dNOPAUSE -sDEVICE=pdfwrite \
   -sOutputFile=cleaned.pdf \
   input.pdf
# WARNING: Re-distilling strips tags. Only use for structural repair.
```

### Reduce File Size

```bash
gs -dBATCH -dNOPAUSE -sDEVICE=pdfwrite \
   -dCompatibilityLevel=1.7 \
   -dPDFSETTINGS=/ebook \
   -sOutputFile=compressed.pdf \
   input.pdf
```

---

## Adobe Acrobat Pro Manual Steps

For structural fixes that cannot be done programmatically, provide these step-by-step Acrobat Pro instructions.

### Add/Edit Tags (Full Tagging)

1. Open PDF in Acrobat Pro
2. **Prepare** panel (right side) > **Accessibility** > **Autotag Document**
3. Review results in **Tags** panel (View > Show/Hide > Navigation Panes > Tags)
4. Fix mis-tagged elements: right-click tag > **Properties** > change tag type
5. For untagged content: select in document, right-click in Tags panel > **Create Tag from Selection**

### Fix Reading Order

1. Open **Accessibility** > **Reading Order** tool (or Touch Up Reading Order in older versions)
2. Numbered regions appear on each page showing the current order
3. Click a region to select it, then drag to reorder
4. For content that should be skipped (decorative): select region > click **Background/Artifact** button
5. Verify with **Read Out Loud** (View > Read Out Loud > Read This Page Only)

### Fix Table Headers

1. Open **Tags** panel
2. Navigate to the `<Table>` tag
3. Expand until you see `<TR>` and `<TD>` elements
4. For header cells: right-click `<TD>` > **Properties** > change type to `<TH>`
5. Set **Scope**: `Row`, `Column`, or `Both` in the properties dialog
6. For complex tables: add **ID** and **Headers** attributes manually

### Add Alt Text to Images

1. Open **Tags** panel
2. Find `<Figure>` tags (or use Accessibility Checker to locate missing alt text)
3. Right-click `<Figure>` > **Properties**
4. In **Alternate Text** field, enter a concise description
5. For decorative images: check **Decorative Figure** checkbox (or set alt text to empty and mark as artifact)

### Fix Form Field Tooltips

1. Open **Prepare Form** tool
2. Double-click each form field to open properties
3. **General** tab > **Tooltip** field: enter descriptive label
4. For radio button groups: ensure each option has a unique tooltip and the group name is descriptive
5. **Tab Order**: select **Use Document Structure** (Acrobat orders by tags)

### Set Document Properties

1. File > **Properties** (Ctrl+D)
2. **Description** tab:
   - Title: enter descriptive title
   - Author: enter author name
   - Subject: enter brief description
3. **Initial View** tab:
   - Show: **Document Title** (not filename)
4. **Advanced** tab:
   - Language: select the correct language from dropdown

### Run Accessibility Checker

1. **Accessibility** > **Accessibility Check** (or Full Check)
2. Select all categories
3. Review results in left panel
4. Right-click each issue > **Fix** (for auto-fixable) or **Explain** (for guidance)
5. Re-run after fixes to verify

### Add Bookmarks

1. View > Show/Hide > Navigation Panes > **Bookmarks**
2. Navigate to each section heading in the document
3. Click **New Bookmark** icon (or Ctrl+B)
4. Type the section title as the bookmark name
5. Alternatively: **Accessibility** > **Autotag Document** may generate bookmarks from headings

---

## Key PDF Accessibility Properties

| Property | Location | Fix Method |
|----------|----------|------------|
| Title | `/Info /Title` + XMP `dc:title` | pikepdf (programmatic) |
| Display title | `/Root /ViewerPreferences /DisplayDocTitle` | pikepdf (programmatic) |
| Language | `/Root /Lang` | pikepdf (programmatic) |
| Tagged flag | `/Root /MarkInfo /Marked` | pikepdf (flag only) |
| Structure tree | `/Root /StructTreeRoot` | Acrobat Pro (manual) |
| Tab order | Page `/Tabs /S` | pikepdf (programmatic) |
| PDF/UA ID | XMP `pdfuaid:part` | pikepdf (programmatic) |
| Bookmarks | `/Root /Outlines` | Acrobat Pro (manual) |
| Alt text | Structure tree `/Alt` attribute | Acrobat Pro (manual) |
| Table headers | `<TH>` vs `<TD>` structure tags | Acrobat Pro (manual) |
| Form tooltips | Field `/TU` entry | Acrobat Pro (manual) |
| Reading order | Structure tree order | Acrobat Pro (manual) |

---

## Rule ID Reference

| Rule ID | Fix Type | Tool |
|---------|----------|------|
| PDFUA.METADATA.TITLE | Auto | pikepdf |
| PDFUA.METADATA.DISPLAY_TITLE | Auto | pikepdf |
| PDFUA.METADATA.LANG | Auto | pikepdf |
| PDFUA.NAV.TAB_ORDER | Auto | pikepdf |
| PDFUA.METADATA.PDFUA_ID | Auto | pikepdf |
| PDFUA.STRUCTURE.MARKED | Auto (flag only) | pikepdf |
| PDFUA.STRUCTURE.TAGGED | Manual | Acrobat Pro |
| PDFUA.STRUCTURE.HEADINGS | Manual | Acrobat Pro |
| PDFUA.STRUCTURE.TABLES | Manual | Acrobat Pro |
| PDFUA.IMG.ALT | Manual | Acrobat Pro |
| PDFUA.FORMS.TOOLTIP | Manual | Acrobat Pro |
| PDFUA.NAV.BOOKMARKS | Manual | Acrobat Pro |
| PDFBP.READING_ORDER | Manual | Acrobat Pro |
| PDFBP.SCANNED_TEXT | Manual | Acrobat Pro OCR |
| PDFQ.CORRUPTED | Repair | Ghostscript re-distill |

---

## Safety Rules

1. **Always back up** the original file before any modification
2. **Never overwrite** the original -- use `-fixed.pdf` suffix or separate output path
3. **pikepdf only for metadata and flags** -- do not attempt structural tagging with pikepdf
4. **Validate after fix** -- re-scan with `scan_pdf_full` or Acrobat Accessibility Checker
5. **Ghostscript re-distill strips tags** -- only use for structural repair of corrupted PDFs, never for tagged documents
6. **PDF/UA flag without tags is misleading** -- if setting `pdfuaid:part=1`, ensure the document is actually tagged
7. **Acrobat Pro required for full accessibility** -- programmatic tools can fix metadata but not structure, reading order, table headers, or alt text in the tag tree
