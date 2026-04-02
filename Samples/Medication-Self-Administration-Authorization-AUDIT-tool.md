# PDF Accessibility Audit Report: Medication Self-Administration Authorization

## Audit Information

- **Date**: April 02, 2026
- **Tool**: PDF Accessibility Tool v0.1.0 (built-in checks only, veraPDF not installed)
- **File**: Medication Self-Administration Authorization.pdf
- **Source application**: Microsoft Word
- **Author**: Galabi, Lora - (galabi)
- **Created**: 2026-02-09 19:20
- **Pages**: 3
- **PDF version**: 1.7

## Executive Summary

- **Score**: 49/100 (Grade: F)
- **Errors**: 2
- **Warnings**: 20
- **Deep analysis issues**: 7
- **Total actionable issues**: 23

This is a document created in Microsoft Word (3 pages). The document is tagged with 173 structure elements. It contains 41 form fields. Key issues include: missing document title, no heading structure, 7 non-standard elements without alt text, table header cells without scope attributes (x8), form fields detached from their labels in reading order.

## Built-in Checker Findings

| Severity | Rule ID | WCAG | Page | Description |
|----------|---------|------|------|-------------|
| Error | PDFUA.TITLE | 2.4.2 | doc | Document title is missing. |
| Warning | PDFBP.NO_HEADINGS | 2.4.6 | doc | Document has no headings (H1-H6). Screen reader users cannot navigate by heading. |
| Warning | PDFBP.NONSTD_NO_ALT | 1.1.1 | 1, 2, 3 | Non-standard tag /InlineShape has no alt text or actual text. (x7) |
| Tip | PDFBP.FLAT_STRUCTURE | 1.3.1 | doc | Document has 79 direct children with no sectioning (Sect/Part/Art). Consider grouping related elements into sections. |
| Warning | PDFBP.TABLE_SCOPE | 1.3.1 | 2 | TH element is missing the Scope attribute. (x8) |
| Error | PDFBP.FORMS_DETACHED | 1.3.2 | doc | 41 of 41 form fields are grouped at reading order positions 97-137, after all page content (positions 0-96). Screen readers encounter all text first, then all fields, making it impossible to associate fields with their labels. |
| Warning | PDFBP.UNDERSCORE_FILL | 1.3.1 | doc | 20 line(s) on page(s) 1, 3 contain underscore fill patterns (e.g., 'Name ___________'). Screen readers announce each underscore character individually. These should be marked as artifacts if a form field is overlaid. |
| Warning | PDFBP.NAV.TABORDER | 2.4.3 | 1, 2, 3 | Page 1 tab order is not set to structure order (/Tabs /S). (x3) |

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

The structure tree contains 96 /P tags and zero /H1 through /H6 tags. The Tag Tree panel displays this flat list of paragraphs, making the problem immediately visible. The Screen Reader Preview shows "96 consecutive paragraphs with no headings" and the Headings Only mode returns "0 headings found."

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

### Issue 3: Non-Standard Tags Without Alt Text (x7)

**Severity**: Important
**WCAG**: 1.1.1 (Non-text Content)
**Impact**: Screen readers encounter unnamed non-text elements. Users hear the tag type name (e.g., 'InlineShape') with no context about what the element represents.

**What the tool detects:**

The Tag Tree panel shows 7 non-standard tag(s) without /Alt attributes. The Alt Text panel lists these as "7 non-standard elements missing alt text" and displays thumbnails of the rendered page regions.

**Detailed inventory:**

| Index | Page | Tag | Maps To | Recommended Action |
|-------|------|-----|---------|-------------------|
| 0 | 1 | /InlineShape | Sect | Mark as decorative artifact |
| 1 | 1 | /InlineShape | Sect | Mark as decorative artifact |
| 2 | 1 | /InlineShape | Sect | Mark as decorative artifact |
| 3 | 1 | /InlineShape | Sect | Mark as decorative artifact |
| 4 | 2 | /InlineShape | Sect | Mark as decorative artifact |
| 5 | ? | /THead |  | Add alt text or change type |
| 6 | 2 | /TBody |  | Add alt text or change type |
| 7 | 3 | /Textbox | Sect | Add alt text or change type |
| 8 | 3 | /InlineShape | Sect | Mark as decorative artifact |

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

### Issue 4: Flat Document Structure

**Severity**: Recommended
**WCAG**: 1.3.1 (Info and Relationships)
**Impact**: A flat tag tree with many direct children and no sections makes it impossible for screen reader users to navigate by section or understand the document's organization.

