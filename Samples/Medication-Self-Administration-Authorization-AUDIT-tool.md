# PDF Accessibility Audit Report (PDF Accessibility Tool)

## Audit Information

- **Date**: April 2, 2026
- **Tool**: PDF Accessibility Tool v0.1.0 (built-in checks only, veraPDF not installed)
- **File**: Medication Self-Administration Authorization.pdf
- **Remediation tool**: PDF Accessibility Tool
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

The structure tree contains 96 /P tags and zero /H1 through /H6 tags. The Tag Tree panel displays this flat list of paragraphs, making the problem immediately visible. The Screen Reader Preview shows "96 consecutive paragraphs with no headings" and the Headings Only mode returns "0 headings found."

The Auto-Tagger (Phase 10) analyzes font metrics extracted from the content stream and identifies bold text on its own line as likely headings. It flags the following candidates:

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

1. **Tag Tree panel** (Phase 3): Use the arrow keys to navigate to the first bold section header in the tag tree. The node displays as /P with a preview of the text content.
2. Press **F2** to open the Change Type editor. Use the arrow keys to select /H1 for the document title, then press **Enter** to confirm. Repeat for each section heading, selecting /H2.
3. Alternatively, use the **Auto-Tagger** (Alt+T, A): The wizard presents the heading candidates above for review. Use **Tab** and **arrow keys** to navigate the suggestion list. Press **Space** to accept or reject each suggestion, then **Enter** on Apply. Each accepted change is recorded as an undoable command (Ctrl+Z to undo).
4. After applying, the **Screen Reader Preview** (Phase 3.5) immediately refreshes to show "Heading level 1: MEDICATION SELF-ADMINISTRATION AUTHORIZATION" followed by navigable section headings.
5. The **Reading Order panel** (Phase 3) now shows headings highlighted, providing confirmation that the landmark structure is in place.

---

### Issue 2: Missing Document Title

**Severity**: Error
**WCAG**: 2.4.2 (Page Titled)
**Impact**: Screen readers announce the filename ("Medication Self-Administration Authorization.pdf") instead of a meaningful title when opening the document.

**What the tool detects:**

The built-in checker flags PDFUA.TITLE as an error. The Document Properties panel shows the Title field as empty. The DisplayDocTitle viewer preference is already set to true, which means once a title is added it will be displayed correctly.

#### How to fix

1. Open **Document Properties** (Alt+Enter).
2. **Tab** to the Title field.
3. Type: "Medication Self-Administration Authorization Form -- University of Arizona Youth Protection"
4. Press **Enter** to apply. The tool writes the title to both /Info /Title and the XMP dc:title metadata simultaneously, keeping them in sync.
5. The checker reruns automatically and the PDFUA.TITLE error clears from the Issues panel.

---

### Issue 3: Seven Non-Standard Tags Without Alt Text

**Severity**: Warning
**WCAG**: 1.1.1 (Non-text Content)
**Impact**: Screen readers encounter seven unnamed non-text elements. Visual inspection reveals six are horizontal rule decorative lines inserted by Microsoft Word as InlineShape objects, and one is a Textbox.

**What the tool detects:**

The Tag Tree panel shows six /InlineShape nodes nested inside /P parents and one /Textbox, each with no /Alt attribute. The Alt Text Panel (Phase 4) lists these as "7 non-standard elements missing alt text" and displays thumbnails of the rendered page regions.

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

1. **Alt Text Panel** (Phase 4): Press **Alt+4** to open or **Tab** to the Alt Text panel. The first InlineShape is listed.
2. Press **Space** on the "Mark as decorative" checkbox. This sets /Alt to an empty string, telling assistive technology to skip this element per PDF/UA conventions.
3. Press **Alt+N** (or Tab to "Next" and press Enter) to advance to the next InlineShape and repeat for all six.
4. Alternatively, in the **Tag Tree panel**: Use arrow keys to navigate to each InlineShape node, then press **Delete** and choose "Mark as Artifact" from the confirmation dialog (use arrow keys and Enter). This removes them from the structure tree entirely -- artifacts are invisible to screen readers, which is optimal for purely decorative elements.

**For the Textbox on page 3:**

1. In the **Tag Tree panel**, arrow to the /Textbox node.
2. Press **F2** to change its type. Select /P (if it contains static text) or /Form (if interactive). Press **Enter** to confirm.
3. If changed to /P, add appropriate content. If it maps to a form field, ensure the corresponding AcroForm field has a tooltip.

---

