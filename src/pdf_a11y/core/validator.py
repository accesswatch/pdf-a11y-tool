"""veraPDF integration (optional, requires Java 11+).

This module invokes the veraPDF CLI tool as a subprocess and parses its XML
output into a list of ValidationIssue objects. When veraPDF is not installed
or Java is unavailable, the validator gracefully degrades.

Planned public API:
    VeraPdfValidator -- Locates veraPDF, runs a check on a PDF path, and returns
                        a list[ValidationIssue].
    is_available()   -- Returns True if veraPDF and Java are on the PATH.
"""
from __future__ import annotations
