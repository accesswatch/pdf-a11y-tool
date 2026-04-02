---
name: scan-inventory
description: Discover and inventory all documents in the workspace. Reports file counts by type, metadata gaps, and delta changes.
mode: agent
agent: document-inventory
tools:
  - readFile
  - runInTerminal
  - listDirectory
---

# Document Inventory

Scan the workspace for all supported document files and build an inventory.

## Scan Target

**Folder:** `${input:folderPath}`

## Instructions

1. Recursively discover all .docx, .xlsx, .pptx, .pdf, and .epub files
2. Skip temporary files (`~$*`, `*.tmp`, `*.bak`) and system directories (`.git`, `node_modules`)
3. Extract metadata for each file: title, author, language, file size, modified date
4. Report:
   - Total file count by type
   - Folder distribution
   - Metadata gaps (missing titles, missing language settings)
   - Files sorted alphabetically within each type group
5. If in a git repository, also report files changed since the last commit

## Output

Structured inventory summary displayed inline.
