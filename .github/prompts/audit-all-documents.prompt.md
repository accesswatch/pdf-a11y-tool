---
description: "Scan all documents in this workspace and generate a full accessibility audit report"
mode: agent
agent: document-accessibility-wizard
---

Scan all documents in the current workspace root folder (`s:\pdf`). Include every `.pdf`, `.docx`, `.xlsx`, and `.pptx` file. Skip temp files (`~$*`), `.zip` archives, and anything inside `.vscode/`, `.git/`, `.mypy_cache/`, or `.history/`.

Use the MCP `scan_folder` tool to scan the entire folder, then delegate to format-specific sub-agents for detailed analysis. Generate the consolidated report as `DOCUMENT-ACCESSIBILITY-AUDIT.md` following the report tone standard.
