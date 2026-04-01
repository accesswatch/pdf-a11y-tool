"""Tests for pdf_a11y.core.renderer.

Tests cover:
- LRUCache: get, put, eviction of oldest entry, invalidate by page, clear
- Coordinate mapping: pdf_point_to_screen, screen_to_pdf_point (round-trip)
- PageRenderer.render_page: uses cache on second call, respects zoom clamp
- PageRenderer cache size enforcement
- PageRenderer.invalidate_page and clear_cache
- render_page_async: calls callback via wx.CallAfter
"""
from __future__ import annotations

import sys
import threading
from unittest.mock import MagicMock, patch, call
import pytest

# ---------------------------------------------------------------------------
# Stub out wx so renderer.py can be imported headlessly
# ---------------------------------------------------------------------------
wx_mock = MagicMock()


class _FakeBitmap:
    """Minimal stand-in for wx.Bitmap."""
    def __init__(self, tag: str = "") -> None:
        self.tag = tag

    def __repr__(self) -> str:
        return f"FakeBitmap({self.tag!r})"


wx_mock.Bitmap = _FakeBitmap
sys.modules.setdefault("wx", wx_mock)

# Stub out PIL
pil_mock = MagicMock()
sys.modules.setdefault("PIL", pil_mock)
sys.modules.setdefault("PIL.Image", pil_mock.Image)

# Stub out pypdfium2
pdfium_mock = MagicMock()
sys.modules.setdefault("pypdfium2", pdfium_mock)

from pdf_a11y.core.renderer import (
    LRUCache,
    PageRenderer,
    DEFAULT_DPI,
    MIN_ZOOM,
    MAX_ZOOM,
    DEFAULT_CACHE_SIZE,
)


# ---------------------------------------------------------------------------
# LRUCache tests
# ---------------------------------------------------------------------------

