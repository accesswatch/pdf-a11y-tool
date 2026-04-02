# PDF Accessibility Audit Report (Adobe Acrobat Pro)

## Audit Information

- **Date**: April 2, 2026
- **Tool**: PDF Accessibility Tool v0.1.0 (built-in checks only, veraPDF not installed)
- **File**: Medication Self-Administration Authorization.pdf
- **Remediation tool**: Adobe Acrobat Pro
- **Source application**: Microsoft Word
- **Author**: Galabi, Lora
- **Created**: February 9, 2026
- **Pages**: 3
- **PDF version**: 1.7

## Executive Summary

- **Score**: 79/100 (Grade: C)
- **Errors**: 2
- **Warnings**: 9
- **Additional issues found by deep analysis**: 5 (not yet covered by built-in checks)
- **Total actionable issues**: 16

This is a University of Arizona Youth Protection medication authorization form. While the document is tagged and has a document language set, it suffers from critical structural problems: no headings, missing document title, InlineShapes without alt text, table header cells without scope attributes, and a flat reading order that provides no navigational landmarks for assistive technology users.

## Built-in Checker Findings

| Severity | Rule ID | WCAG | Page | Description |
|----------|---------|------|------|-------------|
| Error | PDFUA.TITLE | 2.4.2 | doc | Document title is missing |
| Error | PDFBP.FORMS_DETACHED | 1.3.2 | doc | 41 of 41 form fields grouped at reading order positions 97-137, after all page content |
| Warning | PDFBP.NO_HEADINGS | 2.4.6 | doc | No headings (H1-H6) in document |
| Warning | PDFBP.NONSTD_NO_ALT | 1.1.1 | 1-3 | Non-standard tag without alt text (x7) |
| Warning | PDFBP.TABLE_SCOPE | 1.3.1 | 2 | TH element missing Scope attribute (x8) |
| Warning | PDFBP.UNDERSCORE_FILL | 1.3.1 | 1, 3 | 20 lines with underscore fill patterns should be marked as artifacts |
| Tip | PDFBP.FLAT_STRUCTURE | 1.3.1 | doc | 79 direct children with no sectioning |

## Deep Analysis Findings

The following issues were identified through structure tree analysis, reading order mapping, and content flow analysis.

---

### Issue 1: No Headings (CRITICAL)

**Severity**: Error
**WCAG**: 2.4.6 (Headings and Labels), 1.3.1 (Info and Relationships)
**Impact**: Screen reader users cannot navigate between form sections. The document has clear visual sections (Program, Minor, Parent/Legal Guardian, Emergency Contact, Additional Individuals, Medication Table, Allergies/Medical Info, Acknowledgment) but they are all tagged as /P (paragraph) instead of heading tags.

**What the tool detects:**

The structure tree contains 96 /P tags and zero /H1 through /H6 tags. The following heading candidates were identified by analyzing font metrics:

| Current Tag | Suggested Tag | Text Content | Page | Confidence |
|------------|---------------|-------------|------|------------|
| /P | /H1 | MEDICATION SELF-ADMINISTRATION AUTHORIZATION | 1 | High |
| /P | /H2 | Program | 1 | High |
| /P | /H2 | Minor | 1 | High |
| /P | /H2 | Parent/Legal Guardian | 1 | High |
| /P | /H2 | Emergency Contact | 1 | High |
| /P | /H2 | Additional Individuals Authorized to Pick up Minor | 1 | High |
| /P | /H2 | Medication Table heading (implied) | 2 | Medium |
| /P | /H2 | Allergies and Medical Information heading (implied) | 3 | Medium |

#### How to fix

1. Open the **Tags panel** (View > Show/Hide > Navigation Panes > Tags, or press the Tags shortcut if configured).
2. Expand the tag tree and locate each paragraph that should be a heading.
3. Select the /P tag, press **Ctrl+E** to open the Properties dialog.
4. In the **Tag** tab, change the Type field from P to H1 (for the document title) or H2 (for section headings). Press **OK**.
5. Repeat for all 8 heading candidates listed above.

---

### Issue 2: Missing Document Title

**Severity**: Error
**WCAG**: 2.4.2 (Page Titled)
**Impact**: Screen readers announce the filename ("Medication Self-Administration Authorization.pdf") instead of a meaningful title when opening the document.

