"""Content stream parser for marked content operations.

This module handles parsing of PDF content streams to identify and manipulate
marked content sequences (BMC/EMC, BDC/EMC markers). It is used by the
Phase 9 content stream tagging feature to associate content stream objects
with structure tree nodes.

Planned public API:
    MarkedContentRegion  -- Dataclass representing a BMC/BDC...EMC region.
    ContentStreamParser  -- Parses a page's content stream into marked content regions.
"""
from __future__ import annotations
