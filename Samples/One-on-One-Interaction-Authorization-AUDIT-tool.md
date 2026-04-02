# PDF Accessibility Audit Report: One-on-One Interaction Authorization

## Audit Information

- **Date**: April 02, 2026
- **Tool**: PDF Accessibility Tool v0.1.0 (built-in checks only, veraPDF not installed)
- **File**: One-on-One Interaction Authorization.pdf
- **Source application**: Microsoft Word
- **Author**: Galabi, Lora - (galabi)
- **Created**: 2026-02-09 16:59
- **Pages**: 1
- **PDF version**: 1.7

## Executive Summary

- **Score**: 80/100 (Grade: B)
- **Errors**: 2
- **Warnings**: 5
- **Deep analysis issues**: 5
- **Total actionable issues**: 7

This is a document created in Microsoft Word (1 pages). The document is tagged with 41 structure elements. It contains 9 form fields. Key issues include: missing document title, no heading structure, 3 non-standard elements without alt text, form fields detached from their labels in reading order.

## Built-in Checker Findings

| Severity | Rule ID | WCAG | Page | Description |
|----------|---------|------|------|-------------|
| Error | PDFUA.TITLE | 2.4.2 | doc | Document title is missing. |
| Warning | PDFBP.NO_HEADINGS | 2.4.6 | doc | Document has no headings (H1-H6). Screen reader users cannot navigate by heading. |
| Warning | PDFBP.NONSTD_NO_ALT | 1.1.1 | 1 | Non-standard tag /InlineShape has no alt text or actual text. (x3) |
| Error | PDFBP.FORMS_DETACHED | 1.3.2 | doc | 9 of 9 form fields are grouped at reading order positions 18-26, after all page content (positions 0-17). Screen readers encounter all text first, then all fields, making it impossible to associate fields with their labels. |
| Warning | PDFBP.UNDERSCORE_FILL | 1.3.1 | doc | 8 line(s) on page(s) 1 contain underscore fill patterns (e.g., 'Name ___________'). Screen readers announce each underscore character individually. These should be marked as artifacts if a form field is overlaid. |

## Deep Analysis Findings

The following issues were identified through structure tree analysis, reading order mapping, and content flow analysis.

Each issue includes two remediation paths so you can use whichever tool you prefer:

- **PDF Accessibility Tool**: Our tool, with fully keyboard-operable instructions
- **Adobe Acrobat Pro**: The industry-standard commercial alternative

---

### Issue 1: Missing Document Title

**Severity**: CRITICAL
**WCAG**: 2.4.2 (Page Titled)
**Impact**: Screen readers announce the filename instead of a meaningful title when opening the document.

**What the tool detects:**

The built-in checker flags PDFUA.TITLE as an error. The Document Properties panel shows the Title field as empty. The DisplayDocTitle viewer preference is already set to true, which means once a title is added it will be displayed correctly.

#### How to fix: PDF Accessibility Tool

1. Open **Document Properties** (Alt+Enter).
2. **Tab** to the Title field.
3. Type the document title.
4. Press **Enter** to apply. The tool writes the title to both /Info /Title and XMP dc:title metadata simultaneously.
5. The checker reruns automatically and the PDFUA.TITLE error clears from the Issues panel.

#### How to fix: Adobe Acrobat Pro

1. Open **File > Properties** (Ctrl+D).
2. In the **Description** tab, Tab to the Title field.
3. Type the title and press **OK**.
4. Open File > Properties again, go to **Initial View** tab, verify "Show" is set to "Document Title".

---

### Issue 2: No Headings

**Severity**: Important
**WCAG**: 2.4.6 (Headings and Labels)
**Impact**: Screen reader users cannot navigate between form sections. The document may have clear visual sections but they are all tagged as paragraphs instead of heading tags.

**What the tool detects:**

The structure tree contains 24 /P tags and zero /H1 through /H6 tags. The Tag Tree panel displays this flat list of paragraphs, making the problem immediately visible. The Screen Reader Preview shows "24 consecutive paragraphs with no headings" and the Headings Only mode returns "0 headings found."

#### How to fix: PDF Accessibility Tool

1. **Tag Tree panel** (Alt+3): Use the arrow keys to navigate to each bold section header.
2. Press **F2** to open the Change Type editor. Select /H1 for the document title, /H2 for sections.
3. Press **Enter** to confirm. Repeat for each heading.
4. Alternatively, use **Auto-Tagger** (Alt+T, A): Review the heading candidate list, press **Space** to accept/reject each, then **Enter** on Apply.
5. After applying, the **Screen Reader Preview** refreshes to show the new heading structure.

