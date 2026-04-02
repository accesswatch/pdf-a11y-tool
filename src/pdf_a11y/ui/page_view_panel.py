"""Page view panel showing rendered PDF pages.

This panel is the central viewport of the application. It displays a rendered
page bitmap from PageRenderer, supports scroll and zoom, and draws optional
overlays for reading order and tag bounding boxes.

Planned public API:
    PageViewPanel    -- wx.ScrolledWindow subclass displaying the current page
                        bitmap with overlay support. Responds to DocChangedEvent
                        to refresh the rendered page.
"""
from __future__ import annotations
