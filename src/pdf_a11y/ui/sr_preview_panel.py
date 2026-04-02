"""Screen reader linearized preview panel.

This panel shows the text content of the PDF as a screen reader would
announce it, derived from the structure tree via SRLinearizer. Each line
in the list corresponds to a tagged element. Selecting a line highlights
the corresponding element in the Tag Tree and Page View.

Planned public API:
    SRPreviewPanel   -- wx.Panel subclass with a wx.ListBox (or wx.ListCtrl)
                        populated by SRLinearizer. Refreshes on DocChangedEvent
                        and supports bidirectional selection synchronisation.
"""
from __future__ import annotations
