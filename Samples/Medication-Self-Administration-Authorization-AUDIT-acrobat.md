# PDF Accessibility Audit Report (Adobe Acrobat Pro)

## Audit Information

- **Date**: 2026-04-02 20:25 UTC
- **File**: Medication Self-Administration Authorization.pdf
- **Remediation tool**: Adobe Acrobat Pro
- **veraPDF**: No (built-in checks only)

## Executive Summary

- **Score**: 49/100 (Grade: F)
- **Errors**: 2
- **Warnings**: 20
- **Tips**: 1
- **Total findings**: 23

- **Most common issue**: PDFBP.TABLE_SCOPE (8 occurrences)

## Findings by Page

### Document-level

- [ERROR] **PDFUA.TITLE** (WCAG 2.4.2): Document title is missing.
  - How to fix: File > Properties > Description tab > Title field. Enter the title and press OK.
- [WARNING] **PDFBP.NO_HEADINGS** (WCAG 2.4.6): Document has no headings (H1-H6). Screen reader users cannot navigate by heading.
  - How to fix: In the Tags panel, select each paragraph that should be a heading, open Properties (Ctrl+E), and change Type to H1, H2, etc.
- [TIP] **PDFBP.FLAT_STRUCTURE** (WCAG 1.3.1): Document has 79 direct children with no sectioning (Sect/Part/Art). Consider grouping related elements into sections.
  - How to fix: In the Tags panel, create new Sect tags under Document, then drag or cut/paste related heading and content tags into each section.
- [ERROR] **PDFBP.FORMS_DETACHED** (WCAG 1.3.2): 41 of 41 form fields are grouped at reading order positions 97-137, after all page content (positions 0-96). Screen readers encounter all text first, then all fields, making it impossible to associate fields with their labels.
  - How to fix: In the Tags panel, cut each Form tag (Ctrl+X) and paste it (Ctrl+V) after the P tag that contains its label text. Repeat for each field. Or use the Order panel to drag fields inline.
- [WARNING] **PDFBP.UNDERSCORE_FILL** (WCAG 1.3.1): 20 line(s) on page(s) 1, 3 contain underscore fill patterns (e.g., 'Name ___________'). Screen readers announce each underscore character individually. These should be marked as artifacts if a form field is overlaid.
  - How to fix: In the Tags panel, find each P tag containing underscore fills. Select the tag, open Properties (Ctrl+E), and change Type to Artifact. If the label text before the underscores is meaningful, split the tag: keep the label as a P and convert only the underscore portion to Artifact.

### Page 1

- [WARNING] **PDFBP.NONSTD_NO_ALT** (WCAG 1.1.1): Non-standard tag /InlineShape has no alt text or actual text.
  - How to fix: In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. For decorative items, change to Artifact.
- [WARNING] **PDFBP.NONSTD_NO_ALT** (WCAG 1.1.1): Non-standard tag /InlineShape has no alt text or actual text.
  - How to fix: In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. For decorative items, change to Artifact.
- [WARNING] **PDFBP.NONSTD_NO_ALT** (WCAG 1.1.1): Non-standard tag /InlineShape has no alt text or actual text.
  - How to fix: In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. For decorative items, change to Artifact.
- [WARNING] **PDFBP.NONSTD_NO_ALT** (WCAG 1.1.1): Non-standard tag /InlineShape has no alt text or actual text.
  - How to fix: In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. For decorative items, change to Artifact.
- [WARNING] **PDFBP.NAV.TABORDER** (WCAG 2.4.3): Page 1 tab order is not set to structure order (/Tabs /S).
  - How to fix: Run Accessibility Check (Alt+A). Under Page Content, right-click Tab Order and choose Fix. Adobe sets tab order to match the structure order on every page.

### Page 2

- [WARNING] **PDFBP.NONSTD_NO_ALT** (WCAG 1.1.1): Non-standard tag /InlineShape has no alt text or actual text.
  - How to fix: In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. For decorative items, change to Artifact.
