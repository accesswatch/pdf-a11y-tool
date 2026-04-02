---
name: config-epub-scan
description: Create or edit .a11y-epub-config.json to control which ePub accessibility rules are enforced. Manages EPUB Accessibility 1.1 rules and severity filters.
mode: agent
agent: epub-scan-config
tools:
  - askQuestions
  - readFile
  - createFile
  - replaceStringInFile
---

# ePub Scan Configuration Manager

Create and manage `.a11y-epub-config.json` files for ePub accessibility scanning.

## Action

**Action:** `${input:action}` (create, edit, validate, explain)

## Instructions

### Create New Config

Ask:

- **Profile:** strict (all rules), moderate (errors + warnings), minimal (errors only)
- **EPUB standard focus:** EPUB Accessibility 1.1, WCAG 2.2 mapping, or both

### Edit Existing Config

Read the current `.a11y-epub-config.json` and apply requested changes (disable rules, change severity filter).

### Validate Config

Check JSON syntax, rule ID validity (EPUB-E*, EPUB-W*, EPUB-T*), and severity filter correctness.

### Explain Config

For each rule, show: Rule ID, what it checks, EPUB/WCAG criterion, severity, and why it matters.

## Output

Created or updated `.a11y-epub-config.json` in the workspace root.