### Issue 4: Table Header Cells Missing Scope Attribute (x8)

**Severity**: Warning
**WCAG**: 1.3.1 (Info and Relationships)
**Impact**: The medications table on page 2 has 8 TH cells (3 column headers plus 5 row headers) but none specify whether they are column or row headers. Screen readers cannot associate data cells with their headers.

**What the tool detects:**

The built-in checker (Phase 2) flags PDFBP.TABLE_SCOPE for all 8 TH elements. The Table Editor panel (Phase 7) shows the table structure as a grid and highlights header cells with a "Missing Scope" indicator.

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

1. **Table Editor panel** (Phase 7): In the Tag Tree, use arrow keys to navigate to the Table element and press **Enter** to open the Table Editor.
2. Use **Tab** and **arrow keys** to move between cells in the grid view. Header cells are announced with their "Missing Scope" status.
3. For the 3 column header cells (Medication, Dosage, Time): Navigate to each cell, press **Enter** to select it, **Tab** to the Scope dropdown, use **arrow keys** to select "Column", then press **Enter** to apply.
4. For the 5 row header cells (First through Fifth Medication): Navigate to each cell, press **Enter** to select it, **Tab** to the Scope dropdown, use **arrow keys** to select "Row", then press **Enter** to apply.
5. Press **Ctrl+S** or Tab to "Apply All" and press Enter to save. The tool writes /A << /O /Table /Scope /Column >> (or /Row) to each TH element's attribute dictionary. Each change is an undoable command.
6. The Screen Reader Preview now shows: "Column header: Medication" and "Row header: First Medication" with proper associations.
7. The checker reruns and all 8 PDFBP.TABLE_SCOPE warnings clear from the Issues panel.

---

### Issue 5: No Bookmarks

**Severity**: Warning
**WCAG**: 2.4.1 (Bypass Blocks)
**Impact**: A 3-page form with distinct sections has no bookmarks. Users cannot jump directly to the medication table or the signature section.

**What the tool detects:**

The built-in checker flags the absence of an /Outlines entry. After headings are fixed (Issue 1), the tool can auto-generate bookmarks.

#### How to fix

1. First, fix Issue 1 (add headings) so the tool has a heading structure to work with.
2. Open the **Tools menu** (Alt+T) and select **Generate Bookmarks from Headings** (B). The tool reads all H1-H6 tags from the structure tree and creates a bookmark tree matching the heading hierarchy:
   - Medication Self-Administration Authorization (H1)
     - Program (H2)
     - Minor (H2)
     - Parent/Legal Guardian (H2)
     - Emergency Contact (H2)
     - Additional Individuals (H2)
     - Medication Information (H2)
     - Allergies and Medical Information (H2)
     - Acknowledgment (H2)
3. The bookmarks are written to the PDF's /Outlines dictionary. Each bookmark links to the page and position of the corresponding heading element.
4. The checker reruns and the bookmarks warning clears.

---

### Issue 6: Flat Structure with No Sectioning

**Severity**: Warning
**WCAG**: 1.3.1 (Info and Relationships)
**Impact**: All 79 top-level children of /Document are direct /P or /Form tags at depth 1. There is no grouping into /Sect (section) elements. Screen readers cannot convey document structure beyond the individual paragraph level.

**What the tool detects:**

The Tag Tree panel and Reading Order panel show all elements as direct children of Document. The Reading Order visualization overlay shows 79 numbered elements with no hierarchical grouping.

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

1. **Tag Tree panel** (Phase 3): Use arrow keys to navigate to the Document root node. Press **Insert** to add a new child element. In the type selector, choose /Sect and press **Enter**. Name it "Header".
2. Use arrow keys to navigate to the logo Figure, the H1 (after Issue 1 fix), and the explanatory P tag. Hold **Shift** while pressing the arrow keys to multi-select elements, or press **Ctrl+Space** on each to toggle selection.
3. Press **Ctrl+X** to cut the selected elements.
4. Arrow to the new Sect node and press **Ctrl+V** to paste as children. This calls reparent() on each element, updating both the parent's /K array and the child's /P reference.
5. Repeat for each section: press **Insert** on Document to create a new /Sect, then select and reparent the heading and its associated form fields into it.
6. The **Reading Order panel** now shows a hierarchical structure with indentation, and section boundaries are visible.
7. The **Screen Reader Preview** in Headings Only mode shows the heading hierarchy, confirming the document has navigable landmarks.
8. The **Page View overlay** (Ctrl+Shift+O) now shows numbered groups instead of a flat sequence.

