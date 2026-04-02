"""New tagged PDF creation from scratch.

This module provides functionality to create a minimal, fully-tagged PDF
document from scratch using pikepdf, including the document catalog,
structure tree root, and a single blank page with appropriate media box.

Planned public API:
    create_blank_tagged_pdf(path, title, language) -> pikepdf.Pdf
        -- Creates and saves a new blank PDF/UA-compliant document.
"""
from __future__ import annotations