**What the tool detects:**

The document root has 42 direct children with no /Sect, /Part, or /Art grouping elements. The Tag Tree shows a flat list of elements that should be organized into logical sections.

#### How to fix: PDF Accessibility Tool

1. In the **Tag Tree**, select the Document root.
2. Press **Insert** to add a /Sect child.
3. Select related heading and content elements, press **Ctrl+X** to cut.
4. Arrow to the Sect element, press **Ctrl+V** to paste.
5. Repeat for each logical section of the document.

#### How to fix: Adobe Acrobat Pro

1. In the **Tags panel**, create new Sect tags under Document.
2. Drag or cut/paste related heading and content tags into each section.

---

### Issue 5: Table Headers Missing Scope (x8)

**Severity**: Important
**WCAG**: 1.3.1 (Info and Relationships)
**Impact**: Screen readers cannot associate data cells with their headers when navigating the table, making data relationships unclear.

**What the tool detects:**

The Table Editor shows 8 TH cell(s) with no Scope attribute. Without Scope, screen readers cannot determine whether each header applies to its row or column.

The table contains 8 TH cells that all require Scope attributes.

#### How to fix: PDF Accessibility Tool

1. In the **Table Editor**, Tab to the first header cell.
2. Press **Enter** to select it.
3. Use the **Scope dropdown** to set Row or Column.
4. Press **Enter** to apply. Repeat for each TH cell.

#### How to fix: Adobe Acrobat Pro

1. In the **Tags panel**, select a TH tag.
2. Press **Ctrl+E** to open Properties > Tag tab.
3. Set **Scope** to Row or Column.
4. Press **OK**. Repeat for each TH cell.

---

### Issue 6: Form Fields Detached From Labels

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

### Issue 7: Underscore Fill Patterns

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

The document contains **41 form fields**.

**Positive findings:**

- 41 of 41 fields (100%) have tooltips

**Field inventory:**

| Name | Type | Tooltip | Required |
|------|------|---------|----------|
| Program Name | Text | Program Name |  |
| First Day of Program | Text | First Day of Program |  |
| Last Day of Program | Text | Last Day of Program |  |
| Date | Text | Date |  |
| Information regarding allergies, other medications the minor is currently taking, and other pertinent medical information which may be provided to emergency medical personnel in case of a medical emergency | Text | Information regarding allergies, other medications the minor is currently taking, and other pertinent medical information which may be provided to emergency medical personnel in case of a medical emergency.  |  |
| Minor First Name | Text | Minor First Name |  |
| Minor Last Name | Text | Minor Last Name |  |
| Minor Date of Birth Month Day Year | Text | Minor Date of Birth Month Day Year |  |
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
| First Medication | Text | First Medication |  |
| First Medication Dosage | Text | First Medication Dosage |  |
| First Medication Time of Self-Administration | Text | First Medication Time of Self-Administration |  |
| Second Medication | Text | Second Medication |  |
| Second Medication Dosage | Text | Second Medication Dosage |  |
| Second Medication Time of Self-Administration | Text | Second Medication Time of Self-Administration |  |
| Third Medication | Text | Third Medication |  |
| Third Medication Dosage | Text | Third Medication Dosage |  |
| Third Medication Time of Self-Administration | Text | Third Medication Time of Self-Administration |  |
| Fourth Medication | Text | Fourth Medication |  |
| Fourth Medication Dosage | Text | Fourth Medication Dosage |  |
| Fourth Medication Time of Self-Administration | Text | Fourth Medication Time of Self-Administration |  |
| Fifth Medication | Text | Fifth Medication |  |
| Fifth Medication Dosage | Text | Fifth Medication Dosage |  |
| Fifth Medication Time of Self-Administration | Text | Fifth Medication Time of Self-Administration |  |
| Name of Parent Legal Guardian Printed | Text | Name of Parent Legal Guardian Printed |  |
| Signature of Parent Legal Guardian_es_:signer:signature | Text | Signature of Parent Legal Guardian |  |

**Improvement opportunities:**

| Finding | Recommendation |
|---------|---------------|
| Consider marking key fields as required so screen readers announce their mandatory status | Consider marking key fields as required so screen readers announce their mandatory status |
| Reorder form fields to interleave with their labels | Reorder form fields to interleave with their labels (currently grouped at end of reading order) |

## Reading Order Assessment

