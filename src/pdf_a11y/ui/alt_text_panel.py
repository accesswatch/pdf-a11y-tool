"""Alt text editor panel for images.

This panel displays a thumbnail grid of all images found in the current PDF
and allows the user to view and edit the alternative text (Alt attribute) for
each figure element. It is backed by ImageExtractor and writes changes through
PdfDocument commands.

Planned public API:
    AltTextPanel     -- wx.Panel subclass with a thumbnail list on the left and
                        an editable alt text field on the right. Indicates
                        images missing alt text with a warning icon.
"""
from __future__ import annotations
