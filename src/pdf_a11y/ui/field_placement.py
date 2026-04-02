"""New field placement dialog.

This dialog lets the user choose the type of form field to add, then enter
placement mode where they draw a rectangle on the Page View to define the
field's bounding box. After placement the dialog collects the field name
and tooltip before delegating to FieldFactory for creation.

Planned public API:
    FieldPlacementDialog -- wx.Dialog subclass that walks through field type
                            selection, placement on the page canvas, and
                            initial property entry.
"""
from __future__ import annotations
