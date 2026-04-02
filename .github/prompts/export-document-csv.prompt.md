---
name: export-document-csv
description: Export document accessibility audit findings to CSV format with severity scoring, WCAG mapping, and remediation help links.
mode: agent
agent: document-csv-reporter
tools:
  - askQuestions
  - readFile
  - createFile
---

# Export Document Audit to CSV

Export findings from the most recent `DOCUMENT-ACCESSIBILITY-AUDIT.md` (or `PDF-ACCESSIBILITY-AUDIT-FULL.md`) to structured CSV files.

## Instructions

1. Read the most recent audit report in the workspace root
2. Parse all findings with rule IDs, severities, file paths, and WCAG criteria
3. Generate three CSV files:
   - `DOCUMENT-ACCESSIBILITY-FINDINGS.csv` -- one row per issue instance
   - `DOCUMENT-ACCESSIBILITY-SCORECARD.csv` -- one row per audited document
   - `DOCUMENT-ACCESSIBILITY-REMEDIATION.csv` -- prioritized fix plan with ROI scoring
4. Include Microsoft Office and Adobe PDF help URLs for each finding
5. Include WCAG understanding document URLs

Load the `help-url-reference` skill for URL mappings.

## Output

All CSV files written to the workspace root with UTF-8 BOM encoding for Excel compatibility.
