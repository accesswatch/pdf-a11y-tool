"""Shared rule catalog -- single source of truth for all rule knowledge.

Both the desktop report generator (``report.py``) and the agentic report
generators (``tools/report_md.py``, ``tools/report_html.py``) import from
this module so that friendly names, impact descriptions, detection
explanations, remediation steps, WCAG links, and reference URLs are
defined exactly once.

Public API
----------
WCAG_LINKS          -- dict mapping WCAG criterion to (name, url).
REF_LINKS           -- dict mapping reference keys to Markdown links.
RULE_REFERENCE      -- legacy-compatible dict used by agentic generators.
                       Maps rule_id to (standard, wcag, severity,
                       matterhorn_id, description).
READING_ORDER_RULES -- set of rule IDs related to reading order.
MANUAL_REVIEW_RULES -- set of rule IDs requiring human review.
friendly_rule_name  -- Map rule_id to a human-friendly title.
impact_description  -- Map rule_id to a screen-reader-user impact string.
severity_label      -- Map severity string to a report label.
tool_fix_steps      -- PDF Accessibility Tool remediation steps.
acrobat_fix_steps   -- Adobe Acrobat Pro remediation steps.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# WCAG criterion links (merged from both generators)
# ---------------------------------------------------------------------------

WCAG_LINKS: dict[str, tuple[str, str]] = {
    "1.1.1": ("Non-text Content", "https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html"),
    "1.2.1": ("Audio-only and Video-only", "https://www.w3.org/WAI/WCAG22/Understanding/audio-only-and-video-only-prerecorded.html"),
    "1.2.2": ("Captions (Prerecorded)", "https://www.w3.org/WAI/WCAG22/Understanding/captions-prerecorded.html"),
    "1.3.1": ("Info and Relationships", "https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html"),
    "1.3.2": ("Meaningful Sequence", "https://www.w3.org/WAI/WCAG22/Understanding/meaningful-sequence.html"),
    "1.3.3": ("Sensory Characteristics", "https://www.w3.org/WAI/WCAG22/Understanding/sensory-characteristics.html"),
    "1.4.1": ("Use of Color", "https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html"),
    "1.4.3": ("Contrast (Minimum)", "https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html"),
    "2.1.1": ("Keyboard", "https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html"),
    "2.2.1": ("Timing Adjustable", "https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html"),
    "2.3.3": ("Animation from Interactions", "https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html"),
    "2.4.1": ("Bypass Blocks", "https://www.w3.org/WAI/WCAG22/Understanding/bypass-blocks.html"),
    "2.4.2": ("Page Titled", "https://www.w3.org/WAI/WCAG22/Understanding/page-titled.html"),
    "2.4.3": ("Focus Order", "https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html"),
    "2.4.4": ("Link Purpose (In Context)", "https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html"),
    "2.4.5": ("Multiple Ways", "https://www.w3.org/WAI/WCAG22/Understanding/multiple-ways.html"),
    "2.4.6": ("Headings and Labels", "https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels.html"),
    "3.1.1": ("Language of Page", "https://www.w3.org/WAI/WCAG22/Understanding/language-of-page.html"),
    "3.3.2": ("Labels or Instructions", "https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html"),
    "4.1.2": ("Name, Role, Value", "https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html"),
}


# ---------------------------------------------------------------------------
# External tool and specification reference links
# ---------------------------------------------------------------------------

REF_LINKS: dict[str, str] = {
    "pdfua": "[PDF/UA (ISO 14289-1)](https://pdfa.org/resource/iso-14289-pdfua/)",
    "matterhorn": "[Matterhorn Protocol](https://pdfa.org/resource/the-matterhorn-protocol/)",
    "pac": "[PAC 2024 (PDF Accessibility Checker)](https://pac.pdf-accessibility.org/)",
    "acrobat_a11y": "[Adobe Acrobat Pro Accessibility Guide](https://helpx.adobe.com/acrobat/using/creating-accessible-pdfs.html)",
    "ms_word": "[Make your Word documents accessible (Microsoft)](https://support.microsoft.com/en-us/office/make-your-word-documents-accessible-to-people-with-disabilities-d9bf3683-87ac-47ea-b91a-78dcacb3c66d)",
    "ms_excel": "[Make your Excel documents accessible (Microsoft)](https://support.microsoft.com/en-us/office/make-your-excel-documents-accessible-to-people-with-disabilities-6cc05fc5-1314-48b5-8eb3-683e49b3e593)",
    "ms_pptx": "[Make your PowerPoint presentations accessible (Microsoft)](https://support.microsoft.com/en-us/office/make-your-powerpoint-presentations-accessible-to-people-with-disabilities-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25)",
    "webaim_pdf": "[WebAIM: PDF Accessibility](https://webaim.org/techniques/acrobat/)",
    "webaim_alt": "[WebAIM: Alternative Text](https://webaim.org/techniques/alttext/)",
    "webaim_tables": "[WebAIM: Creating Accessible Tables](https://webaim.org/techniques/tables/)",
    "webaim_forms": "[WebAIM: Accessible Forms](https://webaim.org/techniques/forms/)",
    "webaim_links": "[WebAIM: Links and Hypertext](https://webaim.org/techniques/hypertext/)",
    "webaim_contrast": "[WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)",
}


# ---------------------------------------------------------------------------
# RULE_REFERENCE -- legacy-compatible dict for agentic generators
# ---------------------------------------------------------------------------
# Each entry: (standard, wcag_criterion, severity, matterhorn_id, description)

RULE_REFERENCE: dict[str, tuple[str, str, str, str, str]] = {
    # ── PDF (built-in checker rules) ───────────────────────────────────────
    "PDFUA.TITLE":              ("PDF/UA §5.2",     "WCAG 2.4.2",  "Error",   "07-001", "Document title not set in File Properties."),
    "PDFUA.LANG":               ("PDF/UA §5.3",     "WCAG 3.1.1",  "Error",   "06-001", "Document language not set."),
    "PDFUA.TAGGED":             ("PDF/UA §5.1",     "WCAG 1.3.1",  "Error",   "01-001", "Document is not tagged -- structure inaccessible."),
    "PDFUA.IMG.ALT":            ("PDF/UA §6.5",     "WCAG 1.1.1",  "Error",   "13-004", "Figure element missing /Alt text -- image has no alternative text."),
    "PDFUA.HEADINGS":           ("WCAG Technique PDF9", "WCAG 1.3.1", "Error", "14-006", "Heading levels skip one or more levels."),
    "PDFUA.FORMS":              ("PDF/UA §6.6",     "WCAG 1.3.1",  "Error",   "26-001", "Form field missing Tooltip (/TU) -- screen readers have no label."),
    "PDFUA.BOOKMARKS":          ("PDF/UA §6.8",     "WCAG 2.4.1",  "Warning", "12-001", "Document exceeds 20 pages but has no bookmarks for navigation."),
    "PDFBP.DISPLAY_TITLE":      ("PDF/UA Best Practice", "WCAG 2.4.2", "Warning", "07-001", "ViewerPreferences/DisplayDocTitle not enabled."),
    "PDFBP.NO_HEADINGS":        ("WCAG Technique PDF9", "WCAG 2.4.6", "Warning", "14-003", "Document has no headings (H1-H6). Screen reader users cannot navigate by heading."),
    "PDFBP.NONSTD_NO_ALT":     ("PDF/UA §5.4",     "WCAG 1.1.1",  "Warning", "01-007", "Non-standard tag has no alt text or actual text."),
    "PDFBP.TABLE_SCOPE":        ("PDF/UA §6.6",     "WCAG 1.3.1",  "Warning", "15-003", "TH element is missing the Scope attribute."),
    "PDFBP.TABLE_HEADERS":      ("PDF/UA §6.6",     "WCAG 1.3.1",  "Error",   "15-003", "Table has no header cells (/TH elements)."),
    "PDFBP.FLAT_STRUCTURE":     ("PDF/UA Best Practice", "WCAG 1.3.1", "Tip",  "--",     "Document has many direct children with no sectioning (Sect/Part/Art)."),
    "PDFBP.FORMS_DETACHED":     ("PDF/UA Best Practice", "WCAG 1.3.2", "Error", "26-002", "Form fields are grouped at the end of reading order, after all page content."),
    "PDFBP.UNDERSCORE_FILL":    ("PDF/UA Best Practice", "WCAG 1.3.1", "Warning", "--",  "Underscore fill patterns should be marked as artifacts if a form field is overlaid."),
    "PDFBP.NAV.TABORDER":       ("PDF/UA Best Practice", "WCAG 2.4.3", "Warning", "--",  "Page tab order is not set to structure order (/Tabs /S)."),
    "PDFBP.TEXT.EXTRACTABLE":   ("PDF/UA §5.1",     "WCAG 1.3.1",  "Error",   "01-001", "No extractable text found -- document may be scanned or image-only."),
    "PDFBP.ALT_LENGTH":         ("PDF/UA Best Practice", "WCAG 1.1.1", "Warning", "--",  "Alt text exceeds 250 characters -- consider a shorter description."),
    "PDFBP.ALT_QUALITY":        ("PDF/UA Best Practice", "WCAG 1.1.1", "Warning", "--",  "Alt text appears to be a filename or placeholder (e.g. DSC_0042.jpg, image1)."),
    "PDFBP.LANG_VALID":         ("PDF/UA §5.3",     "WCAG 3.1.1",  "Warning", "06-002", "Document /Lang value does not match BCP 47 pattern."),
    "PDFBP.LINK_TEXT":          ("WCAG Technique PDF13", "WCAG 2.4.4", "Warning", "--",  "Link text is non-descriptive (e.g. 'click here', 'read more', or a raw URL)."),
    "PDFBP.EMPTY_TAGS":         ("PDF/UA Best Practice", "WCAG 1.3.1", "Warning", "--",  "Empty P/Span tags cause screen readers to announce 'blank'."),
    "PDFBP.FORMS.DUPLICATE_NAMES": ("PDF/UA §6.6",  "WCAG 1.3.1",  "Warning", "--",     "Non-radio form fields share the same name -- values may overwrite."),
    "PDFBP.FORMS.RADIO_GROUP":  ("WebAIM Forms",    "WCAG 1.3.1",  "Warning", "--",     "Radio button group has only one option -- should be a checkbox."),
    "PDFBP.LIST_STRUCT":        ("PDF/UA §6.5",     "WCAG 1.3.1",  "Warning", "16-003", "List structure is invalid (L > LI > LBody nesting violation)."),
    "PDFBP.FIGURE_CAPTION":     ("PDF/UA §6.5",     "WCAG 1.3.1",  "Warning", "09-004", "Caption tag is not adjacent to its Figure in the structure tree."),
    "PDFBP.ART_TAGS":           ("PDF/UA Best Practice", "WCAG 1.3.1", "Warning", "--",  "Art tags indicate messy structure -- review tag tree organization."),
    "PDFBP.SECT_NESTING":       ("PDF/UA Best Practice", "WCAG 1.3.1", "Tip",  "--",     "Excessive Sect nesting (>3 levels) -- common in PowerPoint exports."),
    "PDFBP.FORMS.TOOLTIP_QUALITY": ("WebAIM Forms", "WCAG 4.1.2",  "Warning", "--",     "Form field tooltip is generic (e.g. 'text', 'field') -- not descriptive."),
    # ── PDF (agentic scanner rules) ────────────────────────────────────────
    "PDFUA.METADATA.TITLE":     ("PDF/UA §5.2",     "WCAG 2.4.2",  "Error",   "07-001", "Document title not set in File Properties."),
    "PDFUA.METADATA.LANG":      ("PDF/UA §5.3",     "WCAG 3.1.1",  "Error",   "06-001", "Document language not set."),
    "PDFUA.METADATA.LANG.REVIEW": ("PDF/UA §5.3",   "WCAG 3.1.1",  "Warning", "06-001", "Document language set but should be verified."),
    "PDFBP.DISPLAY.DOCTITLE":   ("PDF/UA Best Practice", "WCAG 2.4.2", "Warning", "07-001", "ViewerPreferences/DisplayDocTitle not enabled."),
    "PDFUA.STRUCT.TAGGED":      ("PDF/UA §5.1",     "WCAG 1.3.1",  "Error",   "01-001", "Document is not tagged -- structure inaccessible."),
    "PDFQ.METADATA.PDFUA":      ("PDF/UA §5.1",     "--",          "Info",    "--",      "PDF/UA conformance identifier not present."),
    "PDFUA.STRUCT.NOTREE":      ("PDF/UA §5.1",     "WCAG 1.3.1",  "Error",   "01-001", "Tag tree absent or empty."),
    "PDFUA.FORM.STRUCT":        ("PDF/UA §6.6",     "WCAG 1.3.1",  "Error",   "26-002", "Form fields not linked into the structure tree."),
    "PDFBP.FORM.STRUCT":        ("PDF/UA Best Practice", "WCAG 1.3.1", "Warning", "26-002", "Some form fields positioned after all content in tag tree."),
    "PDFBP.LIST.CONTINUATION":  ("PDF/UA Best Practice", "WCAG 1.3.1", "Warning", "--",  "List elements split across page boundaries."),
    "PDFQ.NONSTD.ROLE":         ("PDF/UA §5.4",     "WCAG 1.3.1",  "Info",    "01-007", "Non-standard roles not mapped in RoleMap."),
    "PDFBP.HEADING.SKIP":       ("WCAG Technique PDF9", "WCAG 1.3.1", "Error", "--",     "Heading levels skip one or more levels."),
    "PDFUA.TABLE.HEADERS":      ("PDF/UA §6.6",     "WCAG 1.3.1",  "Error",   "15-003", "Table has no header cells (/TH elements)."),
    "PDFBP.ORDER.FIGURE":       ("PDF/UA §6.5",     "WCAG 1.3.2",  "Warning", "09-004", "Figure not immediately followed by its Caption in tag tree."),
    "PDFBP.ORDER.MCID":         ("PDF/UA §6.1",     "WCAG 1.3.2",  "Warning", "09-004", "Structure-tree MCID order mismatches content-stream paint order."),
    "PDFQ.ORDER.MANUAL":        ("PDF/UA §6.1",     "WCAG 1.3.2",  "Info",    "09-004", "Reading order must be manually verified."),
    "PDFUA.FORM.TU":            ("PDF/UA §6.6",     "WCAG 1.3.1",  "Error",   "26-001", "Form field missing Tooltip (/TU) -- screen readers have no label."),
    "PDFBP.FORMS.REQUIRED_LABEL": ("WebAIM Forms",  "WCAG 3.3.2",  "Warning", "--",     "Required field not labelled as required in Tooltip."),
    "PDFBP.FORMS.BUTTON_TOOLTIP": ("WebAIM Forms",  "WCAG 4.1.2",  "Warning", "--",     "Push button has Tooltip -- tooltip overrides button label."),
    "PDFBP.FORMS.RADIO_TOOLTIP": ("WebAIM Forms",   "WCAG 1.3.1",  "Warning", "--",     "Radio buttons in a group have inconsistent Tooltip text."),
    "PDFBP.FORM.ORPHAN":        ("pypdf docs",      "WCAG 1.3.1",  "Warning", "26-002", "Widget annotation not linked to an AcroForm field."),
    "PDFBP.FORMS.NOACROFORM":   ("PDF/UA §6.6",     "WCAG 1.3.1",  "Info",    "--",     "No AcroForm fields found."),
    # ── DOCX ───────────────────────────────────────────────────────────────
    "DOCX-META.TITLE":          ("WCAG 2.4.2",      "WCAG 2.4.2",  "Error",   "--",     "Word document title not set in core properties."),
    "DOCX-META.LANG":           ("WCAG 3.1.1",      "WCAG 3.1.1",  "Error",   "--",     "Document language not set."),
    "DOCX-STRUCT.HEADINGS":     ("WCAG 1.3.1",      "WCAG 1.3.1",  "Error",   "--",     "Document has body text but no Heading styles."),
    "DOCX-STRUCT.HEADINGSKIP":  ("WCAG 1.3.1",      "WCAG 1.3.1",  "Error",   "--",     "Heading levels skip one or more levels."),
    "DOCX-IMG.ALT":             ("WCAG 1.1.1",      "WCAG 1.1.1",  "Error",   "--",     "Image missing alternative text."),
    "DOCX-IMG.ALT_QUALITY":     ("WCAG 1.1.1",      "WCAG 1.1.1",  "Warning", "--",     "Image alt text appears generic or auto-generated."),
    "DOCX-TABLE.HEADERS":       ("WCAG 1.3.1",      "WCAG 1.3.1",  "Error",   "--",     "Table has no header row designation."),
    "DOCX-TABLE.MERGE":         ("WCAG 1.3.1",      "WCAG 1.3.1",  "Warning", "--",     "Table contains merged cells -- may disorient screen readers."),
    "DOCX-LINK.DESCRIPTIVE":    ("WCAG 2.4.4",      "WCAG 2.4.4",  "Warning", "--",     "Hyperlink text is non-descriptive (e.g. 'click here')."),
    "DOCX-STRUCT.EMPTYPARA":    ("WCAG 1.3.1",      "WCAG 1.3.1",  "Info",    "--",     "Document uses empty paragraphs for spacing."),
    "DOCX-IMG.ALT_FLOAT":       ("WCAG 1.1.1",      "WCAG 1.1.1",  "Error",   "--",     "Floating image missing alternative text."),
    "DOCX-LIST.SEMANTIC":       ("WCAG 1.3.1",      "WCAG 1.3.1",  "Warning", "--",     "Manual lists used without proper list styles."),
    "DOCX-TABLE.NESTED":        ("WCAG 1.3.1",      "WCAG 1.3.1",  "Error",   "--",     "Nested table detected -- may confuse screen readers."),
    "DOCX-STRUCT.TOC":          ("WCAG 2.4.5",      "WCAG 2.4.5",  "Warning", "--",     "No table of contents in a long document."),
    "DOCX-REVIEW.TRACKED":      ("WCAG 1.3.1",      "WCAG 1.3.1",  "Warning", "--",     "Unresolved tracked changes present."),
    "DOCX-STRUCT.HDRFTR":       ("WCAG 1.3.2",      "WCAG 1.3.2",  "Info",    "--",     "Header/footer contains information-bearing content."),
    "DOCX-STRUCT.FOOTNOTES":    ("WCAG 2.4.1",      "WCAG 2.4.1",  "Info",    "--",     "Heavy footnote/endnote usage."),
    # ── XLSX ───────────────────────────────────────────────────────────────
    "XLSX.META.TITLE":          ("Section 508",     "WCAG 2.4.2",  "Error",   "--",     "Workbook title not set in document properties."),
    "XLSX.NAV.SHEET_NAMES":     ("Section 508",     "WCAG 2.4.2",  "Warning", "--",     "Sheet tab(s) use default generic names (Sheet1, etc.)."),
    "XLSX.NAV.SHEET_DUP":       ("Section 508",     "WCAG 2.4.2",  "Warning", "--",     "Duplicate sheet tab names found."),
    "XLSX.NAV.FREEZE_PANES":    ("WebAIM",          "WCAG 1.3.1",  "Info",    "--",     "Sheet has data rows but no frozen header pane."),
    "XLSX.TABLE.NAMED":         ("Section 508",     "WCAG 1.3.1",  "Warning", "--",     "Data range not defined as a named Excel Table object."),
    "XLSX.TABLE.HEADER":        ("Section 508",     "WCAG 1.3.1",  "Error",   "--",     "Excel Table has header row turned off."),
    "XLSX.LAYOUT.MERGED":       ("WebAIM",          "WCAG 1.3.1",  "Warning", "--",     "Merged cells may break screen reader cell navigation."),
    "XLSX.LAYOUT.SPACING":      ("WebAIM",          "WCAG 1.3.1",  "Info",    "--",     "Empty rows used for visual spacing."),
    "XLSX.LINKS.TEXT":          ("WCAG 2.4.4",      "WCAG 2.4.4",  "Warning", "--",     "Hyperlink display text is the raw URL."),
    "XLSX.COLOR.ONLY":          ("WCAG 1.4.1",      "WCAG 1.4.1",  "Warning", "--",     "Cells differentiated by fill color only."),
    "XLSX.CHART.ALT":           ("WCAG 1.1.1",      "WCAG 1.1.1",  "Error",   "--",     "Chart missing alternative text."),
    "XLSX.IMG.ALT":             ("WCAG 1.1.1",      "WCAG 1.1.1",  "Error",   "--",     "Image missing alternative text."),
    "XLSX.LAYOUT.HIDDEN":       ("WCAG 1.3.1",      "WCAG 1.3.1",  "Warning", "--",     "Hidden rows, columns, or sheets detected."),
    "XLSX.PROTECT.SHEET":       ("WCAG 2.1.1",      "WCAG 2.1.1",  "Info",    "--",     "Protected sheet -- ensure interactive elements remain operable."),
    "XLSX.DATA.VALIDATION":     ("WCAG 3.3.2",      "WCAG 3.3.2",  "Warning", "--",     "Data validation rule without input message."),
    # ── PPTX ───────────────────────────────────────────────────────────────
    "PPTX.META.TITLE":          ("Section 508",     "WCAG 2.4.2",  "Error",   "--",     "Presentation title not set in core properties."),
    "PPTX.SLIDE.TITLE":         ("Section 508",     "WCAG 2.4.2",  "Error",   "--",     "Slide(s) missing a title placeholder."),
    "PPTX.SLIDE.TITLE_DUP":     ("Section 508",     "WCAG 2.4.2",  "Warning", "--",     "Multiple slides share the same title."),
    "PPTX.SLIDE.NOTES":         ("WCAG 1.2.1",      "WCAG 1.2.1",  "Info",    "--",     "Slides contain no speaker notes."),
    "PPTX.ORDER.TITLE_FIRST":   ("Section 508",     "WCAG 1.3.2",  "Warning", "--",     "Title placeholder is not first in AT reading order."),
    "PPTX.ORDER.COLUMNS":       ("WCAG 1.3.2",      "WCAG 1.3.2",  "Info",    "--",     "Two-column layout -- reading order must be verified."),
    "PPTX.ORDER.VERIFY":        ("WCAG 1.3.2",      "WCAG 1.3.2",  "Info",    "--",     "Reading order requires manual verification."),
    "PPTX.IMG.ALT":             ("WCAG 1.1.1",      "WCAG 1.1.1",  "Error",   "--",     "Image missing alternative text."),
    "PPTX.IMG.ALT_QUALITY":     ("WCAG 1.1.1",      "WCAG 1.1.1",  "Warning", "--",     "Image alt text appears generic or placeholder."),
    "PPTX.TABLE.HEADER":        ("WCAG 1.3.1",      "WCAG 1.3.1",  "Error",   "--",     "Table missing designated header row."),
    "PPTX.MEDIA.CAPTIONS":      ("WCAG 1.2.2",      "WCAG 1.2.2",  "Warning", "--",     "Presentation contains media -- captions/transcripts must be verified."),
    "PPTX.SECTION.NAME":        ("Section 508",     "WCAG 2.4.1",  "Info",    "--",     "Presentation section(s) using default names."),
    "PPTX.SECTION.DUP":         ("Section 508",     "WCAG 2.4.1",  "Warning", "--",     "Duplicate section names found."),
    "PPTX.LINKS.TEXT":          ("WCAG 2.4.4",      "WCAG 2.4.4",  "Warning", "--",     "Hyperlink display text is the raw URL."),
    "PPTX.META.LANG":           ("WCAG 3.1.1",      "WCAG 3.1.1",  "Error",   "--",     "Presentation language not set."),
    "PPTX.GROUP.ALT":           ("WCAG 1.1.1",      "WCAG 1.1.1",  "Error",   "--",     "Grouped shape missing alternative text."),
    "PPTX.TRANSITION.AUTO":     ("WCAG 2.2.1",      "WCAG 2.2.1",  "Warning", "--",     "Auto-advance slide transition detected."),
    "PPTX.ANIM.EXCESSIVE":      ("WCAG 2.3.3",      "WCAG 2.3.3",  "Info",    "--",     "Excessive animations on slide."),
    # ── EPUB ───────────────────────────────────────────────────────────────
    "EPUB-E001":                 ("EPUB A11y 1.1",   "WCAG 2.4.2",  "Error",   "--",     "Document title (dc:title) missing."),
    "EPUB-E002":                 ("EPUB A11y 1.1",   "--",           "Error",   "--",     "Unique identifier (dc:identifier) missing."),
    "EPUB-E003":                 ("EPUB A11y 1.1",   "WCAG 3.1.1",  "Error",   "--",     "Document language (dc:language) missing."),
    "EPUB-E004":                 ("EPUB A11y 1.1",   "WCAG 2.4.5",  "Error",   "--",     "Table of contents (nav toc / NCX) missing."),
    "EPUB-E005":                 ("EPUB A11y 1.1",   "WCAG 1.1.1",  "Error",   "--",     "Image/SVG/MathML missing alt text."),
    "EPUB-E006":                 ("EPUB A11y 1.1",   "WCAG 1.3.2",  "Error",   "--",     "Spine reading order issue."),
    "EPUB-E007":                 ("EPUB A11y 1.1",   "--",           "Error",   "--",     "Accessibility metadata missing."),
    "EPUB-W001":                 ("EPUB A11y 1.1",   "--",           "Warning", "--",     "Navigation page-list absent."),
    "EPUB-W002":                 ("EPUB A11y 1.1",   "WCAG 2.4.1",  "Warning", "--",     "Navigation landmarks absent."),
    "EPUB-W003":                 ("EPUB A11y 1.1",   "WCAG 2.4.6",  "Error",   "--",     "Heading level skipped in content."),
    "EPUB-W004":                 ("EPUB A11y 1.1",   "WCAG 1.3.1",  "Error",   "--",     "Table missing header elements."),
    "EPUB-W005":                 ("EPUB A11y 1.1",   "WCAG 2.4.4",  "Warning", "--",     "Ambiguous link text."),
    "EPUB-W006":                 ("EPUB A11y 1.1",   "WCAG 1.4.1",  "Warning", "--",     "Fixed-layout ePub detected."),
    "EPUB-T001":                 ("EPUB A11y 1.1",   "--",           "Info",    "--",     "Accessibility summary is brief."),
    "EPUB-T002":                 ("EPUB A11y 1.1",   "--",           "Info",    "--",     "Author (dc:creator) missing."),
    "EPUB-T003":                 ("EPUB A11y 1.1",   "--",           "Info",    "--",     "Description (dc:description) missing."),
    # ── Markdown ───────────────────────────────────────────────────────────
    "MD-A11Y.LINK.AMBIGUOUS":    ("WCAG 2.4.4",      "WCAG 2.4.4",  "Error",   "--",     "Ambiguous link text (e.g. 'click here', 'read more')."),
    "MD-A11Y.LINK.BARE_URL":     ("WCAG 2.4.4",      "WCAG 2.4.4",  "Warning", "--",     "URL used as link text instead of descriptive text."),
    "MD-A11Y.LINK.FILETYPE":     ("WCAG 2.4.4",      "WCAG 2.4.4",  "Warning", "--",     "Download link missing file type indicator."),
    "MD-A11Y.IMG.ALT_MISSING":   ("WCAG 1.1.1",      "WCAG 1.1.1",  "Error",   "--",     "Image missing alt text."),
    "MD-A11Y.IMG.ALT_QUALITY":   ("WCAG 1.1.1",      "WCAG 1.1.1",  "Warning", "--",     "Generic or filename-based alt text."),
    "MD-A11Y.HEADING.MULTIPLE_H1": ("WCAG 1.3.1",    "WCAG 1.3.1",  "Warning", "--",     "Multiple H1 headings in document."),
    "MD-A11Y.HEADING.SKIP":      ("WCAG 1.3.1",      "WCAG 1.3.1",  "Error",   "--",     "Heading level skipped."),
    "MD-A11Y.HEADING.NO_H1":     ("WCAG 1.3.1",      "WCAG 1.3.1",  "Warning", "--",     "No H1 heading in document."),
    "MD-A11Y.TABLE.NO_DESC":     ("WCAG 1.3.1",      "WCAG 1.3.1",  "Warning", "--",     "Table without preceding description."),
    "MD-A11Y.TABLE.EMPTY_HEADER": ("WCAG 1.3.1",     "WCAG 1.3.1",  "Warning", "--",     "Empty table header cell."),
    "MD-A11Y.EMOJI.HEADING":     ("WCAG 1.3.3",      "WCAG 1.3.3",  "Warning", "--",     "Emoji in heading."),
    "MD-A11Y.EMOJI.CONSECUTIVE": ("WCAG 1.3.3",      "WCAG 1.3.3",  "Info",    "--",     "Consecutive emoji sequence."),
    "MD-A11Y.DIAGRAM.MERMAID":   ("WCAG 1.1.1",      "WCAG 1.1.1",  "Error",   "--",     "Mermaid diagram without text alternative."),
    "MD-A11Y.DIAGRAM.ASCII":     ("WCAG 1.1.1",      "WCAG 1.1.1",  "Warning", "--",     "ASCII diagram without text alternative."),
}


# ---------------------------------------------------------------------------
# Rule sets
# ---------------------------------------------------------------------------

READING_ORDER_RULES: set[str] = {
    "PDFBP.ORDER.FIGURE", "PDFBP.ORDER.MCID", "PDFQ.ORDER.MANUAL",
    "PDFBP.FORMS_DETACHED",
    "PPTX.ORDER.TITLE_FIRST", "PPTX.ORDER.COLUMNS", "PPTX.ORDER.VERIFY",
}

MANUAL_REVIEW_RULES: set[str] = {
    r for r, meta in RULE_REFERENCE.items()
    if "manual" in meta[4].lower() or "verify" in meta[4].lower()
} | READING_ORDER_RULES | {"PDFQ.ORDER.MANUAL", "PPTX.ORDER.VERIFY"}


# ---------------------------------------------------------------------------
# Friendly names -- complete coverage for all 29 built-in PDF rules
# ---------------------------------------------------------------------------

_FRIENDLY_NAMES: dict[str, str] = {
    # Original 14 rules
    "PDFUA.TITLE": "Missing Document Title",
    "PDFUA.LANG": "Missing Document Language",
    "PDFUA.TAGGED": "Document Not Tagged",
    "PDFUA.IMG.ALT": "Images Missing Alt Text",
    "PDFUA.HEADINGS": "Heading Hierarchy Issues",
    "PDFUA.FORMS": "Form Fields Missing Tooltips",
    "PDFUA.BOOKMARKS": "Missing Bookmarks",
    "PDFBP.DISPLAY_TITLE": "Display Document Title Not Set",
    "PDFBP.NO_HEADINGS": "No Headings",
    "PDFBP.NONSTD_NO_ALT": "Non-Standard Tags Without Alt Text",
    "PDFBP.TABLE_SCOPE": "Table Headers Missing Scope",
    "PDFBP.TABLE_HEADERS": "Table Missing Header Cells",
    "PDFBP.FLAT_STRUCTURE": "Flat Document Structure",
    "PDFBP.FORMS_DETACHED": "Form Fields Detached From Labels",
    "PDFBP.UNDERSCORE_FILL": "Underscore Fill Patterns",
    "PDFBP.NAV.TABORDER": "Tab Order Not Set to Structure",
    # Batch 1 new rules
    "PDFBP.TEXT.EXTRACTABLE": "No Extractable Text (Scanned/Image-Only)",
    "PDFBP.ALT_LENGTH": "Alt Text Too Long",
    "PDFBP.ALT_QUALITY": "Low-Quality Alt Text (Filename/Placeholder)",
    "PDFBP.LANG_VALID": "Invalid Document Language Code",
    "PDFBP.LINK_TEXT": "Non-Descriptive Link Text",
    "PDFBP.EMPTY_TAGS": "Empty Tags (Blank Announcements)",
    "PDFBP.FORMS.DUPLICATE_NAMES": "Duplicate Form Field Names",
    "PDFBP.FORMS.RADIO_GROUP": "Single-Option Radio Button Group",
    # Batch 2 new rules
    "PDFBP.LIST_STRUCT": "Invalid List Structure",
    "PDFBP.FIGURE_CAPTION": "Caption Not Adjacent to Figure",
    "PDFBP.ART_TAGS": "Art Tags (Messy Structure)",
    "PDFBP.SECT_NESTING": "Excessive Section Nesting",
    "PDFBP.FORMS.TOOLTIP_QUALITY": "Generic Form Field Tooltip",
}


def friendly_rule_name(rule_id: str) -> str:
    """Map a rule_id to a human-friendly issue title."""
    return _FRIENDLY_NAMES.get(rule_id, rule_id)


# ---------------------------------------------------------------------------
# Impact descriptions -- complete coverage for all 29 built-in PDF rules
# ---------------------------------------------------------------------------

_IMPACT_DESCRIPTIONS: dict[str, str] = {
    # Original rules
    "PDFUA.TITLE": (
        "Screen readers announce the filename instead of a meaningful "
        "title when opening the document."
    ),
    "PDFUA.LANG": (
        "Screen readers use the document language to select the correct "
        "speech synthesizer. Without it, text may be mispronounced or "
        "read in the wrong language entirely."
    ),
    "PDFUA.TAGGED": (
        "Without tags, screen readers cannot determine document structure. "
        "Headings, paragraphs, lists, tables, and form fields are all "
        "invisible -- the document is essentially a flat image to "
        "assistive technology."
    ),
    "PDFUA.IMG.ALT": (
        "Images without alternative text are invisible to screen reader "
        "users. The content or function conveyed by the image is lost."
    ),
    "PDFUA.HEADINGS": (
        "Skipped heading levels (e.g., H1 followed by H3) disrupt "
        "screen reader heading navigation and suggest missing content."
    ),
    "PDFUA.FORMS": (
        "Form fields without tooltips are announced as unlabeled "
        "to screen reader users, who cannot determine the field's purpose."
    ),
    "PDFUA.BOOKMARKS": (
        "Long documents without bookmarks force screen reader users to read "
        "linearly through dozens of pages with no way to jump to sections."
    ),
    "PDFBP.DISPLAY_TITLE": (
        "Even when a title is set, if DisplayDocTitle is false, the PDF "
        "viewer shows the filename in the title bar instead of the "
        "meaningful document title."
    ),
    "PDFBP.NO_HEADINGS": (
        "Screen reader users cannot navigate between form sections. "
        "The document may have clear visual sections but they are all "
        "tagged as paragraphs instead of heading tags."
    ),
    "PDFBP.NONSTD_NO_ALT": (
        "Screen readers encounter unnamed non-text elements. Users "
        "hear the tag type name (e.g., 'InlineShape') with no context "
        "about what the element represents."
    ),
    "PDFBP.TABLE_SCOPE": (
        "Screen readers cannot associate data cells with their headers "
        "when navigating the table, making data relationships unclear."
    ),
    "PDFBP.TABLE_HEADERS": (
        "Without header cells, screen readers cannot announce column "
        "or row labels when navigating data cells."
    ),
    "PDFBP.FLAT_STRUCTURE": (
        "A flat tag tree with many direct children and no sections "
        "makes it impossible for screen reader users to navigate "
        "by section or understand the document's organization."
    ),
    "PDFBP.FORMS_DETACHED": (
        "Screen readers encounter all text first, then all fields, "
        "making it impossible to associate fields with their labels."
    ),
    "PDFBP.UNDERSCORE_FILL": (
        "Screen readers announce each underscore character individually, "
        "creating a poor experience. These should be marked as artifacts "
        "if a form field is overlaid."
    ),
    "PDFBP.NAV.TABORDER": (
        "When tab order is not set to structure order, keyboard users "
        "and screen readers tab through form fields in an unpredictable "
        "sequence that does not match the visual layout."
    ),
    # Batch 1 new rules
    "PDFBP.TEXT.EXTRACTABLE": (
        "The document contains no extractable text -- it is likely a scanned "
        "image. Screen readers cannot read any content. The document must be "
        "OCR-processed before any other accessibility fixes apply."
    ),
    "PDFBP.ALT_LENGTH": (
        "Alt text exceeding 250 characters is too long for screen reader "
        "users to absorb in context. Long descriptions should use a "
        "separate long description mechanism instead."
    ),
    "PDFBP.ALT_QUALITY": (
        "Alt text that is a filename (e.g., 'DSC_0042.jpg') or placeholder "
        "(e.g., 'image1') provides no information about the image content. "
        "Screen reader users hear meaningless text instead of a description."
    ),
    "PDFBP.LANG_VALID": (
        "An invalid language code (not matching BCP 47) means screen readers "
        "cannot determine the correct speech synthesizer, potentially "
        "mispronouncing the entire document."
    ),
    "PDFBP.LINK_TEXT": (
        "Non-descriptive link text like 'click here' or 'read more' gives "
        "screen reader users no information about the link destination. "
        "Users navigating by link list hear only the vague text."
    ),
    "PDFBP.EMPTY_TAGS": (
        "Empty P or Span tags cause screen readers to announce 'blank' "
        "repeatedly, cluttering the reading experience and suggesting "
        "missing content."
    ),
    "PDFBP.FORMS.DUPLICATE_NAMES": (
        "When non-radio form fields share the same name, filling one field "
        "may overwrite another. Screen readers announce duplicate names, "
        "making it unclear which field the user is editing."
    ),
    "PDFBP.FORMS.RADIO_GROUP": (
        "A radio button group with only one option should be a checkbox. "
        "Screen readers announce 'radio button 1 of 1', which is confusing "
        "and unconventional."
    ),
    # Batch 2 new rules
    "PDFBP.LIST_STRUCT": (
        "Invalid list nesting (missing LI or LBody) breaks screen reader "
        "list navigation. Users cannot hear item counts or navigate between "
        "list items using keyboard shortcuts."
    ),
    "PDFBP.FIGURE_CAPTION": (
        "A caption separated from its figure in the structure tree is read "
        "out of context. Screen reader users hear the image description "
        "followed by unrelated text, then eventually the caption."
    ),
    "PDFBP.ART_TAGS": (
        "Art tags typically indicate an incompletely tagged or messy structure "
        "tree. Screen readers may announce tag type names instead of content, "
        "or skip content entirely."
    ),
    "PDFBP.SECT_NESTING": (
        "Excessive Sect nesting (more than 3 levels deep) is common in "
        "PowerPoint exports and adds unnecessary verbosity to screen reader "
        "navigation without providing meaningful structure."
    ),
    "PDFBP.FORMS.TOOLTIP_QUALITY": (
        "Generic tooltips like 'text' or 'field' give screen reader users "
        "no information about what to enter. The tooltip should match or "
        "describe the visual label."
    ),
}


def impact_description(rule_id: str) -> str:
    """Return an impact description for a rule."""
    return _IMPACT_DESCRIPTIONS.get(
        rule_id,
        "Assistive technology users may have difficulty with this content.",
    )


# ---------------------------------------------------------------------------
# Severity label mapping
# ---------------------------------------------------------------------------

def severity_label(severity: str) -> str:
    """Map a severity string to a report label."""
    return {
        "error": "CRITICAL",
        "warning": "Important",
        "tip": "Recommended",
    }.get(severity.lower(), severity.capitalize())


# ---------------------------------------------------------------------------
# Remediation steps -- PDF Accessibility Tool
# ---------------------------------------------------------------------------

_TOOL_FIX_STEPS: dict[str, list[str]] = {
    "PDFUA.TITLE": [
        "Open **Document Properties** (Alt+Enter).",
        "**Tab** to the Title field.",
        "Type the document title.",
        "Press **Enter** to apply. The tool writes the title to both /Info /Title and XMP dc:title metadata simultaneously.",
        "The checker reruns automatically and the PDFUA.TITLE error clears from the Issues panel.",
    ],
    "PDFUA.LANG": [
        "Open **Document Properties** (Alt+Enter).",
        "**Tab** to the Language dropdown.",
        "Select the correct language (e.g. 'en-US' for English, 'es' for Spanish).",
        "Press **Enter** to apply.",
    ],
    "PDFUA.TAGGED": [
        "This document must be re-exported from its source application with tagging enabled.",
        "In **Word**: File > Save As > PDF > Options > check 'Document structure tags for accessibility'.",
        "In **PowerPoint**: File > Save As > PDF > Options > check 'Document structure tags'.",
        "If no source is available, use **Auto-Tagger** (Alt+T, A) to generate initial tags.",
    ],
    "PDFUA.IMG.ALT": [
        "**Alt Text Panel** (Alt+4): The images are listed.",
        "For each image, type appropriate alt text describing the content.",
        "Press **Enter** to apply, then **Alt+N** for next image.",
        "For decorative images, check **Mark as decorative** instead.",
    ],
    "PDFUA.HEADINGS": [
        "In the **Tag Tree** (Alt+3), navigate to the heading with the wrong level.",
        "Press **F2** to open the Change Type editor.",
        "Select the correct heading level (H1-H6) maintaining proper hierarchy.",
        "Press **Enter** to confirm.",
    ],
    "PDFUA.FORMS": [
        "In the **Field Properties panel**, Tab to the Tooltip field.",
        "Enter a descriptive label that matches the visual label.",
        "Press **Enter** to apply. Repeat for each field.",
    ],
    "PDFUA.BOOKMARKS": [
        "Use **Auto-Generate Bookmarks** (Alt+T, B) to create bookmarks from headings.",
        "If no headings exist, add headings first (see PDFBP.NO_HEADINGS fix).",
        "Review the generated bookmark tree and adjust as needed.",
    ],
    "PDFBP.DISPLAY_TITLE": [
        "Open **Document Properties** (Alt+Enter).",
        "Tab to the **Display Document Title** checkbox.",
        "Press **Space** to enable it.",
        "Press **Enter** to apply.",
    ],
    "PDFBP.NO_HEADINGS": [
        "**Tag Tree panel** (Alt+3): Use the arrow keys to navigate to each bold section header.",
        "Press **F2** to open the Change Type editor. Select /H1 for the document title, /H2 for sections.",
        "Press **Enter** to confirm. Repeat for each heading.",
        "Alternatively, use **Auto-Tagger** (Alt+T, A): Review the heading candidate list, press **Space** to accept/reject each, then **Enter** on Apply.",
        "After applying, the **Screen Reader Preview** refreshes to show the new heading structure.",
    ],
    "PDFBP.NONSTD_NO_ALT": [
        "**Alt Text Panel** (Alt+4): The non-standard elements are listed.",
        "For decorative items: Press **Space** on the \"Mark as decorative\" checkbox.",
        "Press **Alt+N** to advance to the next element and repeat.",
        "For meaningful images: Type appropriate alt text in the field and press Enter.",
        "Alternatively, in the **Tag Tree**: Navigate to each element, press **Delete** and choose \"Mark as Artifact\" for decorative items.",
    ],
    "PDFBP.TABLE_SCOPE": [
        "In the **Table Editor**, Tab to the first header cell.",
        "Press **Enter** to select it.",
        "Use the **Scope dropdown** to set Row or Column.",
        "Press **Enter** to apply. Repeat for each TH cell.",
    ],
    "PDFBP.TABLE_HEADERS": [
        "In the **Table Editor**, select the first row of cells.",
        "Press **Ctrl+H** to convert TD cells to TH header cells.",
        "Then set Scope on each new header cell.",
    ],
    "PDFBP.FLAT_STRUCTURE": [
        "In the **Tag Tree**, select the Document root.",
        "Press **Insert** to add a /Sect child.",
        "Select related heading and content elements, press **Ctrl+X** to cut.",
        "Arrow to the Sect element, press **Ctrl+V** to paste.",
        "Repeat for each logical section of the document.",
    ],
    "PDFBP.FORMS_DETACHED": [
        "Use **Auto-Sort Reading Order** (Alt+T, R) to interleave form fields with their labels.",
        "Preview the proposed order in the dialog.",
        "Press **Enter** to apply. Each field is reparented to follow its label.",
        "Ctrl+Z undoes all changes if needed.",
    ],
    "PDFBP.UNDERSCORE_FILL": [
        "In the **Tag Tree**, navigate to each paragraph with underscore fills.",
        "If a form field overlaps, press **Delete** and choose 'Mark as Artifact'.",
        "The **'Clean All Underscore Fills'** batch action (Alt+T, U) processes all flagged elements at once.",
    ],
    "PDFBP.NAV.TABORDER": [
        "In the **Accessibility Checker** results, right-click the Tab Order finding.",
        "Choose **Fix** to set all pages to structure-based tab order.",
        "Alternatively, open **Page Properties** for each page and set Tab Order to Structure.",
    ],
    "PDFBP.TEXT.EXTRACTABLE": [
        "This document needs **OCR** before other fixes can be applied.",
        "Use **Recognize Text** (Alt+T, O): Select the language, then run OCR.",
        "After OCR completes, re-run the accessibility checker to identify remaining issues.",
        "Review OCR accuracy -- especially for handwritten text, forms, and non-Latin scripts.",
    ],
    "PDFBP.ALT_LENGTH": [
        "In the **Alt Text Panel** (Alt+4), navigate to the flagged image.",
        "Shorten the alt text to a concise description (aim for under 150 characters).",
        "If a detailed description is needed, use a **long description** link or adjacent text instead.",
    ],
    "PDFBP.ALT_QUALITY": [
        "In the **Alt Text Panel** (Alt+4), locate the image with the placeholder alt text.",
        "Replace the filename or placeholder with a meaningful description of the image content.",
        "Press **Enter** to apply.",
    ],
    "PDFBP.LANG_VALID": [
        "Open **Document Properties** (Alt+Enter).",
        "Tab to the Language dropdown.",
        "Select a valid BCP 47 language code (e.g. 'en-US', 'es', 'fr').",
        "Press **Enter** to apply.",
    ],
    "PDFBP.LINK_TEXT": [
        "In the **Tag Tree** (Alt+3), navigate to each Link element.",
        "Press **F2** to edit the link's visible text.",
        "Replace 'click here' or raw URLs with descriptive text explaining the destination.",
        "Press **Enter** to apply.",
    ],
    "PDFBP.EMPTY_TAGS": [
        "In the **Tag Tree** (Alt+3), navigate to each empty P or Span tag.",
        "Press **Delete** to remove the empty tag, or choose 'Mark as Artifact'.",
        "The **Clean Empty Tags** batch action (Alt+T, E) removes all empty tags at once.",
    ],
    "PDFBP.FORMS.DUPLICATE_NAMES": [
        "In the **Field Properties panel**, Tab to the Name field.",
        "Rename each duplicate field to be unique (e.g. 'Phone_1', 'Phone_2').",
        "Press **Enter** to apply. Repeat for each duplicate.",
    ],
    "PDFBP.FORMS.RADIO_GROUP": [
        "If the radio group should be a checkbox: In the **Tag Tree**, change the field type.",
        "If it genuinely needs multiple options: Add the missing option(s) in the form editor.",
        "Press **Enter** to apply.",
    ],
    "PDFBP.LIST_STRUCT": [
        "In the **Tag Tree** (Alt+3), navigate to the malformed list.",
        "Verify the structure follows L > LI > LBody nesting.",
        "If LBody is missing, select the LI content and press **Ctrl+Shift+B** to wrap in LBody.",
        "If LI is missing, select content and press **Ctrl+Shift+I** to wrap in LI.",
    ],
    "PDFBP.FIGURE_CAPTION": [
        "In the **Tag Tree** (Alt+3), locate the Caption tag that is separated from its Figure.",
        "Press **Ctrl+X** to cut the Caption.",
        "Navigate to immediately after the Figure tag and press **Ctrl+V** to paste.",
        "Verify the Caption now follows directly after the Figure in the tree.",
    ],
    "PDFBP.ART_TAGS": [
        "In the **Tag Tree** (Alt+3), locate each Art tag.",
        "Review whether the Art tag should be a Sect, Figure, or other standard tag.",
        "Press **F2** to change the type to the appropriate standard tag.",
        "Press **Enter** to confirm.",
    ],
    "PDFBP.SECT_NESTING": [
        "In the **Tag Tree** (Alt+3), expand the deeply nested Sect elements.",
        "Flatten unnecessary nesting by selecting content and moving it to a parent Sect.",
        "Press **Ctrl+X** to cut and **Ctrl+V** to paste at the correct level.",
        "Aim for no more than 3 levels of Sect nesting.",
    ],
    "PDFBP.FORMS.TOOLTIP_QUALITY": [
        "In the **Field Properties panel**, Tab to the Tooltip field.",
        "Replace the generic text ('text', 'field', etc.) with the actual visual label text.",
        "Press **Enter** to apply. Repeat for each field with a generic tooltip.",
    ],
}


def tool_fix_steps(rule_id: str) -> list[str]:
    """Return PDF Accessibility Tool remediation steps for a rule."""
    return _TOOL_FIX_STEPS.get(
        rule_id,
        ["Follow the remediation guidance in the Findings section above."],
    )


# ---------------------------------------------------------------------------
# Remediation steps -- Adobe Acrobat Pro
# ---------------------------------------------------------------------------

_ACROBAT_FIX_STEPS: dict[str, list[str]] = {
    "PDFUA.TITLE": [
        "Open **File > Properties** (Ctrl+D).",
        "In the **Description** tab, Tab to the Title field.",
        "Type the title and press **OK**.",
        "Open File > Properties again, go to **Initial View** tab, verify \"Show\" is set to \"Document Title\".",
    ],
    "PDFUA.LANG": [
        "Open **File > Properties** (Ctrl+D).",
        "In the **Advanced** tab, select the correct language from the **Language** dropdown.",
        "Press **OK**.",
    ],
    "PDFUA.TAGGED": [
        "Run **All Tools > Accessibility > AutoTag Document**.",
        "Review the Tags panel for accuracy -- fix any /P elements that should be headings.",
        "Run **Accessibility Check** (All Tools > Accessibility > Full Check) to verify.",
        "File > Save As.",
    ],
    "PDFUA.IMG.ALT": [
        "In the **Tags panel**, select the Figure tag.",
        "Press **Ctrl+E** to open Properties.",
        "Enter **Alternative Text** describing the image content.",
        "For decorative images, change type to Artifact.",
    ],
    "PDFUA.HEADINGS": [
        "In the **Tags panel**, select the heading tag.",
        "Press **Ctrl+E** to open Properties.",
        "Change the **Type** to the correct heading level (H1-H6).",
        "Press **OK**.",
    ],
    "PDFUA.FORMS": [
        "Select the form field in the document.",
        "Open Properties (**Ctrl+E**), General tab.",
        "Enter a descriptive **Tooltip** matching the visual label.",
        "Press **OK**. Repeat for each field.",
    ],
    "PDFUA.BOOKMARKS": [
        "In Acrobat, go to **All Tools > Accessibility > Add Bookmarks**.",
        "Select to generate bookmarks from the document structure.",
        "Review and adjust the bookmark names in the Bookmarks panel.",
    ],
    "PDFBP.DISPLAY_TITLE": [
        "Open **File > Properties** (Ctrl+D).",
        "Go to the **Initial View** tab.",
        "Set **Show** to \"Document Title\".",
        "Press **OK**.",
    ],
    "PDFBP.NO_HEADINGS": [
        "Open the **Tags panel** (View > Show/Hide > Navigation Panes > Tags).",
        "Expand the tag tree and locate each paragraph that should be a heading.",
        "Select the /P tag, press **Ctrl+E** to open Properties.",
        "In the **Tag** tab, change the Type from P to H1 (title) or H2 (sections). Press **OK**.",
        "Repeat for all heading candidates.",
    ],
    "PDFBP.NONSTD_NO_ALT": [
        "In the **Tags panel**, select the non-standard tag.",
        "Press **Ctrl+E** to open Properties.",
        "Enter **Alternative Text** for meaningful content.",
        "For decorative items, change Type to **Artifact**.",
    ],
    "PDFBP.TABLE_SCOPE": [
        "In the **Tags panel**, select a TH tag.",
        "Press **Ctrl+E** to open Properties > Tag tab.",
        "Set **Scope** to Row or Column.",
        "Press **OK**. Repeat for each TH cell.",
    ],
    "PDFBP.TABLE_HEADERS": [
        "In the **Tags panel**, select each TD in the header row.",
        "Press **Ctrl+E** to open Properties.",
        "Change **Type** from TD to TH.",
        "Then set Scope to Column. Press **OK**.",
    ],
    "PDFBP.FLAT_STRUCTURE": [
        "In the **Tags panel**, create new Sect tags under Document.",
        "Drag or cut/paste related heading and content tags into each section.",
    ],
    "PDFBP.FORMS_DETACHED": [
        "In the **Tags panel**, cut each Form tag (Ctrl+X).",
        "Paste it (Ctrl+V) after the P tag that contains its label text.",
        "Repeat for each field. Or use the **Order panel** to drag fields inline.",
    ],
    "PDFBP.UNDERSCORE_FILL": [
        "In the **Tags panel**, find each paragraph with underscore fills.",
        "If a form field overlaps, select the tag.",
        "Press **Ctrl+E**, change Type to **Artifact**. Press **OK**.",
    ],
    "PDFBP.NAV.TABORDER": [
        "Run **Accessibility Check** (Alt+A).",
        "In the results, right-click **Tab Order** and choose **Fix**.",
        "This sets all pages to structure-based tab order.",
    ],
    "PDFBP.TEXT.EXTRACTABLE": [
        "Open **All Tools > Scan & OCR > Recognize Text**.",
        "Choose the correct language for the document.",
        "Click **Recognize Text** to run OCR.",
        "After OCR completes, verify text accuracy and re-run accessibility check.",
    ],
    "PDFBP.ALT_LENGTH": [
        "In the **Tags panel**, select the Figure tag with the long alt text.",
        "Press **Ctrl+E** to open Properties.",
        "Shorten the **Alternative Text** to a concise summary.",
        "If detailed description is needed, add adjacent text or a long description link.",
    ],
    "PDFBP.ALT_QUALITY": [
        "In the **Tags panel**, select the Figure tag with the placeholder alt text.",
        "Press **Ctrl+E** to open Properties.",
        "Replace the filename or 'image1' text with a meaningful description.",
        "Press **OK**.",
    ],
    "PDFBP.LANG_VALID": [
        "Open **File > Properties** (Ctrl+D).",
        "In the **Advanced** tab, correct the language to a valid BCP 47 code.",
        "Press **OK**.",
    ],
    "PDFBP.LINK_TEXT": [
        "In the **Tags panel**, locate each Link tag with non-descriptive text.",
        "Press **Ctrl+E** to open Properties.",
        "Edit the visible link text to describe the destination.",
        "Press **OK**.",
    ],
    "PDFBP.EMPTY_TAGS": [
        "In the **Tags panel**, locate empty P or Span tags.",
        "Right-click and choose **Delete Tag** for each empty tag.",
        "Alternatively, change the Type to Artifact.",
    ],
    "PDFBP.FORMS.DUPLICATE_NAMES": [
        "Select each duplicate form field in the document.",
        "Open Properties (Ctrl+E), General tab.",
        "Change the **Name** to be unique (e.g. 'Phone_1', 'Phone_2').",
        "Press **OK**.",
    ],
    "PDFBP.FORMS.RADIO_GROUP": [
        "If the group should be a checkbox, delete the radio button and insert a checkbox field.",
        "If it genuinely needs options, add the missing option(s) using the form tools.",
    ],
    "PDFBP.LIST_STRUCT": [
        "In the **Tags panel**, expand the list structure.",
        "Verify the nesting follows L > LI > LBody.",
        "If LBody is missing, select the LI content, Ctrl+E > change Type to LBody > OK.",
        "If LI is missing, wrap content in a new LI tag.",
    ],
    "PDFBP.FIGURE_CAPTION": [
        "In the **Tags panel**, locate the orphaned Caption tag.",
        "Cut it (Ctrl+X) and paste it (Ctrl+V) immediately after the associated Figure tag.",
    ],
    "PDFBP.ART_TAGS": [
        "In the **Tags panel**, locate each Art tag.",
        "Press **Ctrl+E** to open Properties.",
        "Change the **Type** to the appropriate standard tag (Sect, Figure, Div).",
        "Press **OK**.",
    ],
    "PDFBP.SECT_NESTING": [
        "In the **Tags panel**, expand the deeply nested Sect hierarchy.",
        "Move content from deeply nested Sects to the parent level using cut/paste.",
        "Aim for no more than 3 levels of Sect nesting.",
    ],
    "PDFBP.FORMS.TOOLTIP_QUALITY": [
        "Select the form field with the generic tooltip.",
        "Open Properties (Ctrl+E), General tab.",
        "Replace the **Tooltip** text with the actual visual label.",
        "Press **OK**.",
    ],
}


def acrobat_fix_steps(rule_id: str) -> list[str]:
    """Return Adobe Acrobat Pro remediation steps for a rule."""
    return _ACROBAT_FIX_STEPS.get(
        rule_id,
        ["Follow the remediation guidance in the Findings section above."],
    )


# ---------------------------------------------------------------------------
# WCAG name lookup
# ---------------------------------------------------------------------------

def wcag_name(criterion: str) -> str:
    """Return the WCAG criterion name, or empty string if unknown."""
    entry = WCAG_LINKS.get(criterion)
    return entry[0] if entry else ""


def wcag_md(criterion: str) -> str:
    """Return a markdown link for a WCAG criterion."""
    if criterion in WCAG_LINKS:
        name, url = WCAG_LINKS[criterion]
        return f"[WCAG {criterion}: {name}]({url})"
    return f"WCAG {criterion}"


def wcag_html(criterion: str) -> str:
    """Return an HTML link for a WCAG criterion."""
    if criterion in WCAG_LINKS:
        name, url = WCAG_LINKS[criterion]
        return f'<a href="{url}">WCAG {criterion}: {name}</a>'
    return f"WCAG {criterion}"


# ---------------------------------------------------------------------------
# Set of all built-in checker rule IDs (for test coverage checks)
# ---------------------------------------------------------------------------

BUILTIN_RULE_IDS: frozenset[str] = frozenset(_FRIENDLY_NAMES.keys())
