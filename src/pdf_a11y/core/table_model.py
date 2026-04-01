"""Table structure grid model.

This module provides an in-memory grid model for PDF table structure elements,
mapping TH/TD cells to their row/column positions and header scope attributes.
It is used by the Table Header Scope Editor panel.

Planned public API:
    CellRole         -- Enum: HEADER or DATA.
    TableCell        -- Dataclass for a single table cell with span and scope info.
    TableModel       -- Grid model constructed from a Table StructNode; supports
                        get_cell(), set_scope(), set_header_id(), and merge operations.
"""
from __future__ import annotations