**What the tool detects:**

The built-in checker flags PDFUA.TITLE as an error. The Document Properties panel shows the Title field as empty. The DisplayDocTitle viewer preference is already set to true, which means once a title is added it will be displayed correctly.

#### How to fix

1. Open **File > Properties** (Ctrl+D).
2. In the **Description** tab, **Tab** to the Title field.
3. Type: "Medication Self-Administration Authorization Form -- University of Arizona Youth Protection"
4. Press **OK**.
5. Then open **File > Properties** again, go to the **Initial View** tab, and verify that "Show" is set to "Document Title" (this enables DisplayDocTitle).

---

### Issue 3: Seven Non-Standard Tags Without Alt Text

**Severity**: Warning
**WCAG**: 1.1.1 (Non-text Content)
**Impact**: Screen readers encounter seven unnamed non-text elements. Visual inspection reveals six are horizontal rule decorative lines inserted by Microsoft Word as InlineShape objects, and one is a Textbox.

**What the tool detects:**

The Tag Tree panel shows six /InlineShape nodes nested inside /P parents and one /Textbox, each with no /Alt attribute.

**Detailed inventory:**

| Index | Page | Tag | Visual Content | Recommended Action |
|-------|------|-----|---------------|-------------------|
| 0 | 1 | /InlineShape | Horizontal rule line below subtitle | Mark as decorative artifact |
| 1 | 1 | /InlineShape | Horizontal rule line below Program section | Mark as decorative artifact |
| 2 | 1 | /InlineShape | Horizontal rule line below Minor section | Mark as decorative artifact |
| 3 | 1 | /InlineShape | Horizontal rule line below bottom of page 1 | Mark as decorative artifact |
| 4 | 2 | /InlineShape | Horizontal rule line below policy text | Mark as decorative artifact |
| 5 | 3 | /InlineShape | Horizontal rule line above acknowledgment | Mark as decorative artifact |
| 6 | 3 | /Textbox | Free-form text entry area | Change to /P or /Form |

#### How to fix

**For the 6 decorative InlineShapes:**

1. In the **Tags panel**, locate each /InlineShape tag.
2. Select the tag, press **Ctrl+E** to open Properties.
3. Change the **Type** to "Artifact" to remove it from the tag structure. Press **OK**.
4. Alternatively, select the tag and delete it from the Tags panel, which converts the content to an artifact.

**For the Textbox:**

1. Select the /Textbox tag in the Tags panel, press **Ctrl+E**.
2. Change the Type to P or Form as appropriate. Press **OK**.

---

### Issue 4: Table Header Cells Missing Scope Attribute (x8)

**Severity**: Warning
**WCAG**: 1.3.1 (Info and Relationships)
**Impact**: The medications table on page 2 has 8 TH cells (3 column headers plus 5 row headers) but none specify whether they are column or row headers. Screen readers cannot associate data cells with their headers.

**What the tool detects:**

The built-in checker (Phase 2) flags PDFBP.TABLE_SCOPE for all 8 TH elements.

**Table structure analysis:**

```
THead:
  TR: [TH: "Medication"] [TH: "Dosage (can't be different...)"] [TH: "Time of Self-Administration"]
TBody:
  TR: [TH: "First Medication"]   [TD: (empty)] [TD: (empty)]
  TR: [TH: "Second Medication"]  [TD: (empty)] [TD: (empty)]
  TR: [TH: "Third Medication"]   [TD: (empty)] [TD: (empty)]
  TR: [TH: "Fourth Medication"]  [TD: (empty)] [TD: (empty)]
  TR: [TH: "Fifth Medication"]   [TD: (empty)] [TD: (empty)]
```

#### How to fix

1. In the **Tags panel**, expand the Table tag and locate each TH element.
2. Select the first TH, press **Ctrl+E** to open Properties.
3. In the **Tag** tab, find the Attribute Objects section. Add a Table attribute with Scope set to "Column" (for header row cells) or "Row" (for row header cells). Press **OK**.
4. Alternatively, use the **Table Editor** (Accessibility > Table Editor): Tab through each header cell. The Table Editor highlights headers and lets you set scope with keyboard controls.
5. Repeat for all 8 TH cells.

---

### Issue 5: No Bookmarks

