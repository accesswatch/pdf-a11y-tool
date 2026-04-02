# PDF Accessibility Audit Report: Formulario Para El Padre Madre Tutor(a) Legal

## Audit Information

- **Date**: April 02, 2026
- **Tool**: PDF Accessibility Tool v0.1.0 (built-in checks only, veraPDF not installed)
- **File**: Formulario Para El Padre Madre Tutor(a) Legal.pdf
- **Source application**: Acrobat PDFMaker 25 for Word
- **Author**: Galabi, Lora - (galabi)
- **Created**: 2026-03-18 09:48
- **Pages**: 5
- **PDF version**: 1.6

## Executive Summary

- **Score**: 67/100 (Grade: D)
- **Errors**: 3
- **Warnings**: 9
- **Deep analysis issues**: 6
- **Total actionable issues**: 12

This is a document created in Microsoft Word (5 pages). The document is tagged with 191 structure elements. It contains 27 form fields. Key issues include: missing document title, no heading structure, 6 non-standard elements without alt text, form fields detached from their labels in reading order, 1 form field(s) missing tooltips.

## Built-in Checker Findings

| Severity | Rule ID | WCAG | Page | Description |
|----------|---------|------|------|-------------|
| Error | PDFUA.TITLE | 2.4.2 | doc | Document title is missing. |
| Warning | PDFBP.NO_HEADINGS | 2.4.6 | doc | Document has no headings (H1-H6). Screen reader users cannot navigate by heading. |
| Warning | PDFBP.NONSTD_NO_ALT | 1.1.1 | 1, 2, 3, 5 | Non-standard tag /Artifact has no alt text or actual text. (x6) |
| Error | PDFUA.FORMS | 4.1.2 | doc | Form field is missing a tooltip (TU entry). |
| Error | PDFBP.FORMS_DETACHED | 1.3.2 | doc | 28 of 28 form fields are grouped at reading order positions 138-165, after all page content (positions 0-137). Screen readers encounter all text first, then all fields, making it impossible to associate fields with their labels. |
| Warning | PDFBP.UNDERSCORE_FILL | 1.3.1 | doc | 21 line(s) on page(s) 1, 5 contain underscore fill patterns (e.g., 'Name ___________'). Screen readers announce each underscore character individually. These should be marked as artifacts if a form field is overlaid. |
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

The structure tree contains 123 /P tags and zero /H1 through /H6 tags. The Tag Tree panel displays this flat list of paragraphs, making the problem immediately visible. The Screen Reader Preview shows "123 consecutive paragraphs with no headings" and the Headings Only mode returns "0 headings found."

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

### Issue 3: Non-Standard Tags Without Alt Text (x6)

**Severity**: Important
**WCAG**: 1.1.1 (Non-text Content)
**Impact**: Screen readers encounter unnamed non-text elements. Users hear the tag type name (e.g., 'InlineShape') with no context about what the element represents.

**What the tool detects:**

The Tag Tree panel shows 6 non-standard tag(s) without /Alt attributes. The Alt Text panel lists these as "6 non-standard elements missing alt text" and displays thumbnails of the rendered page regions.

**Detailed inventory:**

| Index | Page | Tag | Maps To | Recommended Action |
|-------|------|-----|---------|-------------------|
| 0 | 1 | /Artifact | P | Add alt text or change type |
| 1 | 1 | /Artifact | P | Add alt text or change type |
| 2 | 2 | /Artifact | P | Add alt text or change type |
| 3 | 3 | /Artifact | P | Add alt text or change type |
| 4 | 3 | /Artifact | P | Add alt text or change type |
| 5 | 5 | /Artifact | P | Add alt text or change type |

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

### Issue 4: Form Fields Missing Tooltips

**Severity**: CRITICAL
**WCAG**: 4.1.2 (Name, Role, Value)
**Impact**: Form fields without tooltips are announced as unlabeled to screen reader users, who cannot determine the field's purpose.

#### How to fix: PDF Accessibility Tool

1. In the **Field Properties panel**, Tab to the Tooltip field.
2. Enter a descriptive label that matches the visual label.
3. Press **Enter** to apply. Repeat for each field.

#### How to fix: Adobe Acrobat Pro

1. Select the form field in the document.
2. Open Properties (**Ctrl+E**), General tab.
3. Enter a descriptive **Tooltip** matching the visual label.
4. Press **OK**. Repeat for each field.

---

### Issue 5: Form Fields Detached From Labels

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

### Issue 6: Underscore Fill Patterns

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

The document contains **27 form fields**.

**Positive findings:**

- 26 of 27 fields (96%) have tooltips

**Field inventory:**

