"""Structure tree to screen reader linearized text converter.

This module traverses the PDF structure tree and produces a flat, ordered list
of text chunks that approximates what a screen reader would announce. It is
used by the Screen Reader Preview panel (Phase 3.5).

Planned public API:
    SRLine           -- Dataclass for a single linearized text entry with tag context.
    SRLinearizer     -- Walks the StructTree and produces a list[SRLine].
"""
from __future__ import annotations
