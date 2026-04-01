"""Form field property editor panel.

This panel shows and edits all properties of a selected AcroForm field,
including the field name, tooltip (TU entry), required/read-only flags,
default value, and appearance settings. Changes are committed through the
PdfDocument CommandStack.

Planned public API:
    FieldPropertiesPanel -- wx.Panel subclass with a property grid or labelled
                            controls for all field attributes. Automatically
                            refreshes when a new field is selected in the
                            FieldsListPanel.
"""
from __future__ import annotations
