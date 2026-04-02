---
description: "Scan a single document for accessibility issues"
mode: agent
agent: document-accessibility-wizard
---

Scan the file: ${input:filePath:Enter the document path to scan}

Use the MCP `scan_document` tool to auto-detect the file type and run the appropriate scanner. Present findings organized by severity (errors first, then warnings, then tips). Include rule IDs, WCAG criteria, and step-by-step fix instructions using the native application UI.
