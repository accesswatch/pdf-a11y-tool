---
name: config-office-scan
description: Create or edit .a11y-office-config.json to control which accessibility rules are enforced for Word, Excel, and PowerPoint scanning.
mode: agent
agent: office-scan-config
tools:
  - askQuestions
  - readFile
  - createFile
  - replaceStringInFile
---

# Office Scan Configuration Manager

Create and manage `.a11y-office-config.json` files for Word, Excel, and PowerPoint accessibility scanning.

## Action

**Action:** `${input:action}` (create, edit, validate, explain)

## Instructions

### Create New Config

Ask:

- **Profile:** strict (all rules, all severities -- recommended for DRC), moderate (all rules, errors + warnings), minimal (errors only)
- **Document types:** docx, xlsx, pptx (all or specific)

### Edit Existing Config

Read the current `.a11y-office-config.json` and apply requested changes (disable rules, change severity filter, add type-specific settings).

### Validate Config

Check JSON syntax, rule ID validity, and severity filter correctness.

### Explain Config

For each rule, show: Rule ID, what it checks, WCAG criterion, severity, and why it matters.

## Output

Created or updated `.a11y-office-config.json` in the workspace root.
