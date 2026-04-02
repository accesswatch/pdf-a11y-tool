"""Audit report generation (Markdown and CSV).

This module takes a list of ValidationIssue objects and renders them as
human-readable Markdown or machine-readable CSV reports, suitable for
export or inclusion in documentation.

Planned public API:
    ReportFormat     -- Enum: MARKDOWN or CSV.
    ReportGenerator  -- Accepts a list[ValidationIssue] and a document path;
                        produces a formatted report string or writes to a file.
"""
from __future__ import annotations
