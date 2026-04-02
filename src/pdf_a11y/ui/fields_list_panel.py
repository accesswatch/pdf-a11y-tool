"""Form fields list and tab order panel.

This panel lists all AcroForm fields in the current PDF with their page,
name, type, tooltip, and required status. It supports reordering the tab
order (which maps to the field array order in AcroForm) via Alt+Up/Down.

Planned public API:
    FieldsListPanel  -- wx.Panel subclass with a wx.ListCtrl showing all form
                        fields. Tab order changes are committed as undoable
                        commands. Double-click opens the field properties panel.
"""
from __future__ import annotations
