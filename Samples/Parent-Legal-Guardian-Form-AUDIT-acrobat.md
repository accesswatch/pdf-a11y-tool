# PDF Accessibility Audit Report: Parent Legal Guardian Form

## Audit Information

- **Date**: April 02, 2026
- **Tool**: PDF Accessibility Tool v0.1.0 (built-in checks only, veraPDF not installed)
- **File**: Parent Legal Guardian Form.pdf
- **Source application**: Microsoft Word
- **Author**: Galabi, Lora - (galabi)
- **Created**: 2026-02-16 21:00
- **Pages**: 5
- **PDF version**: 1.6

## Executive Summary

- **Score**: 63/100 (Grade: D)
- **Errors**: 4
- **Warnings**: 8
- **Deep analysis issues**: 6
- **Total actionable issues**: 13

This is a document created in Microsoft Word (5 pages). The document is tagged with 184 structure elements. It contains 27 form fields. Key issues include: missing document title, no heading structure, form fields detached from their labels in reading order, 1 form field(s) missing tooltips.

## Built-in Checker Findings

| Severity | Rule ID | WCAG | Page | Description |
|----------|---------|------|------|-------------|
| Error | PDFUA.TITLE | 2.4.2 | doc | Document title is missing. |
| Error | PDFUA.LANG | 3.1.1 | doc | Document language is not set. |
| Warning | PDFBP.NO_HEADINGS | 2.4.6 | doc | Document has no headings (H1-H6). Screen reader users cannot navigate by heading. |
| Tip | PDFBP.FLAT_STRUCTURE | 1.3.1 | doc | Document has 27 direct children with no sectioning (Sect/Part/Art). Consider grouping related elements into sections. |
| Error | PDFUA.FORMS | 4.1.2 | doc | Form field is missing a tooltip (TU entry). |
| Error | PDFBP.FORMS_DETACHED | 1.3.2 | doc | 26 of 26 form fields are grouped at reading order positions 139-164, after all page content (positions 0-138). Screen readers encounter all text first, then all fields, making it impossible to associate fields with their labels. |
| Warning | PDFBP.UNDERSCORE_FILL | 1.3.1 | doc | 21 line(s) on page(s) 1, 5 contain underscore fill patterns (e.g., 'Name ___________'). Screen readers announce each underscore character individually. These should be marked as artifacts if a form field is overlaid. |
| Warning | PDFBP.NAV.TABORDER | 2.4.3 | 1, 2, 3, 4, 5 | Page 1 tab order is not set to structure order (/Tabs /S). (x5) |
| Warning | PDFBP.DISPLAY_TITLE | 2.4.2 | doc | DisplayDocTitle is not set (no ViewerPreferences). |

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

The built-in checker flags PDFUA.TITLE as an error. The Document Properties panel shows the Title field as empty.

#### How to fix: Adobe Acrobat Pro

1. Open **File > Properties** (Ctrl+D).
2. In the **Description** tab, Tab to the Title field.
3. Type the title and press **OK**.
4. Open File > Properties again, go to **Initial View** tab, verify "Show" is set to "Document Title".

#### How to fix: PDF Accessibility Tool

1. Open **Document Properties** (Alt+Enter).
2. **Tab** to the Title field.
3. Type the document title.
4. Press **Enter** to apply. The tool writes the title to both /Info /Title and XMP dc:title metadata simultaneously.
5. The checker reruns automatically and the PDFUA.TITLE error clears from the Issues panel.

---

### Issue 2: No Headings

**Severity**: Important
**WCAG**: 2.4.6 (Headings and Labels)
**Impact**: Screen reader users cannot navigate between form sections. The document may have clear visual sections but they are all tagged as paragraphs instead of heading tags.

**What the tool detects:**

The structure tree contains 110 /P tags and zero /H1 through /H6 tags. The Tag Tree panel displays this flat list of paragraphs, making the problem immediately visible. The Screen Reader Preview shows "110 consecutive paragraphs with no headings" and the Headings Only mode returns "0 headings found."

#### How to fix: Adobe Acrobat Pro

1. Open the **Tags panel** (View > Show/Hide > Navigation Panes > Tags).
2. Expand the tag tree and locate each paragraph that should be a heading.
3. Select the /P tag, press **Ctrl+E** to open Properties.
4. In the **Tag** tab, change the Type from P to H1 (title) or H2 (sections). Press **OK**.
5. Repeat for all heading candidates.

#### How to fix: PDF Accessibility Tool