**Severity**: Warning
**WCAG**: 2.4.1 (Bypass Blocks)
**Impact**: A 3-page form with distinct sections has no bookmarks. Users cannot jump directly to the medication table or the signature section.

**What the tool detects:**

The built-in checker flags the absence of an /Outlines entry. After headings are fixed (Issue 1), bookmarks can be generated.

#### How to fix

1. Open the **Bookmarks panel** (View > Show/Hide > Navigation Panes > Bookmarks).
2. Navigate to the first heading location in the document.
3. Press **Ctrl+B** to create a new bookmark at the current position. Type the heading text and press Enter.
4. Repeat for each section heading. Use **Tab** and **Shift+Tab** to nest child bookmarks under the H1 bookmark.
5. Alternatively, if headings are already tagged: some third-party Acrobat plugins (e.g., AutoBookmark) can generate bookmarks from the heading tag structure.
6. The expected bookmark structure:
   - Medication Self-Administration Authorization (H1)
     - Program (H2)
     - Minor (H2)
     - Parent/Legal Guardian (H2)
     - Emergency Contact (H2)
     - Additional Individuals (H2)
     - Medication Information (H2)
     - Allergies and Medical Information (H2)
     - Acknowledgment (H2)

---

### Issue 6: Flat Structure with No Sectioning

**Severity**: Warning
**WCAG**: 1.3.1 (Info and Relationships)
**Impact**: All 79 top-level children of /Document are direct /P or /Form tags at depth 1. There is no grouping into /Sect (section) elements. Screen readers cannot convey document structure beyond the individual paragraph level.

**What the tool detects:**

All elements are direct children of Document. The Reading Order visualization overlay shows 79 numbered elements with no hierarchical grouping.

**Recommended structure:**

```
/Document
  /Sect "Header"
    /Figure (logo with alt text)
    /H1 "Medication Self-Administration Authorization"
    /P (explanatory text)
  /Sect "Program"
    /H2 "Program"
    /Form "Program Name"
    /Form "First Day of Program"
    /Form "Last Day of Program"
  /Sect "Minor"
    /H2 "Minor"
    /Form "First Name"
    /Form "Last Name"
    /Form "Date of Birth"
  /Sect "Parent/Legal Guardian"
    /H2 "Parent/Legal Guardian"
    /Form "First Name" ... /Form "Email"
  /Sect "Emergency Contact"
    /H2 "Emergency Contact"
    /Form "First Name" ... /Form "Phone Number"
  /Sect "Additional Individuals"
    /H2 "Additional Individuals Authorized to Pick up Minor"
    /Form (x8 fields for two additional contacts)
  /Sect "Policy"
    /P (policy paragraphs -- page 2 text blocks)
  /Sect "Medications"
    /H2 "Please provide the information below."
    /Table (medications table with proper scope)
  /Sect "Medical Information"
    /H2 "Allergies and Medical Information"
    /P (instructions)
    /Form "Medical information text area"
  /Sect "Acknowledgment"
    /P (acknowledgment text)
    /Form "Name of Parent/Legal Guardian Printed"
    /Form "Signature"
    /Form "Date"
```

#### How to fix

1. In the **Tags panel**, select the Document root tag.
2. Use the **Options menu** (or press Shift+F10 for context menu) and select "New Tag". Set Type to Sect.
3. Select the elements that belong in this section (logo, H1, intro paragraph). Use **Ctrl+X** to cut and **Ctrl+V** to paste them inside the new Sect tag.
4. Repeat for each document section: create a Sect tag, then move related heading and content tags into it.
5. Verify the reading order by running the **Read Out Loud** feature (View > Read Out Loud > Read This Page) or by checking the Order panel.

---

### Issue 8: Form Fields Detached from Labels in Reading Order (CRITICAL)

**Severity**: Error
**WCAG**: 1.3.2 (Meaningful Sequence)
**Impact**: All 41 form fields appear at reading order positions 97-137, completely after all 97 text elements (positions 0-96). A screen reader user hears all the labels and paragraph text first -- "Program", "Minor", "First Name", "Last Name", etc. -- with no form fields. Then, after all 96 paragraphs, the user encounters 41 form fields in a row, completely disconnected from the labels they belong to. The user must memorize or guess which field corresponds to which label.