- [WARNING] **PDFBP.TABLE_SCOPE** (WCAG 1.3.1): TH element is missing the Scope attribute.
  - How to fix: In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
- [WARNING] **PDFBP.TABLE_SCOPE** (WCAG 1.3.1): TH element is missing the Scope attribute.
  - How to fix: In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
- [WARNING] **PDFBP.TABLE_SCOPE** (WCAG 1.3.1): TH element is missing the Scope attribute.
  - How to fix: In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
- [WARNING] **PDFBP.TABLE_SCOPE** (WCAG 1.3.1): TH element is missing the Scope attribute.
  - How to fix: In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
- [WARNING] **PDFBP.TABLE_SCOPE** (WCAG 1.3.1): TH element is missing the Scope attribute.
  - How to fix: In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
- [WARNING] **PDFBP.TABLE_SCOPE** (WCAG 1.3.1): TH element is missing the Scope attribute.
  - How to fix: In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
- [WARNING] **PDFBP.TABLE_SCOPE** (WCAG 1.3.1): TH element is missing the Scope attribute.
  - How to fix: In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
- [WARNING] **PDFBP.TABLE_SCOPE** (WCAG 1.3.1): TH element is missing the Scope attribute.
  - How to fix: In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
- [WARNING] **PDFBP.NAV.TABORDER** (WCAG 2.4.3): Page 2 tab order is not set to structure order (/Tabs /S).
  - How to fix: Run Accessibility Check (Alt+A). Under Page Content, right-click Tab Order and choose Fix. Adobe sets tab order to match the structure order on every page.

### Page 3

- [WARNING] **PDFBP.NONSTD_NO_ALT** (WCAG 1.1.1): Non-standard tag /Textbox has no alt text or actual text.
  - How to fix: In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. For decorative items, change to Artifact.
- [WARNING] **PDFBP.NONSTD_NO_ALT** (WCAG 1.1.1): Non-standard tag /InlineShape has no alt text or actual text.
  - How to fix: In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. For decorative items, change to Artifact.
- [WARNING] **PDFBP.NAV.TABORDER** (WCAG 2.4.3): Page 3 tab order is not set to structure order (/Tabs /S).
  - How to fix: Run Accessibility Check (Alt+A). Under Page Content, right-click Tab Order and choose Fix. Adobe sets tab order to match the structure order on every page.

## Findings by Rule

| Rule ID | Count | Severity | WCAG |
|---------|-------|----------|------|
| PDFBP.TABLE_SCOPE | 8 | warning | 1.3.1 |
| PDFBP.NONSTD_NO_ALT | 7 | warning | 1.1.1 |
| PDFBP.NAV.TABORDER | 3 | warning | 2.4.3 |
| PDFUA.TITLE | 1 | error | 2.4.2 |
| PDFBP.NO_HEADINGS | 1 | warning | 2.4.6 |
| PDFBP.FLAT_STRUCTURE | 1 | tip | 1.3.1 |
| PDFBP.FORMS_DETACHED | 1 | error | 1.3.2 |
| PDFBP.UNDERSCORE_FILL | 1 | warning | 1.3.1 |

## Remediation Priority

### Immediate (Errors)

1. **PDFUA.TITLE**: Document title is missing.
   - File > Properties > Description tab > Title field. Enter the title and press OK.
1. **PDFBP.FORMS_DETACHED**: 41 of 41 form fields are grouped at reading order positions 97-137, after all page content (positions 0-96). Screen readers encounter all text first, then all fields, making it impossible to associate fields with their labels.
   - In the Tags panel, cut each Form tag (Ctrl+X) and paste it (Ctrl+V) after the P tag that contains its label text. Repeat for each field. Or use the Order panel to drag fields inline.

### Soon (Warnings)

1. **PDFBP.NO_HEADINGS**: Document has no headings (H1-H6). Screen reader users cannot navigate by heading.
   - In the Tags panel, select each paragraph that should be a heading, open Properties (Ctrl+E), and change Type to H1, H2, etc.
