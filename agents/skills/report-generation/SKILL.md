---
name: report-generation
description: Audit report formatting, severity scoring, scorecard computation, and compliance export for document accessibility audits. Use when generating DOCUMENT-ACCESSIBILITY-AUDIT.md reports, computing document severity scores (0-100 with A-F grades), creating VPAT/ACR compliance exports, or formatting remediation priorities.
---

# Report Generation

## Canonical Report Generator

The reference implementation is `tools/report_md.py`. It defines:

- **`RULE_REFERENCE`** dict (46 rules) — each entry maps a rule ID to `(standard, WCAG, severity, Matterhorn checkpoint, description)`. This is the authoritative rule metadata.
- **15 section renderers** — `_render_header`, `_render_executive_summary`, `_render_quick_fixes`, `_render_manual_review`, `_render_additional_improvements`, `_render_summary_table`, `_render_priority_plan`, `_render_whats_working`, `_render_time_estimate`, `_render_final_assessment`, `_render_appendix_a` through `_render_appendix_e`.
- **`generate_report()`** — composes all sections into the final markdown.

When generating reports, follow the structure and tone of `report_md.py` output. See the "Report Tone and Writing Standard" section in `document-accessibility-wizard.agent.md` for the 10 tone principles and dual-audience layering approach.

## Report File

Default output: `DOCUMENT-ACCESSIBILITY-AUDIT.md` in the project root.

## Required Sections

Every audit report MUST include these sections (mapped to `report_md.py` renderers):

1. **Header** (`_render_header`) — date, audience, document count, overall score/grade
2. **Executive Summary** (`_render_executive_summary`) — grade-contextualized intro, main issues, what is working
3. **Quick Fixes** (`_render_quick_fixes`) — numbered "Fix N" blocks per issue type with per-format steps and "Why this matters"
4. **Manual Review** (`_render_manual_review`) — reading order ALWAYS FIRST, then color contrast, then PDF checker
5. **Additional Improvements** (`_render_additional_improvements`) — bookmarks, speaker notes, PDF/UA id, heading structure
6. **Summary Table** (`_render_summary_table`) — per-rule frequencies
7. **Priority Action Plan** (`_render_priority_plan`) — Sprint 1/2/3 ordering
8. **What Is Already Working** (`_render_whats_working`) — explicit passing checks
9. **Time Estimate** (`_render_time_estimate`) — per-fix and cumulative
10. **Final Assessment** (`_render_final_assessment`) — projected scores after fixes
11. **Appendix A** (`_render_appendix_a`) — scoring methodology
12. **Appendix B** (`_render_appendix_b`) — per-file detail
13. **Appendix C** (`_render_appendix_c`) — WCAG mapping
14. **Appendix D** (`_render_appendix_d`) — rule reference
15. **Appendix E** (`_render_appendix_e`) — glossary

### Optional Sections (include when applicable)

- **Template Analysis** - when batch scanning detects shared templates
- **Comparison Report** - when re-scanning against a baseline
- **CI/CD Recommendations** - when no config files exist

## Severity Scoring Formula

```text
Document Score = 100 - (sum of weighted findings)

Weights:
  Error (high confidence):   -10 points
  Error (medium confidence):  -7 points
  Error (low confidence):     -3 points
  Warning (high confidence):  -3 points
  Warning (medium confidence):-2 points
  Warning (low confidence):   -1 point
  Tips:                        0 points

Floor: 0 (minimum score)
```

## Score Grades

| Score | Grade | Meaning |
|-------|-------|---------|
| 90-100 | A | Excellent - minor or no issues |
| 75-89 | B | Good - some warnings, few errors |
| 50-74 | C | Needs Work - multiple errors |
| 25-49 | D | Poor - significant accessibility barriers |
| 0-24 | F | Failing - critical barriers, likely unusable with AT |

## Organization Modes

| Mode | Description | Best For |
|------|-------------|----------|
| By file | Group all issues under each document | Small batches (< 10 files) |
| By issue type | Group all instances of each rule across documents | Seeing patterns |
| By severity | Critical first, then serious, moderate, minor | Prioritizing fixes |

## VPAT/ACR Compliance Export

### Conformance Levels

| Level | Criteria |
|-------|----------|
| Supports | No findings for this WCAG criterion across any document |
| Partially Supports | Some documents pass, some fail |
| Does Not Support | All or most documents fail |
| Not Applicable | Criterion does not apply to scanned document types |

### Supported VPAT Editions

- **VPAT 2.5 (WCAG)** - maps to WCAG 2.2 criteria
- **VPAT 2.5 (508)** - maps to Revised Section 508 standards
- **VPAT 2.5 (EN 301 549)** - maps to EU accessibility directive
- **VPAT 2.5 (INT)** - International edition (all three combined)

## Remediation Tracking

When comparing against a baseline audit report:

| Status | Meaning |
|--------|---------|
| Fixed | Issue was in previous report but is now resolved |
| New | Issue was not in previous report but appears now |
| Persistent | Issue remains from previous report |
| Regressed | Issue was previously fixed but has returned |

### Progress Metrics

- Issue reduction percentage: `(fixed / previous_total) * 100`
- Score change: `current_score - previous_score`
- Documents improved: count of documents with higher scores