**Root cause**: Microsoft Word's PDF export appends all AcroForm field structure elements as direct children of /Document after all page content, regardless of where the fields appear visually on the page.

**What the tool detects:**

The built-in checker (PDFBP.FORMS_DETACHED) performs depth-first traversal of the structure tree and numbers each leaf element. It finds:

- 97 text-bearing elements at positions 0-96
- 41 /Form elements at positions 97-137 (every form field)
- 0 text elements interleaved with the form field block
- 100% of form fields are detached from their labels

#### How to fix

1. In the **Tags panel**, expand the Document root to see all child tags.
2. Locate the /Form tags at the bottom of the child list (positions 97-137).
3. For each form field: select the /Form tag, press **Ctrl+X** to cut it.
4. Navigate up to the /P tag that contains the label text for this field (e.g., find the /P containing "Program Name").
5. Select that /P tag and press **Ctrl+V** to paste the /Form tag as the next sibling after the label.
6. Repeat for all 41 form fields. Work section by section:
   - Program section: 3 fields (Program Name, First Day, Last Day)
   - Minor section: 3 fields (First Name, Last Name, DOB)
   - Parent/Legal Guardian section: 7 fields (First Name through Email)
   - Emergency Contact section: 4 fields
   - Additional Individuals section: 8 fields
   - Medication table: no form fields in table
   - Page 3: remaining fields (Medical info, Acknowledgment, Signature)
7. Alternatively, use the **Order panel** (View > Show/Hide > Navigation Panes > Order) to drag form fields inline with their labels. This is faster for visual users but requires precise mouse control.
8. After rearranging, verify reading order using **Read Out Loud** (View > Read Out Loud > Read This Page) -- each label should be immediately followed by its form field.

---

### Issue 9: Underscore Fill Lines Should Be Artifacts

**Severity**: Warning
**WCAG**: 1.3.1 (Info and Relationships)
**Impact**: 20 lines across pages 1 and 3 contain underscore fill patterns (e.g., "Name ___________"). Screen readers announce each underscore character individually -- a user hears "underscore underscore underscore underscore..." repeated dozens of times per line. Where a form field is overlaid on the underscores, the visual underscores serve no purpose for assistive technology and should be marked as artifacts.

**What the tool detects:**

The built-in checker (PDFBP.UNDERSCORE_FILL) finds:

- **Page 1**: 17 lines with underscore fills (form field blanks for Program, Minor, Parent/Legal Guardian, Emergency Contact, Additional Individuals sections)
- **Page 3**: 3 lines with underscore fills (Medical Information and Acknowledgment sections)

**Example lines detected:**

```
Program Name ____________________________________
First Name _________________ Last Name _________________
Date of Birth _____ / _____ / _________
Phone Number (____)____-____________
```

#### How to fix

1. In the **Tags panel**, expand the Document root and locate each /P tag containing underscore fill text.
2. Select the /P tag, press **Ctrl+E** to open Properties.
3. Change the **Type** to "Artifact" to remove it from the tag structure. Press **OK**.
4. If the label text before the underscores is meaningful (e.g., "First Name"), you need to split the tag:
   - Select the text content within the tag that contains underscores.
   - Use **Edit > Cut** to remove the underscore portion.
   - The label text remains as a /P tag.
   - The underscore content becomes an artifact (untagged content).
5. Repeat for all 20 flagged lines across pages 1 and 3.
6. After removing underscores from the tag tree, the form fields (once interleaved per Issue 8) provide the actual interactive input -- the visual underscores remain on the printed page but are no longer announced.

---

### Issue 10: RoleMap Contains Non-Standard Tags Without Remediation

**Severity**: Info
**WCAG**: 4.1.1 (Parsing)
**Impact**: The RoleMap maps 19 custom role names (InlineShape, Textbox, Header, Footer, Annotation, etc.) to standard tags. While this is technically valid PDF, it adds complexity and some mappings are questionable (e.g., /Artifact mapped to /Sect means artifacts are treated as sections rather than being excluded from the tag tree).

**What the tool detects:**

The Tags panel shows custom tag names. Opening element properties (Ctrl+E) shows the full role mapping.

#### How to fix