| Name | Type | Tooltip | Required |
|------|------|---------|----------|
| Nombre del programa | Text | Nombre del programa |  |
| Primer día del programa | Text | Primer día del programa |  |
| Último día del programa | Text | Último día del programa |  |
| Fecha | Text | Fecha |  |
| Nombre del padre/madre/tutor(a) legal (impreso) | Text | Nombre del padre/madre/tutor(a) legal (impreso) |  |
| Nombre del padre/madre/tutor(a) legal | Text | Nombre del padre/madre/tutor(a) legal |  |
| Apellido del padre/madre/tutor(a) legal | Text | Apellido del padre/madre/tutor(a) legal |  |
| Apellido de el/la menor | Text | Apellido de el/la menor |  |
| Nombre de el/la menor | Text | Nombre de el/la menor |  |
| Fecha de nacimiento (mes/día/año) de el/la menor | Text | Fecha de nacimiento (mes/día/año) de el/la menor |  |
| Número de teléfono del padre/madre/tutor(a) legal | Text | Número de teléfono del padre/madre/tutor(a) legal |  |
| Correo electrónico del padre/madre/tutor(a) legal | Text | Correo electrónico del padre/madre/tutor(a) legal |  |
| Dirección del domicilio de el/la menor | Text | Dirección del domicilio de el/la menor |  |
| Nombre del contacto de emergencia | Text | Nombre del contacto de emergencia |  |
| Apellido del contacto de emergencia | Text | Apellido del contacto de emergencia |  |
| Nombre de la persona adicional autorizada a recoger a el/la menor | Text | Nombre de la segunda persona adicional autorizada a recoger a el/la menor |  |
| Apellido de la persona adicional autorizada a recoger a el/la menor | Text | Apellido de la segunda persona adicional autorizada a recoger a el/la menor |  |
| Número de teléfono del contacto de emergencia | Text | Número de teléfono del contacto de emergencia |  |
| Número de teléfono de la persona adicional autorizada a recoger a el/la menor | Text | Número de teléfono de la segunda persona adicional autorizada a recoger a el/la menor |  |
| Firma del padre/madre/tutor(a) legal_es_:signature | Text | Firma del padre/madre/tutor(a) legal |  |
| Consentimiento | Button | (missing) |  |
| Relación con el/la menor del contacto de emergencia | Text | Relación con el/la menor del contacto de emergencia |  |
| Relación con el/la menor de la persona adicional autorizada a recoger a el/la menor | Text | Relación con el/la menor de la persona adicional autorizada a recoger a el/la menor |  |
| Nombre de la segunda persona adicional autorizada a recoger a el/la menor | Text | Nombre de la segunda persona adicional autorizada a recoger a el/la menor |  |
| Apellido de la segunda persona adicional autorizada a recoger a el/la menor | Text | Apellido de la segunda persona adicional autorizada a recoger a el/la menor |  |
| Número de teléfono de la segunda persona adicional autorizada a recoger a el/la menor | Text | Número de teléfono de la segunda persona adicional autorizada a recoger a el/la menor |  |
| Relación con el/la menor de la segunda persona adicional autorizada a recoger a el/la menor | Text | Relación con el/la menor de la segunda persona adicional autorizada a recoger a el/la menor |  |

**Improvement opportunities:**

| Finding | Recommendation |
|---------|---------------|
| Add tooltips to 1 field | Add tooltips to 1 field(s) missing them (WCAG 4.1.2) |
| Consider marking key fields as required so screen readers announce their mandatory status | Consider marking key fields as required so screen readers announce their mandatory status |
| Reorder form fields to interleave with their labels | Reorder form fields to interleave with their labels (currently grouped at end of reading order) |

## Reading Order Assessment

The structure tree defines reading order for 191 elements across 5 page(s).

**Page 1** (39 elements): 35 P, 2 Artifact, 1 Figure, 1 Span

**Page 2** (30 elements): 29 P, 1 Artifact

**Page 3** (31 elements): 15 P, 14 LBody, 2 Artifact

**Page 4** (18 elements): 17 P, 1 Span

**Page 5** (27 elements): 26 P, 1 Artifact

**Reading order issues:**

- Form fields are grouped at the end of the reading order, separated from their labels. Screen readers will read all text first, then encounter all form fields without context.

**Recommendations:**

- Use Auto-Sort Reading Order (Alt+T, R) to interleave form fields with their labels.
- Add headings (H1-H6) to provide navigational landmarks.
- Use the Reading Order overlay (Ctrl+Shift+O) to visually verify element sequence.

## Screen Reader Preview (Simulated)

