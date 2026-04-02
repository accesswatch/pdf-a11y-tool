---
name: config-pdf-scan
description: Create or edit .a11y-pdf-config.json to control which PDF accessibility rules are enforced. Manages PDFUA, PDFBP, and PDFQ rule layers.
mode: agent
agent: pdf-scan-config
tools:
  - askQuestions
  - readFile
  - createFile
  - replaceStringInFile
---

# PDF Scan Configuration Manager

Create and manage `.a11y-pdf-config.json` files for PDF accessibility scanning.

## Action

**Action:** `${input:action}` (create, edit, validate, explain)

## Instructions

### Create New Config

Ask:

- **Profile:** strict (all 3 rule layers -- recommended for government and DRC), moderate (skip pipeline tips), minimal (errors only, for legacy triage)
- **Rule layers:** PDFUA (conformance), PDFBP (best practices), PDFQ (quality/pipeline)

### Edit Existing Config

Read the current `.a11y-pdf-config.json` and apply requested changes (disable rules, change layers, adjust severity filter, set max file size).

### Validate Config

Check JSON syntax, rule ID validity against the three layers, and severity filter correctness.

### Explain Config

For each rule, show: Rule ID, layer, what it checks, WCAG criterion, severity, and why it matters.

## Output

Created or updated `.a11y-pdf-config.json` in the workspace root.