#### How to fix: Adobe Acrobat Pro

1. Open the **Tags panel** (View > Show/Hide > Navigation Panes > Tags).
2. Expand the tag tree and locate each paragraph that should be a heading.
3. Select the /P tag, press **Ctrl+E** to open Properties.
4. In the **Tag** tab, change the Type from P to H1 (title) or H2 (sections). Press **OK**.
5. Repeat for all heading candidates.

---

### Issue 3: Non-Standard Tags Without Alt Text (x3)

**Severity**: Important
**WCAG**: 1.1.1 (Non-text Content)
**Impact**: Screen readers encounter unnamed non-text elements. Users hear the tag type name (e.g., 'InlineShape') with no context about what the element represents.

**What the tool detects:**

The Tag Tree panel shows 3 non-standard tag(s) without /Alt attributes. The Alt Text panel lists these as "3 non-standard elements missing alt text" and displays thumbnails of the rendered page regions.

**Detailed inventory:**

| Index | Page | Tag | Maps To | Recommended Action |
|-------|------|-----|---------|-------------------|
| 0 | 1 | /InlineShape | Sect | Mark as decorative artifact |
| 1 | 1 | /InlineShape | Sect | Mark as decorative artifact |
| 2 | 1 | /InlineShape | Sect | Mark as decorative artifact |

#### How to fix: PDF Accessibility Tool

1. **Alt Text Panel** (Alt+4): The non-standard elements are listed.
2. For decorative items: Press **Space** on the "Mark as decorative" checkbox.
3. Press **Alt+N** to advance to the next element and repeat.
4. For meaningful images: Type appropriate alt text in the field and press Enter.
5. Alternatively, in the **Tag Tree**: Navigate to each element, press **Delete** and choose "Mark as Artifact" for decorative items.

#### How to fix: Adobe Acrobat Pro

1. In the **Tags panel**, select the non-standard tag.
2. Press **Ctrl+E** to open Properties.
3. Enter **Alternative Text** for meaningful content.
4. For decorative items, change Type to **Artifact**.

---

### Issue 4: Form Fields Detached From Labels

**Severity**: CRITICAL
**WCAG**: 1.3.2 (Meaningful Sequence)
**Impact**: Screen readers encounter all text first, then all fields, making it impossible to associate fields with their labels.

**What the tool detects:**

The reading order analysis shows form fields grouped in a contiguous block at the end of the structure tree, separated from their visual labels. The Auto-Sort Reading Order tool can detect and fix this by interleaving fields with their labels.

#### How to fix: PDF Accessibility Tool

1. Use **Auto-Sort Reading Order** (Alt+T, R) to interleave form fields with their labels.
2. Preview the proposed order in the dialog.
3. Press **Enter** to apply. Each field is reparented to follow its label.
4. Ctrl+Z undoes all changes if needed.

#### How to fix: Adobe Acrobat Pro

1. In the **Tags panel**, cut each Form tag (Ctrl+X).
2. Paste it (Ctrl+V) after the P tag that contains its label text.
3. Repeat for each field. Or use the **Order panel** to drag fields inline.

---

### Issue 5: Underscore Fill Patterns

**Severity**: Important
**WCAG**: 1.3.1 (Info and Relationships)
**Impact**: Screen readers announce each underscore character individually, creating a poor experience. These should be marked as artifacts if a form field is overlaid.

#### How to fix: PDF Accessibility Tool

1. In the **Tag Tree**, navigate to each paragraph with underscore fills.
2. If a form field overlaps, press **Delete** and choose 'Mark as Artifact'.
3. The **'Clean All Underscore Fills'** batch action (Alt+T, U) processes all flagged elements at once.

#### How to fix: Adobe Acrobat Pro

1. In the **Tags panel**, find each paragraph with underscore fills.
2. If a form field overlaps, select the tag.
3. Press **Ctrl+E**, change Type to **Artifact**. Press **OK**.

---

## Form Fields Assessment

The document contains **9 form fields**.

**Positive findings:**

- 9 of 9 fields (100%) have tooltips

**Field inventory:**

