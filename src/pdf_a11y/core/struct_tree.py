"""Structure tree wrapper for PDF tag trees.

This module provides the in-memory model that bridges pikepdf PDF dictionaries
and the UI panels. It will contain the StructNode dataclass and tree operations
including change_tag, set_alt_text, reorder_children, and related helpers.

Planned public API:
    StructNode       -- Dataclass representing a single node in the structure tree.
    StructTree       -- Wrapper around the PDF /StructTreeRoot that provides
                        high-level read/write operations over the tag hierarchy.
"""
from __future__ import annotations
