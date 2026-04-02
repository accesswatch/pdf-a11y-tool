"""Reading order panel with reorder capability.

This panel shows a flat, ordered list of tagged content regions and lets the
user change their reading sequence using Alt+Up / Alt+Down or drag-and-drop.
Changes are pushed onto the document's CommandStack so they are undoable.

Planned public API:
    ReadingOrderPanel -- wx.Panel subclass with a wx.ListCtrl showing the
                         linearized reading order. Supports keyboard reordering
                         and synchronisation with the Tag Tree selection.
"""
from __future__ import annotations