1. For each non-standard tag: select it in the Tags panel, press **Ctrl+E** to open Properties, and change the Type to the appropriate standard tag (Figure, P, Form, or Artifact).
2. The RoleMap is modified automatically when you change all instances of a custom tag to standard tags. Once no elements use a custom role, that mapping becomes unused.

---

## Form Fields Assessment

All 41 form fields are properly tagged in the structure tree with /Form tags (41 /Form nodes found). Every field has a tooltip (/TU) matching its field name (/T), which is good practice. All fields are text inputs (/Tx).

**Positive findings:**

- All 41 fields have accessible names (tooltips)
- All fields are in the structure tree (tagged)
- Field names are descriptive and human-readable
- The signature field uses Adobe EchoSign integration

**Opportunities for improvement:**

| Finding | Recommendation | How to fix |
|---------|---------------|------------|
| No required fields marked | Mark name, DOB, and signature as required (/Ff bit 2) | Forms > Edit: select field, Ctrl+E, check Required |
| Form tab order not explicitly set | Set tab order to Structure mode (/Tabs /S) on each page | Page Thumbnails panel: select all pages, Page Properties, Tab Order: Use Document Structure |
| No field validation | Add format validation for date, phone, and email fields | Forms > Edit: select field, Properties, Format tab |
| Large text area on page 3 has no character limit guidance | Add a tooltip describing the expected input | Select field, Ctrl+E, General tab, Tooltip |

## Reading Order Assessment

**CRITICAL DEFECT**: The reading order has a fundamental structural problem. While text content flows correctly (top-to-bottom, left-to-right within each page), all 41 form fields are completely detached from the text -- they appear as a contiguous block at the end of the structure tree (positions 97-137), after all 97 text elements. See Issue 8 for details.

**Page 1 text content** (positions 0-37): Logo, title, explanatory text, section labels (Program, Minor, Parent/Legal Guardian, Emergency Contact, Additional Individuals), and underscore fill lines. The text flows correctly, but the form fields that visually appear next to these labels are NOT here -- they are all at the end of the document.

**Page 2 text content** (positions 38-52): Policy text paragraphs followed by the medications table. The table reads in the correct order: header row, then data rows left-to-right.

**Page 3 text content** (positions 53-96): Allergy information paragraphs, more underscore fill lines, acknowledgment text, and Textbox content.

**Form field block** (positions 97-137): All 41 form fields appear here, in a partially jumbled order. Fields from page 1 (Program Name, Minor First Name, etc.) are mixed with fields from pages 2 and 3. Within pages, some fields are out of order (e.g., Last Name before First Name for the Parent/Legal Guardian section).

**Recommendations:**

1. Fix Issue 8 first (FORMS_DETACHED) -- this is the most impactful reading order problem. In the Tags panel, cut each /Form tag and paste it after its label /P tag.
2. After adding sections (Issue 6), verify the reading order within each section using the **Order panel** (View > Show/Hide > Navigation Panes > Order).
3. Use **Read Out Loud** (View > Read Out Loud > Read This Page) to confirm each label is immediately followed by its form field.
4. After interleaving is applied, verify the paired label/field elements read correctly (e.g., "Program" label immediately followed by "Program Name" field).

## Screen Reader Preview (Simulated)

Based on the current tag tree, a screen reader would encounter the document as follows (with warnings noted):

```
Image: University of Arizona "A" and Youth Protection logo          (p.1)
(empty paragraph)                                                    (p.1)
MEDICATION SELF-ADMINISTRATION AUTHORIZATION                         (p.1)
This form is not necessary for asthma inhalers, epinephrine...      (p.1)
WARNING: InlineShape with no alternative text                        (p.1)
Program                                                              (p.1)
WARNING: InlineShape with no alternative text                        (p.1)
Text field: Program Name                                             (p.1)
Text field: First Day of Program                                     (p.1)
Text field: Last Day of Program                                      (p.1)
WARNING: InlineShape with no alternative text                        (p.1)
Minor                                                                (p.1)
Text field: Minor First Name                                         (p.1)
Text field: Minor Last Name                                          (p.1)
Text field: Minor Date of Birth Month Day Year                       (p.1)
Parent/Legal Guardian                                                (p.1)
Text field: Parent Legal Guardian First Name                         (p.1)
...
(continues for 96 paragraphs with no heading navigation possible)
...
Table with 6 rows and 3 columns                                     (p.2)
  Column header: Medication                                          (p.2)
  WARNING: header has no Scope attribute
  Column header: Dosage (can't be different from dosage...)          (p.2)
  WARNING: header has no Scope attribute
  ...
Text field: Name of Parent Legal Guardian Printed                    (p.3)
Text field: Signature of Parent Legal Guardian                       (p.3)
```

