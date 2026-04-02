"""Document metadata editor panel.

This panel provides editable fields for the core document metadata stored in
the PDF /Info dictionary and the /Catalog: Title, Author, Subject, Creator,
Language (BCP 47). Changes are written through PdfDocument property setters
and are undoable via the CommandStack.

Planned public API:
    DocPropertiesPanel -- wx.Panel subclass with labelled text controls for
                          each metadata field. Synchronises with the document
                          model on DocChangedEvent.
"""
from __future__ import annotations