1. **Tag Tree panel** (Alt+3): Use the arrow keys to navigate to each bold section header.
2. Press **F2** to open the Change Type editor. Select /H1 for the document title, /H2 for sections.
3. Press **Enter** to confirm. Repeat for each heading.
4. Alternatively, use **Auto-Tagger** (Alt+T, A): Review the heading candidate list, press **Space** to accept/reject each, then **Enter** on Apply.
5. After applying, the **Screen Reader Preview** refreshes to show the new heading structure.

---

### Issue 3: Flat Document Structure

**Severity**: Recommended
**WCAG**: 1.3.1 (Info and Relationships)
**Impact**: A flat tag tree with many direct children and no sections makes it impossible for screen reader users to navigate by section or understand the document's organization.

**What the tool detects:**

The document root has 0 direct children with no /Sect, /Part, or /Art grouping elements. The Tag Tree shows a flat list of elements that should be organized into logical sections.

#### How to fix: Adobe Acrobat Pro

1. In the **Tags panel**, create new Sect tags under Document.
2. Drag or cut/paste related heading and content tags into each section.

#### How to fix: PDF Accessibility Tool

1. In the **Tag Tree**, select the Document root.
2. Press **Insert** to add a /Sect child.
3. Select related heading and content elements, press **Ctrl+X** to cut.
4. Arrow to the Sect element, press **Ctrl+V** to paste.
5. Repeat for each logical section of the document.

---

### Issue 4: Form Fields Missing Tooltips

**Severity**: CRITICAL
**WCAG**: 4.1.2 (Name, Role, Value)
**Impact**: Form fields without tooltips are announced as unlabeled to screen reader users, who cannot determine the field's purpose.

#### How to fix: Adobe Acrobat Pro

1. Select the form field in the document.
2. Open Properties (**Ctrl+E**), General tab.
3. Enter a descriptive **Tooltip** matching the visual label.
4. Press **OK**. Repeat for each field.

#### How to fix: PDF Accessibility Tool

1. In the **Field Properties panel**, Tab to the Tooltip field.
2. Enter a descriptive label that matches the visual label.
3. Press **Enter** to apply. Repeat for each field.

---

### Issue 5: Form Fields Detached From Labels

**Severity**: CRITICAL
**WCAG**: 1.3.2 (Meaningful Sequence)
**Impact**: Screen readers encounter all text first, then all fields, making it impossible to associate fields with their labels.

**What the tool detects:**

The reading order analysis shows form fields grouped in a contiguous block at the end of the structure tree, separated from their visual labels. The Auto-Sort Reading Order tool can detect and fix this by interleaving fields with their labels.

#### How to fix: Adobe Acrobat Pro

1. In the **Tags panel**, cut each Form tag (Ctrl+X).
2. Paste it (Ctrl+V) after the P tag that contains its label text.
3. Repeat for each field. Or use the **Order panel** to drag fields inline.

#### How to fix: PDF Accessibility Tool

1. Use **Auto-Sort Reading Order** (Alt+T, R) to interleave form fields with their labels.
2. Preview the proposed order in the dialog.
3. Press **Enter** to apply. Each field is reparented to follow its label.
4. Ctrl+Z undoes all changes if needed.

---

### Issue 6: Underscore Fill Patterns

**Severity**: Important
**WCAG**: 1.3.1 (Info and Relationships)
**Impact**: Screen readers announce each underscore character individually, creating a poor experience. These should be marked as artifacts if a form field is overlaid.

#### How to fix: Adobe Acrobat Pro

1. In the **Tags panel**, find each paragraph with underscore fills.
2. If a form field overlaps, select the tag.
3. Press **Ctrl+E**, change Type to **Artifact**. Press **OK**.

#### How to fix: PDF Accessibility Tool

1. In the **Tag Tree**, navigate to each paragraph with underscore fills.
2. If a form field overlaps, press **Delete** and choose 'Mark as Artifact'.
3. The **'Clean All Underscore Fills'** batch action (Alt+T, U) processes all flagged elements at once.

---

## Form Fields Assessment

The document contains **27 form fields**.

**Positive findings:**

- 26 of 27 fields (96%) have tooltips

**Field inventory:**

