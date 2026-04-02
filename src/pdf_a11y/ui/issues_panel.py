"""Accessibility findings list panel.

This panel shows the results of the most recent accessibility check run,
listing each ValidationIssue with its severity, rule ID, WCAG criterion,
description, and page reference. Double-clicking an issue navigates to the
offending element in the Tag Tree and Page View.

Planned public API:
    IssuesPanel      -- wx.Panel subclass wrapping a wx.ListCtrl populated
                        from a list[ValidationIssue]. Supports sorting by
                        column and filtering by severity.
"""
from __future__ import annotations
