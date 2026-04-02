"""Tag tree panel for browsing and editing the PDF structure tree.

This panel wraps a wx.TreeCtrl to display the full PDF structure hierarchy.
It supports selection, drag-and-drop reordering, context menus for tag
operations (change type, set alt text, set language, delete), and keyboard
navigation with F2 to rename.

Planned public API:
    TagTreePanel     -- wx.Panel subclass containing a populated wx.TreeCtrl
                        bound to a StructTree model. Fires selection-change
                        events that other panels listen to.
"""
from __future__ import annotations