| Name | Type | Tooltip | Required |
|------|------|---------|----------|
| Program Name | Text | Program Name |  |
| First Day of Program | Text | First Day of Program |  |
| Date | Text | Date |  |
| Last Day of Program | Text | Last Day of Program |  |
| Minor First Name | Text | Minor First Name |  |
| Minor Last Name | Text | Minor Last Name |  |
| Minor Date of Birth Month Day Year | Text | Minor Date of Birth Month Day Year |  |
| Name of Parent Legal Guardian Printed | Text | Name of Parent Legal Guardian Printed |  |
| Signature of Parent Legal Guardian_es_:signer:signature | Text | Signature of Parent Legal Guardian |  |

**Improvement opportunities:**

| Finding | Recommendation |
|---------|---------------|
| Consider marking key fields as required so screen readers announce their mandatory status | Consider marking key fields as required so screen readers announce their mandatory status |
| Reorder form fields to interleave with their labels | Reorder form fields to interleave with their labels (currently grouped at end of reading order) |

## Reading Order Assessment

The structure tree defines reading order for 41 elements across 1 page(s).

**Page 1** (28 elements): 24 P, 3 InlineShape, 1 Figure

**Reading order issues:**

- Form fields are grouped at the end of the reading order, separated from their labels. Screen readers will read all text first, then encounter all form fields without context.

**Recommendations:**

- Use Auto-Sort Reading Order (Alt+T, R) to interleave form fields with their labels.
- Add headings (H1-H6) to provide navigational landmarks.
- Use the Reading Order overlay (Ctrl+Shift+O) to visually verify element sequence.

## Screen Reader Preview (Simulated)

This section approximates what a screen reader (NVDA, JAWS, VoiceOver) would announce when reading this document from top to bottom. Warnings are inserted inline where a screen reader user would encounter the problem.

```
Image: University of Arizona "A" and Youth Protection logo   (p.1)
Image  (p.1)
Image  (p.1)
Image  (p.1)
Text field: Program Name
Text field: First Day of Program
Text field: Last Day of Program
Text field: Minor First Name
Text field: Minor Last Name
Text field: Minor Date of Birth Month Day Year
Text field: Name of Parent Legal Guardian Printed
Text field: Signature of Parent Legal Guardian
Text field: Date
WARNING: Document title is missing.
WARNING: Document has no headings (H1-H6). Screen reader users cannot navigate by heading.
WARNING: 9 of 9 form fields are grouped at reading order positions 18-26, after all page content (positions 0-17). Screen readers encounter all text first, then all fields, making it impossible to associate fields with their labels.
```

## Remediation Priority

### Immediate (Errors -- must fix for PDF/UA conformance)

| Priority | Issue | WCAG | PDF Accessibility Tool | Adobe Acrobat Pro |
|----------|-------|------|----------------------|-------------------|
| 1 | Missing Document Title | 2.4.2 | Open Document Properties (Alt+Enter), Tab to the Title field, type the title, then press Enter to apply.. | File > Properties > Description tab > Title field. |
| 2 | Form Fields Detached From Labels | 1.3.2 | Use Auto-Sort Reading Order (Alt+T, R) to interleave form fields with their labels. | In the Tags panel, cut each Form tag (Ctrl+X) and paste it (Ctrl+V) after the P tag that contains its label text. |

### Soon (Warnings -- significant accessibility improvement)

| Priority | Issue | WCAG | PDF Accessibility Tool | Adobe Acrobat Pro |
|----------|-------|------|----------------------|-------------------|
| 1 | No Headings | 2.4.6 | In the Tag Tree, arrow to each section title, press F2, and change the type from P to H1, H2, etc. | In the Tags panel, select each paragraph that should be a heading, open Properties (Ctrl+E), and change Type to H1, H2, etc.. |
| 2 | Non-Standard Tags Without Alt Text | 1.1.1 | In the Tag Tree, arrow to the element, press F2 to add alt text. | In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. |
| 3 | Underscore Fill Patterns | 1.3.1 | In the Tag Tree, navigate to each paragraph with underscore fills. | In the Tags panel, find each P tag containing underscore fills. |

## Accessibility Scorecard

| Metric | Current | After Remediation (Projected) |
|--------|---------|-------------------------------|
| Score | 80/100 | 100/100 |
| Grade | B | A |
| Errors | 2 | 0 |
| Warnings | 5 | 0 |
| Headings | 0 | 5+ (estimated after fix) |
| Form fields with tooltips | 9/9 | 9/9 |