| Name | Type | Tooltip | Required |
|------|------|---------|----------|
| Program Name | Text | Program Name |  |
| First Day of Program | Text | First Day of Program |  |
| Last Day of Program | Text | Last Day of Program |  |
| Minor First Name | Text | Minor First Name |  |
| Minor Last Name | Text | Minor Last Name |  |
| Minor Date of Birth Month Day Year | Text | Minor Date of Birth Month Day Year |  |
| Minor Home Address | Text | Minor Home Address |  |
| Parent Legal Guardian First Name | Text | Parent Legal Guardian First Name |  |
| Parent Legal Guardian Last Name | Text | Parent Legal Guardian Last Name |  |
| Parent Legal Guardian Phone Number | Text | Parent Legal Guardian Phone Number |  |
| Parent Legal Guardian Email | Text | Parent Legal Guardian Email |  |
| Emergency Contact First Name | Text | Emergency Contact First Name |  |
| Emergency Contact Last Name | Text | Emergency Contact Last Name |  |
| Emergency Contact Relationship to Minor | Text | Emergency Contact Relationship to Minor |  |
| Emergency Contact Phone Number | Text | Emergency Contact Phone Number |  |
| Additional Individual Authorized to Pick Up Minor First Name | Text | Additional Individual Authorized to Pick Up Minor First Name |  |
| Additional Individual Authorized to Pick Up Minor Last Name | Text | Additional Individual Authorized to Pick Up Minor Last Name |  |
| Additional Individual Authorized to Pick Up Minor Relationship to Minor | Text | Additional Individual Authorized to Pick Up Minor Relationship to Minor |  |
| Additional Individual Authorized to Pick Up Minor Phone Number | Text | Additional Individual Authorized to Pick Up Minor Phone Number |  |
| Second Additional Individual Authorized to Pick Up Minor First Name | Text | Second Additional Individual Authorized to Pick Up Minor First Name |  |
| Second Additional Individual Authorized to Pick Up Minor Last Name | Text | Second Additional Individual Authorized to Pick Up Minor Last Name |  |
| Second Additional Individual Authorized to Pick Up Minor Relationship to Minor | Text | Second Additional Individual Authorized to Pick Up Minor Relationship to Minor |  |
| Second Additional Individual Authorized to Pick Up Minor Phone Number | Text | Second Additional Individual Authorized to Pick Up Minor Phone Number |  |
| Consent and release | Button | (missing) |  |
| Name of Parent Legal Guardian Printed | Text | Name of Parent Legal Guardian Printed |  |
| Date | Text | Date |  |
| Signature of Parent Legal Guardian_es_:signer:signature | Text | Signature of Parent Legal Guardian |  |

**Improvement opportunities:**

| Finding | Recommendation |
|---------|---------------|
| Add tooltips to 1 field | Add tooltips to 1 field(s) missing them (WCAG 4.1.2) |
| Consider marking key fields as required so screen readers announce their mandatory status | Consider marking key fields as required so screen readers announce their mandatory status |
| Reorder form fields to interleave with their labels | Reorder form fields to interleave with their labels (currently grouped at end of reading order) |

## Reading Order Assessment

The structure tree defines reading order for 184 elements across 5 page(s).

**Page 1** (38 elements): 36 P, 1 Sect, 1 Figure

**Page 2** (33 elements): 25 P, 4 Lbl, 4 LBody

**Page 3** (35 elements): 15 P, 10 Lbl, 10 LBody

**Page 4** (17 elements): 17 P

**Page 5** (16 elements): 16 P

**Reading order issues:**

- Form fields are grouped at the end of the reading order, separated from their labels. Screen readers will read all text first, then encounter all form fields without context.
- The document has a flat structure with no sectioning. Screen reader users cannot jump between sections.

**Recommendations:**

- Use Auto-Sort Reading Order (Alt+T, R) to interleave form fields with their labels.
- Add /Sect grouping elements to organize content into logical sections.
- Add headings (H1-H6) to provide navigational landmarks.
- Use the Reading Order overlay (Ctrl+Shift+O) to visually verify element sequence.

## Screen Reader Preview (Simulated)

This section approximates what a screen reader (NVDA, JAWS, VoiceOver) would announce when reading this document from top to bottom. Warnings are inserted inline where a screen reader user would encounter the problem.