**After all recommended fixes are applied, the preview would show:**

```
Heading level 1: Medication Self-Administration Authorization        (p.1)
Image: University of Arizona "A" and Youth Protection logo           (p.1)
This form is not necessary for asthma inhalers, epinephrine...      (p.1)
Heading level 2: Program                                             (p.1)
Text field: Program Name                                             (p.1)
Text field: First Day of Program                                     (p.1)
Text field: Last Day of Program                                      (p.1)
Heading level 2: Minor                                               (p.1)
Text field: Minor First Name                                         (p.1)
Text field: Minor Last Name                                          (p.1)
Text field: Minor Date of Birth Month Day Year                       (p.1)
Heading level 2: Parent/Legal Guardian                               (p.1)
Text field: Parent Legal Guardian First Name, required               (p.1)
...
Heading level 2: Medication Information                              (p.2)
Table with 6 rows and 3 columns                                     (p.2)
  Column header: Medication                                          (p.2)
  Column header: Dosage                                              (p.2)
  Column header: Time of Self-Administration                         (p.2)
  Row header: First Medication                                       (p.2)
...
Heading level 2: Acknowledgment                                      (p.3)
I acknowledge that the above-named minor is capable of...            (p.3)
Text field: Name of Parent Legal Guardian Printed, required          (p.3)
Text field: Signature of Parent Legal Guardian, required             (p.3)
```

## Remediation Priority

### Immediate (Errors -- must fix for PDF/UA conformance)

| Priority | Issue | WCAG | How to fix |
|----------|-------|------|------------|
| 1 | Interleave form fields with labels in reading order | 1.3.2 | Tags panel: Ctrl+X each /Form tag, Ctrl+V after its label /P tag |
| 2 | Add document title | 2.4.2 | File > Properties (Ctrl+D), Description tab, Title field |
| 3 | Convert bold section text to H1/H2 headings | 2.4.6, 1.3.1 | Tags panel: select tag, Ctrl+E, change Type to H1/H2 |

### Soon (Warnings -- significant accessibility improvement)

| Priority | Issue | WCAG | How to fix |
|----------|-------|------|------------|
| 4 | Set Scope on all 8 TH cells | 1.3.1 | Tags panel: select TH, Ctrl+E, add Scope attribute |
| 5 | Mark 6 InlineShapes as artifacts | 1.1.1 | Tags panel: select tag, Ctrl+E, change Type to Artifact |
| 6 | Mark 20 underscore fill lines as artifacts | 1.3.1 | Tags panel: select /P with underscores, Ctrl+E, change Type to Artifact |
| 7 | Add bookmarks from headings | 2.4.1 | Bookmarks panel, Ctrl+B per section |
| 8 | Group elements into /Sect sections | 1.3.1 | Tags panel: New Tag (Sect), cut/paste children |

### Recommended (Best practices)

| Priority | Issue | How to fix |
|----------|-------|------------|
| 9 | Set explicit tab order to Structure mode | Page Thumbnails: select all, Page Properties, Tab Order |
| 10 | Mark required fields (name, DOB, signature) | Forms > Edit: select field, Ctrl+E, check Required |
| 11 | Clean up RoleMap custom tags | Tags panel: Ctrl+E, change Type on each non-standard tag |

## Accessibility Scorecard

| Metric | Current | After Remediation (Projected) |
|--------|---------|-------------------------------|
| Score | 79/100 | 98/100 |
| Grade | C | A |
| Errors | 2 | 0 |
| Warnings | 9 | 0 |
| Headings | 0 | 8 (H1 + 7 H2) |
| Images with alt text | 1/7 | 1/1 (6 artifacts removed) |
| Underscore fill lines | 20 (tagged) | 0 (all artifacts) |
| Table headers with scope | 0/8 | 8/8 |
| Bookmarks | 0 | 9 |
| Form fields interleaved | No (all at end) | Yes (after labels) |
| Required fields marked | 0 | 5+ |