---

### Issue 7: RoleMap Contains Non-Standard Tags Without Remediation

**Severity**: Info
**WCAG**: 4.1.1 (Parsing)
**Impact**: The RoleMap maps 19 custom role names (InlineShape, Textbox, Header, Footer, Annotation, etc.) to standard tags. While this is technically valid PDF, it adds complexity and some mappings are questionable (e.g., /Artifact mapped to /Sect means artifacts are treated as sections rather than being excluded from the tag tree).

**What the tool detects:**

The Tag Tree panel shows custom tag names with their mapped standard role in parentheses: "InlineShape (Sect)". Opening the element details (press Enter on the node) shows the full role mapping.

#### How to fix

1. For each InlineShape: if purely decorative, use arrow keys in the Tag Tree to navigate to it, then press **Delete** and select "Mark as Artifact" from the confirmation dialog (arrow keys and Enter). If meaningful, press **F2** and change to /Figure, then press **Tab** to the alt text field and enter descriptive text.
2. For the Textbox on page 3: press **F2** and change to /Form or /P as appropriate. Press **Enter** to confirm.
3. The RoleMap itself can be edited through the Document Properties panel (Alt+Enter, then Tab to the RoleMap section), but the preferred approach is to replace custom tags with standard ones directly.

---

### Issue 8: Form Fields Detached from Labels in Reading Order (CRITICAL)

**Severity**: Error
**WCAG**: 1.3.2 (Meaningful Sequence)
**Impact**: All 41 form fields appear at reading order positions 97-137, completely after all 97 text elements (positions 0-96). A screen reader user hears all the labels and paragraph text first -- "Program", "Minor", "First Name", "Last Name", etc. -- with no form fields. Then, after all 96 paragraphs, the user encounters 41 form fields in a row, completely disconnected from the labels they belong to. The user must memorize or guess which field corresponds to which label. Additionally, within the form field block, the fields are internally jumbled (e.g., "Parent Legal Guardian Last Name" at position 102 appears before "Parent Legal Guardian First Name" at position 104).

**Root cause**: Microsoft Word's PDF export appends all AcroForm field structure elements as direct children of /Document after all page content, regardless of where the fields appear visually on the page. Word generates the correct visual layout and field tooltips, but the structure tree (/K arrays) -- which determines reading order for screen readers -- places every /Form element in a contiguous block at the end.

**What the tool detects:**

The built-in checker (PDFBP.FORMS_DETACHED) performs depth-first traversal of the structure tree and numbers each leaf element. It finds:

- 97 text-bearing elements at positions 0-96 (all /P, /Figure, /InlineShape, /Textbox, /Table content)
- 41 /Form elements at positions 97-137 (every form field)
- 0 text elements interleaved with the form field block
- 100% of form fields are detached from their labels

**Sample of the actual reading order (what a screen reader announces):**

```
Position  Tag      Content
--------  -------  ---------------------------------
  0       /P       (empty paragraph)
  1       /Figure  UA Youth Protection logo
  2       /P       "MEDICATION SELF-ADMINISTRATION..."
  3       /P       "This form is not necessary..."
  5       /P       "Program"
  7       /P       "Program Name _______________"
 ...
 12       /P       "Minor"
 13       /P       "First Name _______________"
 ...
 96       /P       (last text paragraph on page 3)
 97       /Form    [Program Name]           <-- fields START here
 98       /Form    [First Day of Program]
 99       /Form    [Last Day of Program]
100       /Form    [Minor First Name]
101       /Form    [Minor Date of Birth]
102       /Form    [Parent Legal Guardian Last Name]  <-- JUMBLED: Last before First
103       /Form    [Minor Last Name]
104       /Form    [Parent Legal Guardian First Name]
...
121       /Form    [Name of Parent Legal Guardian Printed]
122       /Form    [Signature]
...
137       /Form    [Additional Individual Phone Number]
```

This means a screen reader user experiences the document as: all text on pages 1-3, then all form fields piled together with no context about which section or label each field belongs to.

#### How to fix

1. **Auto-Sort Reading Order** (Phase 3.5): Open the **Tools menu** (Alt+T) and select **Auto-Sort Reading Order** (R). The tool analyzes each form field's visual position on the page and its tooltip text, then matches it to the nearest preceding label /P element.
2. A **preview dialog** appears showing the proposed interleaved order:

   ```
   /P "Program"
   /Form [Program Name]          <-- moved from position 97 to after its label
   /Form [First Day of Program]  <-- moved from position 98
   /Form [Last Day of Program]   <-- moved from position 99
   /P "Minor"
   /Form [Minor First Name]      <-- moved from position 100
   /Form [Minor Last Name]       <-- moved from position 103
   /Form [Minor Date of Birth]   <-- moved from position 101
   ...
   ```