1. **PDFBP.NONSTD_NO_ALT**: Non-standard tag /InlineShape has no alt text or actual text.
   - In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. For decorative items, change to Artifact.
1. **PDFBP.NONSTD_NO_ALT**: Non-standard tag /InlineShape has no alt text or actual text.
   - In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. For decorative items, change to Artifact.
1. **PDFBP.NONSTD_NO_ALT**: Non-standard tag /InlineShape has no alt text or actual text.
   - In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. For decorative items, change to Artifact.
1. **PDFBP.NONSTD_NO_ALT**: Non-standard tag /InlineShape has no alt text or actual text.
   - In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. For decorative items, change to Artifact.
1. **PDFBP.NONSTD_NO_ALT**: Non-standard tag /InlineShape has no alt text or actual text.
   - In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. For decorative items, change to Artifact.
1. **PDFBP.NONSTD_NO_ALT**: Non-standard tag /Textbox has no alt text or actual text.
   - In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. For decorative items, change to Artifact.
1. **PDFBP.NONSTD_NO_ALT**: Non-standard tag /InlineShape has no alt text or actual text.
   - In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. For decorative items, change to Artifact.
1. **PDFBP.TABLE_SCOPE**: TH element is missing the Scope attribute.
   - In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
1. **PDFBP.TABLE_SCOPE**: TH element is missing the Scope attribute.
   - In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
1. **PDFBP.TABLE_SCOPE**: TH element is missing the Scope attribute.
   - In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
1. **PDFBP.TABLE_SCOPE**: TH element is missing the Scope attribute.
   - In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
1. **PDFBP.TABLE_SCOPE**: TH element is missing the Scope attribute.
   - In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
1. **PDFBP.TABLE_SCOPE**: TH element is missing the Scope attribute.
   - In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
1. **PDFBP.TABLE_SCOPE**: TH element is missing the Scope attribute.
   - In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
1. **PDFBP.TABLE_SCOPE**: TH element is missing the Scope attribute.
   - In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.
1. **PDFBP.UNDERSCORE_FILL**: 20 line(s) on page(s) 1, 3 contain underscore fill patterns (e.g., 'Name ___________'). Screen readers announce each underscore character individually. These should be marked as artifacts if a form field is overlaid.
   - In the Tags panel, find each P tag containing underscore fills. Select the tag, open Properties (Ctrl+E), and change Type to Artifact. If the label text before the underscores is meaningful, split the tag: keep the label as a P and convert only the underscore portion to Artifact.
1. **PDFBP.NAV.TABORDER**: Page 1 tab order is not set to structure order (/Tabs /S).
   - Run Accessibility Check (Alt+A). Under Page Content, right-click Tab Order and choose Fix. Adobe sets tab order to match the structure order on every page.
1. **PDFBP.NAV.TABORDER**: Page 2 tab order is not set to structure order (/Tabs /S).
   - Run Accessibility Check (Alt+A). Under Page Content, right-click Tab Order and choose Fix. Adobe sets tab order to match the structure order on every page.
1. **PDFBP.NAV.TABORDER**: Page 3 tab order is not set to structure order (/Tabs /S).
   - Run Accessibility Check (Alt+A). Under Page Content, right-click Tab Order and choose Fix. Adobe sets tab order to match the structure order on every page.

### When Possible (Tips)

1. **PDFBP.FLAT_STRUCTURE**: Document has 79 direct children with no sectioning (Sect/Part/Art). Consider grouping related elements into sections.
   - In the Tags panel, create new Sect tags under Document, then drag or cut/paste related heading and content tags into each section.
   - Adobe Acrobat Pro: In the Tags panel, create new Sect tags under Document, then drag or cut/paste related heading and content tags into each section.

## Accessibility Scorecard

| Metric | Value |
|--------|-------|
| Score | 49/100 |
| Grade | F |
| Errors | 2 |
| Warnings | 20 |
| Tips | 1 |
