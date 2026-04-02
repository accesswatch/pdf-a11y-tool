---
description: "Implement a specific phase from the PROJECT-PLAN.md roadmap. Reads the plan, identifies stub files, and generates implementation code plus tests."
agent: "agent"
argument-hint: "Phase number (e.g., 3, 3.5, 4)"
tools: [read, edit, search, execute]
---
# Implement Phase

Implement phase {{ input }} from the project roadmap.

## Steps

1. Read [PROJECT-PLAN.md](../../PROJECT-PLAN.md) and locate the section for phase {{ input }}
2. Identify all stub files listed for that phase (files with only `from __future__ import annotations` and a docstring)
3. Read the "Planned public API" in each stub's docstring to understand the interface contract
4. Read any completed modules that the phase depends on (check the Phase Dependencies Map in PROJECT-PLAN.md)
5. Implement each module following these rules:
   - `from __future__ import annotations` at the top of every file
   - Core modules (`src/pdf_a11y/core/`): no wx imports, use Command pattern for edits
   - UI modules (`src/pdf_a11y/ui/`): wxPython panels with keyboard navigation and screen reader labels
   - Match the code style: 100-char lines, type hints, module docstring with "Public API:" section
6. Create or update tests in `tests/test_<module>.py` for each implemented module
7. Run `ruff check src tests` and `pytest` to verify everything passes
8. Summarize what was implemented and what the next phase should tackle
