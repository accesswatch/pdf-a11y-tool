---
name: audit-epub
description: Scan an ePub document for EPUB Accessibility 1.1 conformance (WCAG 2.x), reading order, navigation, and accessibility metadata.
mode: agent
agent: epub-accessibility
tools:
  - askQuestions
  - readFile
  - runInTerminal
  - listDirectory
---

# ePub Accessibility Audit

Audit an ePub document for EPUB Accessibility 1.1 conformance (WCAG 2.x compliance).

## ePub to Audit

**File:** `${input:epubFile}`

## Instructions

1. Extract the ePub (ZIP archive) to inspect contents
2. Check `content.opf` for schema.org accessibility metadata
3. Verify spine reading order matches logical reading order
4. Check navigation document (`nav.xhtml`) for TOC and landmarks
5. Scan each XHTML content document for heading structure, alt text, table headers, and language
6. Run `epubcheck` validation if available
7. Run Ace by DAISY (`npx @daisy/ace`) if available
8. Generate severity score (0-100, A-F grade)
9. Provide remediation steps for each finding

## Output

Inline accessibility audit report with severity scoring and prioritized remediation.
