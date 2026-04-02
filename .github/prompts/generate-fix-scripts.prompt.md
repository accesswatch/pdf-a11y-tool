---
description: "Generate remediation fix scripts for audit findings"
mode: agent
agent: document-accessibility-wizard
---

Read the most recent `DOCUMENT-ACCESSIBILITY-AUDIT.md` or `PDF-ACCESSIBILITY-AUDIT-FULL.md` report in the workspace root.

For each document with errors:
1. Identify which fixes are auto-fixable via Python scripts (python-docx, openpyxl, python-pptx, pikepdf/qpdf)
2. Generate a Python remediation script that writes to a `-fixed` copy (never overwrite originals)
3. For issues requiring manual intervention, provide step-by-step native application UI instructions

Group output by document. Start each section with a summary of what the script will fix and what needs manual attention.