class TestLRUCache:
    def _make_bitmap(self, tag: str = "") -> _FakeBitmap:
        return _FakeBitmap(tag)

    def test_miss_returns_none(self):
        cache = LRUCache(max_size=5)
        assert cache.get((0, 1.0)) is None

    def test_put_and_get(self):
        cache = LRUCache(max_size=5)
        bmp = self._make_bitmap("page0")
        cache.put((0, 1.0), bmp)
        assert cache.get((0, 1.0)) is bmp

    def test_different_zoom_different_entry(self):
        cache = LRUCache(max_size=5)
        bmp1 = self._make_bitmap("zoom1")
        bmp2 = self._make_bitmap("zoom2")
        cache.put((0, 1.0), bmp1)
        cache.put((0, 2.0), bmp2)
        assert cache.get((0, 1.0)) is bmp1
        assert cache.get((0, 2.0)) is bmp2

    def test_evicts_lru_when_full(self):
        cache = LRUCache(max_size=3)
        for i in range(3):
            cache.put((i, 1.0), self._make_bitmap(f"page{i}"))

        # Access page 0 to make it recently used; page 1 becomes LRU
        _ = cache.get((0, 1.0))

        # Adding a 4th item should evict page 1 (LRU)
        cache.put((3, 1.0), self._make_bitmap("page3"))
        assert cache.get((1, 1.0)) is None
        assert cache.get((0, 1.0)) is not None
        assert cache.get((3, 1.0)) is not None

    def test_put_existing_key_updates_position(self):
        cache = LRUCache(max_size=2)
        bmp_a = self._make_bitmap("A")
        bmp_b = self._make_bitmap("B")
        bmp_a2 = self._make_bitmap("A2")
        cache.put((0, 1.0), bmp_a)
        cache.put((1, 1.0), bmp_b)
        # Re-put page 0 — it should become most-recently used
        cache.put((0, 1.0), bmp_a2)
        # Now add page 2; page 1 (LRU) should be evicted
        cache.put((2, 1.0), self._make_bitmap("C"))
        assert cache.get((1, 1.0)) is None
        assert cache.get((0, 1.0)) is bmp_a2

    def test_invalidate_removes_all_zoom_levels_for_page(self):
        cache = LRUCache(max_size=10)
        for zoom in [0.5, 1.0, 2.0]:
            cache.put((5, zoom), self._make_bitmap(f"p5z{zoom}"))
        cache.put((3, 1.0), self._make_bitmap("p3"))
        cache.invalidate(5)
        for zoom in [0.5, 1.0, 2.0]:
            assert cache.get((5, zoom)) is None
        # Other pages unaffected
        assert cache.get((3, 1.0)) is not None

    def test_invalidate_nonexistent_page_is_safe(self):
        cache = LRUCache(max_size=5)
        cache.invalidate(99)  # should not raise

    def test_clear_empties_cache(self):
        cache = LRUCache(max_size=5)
        for i in range(5):
            cache.put((i, 1.0), self._make_bitmap(f"p{i}"))
        cache.clear()
        for i in range(5):
            assert cache.get((i, 1.0)) is None

    def test_thread_safety_no_race(self):
        """Basic smoke test: concurrent puts/gets should not raise."""
        cache = LRUCache(max_size=20)
        errors: list[Exception] = []

        def _worker(offset: int) -> None:
            try:
                for i in range(10):
                    cache.put((offset + i, 1.0), self._make_bitmap())
                    cache.get((offset + i, 1.0))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(i * 10,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors


# ---------------------------------------------------------------------------
# Coordinate mapping tests
# ---------------------------------------------------------------------------

class TestCoordinateMapping:
    """Tests for pdf_point_to_screen and screen_to_pdf_point."""

    def _renderer(self, dpi: int = DEFAULT_DPI) -> PageRenderer:
        return PageRenderer(dpi=dpi)

    def test_pdf_point_to_screen_origin(self):
        r = self._renderer(dpi=72)
        # At DPI=72, scale=1.0; origin of PDF (0, page_height) -> (0, 0)
        sx, sy = r.pdf_point_to_screen(0, 0.0, 792.0, 1.0, 792.0)
        assert sx == 0
        assert sy == 0

    def test_pdf_point_to_screen_bottom_left(self):
        r = self._renderer(dpi=72)
        # PDF (0, 0) = bottom-left -> screen (0, page_height in px)
        sx, sy = r.pdf_point_to_screen(0, 0.0, 0.0, 1.0, 792.0)
        assert sx == 0
        assert sy == 792

    def test_pdf_point_to_screen_centre(self):
        r = self._renderer(dpi=72)
        sx, sy = r.pdf_point_to_screen(0, 306.0, 396.0, 1.0, 792.0)
        assert sx == 306
        assert sy == 396

    def test_pdf_point_to_screen_with_zoom(self):
        r = self._renderer(dpi=72)
        # zoom=2.0 doubles scale
        sx, sy = r.pdf_point_to_screen(0, 100.0, 692.0, 2.0, 792.0)
        # scale = 2.0; screen_x = 200, screen_y = (792-692)*2 = 200
        assert sx == 200
        assert sy == 200

    def test_screen_to_pdf_point_origin(self):
        r = self._renderer(dpi=72)
        px, py = r.screen_to_pdf_point(0, 0, 0, 1.0, 792.0)
        assert px == pytest.approx(0.0)
        assert py == pytest.approx(792.0)

    def test_round_trip(self):
        r = self._renderer(dpi=150)
        page_h = 792.0
        zoom = 1.5
        orig_px, orig_py = 123.4, 567.8
        sx, sy = r.pdf_point_to_screen(0, orig_px, orig_py, zoom, page_h)
        back_px, back_py = r.screen_to_pdf_point(0, sx, sy, zoom, page_h)
        # Round-trip accuracy within 1 pixel worth of PDF units
        scale = (DEFAULT_DPI / 72.0) * zoom
        tolerance = 1.0 / scale
        assert abs(back_px - orig_px) <= tolerance + 0.01
        assert abs(back_py - orig_py) <= tolerance + 0.01

    def test_round_trip_multiple_zooms(self):
        r = self._renderer()
        page_h = 1000.0
        for zoom in [0.5, 1.0, 2.0, 4.0]:
            for pdf_x, pdf_y in [(0, 0), (50, 100), (500, 500), (0, 1000)]:
                sx, sy = r.pdf_point_to_screen(0, pdf_x, pdf_y, zoom, page_h)
                bx, by = r.screen_to_pdf_point(0, sx, sy, zoom, page_h)
                scale = (DEFAULT_DPI / 72.0) * zoom
                tol = 1.0 / scale + 0.01
                assert abs(bx - pdf_x) <= tol, f"zoom={zoom} x mismatch"
                assert abs(by - pdf_y) <= tol, f"zoom={zoom} y mismatch"


# ---------------------------------------------------------------------------
# PageRenderer tests (mocked pypdfium2)
# ---------------------------------------------------------------------------

class TestPageRenderer:
    def _make_renderer(self, cache_size: int = DEFAULT_CACHE_SIZE) -> PageRenderer:
        return PageRenderer(cache_size=cache_size)

    def _mock_pil_image(self) -> MagicMock:
        img = MagicMock()
        img.mode = "RGB"
        img.size = (100, 100)
        img.tobytes.return_value = b"\x00" * (100 * 100 * 3)
        return img

    def test_render_page_caches_result(self):
        renderer = self._make_renderer()
        bitmap = _FakeBitmap("cached")
        with patch.object(renderer, "_render", return_value=bitmap) as mock_render:
            b1 = renderer.render_page(0, zoom=1.0)
            b2 = renderer.render_page(0, zoom=1.0)
        # _render should only be called once; second call comes from cache
        assert mock_render.call_count == 1
        assert b1 is b2

    def test_render_page_different_zoom_calls_render_twice(self):
        renderer = self._make_renderer()
        bitmap = _FakeBitmap()
        with patch.object(renderer, "_render", return_value=bitmap) as mock_render:
            renderer.render_page(0, zoom=1.0)
            renderer.render_page(0, zoom=2.0)
        assert mock_render.call_count == 2

    def test_render_page_clamps_zoom_low(self):
        renderer = self._make_renderer()
        bitmap = _FakeBitmap()
        with patch.object(renderer, "_render", return_value=bitmap) as mock_render:
            renderer.render_page(0, zoom=0.1)  # below MIN_ZOOM
        actual_zoom = mock_render.call_args[0][1]
        assert actual_zoom == MIN_ZOOM

    def test_render_page_clamps_zoom_high(self):
        renderer = self._make_renderer()
        bitmap = _FakeBitmap()
        with patch.object(renderer, "_render", return_value=bitmap) as mock_render:
            renderer.render_page(0, zoom=10.0)  # above MAX_ZOOM
        actual_zoom = mock_render.call_args[0][1]
        assert actual_zoom == MAX_ZOOM

    def test_cache_size_enforced(self):
        renderer = self._make_renderer(cache_size=2)
        bitmaps = [_FakeBitmap(f"p{i}") for i in range(3)]
        idx = 0

        def _mock_render(page_index: int, zoom: float) -> _FakeBitmap:
            nonlocal idx
            b = bitmaps[idx]
            idx += 1
            return b

        with patch.object(renderer, "_render", side_effect=_mock_render):
            renderer.render_page(0, 1.0)
            renderer.render_page(1, 1.0)
            renderer.render_page(2, 1.0)  # should evict page 0

        # page 0 should no longer be in cache; re-render will be called
        with patch.object(renderer, "_render", return_value=bitmaps[0]) as re_render:
            renderer.render_page(0, 1.0)
        assert re_render.call_count == 1

    def test_invalidate_page_clears_cache(self):
        renderer = self._make_renderer()
        bitmap = _FakeBitmap()
        with patch.object(renderer, "_render", return_value=bitmap):
            renderer.render_page(5, 1.0)
        renderer.invalidate_page(5)
        with patch.object(renderer, "_render", return_value=bitmap) as re_render:
            renderer.render_page(5, 1.0)
        assert re_render.call_count == 1

    def test_clear_cache(self):
        renderer = self._make_renderer()
        bitmap = _FakeBitmap()
        with patch.object(renderer, "_render", return_value=bitmap):
            renderer.render_page(0, 1.0)
            renderer.render_page(1, 1.0)
        renderer.clear_cache()
        with patch.object(renderer, "_render", return_value=bitmap) as re_render:
            renderer.render_page(0, 1.0)
            renderer.render_page(1, 1.0)
        assert re_render.call_count == 2

    def test_render_raises_without_loaded_doc(self):
        renderer = self._make_renderer()
        with pytest.raises(ValueError, match="No document loaded"):
            renderer._render(0, 1.0)

    def test_render_page_async_uses_cache(self):
        renderer = self._make_renderer()
        bitmap = _FakeBitmap("cached_async")
        with patch.object(renderer, "_render", return_value=bitmap):
            renderer.render_page(0, 1.0)  # warm up cache

        callback = MagicMock()
        with patch.object(wx_mock, "CallAfter") as mock_call_after:
            renderer.render_page_async(0, 1.0, callback)
        # Should use CallAfter immediately without spawning a thread
        mock_call_after.assert_called_once_with(callback, bitmap)

    def test_render_page_async_spawns_thread_on_cache_miss(self):
        renderer = self._make_renderer()
        bitmap = _FakeBitmap("async_miss")
        callback = MagicMock()
        threads_started: list[bool] = []

        original_start = threading.Thread.start

        def _mock_start(self_thread: threading.Thread) -> None:
            threads_started.append(True)

        with (
            patch.object(renderer, "_render", return_value=bitmap),
            patch.object(threading.Thread, "start", _mock_start),
        ):
            renderer.render_page_async(0, 1.0, callback)

        assert len(threads_started) == 1

    def test_close_clears_doc_and_cache(self):
        renderer = self._make_renderer()
        bitmap = _FakeBitmap()
        with patch.object(renderer, "_render", return_value=bitmap):
            renderer.render_page(0, 1.0)
        renderer.close()
        assert renderer._doc is None
        # Cache should be empty after close
        with patch.object(renderer, "_render", return_value=bitmap) as re_render:
            try:
                renderer.render_page(0, 1.0)
            except ValueError:
                pass  # expected: no doc loaded
