"""Built-in accessibility checks (pure pikepdf, no external tools required).

This module implements a suite of PDF accessibility checks that run entirely
within Python using pikepdf. Checks cover PDF/UA-1 and WCAG 2.1 Level AA
requirements including structure tree presence, language, title, alt text on
figures, tab order, heading hierarchy, and more.

Planned public API:
    ValidationIssue  -- Dataclass with severity, rule ID, WCAG criterion,
                        description, page number, and object reference.
    BuiltinChecker   -- Runs all built-in checks on a PdfDocument and returns
                        a list[ValidationIssue].
"""
from __future__ import annotations
