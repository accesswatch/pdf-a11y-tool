"""Table header scope editor panel.

This panel presents a spreadsheet-like grid representing the rows and columns
of a selected Table structure element. Users can assign header scope (Column,
Row, Both, None) to TH cells and associate TD cells with their headers.

Planned public API:
    TableEditorPanel -- wx.Panel subclass with a wx.grid.Grid bound to a
                        TableModel. Scope changes are committed as undoable
                        commands on the PdfDocument CommandStack.
"""
from __future__ import annotations
