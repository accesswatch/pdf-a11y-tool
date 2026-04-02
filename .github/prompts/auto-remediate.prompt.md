---
description: "Run scan-fix-verify loop on documents with auto-remediation"
mode: agent
agent: document-accessibility-wizard
---

Run the full scan-fix-verify remediation loop on documents in this workspace:

1. Scan all supported documents (.docx, .xlsx, .pptx, .pdf, .epub) to identify accessibility issues
2. For each document with auto-fixable issues, use the appropriate fix tool (fix_word_document, fix_excel_workbook, fix_powerpoint_pres, fix_pdf_document, fix_epub_document)
3. Re-scan each fixed document using verify_fix to confirm improvements
4. Report the delta: what was fixed, what remains, any regressions

If the workspace has an existing audit report, use it to skip unchanged files. Apply up to 3 fix-verify iterations per document to catch cascading fixes. Update `.a11y-remediation-knowledge.json` with results.
