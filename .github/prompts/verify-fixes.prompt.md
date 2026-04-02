---
description: "Verify accessibility fixes by comparing before/after scans"
mode: agent
agent: document-accessibility-wizard
---

Find all `-fixed` documents in the workspace (e.g., `report-fixed.docx`, `data-fixed.xlsx`, `slides-fixed.pptx`, `manual-fixed.pdf`, `book-fixed.epub`).

For each fixed document:
1. Locate the corresponding original file
2. Use verify_fix to compare before/after scan results
3. Report: score change, resolved issues, remaining issues, any regressions

Generate a summary table at the end showing all documents, their before/after scores, and fix success rates. Flag any regressions prominently.