The structure tree defines reading order for 173 elements across 3 page(s).

**Page 1** (41 elements): 36 P, 4 InlineShape, 1 Figure

**Page 2** (60 elements): 34 P, 10 TD, 8 TH, 6 TR, 1 InlineShape

**Page 3** (28 elements): 26 P, 1 Textbox, 1 InlineShape

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
Image: University of Arizona "A" and Youth Protection logo   (p.1)
Image  (p.1)
Image  (p.1)
Image  (p.1)
Image  (p.1)
Image  (p.2)
Table with 6 rows and 3 columns
Image  (p.3)
Text field: Program Name
Text field: First Day of Program
Text field: Last Day of Program
Text field: Minor First Name
Text field: Minor Date of Birth Month Day Year
Text field: Parent Legal Guardian Last Name
Text field: Minor Last Name
Text field: Parent Legal Guardian First Name
Text field: Parent Legal Guardian Email
Text field: Emergency Contact First Name
Text field: Emergency Contact Relationship to Minor
Text field: Additional Individual Authorized to Pick Up Minor First Name
Text field: Additional Individual Authorized to Pick Up Minor Relationship to Minor
Text field: Second Additional Individual Authorized to Pick Up Minor First Name
Text field: Second Additional Individual Authorized to Pick Up Minor Relationship to Minor
Text field: First Medication
Text field: First Medication Time of Self-Administration
Text field: Second Medication
Text field: Second Medication Time of Self-Administration
Text field: Third Medication Dosage
Text field: Fourth Medication
Text field: Fourth Medication Time of Self-Administration
Text field: Fifth Medication
Text field: Fifth Medication Time of Self-Administration
Text field: Name of Parent Legal Guardian Printed
Text field: Signature of Parent Legal Guardian
Text field: Parent Legal Guardian Phone Number
Text field: Emergency Contact Last Name
Text field: Additional Individual Authorized to Pick Up Minor Last Name
Text field: Second Additional Individual Authorized to Pick Up Minor Last Name
Text field: First Medication Dosage
Text field: Second Medication Dosage
Text field: Third Medication Time of Self-Administration
Text field: Fourth Medication Dosage
Text field: Information regarding allergies, other medications the minor is currently taking, and other pertinent medical information which may be provided to emergency medical personnel in case of a medical emergency.
Text field: Emergency Contact Phone Number
Text field: Second Additional Individual Authorized to Pick Up Minor Phone Number
Text field: Third Medication
Text field: Fifth Medication Dosage
Text field: Date
Text field: Additional Individual Authorized to Pick Up Minor Phone Number
WARNING: Document title is missing.
WARNING: Document has no headings (H1-H6). Screen reader users cannot navigate by heading.
WARNING: 41 of 41 form fields are grouped at reading order positions 97-137, after all page content (positions 0-96). Screen readers encounter all text first, then all fields, making it impossible to associate fields with their labels.
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
| 3 | Table Headers Missing Scope | 1.3.1 | In the Table Editor, Tab to the header cell, press Enter to select it, then use the Scope dropdown to set Row or Column. | In the Tags panel, select the TH tag, open Properties (Ctrl+E) > Tag tab, and set Scope to Row or Column.. |
| 4 | Underscore Fill Patterns | 1.3.1 | In the Tag Tree, navigate to each paragraph with underscore fills. | In the Tags panel, find each P tag containing underscore fills. |
| 5 | Tab Order Not Set to Structure | 2.4.3 | In the Accessibility Checker results, right-click the Tab Order finding and choose Fix. | Run Accessibility Check (Alt+A). |

### When Possible (Tips)

| Priority | Issue | WCAG | PDF Accessibility Tool | Adobe Acrobat Pro |
|----------|-------|------|----------------------|-------------------|
| 1 | Flat Document Structure | 1.3.1 | In the Tag Tree, select the Document root, press Insert to add a Sect child, then select related elements and press Ctrl+X to cut, arrow to the Sect, and Ctrl+V to paste.. | In the Tags panel, create new Sect tags under Document, then drag or cut/paste related heading and content tags into each section.. |

## Accessibility Scorecard

| Metric | Current | After Remediation (Projected) |
|--------|---------|-------------------------------|
| Score | 49/100 | 99/100 |
| Grade | F | A |
| Errors | 2 | 0 |
| Warnings | 20 | 0 |
| Headings | 0 | 5+ (estimated after fix) |
| Form fields with tooltips | 41/41 | 41/41 |
