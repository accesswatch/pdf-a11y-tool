---
description: "Audit markdown documentation for accessibility"
mode: agent
agent: markdown-a11y-assistant
---

Scan all markdown (.md) files in this workspace for accessibility issues. Check:
- Ambiguous or non-descriptive link text ("click here", "read more", "here")
- Missing or inadequate image alt text
- Heading hierarchy violations (skipped levels, missing h1)
- Tables without descriptions or header context
- Emoji usage (remove or translate to English text equivalent)
- Mermaid/ASCII diagrams (replace with accessible text alternatives)
- Em-dashes without surrounding spaces
- Broken anchor links

Generate a `MARKDOWN-ACCESSIBILITY-AUDIT.md` report with severity scores and prioritized remediation guidance. Auto-fix what can be fixed safely and present human-judgment fixes for approval.