```
List with 4 items
Lbl  (p.2)
Lbl  (p.2)
Lbl  (p.2)
Lbl  (p.2)
List with 10 items
Lbl  (p.3)
Lbl  (p.3)
Lbl  (p.3)
Lbl  (p.3)
Lbl  (p.3)
Lbl  (p.3)
Lbl  (p.3)
Lbl  (p.3)
Lbl  (p.3)
Lbl  (p.3)
Image: University of Arizona "A" and Youth Protection logo  (p.1)
Text field: Program Name
Text field: First Day of Program
Text field: Last Day of Program
Text field: Minor First Name
Text field: Minor Last Name
Text field: Minor Date of Birth Month Day Year
Text field: Minor Home Address
Text field: Parent Legal Guardian First Name
Text field: Parent Legal Guardian Last Name
Text field: Parent Legal Guardian Phone Number
Text field: Parent Legal Guardian Email
Text field: Emergency Contact First Name
Text field: Emergency Contact Last Name
Text field: Emergency Contact Relationship to Minor
Text field: Emergency Contact Phone Number
Text field: Additional Individual Authorized to Pick Up Minor First Name
Text field: Additional Individual Authorized to Pick Up Minor Last Name
Text field: Additional Individual Authorized to Pick Up Minor Relationship to Minor
Text field: Additional Individual Authorized to Pick Up Minor Phone Number
Text field: Second Additional Individual Authorized to Pick Up Minor First Name
Text field: Second Additional Individual Authorized to Pick Up Minor Last Name
Text field: Second Additional Individual Authorized to Pick Up Minor Relationship to Minor
Text field: Second Additional Individual Authorized to Pick Up Minor Phone Number
Text field: Name of Parent Legal Guardian Printed
Text field: Date
Text field: Signature of Parent Legal Guardian
WARNING: Document title is missing.
WARNING: Document language is not set.
WARNING: Document has no headings (H1-H6). Screen reader users cannot navigate by heading.
WARNING: Form field is missing a tooltip (TU entry).
WARNING: 26 of 26 form fields are grouped at reading order positions 139-164, after all page content (positions 0-138). Screen readers encounter all text first, then all fields, making it impossible to associate fields with their labels.
```

## Remediation Priority

### Immediate (Errors -- must fix for PDF/UA conformance)

| Priority | Issue | WCAG | PDF Accessibility Tool | Adobe Acrobat Pro |
|----------|-------|------|----------------------|-------------------|
| 1 | Missing Document Title | 2.4.2 | Open Document Properties (Alt+Enter), Tab to the Title field, type the title, then press Enter to apply.. | File > Properties > Description tab > Title field. |
| 2 | PDFUA.LANG | 3.1.1 | Open Document Properties (Alt+Enter), Tab to the Language field, type the language code (e.g. | File > Properties > Advanced tab > Language dropdown. |
| 3 | Form Fields Missing Tooltips | 4.1.2 | In the Field Properties panel, Tab to the Tooltip field and enter a descriptive label. | Select the form field, open Properties (Ctrl+E), General tab, and enter a Tooltip.. |
| 4 | Form Fields Detached From Labels | 1.3.2 | Use Auto-Sort Reading Order (Alt+T, R) to interleave form fields with their labels. | In the Tags panel, cut each Form tag (Ctrl+X) and paste it (Ctrl+V) after the P tag that contains its label text. |

### Soon (Warnings -- significant accessibility improvement)

| Priority | Issue | WCAG | PDF Accessibility Tool | Adobe Acrobat Pro |
|----------|-------|------|----------------------|-------------------|
| 1 | No Headings | 2.4.6 | In the Tag Tree, arrow to each section title, press F2, and change the type from P to H1, H2, etc. | In the Tags panel, select each paragraph that should be a heading, open Properties (Ctrl+E), and change Type to H1, H2, etc.. |
| 2 | Underscore Fill Patterns | 1.3.1 | In the Tag Tree, navigate to each paragraph with underscore fills. | In the Tags panel, find each P tag containing underscore fills. |
| 3 | Tab Order Not Set to Structure | 2.4.3 | In the Accessibility Checker results, right-click the Tab Order finding and choose Fix. | Run Accessibility Check (Alt+A). |
| 4 | Display Document Title Not Set | 2.4.2 | Open Document Properties (Alt+Enter), Tab to the 'Display document title in title bar' checkbox, and press Space to enable it.. | File > Properties > Initial View tab. |

### When Possible (Tips)

| Priority | Issue | WCAG | PDF Accessibility Tool | Adobe Acrobat Pro |
|----------|-------|------|----------------------|-------------------|
| 1 | Flat Document Structure | 1.3.1 | In the Tag Tree, select the Document root, press Insert to add a Sect child, then select related elements and press Ctrl+X to cut, arrow to the Sect, and Ctrl+V to paste.. | In the Tags panel, create new Sect tags under Document, then drag or cut/paste related heading and content tags into each section.. |

## Accessibility Scorecard

| Metric | Current | After Remediation (Projected) |
|--------|---------|-------------------------------|
| Score | 63/100 | 99/100 |
| Grade | D | A |
| Errors | 4 | 0 |
| Warnings | 8 | 0 |
| Headings | 0 | 5+ (estimated after fix) |
| Form fields with tooltips | 26/27 | 27/27 |
