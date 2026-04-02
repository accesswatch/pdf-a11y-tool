"""Form field read/write model for AcroForm fields.

This module provides a high-level interface for reading and writing PDF AcroForm
fields via pikepdf. It abstracts over field types (text, checkbox, radio,
dropdown, listbox, button) and exposes a uniform property API.

Planned public API:
    FieldType        -- Enum of supported AcroForm field types.
    FormField        -- Dataclass wrapping an AcroForm field dictionary.
    FormModel        -- Aggregates all fields in a document and provides
                        CRUD operations.
"""
from __future__ import annotations
