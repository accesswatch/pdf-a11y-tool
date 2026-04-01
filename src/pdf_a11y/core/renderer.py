"""Page renderer: converts PDF pages to wx.Bitmap using pypdfium2.

Features:
- Render a single page at a given DPI (default 150)
- Return a wx.Bitmap for display
- Zoom support: 50% to 400%
- LRU page cache (default 10 pages)
- Background rendering via worker thread with wx.CallAfter() delivery
- Coordinate mapping between PDF points and screen pixels
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Callable

import pypdfium2 as pdfium
import wx
from PIL import Image


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DPI = 150
MIN_ZOOM = 0.5   # 50%
MAX_ZOOM = 4.0   # 400%
DEFAULT_CACHE_SIZE = 10


# ---------------------------------------------------------------------------
# LRU Cache
# ---------------------------------------------------------------------------

class LRUCache:
    """Least-recently-used cache for rendered bitmaps."""

    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE) -> None:
        self._max_size = max_size
        self._cache: OrderedDict[tuple[int, float], wx.Bitmap] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: tuple[int, float]) -> wx.Bitmap | None:
        with self._lock:
            if key not in self._cache:
                return None
            self._cache.move_to_end(key)
            return self._cache[key]

    def put(self, key: tuple[int, float], bitmap: wx.Bitmap) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)
                self._cache[key] = bitmap

    def invalidate(self, page_index: int) -> None:
        """Remove all cached entries for a specific page."""
        with self._lock:
            keys = [k for k in self._cache if k[0] == page_index]
            for k in keys:
                del self._cache[k]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


# ---------------------------------------------------------------------------
# Page renderer
# ---------------------------------------------------------------------------

class PageRenderer:
    """Renders PDF pages to wx.Bitmap using pypdfium2 with an LRU cache."""

    def __init__(self, cache_size: int = DEFAULT_CACHE_SIZE, dpi: int = DEFAULT_DPI) -> None:
        self._dpi = dpi
        self._cache = LRUCache(cache_size)
        self._doc: pdfium.PdfDocument | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Document management
    # ------------------------------------------------------------------

    def load(self, path: str) -> None:
        """Load a PDF document for rendering."""
        with self._lock:
            if self._doc is not None:
                self._doc.close()
            self._doc = pdfium.PdfDocument(path)
            self._cache.clear()

    def close(self) -> None:
        with self._lock:
            if self._doc is not None:
                self._doc.close()
                self._doc = None
            self._cache.clear()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_page(self, page_index: int, zoom: float = 1.0) -> wx.Bitmap:
        """Render a page synchronously, returning a wx.Bitmap.

        Uses the LRU cache. Zoom is a multiplier (1.0 = 100%).
        """
        zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))
        cache_key = (page_index, zoom)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        bitmap = self._render(page_index, zoom)
        self._cache.put(cache_key, bitmap)
        return bitmap

    def render_page_async(
        self,
        page_index: int,
        zoom: float,
        callback: Callable[[wx.Bitmap], None],
    ) -> None:
        """Render a page on a background thread, delivering the result via wx.CallAfter."""
        zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))
        cache_key = (page_index, zoom)
        cached = self._cache.get(cache_key)
        if cached is not None:
            wx.CallAfter(callback, cached)
            return

        def _worker() -> None:
            bitmap = self._render(page_index, zoom)
            self._cache.put(cache_key, bitmap)
            wx.CallAfter(callback, bitmap)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def _render(self, page_index: int, zoom: float) -> wx.Bitmap:
        """Internal: render a page at the given zoom level."""
        with self._lock:
            if self._doc is None:
                raise ValueError("No document loaded.")
            page = self._doc[page_index]
            scale = (self._dpi / 72.0) * zoom
            bitmap_obj = page.render(scale=scale, rotation=0)
            pil_image = bitmap_obj.to_pil()

        return self._pil_to_wx_bitmap(pil_image)

    @staticmethod
    def _pil_to_wx_bitmap(pil_image: Image.Image) -> wx.Bitmap:
        """Convert a PIL Image to a wx.Bitmap."""
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        width, height = pil_image.size
        wx_image = wx.Image(width, height)
        wx_image.SetData(pil_image.tobytes())
        return wx_image.ConvertToBitmap()

    # ------------------------------------------------------------------
    # Coordinate mapping
    # ------------------------------------------------------------------

    def pdf_point_to_screen(
        self,
        page_index: int,
        pdf_x: float,
        pdf_y: float,
        zoom: float,
        page_height: float,
    ) -> tuple[int, int]:
        """Convert PDF user units (points) to screen pixels at the given zoom.

        PDF coordinates have origin at bottom-left; screen pixels origin is top-left.
        page_height is the height of the page in PDF points (from MediaBox).
        """
        scale = (self._dpi / 72.0) * zoom
        screen_x = int(pdf_x * scale)
        screen_y = int((page_height - pdf_y) * scale)
        return (screen_x, screen_y)

    def screen_to_pdf_point(
        self,
        page_index: int,
        screen_x: int,
        screen_y: int,
        zoom: float,
        page_height: float,
    ) -> tuple[float, float]:
        """Convert screen pixels to PDF user units (points).

        page_height is the height of the page in PDF points.
        """
        scale = (self._dpi / 72.0) * zoom
        pdf_x = screen_x / scale
        pdf_y = page_height - (screen_y / scale)
        return (pdf_x, pdf_y)

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def invalidate_page(self, page_index: int) -> None:
        """Invalidate cached renders for a specific page (call after editing)."""
        self._cache.invalidate(page_index)

    def clear_cache(self) -> None:
        self._cache.clear()