3. Use **Tab** and **arrow keys** to review the proposed order. Press **Space** to accept or reject individual moves. Press **Enter** on "Apply All" to execute.
4. Each move is a `reparent()` command that updates the /K array of the parent and the /P reference of the child. The entire batch is a single compound command -- one **Ctrl+Z** undoes all moves.
5. After applying, the **Screen Reader Preview** (Alt+P) shows labels immediately followed by their fields: "Program. Text field: Program Name. Text field: First Day of Program..."
6. The PDFBP.FORMS_DETACHED error clears from the Issues panel.

**Manual alternative**: In the **Tag Tree panel** (Alt+3), arrow to each /Form node at the bottom of the tree. Press **Ctrl+X** to cut, then arrow up to the label /P node where the field belongs, and press **Ctrl+V** to paste it as the next sibling. Repeat for each field. This is tedious for 41 fields but gives full control.

---

### Issue 9: Underscore Fill Lines Should Be Artifacts

**Severity**: Warning
**WCAG**: 1.3.1 (Info and Relationships)
**Impact**: 20 lines across pages 1 and 3 contain underscore fill patterns (e.g., "Name ___________"). Screen readers announce each underscore character individually -- a user hears "underscore underscore underscore underscore..." repeated dozens of times per line. Where a form field is overlaid on the underscores, the visual underscores serve no purpose for assistive technology and should be marked as artifacts.

**What the tool detects:**

The built-in checker (PDFBP.UNDERSCORE_FILL) extracts page text using pypdfium2 and flags lines where more than 30% of characters are underscores and at least 12 consecutive underscores appear. It finds:

- **Page 1**: 17 lines with underscore fills (form field blanks for Program, Minor, Parent/Legal Guardian, Emergency Contact, Additional Individuals sections)
- **Page 3**: 3 lines with underscore fills (Medical Information and Acknowledgment sections)

**Example lines detected:**

```
Program Name ____________________________________
First Name _________________ Last Name _________________
Date of Birth _____ / _____ / _________
Phone Number (____)____-____________
```

These underscores are visual placeholders from the original Word document. Each one is tagged as content in a /P element, but since AcroForm fields are overlaid at the same position, the underscores are redundant and create noise for screen readers.

#### How to fix

1. **Batch action** (fastest): Open the **Tools menu** (Alt+T) and select **Clean All Underscore Fills** (U). The tool identifies all /P elements containing underscore fill patterns and offers to mark them as artifacts in a single batch. Preview the list, press **Enter** to apply.
2. **Individual**: In the **Tag Tree** (Alt+3), arrow to a /P element flagged with underscore content. Press **Delete** and choose **Mark as Artifact** to remove it from the tag tree. The visual underscores remain on the page but are no longer announced by screen readers.
3. If the label text before the underscores is meaningful (e.g., "First Name"), you may need to **split the tag**: keep the label portion as a /P and convert only the underscore portion to an artifact. Use **Edit Tag Content** (F4) to select the underscore run and press **Delete** to artifact just that portion.

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
| No required fields marked | Mark name, DOB, and signature as required (/Ff bit 2) | Field Properties panel (Phase 5): Tab to the Required checkbox, press Space to toggle |
| Form tab order not explicitly set | Set tab order to Structure mode (/Tabs /S) on each page | Tab Order Editor (Phase 5): Alt+T, then Tab Order. Select "Use Structure Order" and press Enter |
| No field validation | Add format validation for date, phone, and email fields | Field Properties panel (Phase 5): Tab to Validation section, configure format |
| Large text area on page 3 has no character limit guidance | Add a tooltip describing the expected input | Field Properties panel: Tab to Tooltip and edit |

## Reading Order Assessment

**CRITICAL DEFECT**: The reading order has a fundamental structural problem. While text content flows correctly (top-to-bottom, left-to-right within each page), all 41 form fields are completely detached from the text -- they appear as a contiguous block at the end of the structure tree (positions 97-137), after all 97 text elements. See Issue 8 for details.