This section approximates what a screen reader (NVDA, JAWS, VoiceOver) would announce when reading this document from top to bottom. Warnings are inserted inline where a screen reader user would encounter the problem.

```
Image: La "A" de la Universidad de Arizona y el logo de la Oficina de la Protección de Menores    (p.1)
Artifact  (p.1)
Artifact  (p.1)
Artifact  (p.2)
Artifact  (p.3)
List with 14 items
Artifact  (p.3)
Artifact  (p.5)
Text field: Nombre del programa
Text field: Primer día del programa
Text field: Último día del programa
Text field: Nombre de el/la menor
Text field: Apellido de el/la menor
Text field: Fecha de nacimiento (mes/día/año) de el/la menor
Text field: Dirección del domicilio de el/la menor
Text field: Nombre del padre/madre/tutor(a) legal
Text field: Apellido del padre/madre/tutor(a) legal
Text field: Número de teléfono del padre/madre/tutor(a) legal
Text field: Correo electrónico del padre/madre/tutor(a) legal
Text field: Nombre del contacto de emergencia
Text field: Apellido del contacto de emergencia
Text field: Relación con el/la menor del contacto de emergencia
Text field: Número de teléfono del contacto de emergencia
Text field
Text field
Text field: Relación con el/la menor de la persona adicional autorizada a recoger a el/la menor
Text field
Text field: Nombre de la segunda persona adicional autorizada a recoger a el/la menor
Text field: Apellido de la segunda persona adicional autorizada a recoger a el/la menor
Text field: Relación con el/la menor de la segunda persona adicional autorizada a recoger a el/la menor
Text field: Número de teléfono de la segunda persona adicional autorizada a recoger a el/la menor
Text field: Nombre del padre/madre/tutor(a) legal (impreso)
Text field: Firma del padre/madre/tutor(a) legal
Text field: Fecha
Text field
Text field
WARNING: Document title is missing.
WARNING: Document has no headings (H1-H6). Screen reader users cannot navigate by heading.
WARNING: Form field is missing a tooltip (TU entry).
WARNING: 28 of 28 form fields are grouped at reading order positions 138-165, after all page content (positions 0-137). Screen readers encounter all text first, then all fields, making it impossible to associate fields with their labels.
```

## Remediation Priority

### Immediate (Errors -- must fix for PDF/UA conformance)

| Priority | Issue | WCAG | PDF Accessibility Tool | Adobe Acrobat Pro |
|----------|-------|------|----------------------|-------------------|
| 1 | Missing Document Title | 2.4.2 | Open Document Properties (Alt+Enter), Tab to the Title field, type the title, then press Enter to apply.. | File > Properties > Description tab > Title field. |
| 2 | Form Fields Missing Tooltips | 4.1.2 | In the Field Properties panel, Tab to the Tooltip field and enter a descriptive label. | Select the form field, open Properties (Ctrl+E), General tab, and enter a Tooltip.. |
| 3 | Form Fields Detached From Labels | 1.3.2 | Use Auto-Sort Reading Order (Alt+T, R) to interleave form fields with their labels. | In the Tags panel, cut each Form tag (Ctrl+X) and paste it (Ctrl+V) after the P tag that contains its label text. |

### Soon (Warnings -- significant accessibility improvement)

| Priority | Issue | WCAG | PDF Accessibility Tool | Adobe Acrobat Pro |
|----------|-------|------|----------------------|-------------------|
| 1 | No Headings | 2.4.6 | In the Tag Tree, arrow to each section title, press F2, and change the type from P to H1, H2, etc. | In the Tags panel, select each paragraph that should be a heading, open Properties (Ctrl+E), and change Type to H1, H2, etc.. |
| 2 | Non-Standard Tags Without Alt Text | 1.1.1 | In the Tag Tree, arrow to the element, press F2 to add alt text. | In the Tags panel, select the tag, open Properties (Ctrl+E), and enter Alternative Text. |
| 3 | Underscore Fill Patterns | 1.3.1 | In the Tag Tree, navigate to each paragraph with underscore fills. | In the Tags panel, find each P tag containing underscore fills. |
| 4 | Display Document Title Not Set | 2.4.2 | Open Document Properties (Alt+Enter), Tab to the 'Display document title in title bar' checkbox, and press Space to enable it.. | File > Properties > Initial View tab. |

## Accessibility Scorecard

| Metric | Current | After Remediation (Projected) |
|--------|---------|-------------------------------|
| Score | 67/100 | 100/100 |
| Grade | D | A |
| Errors | 3 | 0 |
| Warnings | 9 | 0 |
| Headings | 0 | 5+ (estimated after fix) |
| Form fields with tooltips | 26/27 | 27/27 |