**Page 1 text content** (positions 0-37): Logo, title, explanatory text, section labels (Program, Minor, Parent/Legal Guardian, Emergency Contact, Additional Individuals), and underscore fill lines. The text flows correctly, but the form fields that visually appear next to these labels are NOT here -- they are all at the end of the document.

**Page 2 text content** (positions 38-52): Policy text paragraphs followed by the medications table. The table reads in the correct order: header row, then data rows left-to-right.

**Page 3 text content** (positions 53-96): Allergy information paragraphs, more underscore fill lines, acknowledgment text, and Textbox content.

**Form field block** (positions 97-137): All 41 form fields appear here, in a partially jumbled order. Fields from page 1 (Program Name, Minor First Name, etc.) are mixed with fields from pages 2 and 3. Within pages, some fields are out of order (e.g., Last Name before First Name for the Parent/Legal Guardian section).

**Recommendations:**

1. Fix Issue 8 first (FORMS_DETACHED) -- this is the most impactful reading order problem. Use Auto-Sort Reading Order (Alt+T, R) to interleave fields with their labels.
2. After adding sections (Issue 6), verify the reading order within each section using the Reading Order panel (Tab to the panel, then use arrow keys to walk through elements).
3. Use the **Reading Order overlay** (Ctrl+Shift+O) on the Page View to confirm the numbered sequence matches the logical reading flow.
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
| 1 | Interleave form fields with labels in reading order | 1.3.2 | Auto-Sort Reading Order (Alt+T, R), preview, Enter to apply |
| 2 | Add document title | 2.4.2 | Document Properties (Alt+Enter), Tab to Title, type, Enter |
| 3 | Convert bold section text to H1/H2 headings | 2.4.6, 1.3.1 | Tag Tree: arrow to element, F2, select H1/H2, Enter. Or Auto-Tagger (Alt+T, A) |

### Soon (Warnings -- significant accessibility improvement)

| Priority | Issue | WCAG | How to fix |
|----------|-------|------|------------|
| 4 | Set Scope on all 8 TH cells | 1.3.1 | Table Editor: Tab to cell, Enter, Scope dropdown, arrow to Row/Column, Enter |
| 5 | Mark 6 InlineShapes as artifacts | 1.1.1 | Tag Tree: arrow to element, Delete, "Mark as Artifact", Enter |
| 6 | Mark 20 underscore fill lines as artifacts | 1.3.1 | Clean All Underscore Fills (Alt+T, U), preview, Enter to apply |
| 7 | Add bookmarks from headings | 2.4.1 | Tools menu, Generate Bookmarks (Alt+T, B) |
| 8 | Group elements into /Sect sections | 1.3.1 | Tag Tree: Insert on Document for Sect, multi-select, Ctrl+X, Ctrl+V into Sect |

### Recommended (Best practices)

| Priority | Issue | How to fix |
|----------|-------|------------|
| 9 | Set explicit tab order to Structure mode | Tab Order Editor (Alt+T, Tab Order), Enter on "Use Structure Order" |
| 10 | Mark required fields (name, DOB, signature) | Field Properties panel: Tab to Required checkbox, Space to toggle |
| 11 | Clean up RoleMap custom tags | Tag Tree: F2 to change type, or Delete to mark as Artifact |

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

## Tool Capability Coverage

Every issue identified in this report can be fully remediated using the PDF Accessibility Tool:

| Phase | Feature | Issues Addressed | Keyboard Shortcut |
|-------|---------|-----------------|-------------------|
| Phase 2 | Accessibility Checker | Detects title, scope, bookmarks, tagged status, headings, non-standard tags, flat structure | F5 (run check) |
| Phase 3 | Tag Tree panel | Change tag types (F2), reparent/move (Ctrl+X/V), create sections (Insert), mark as artifact (Delete) | Alt+3 |
| Phase 3 | Reading Order panel | Verify and adjust element sequence | Ctrl+Shift+O (overlay) |
| Phase 3.5 | Screen Reader Preview | Before/after comparison of assistive technology experience | Alt+P |
| Phase 4 | Alt Text panel | Mark decorative (Space on checkbox), edit alt text | Alt+4 |
| Phase 5 | Field Properties panel | Set required flag (Space), set tab order | Alt+5 |
| Phase 7 | Table Editor panel | Set Scope attribute on TH cells | Enter on Table in Tag Tree |
| Phase 8 | Document Properties panel | Set document title, generate bookmarks, edit RoleMap | Alt+Enter |
| Phase 10 | Auto-Tagger | Detect heading candidates from font metrics | Alt+T, A |
