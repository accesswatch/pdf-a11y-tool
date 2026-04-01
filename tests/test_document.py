"""Comprehensive tests for pdf_a11y.core.document.

Tests cover:
- Open/close operations
- Page count and dimensions
- Metadata read/write (title, author, subject, language)
- CommandStack push, undo, redo, clear
- Dirty flag tracking
- can_undo, can_redo properties
- CompoundCommand execution and undo
- Save / save_as operations
- Event notification (using a mock sink)
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

# ---------------------------------------------------------------------------
# Isolate wx before importing the module under test
# ---------------------------------------------------------------------------

# Create a minimal wx mock so document.py can be imported without a display
wx_mock = MagicMock()
wx_mock.EvtHandler = object  # so isinstance checks work against plain object
sys.modules.setdefault("wx", wx_mock)
sys.modules.setdefault("wx.lib", MagicMock())
sys.modules.setdefault("wx.lib.newevent", MagicMock())

# Patch wx.lib.newevent.NewEvent to return distinct sentinel objects
_doc_changed_evt = MagicMock(name="DocChangedEvent")
_evt_doc_changed = MagicMock(name="EVT_DOC_CHANGED")
_doc_closed_evt = MagicMock(name="DocClosedEvent")
_evt_doc_closed = MagicMock(name="EVT_DOC_CLOSED")

wx_mock.lib.newevent.NewEvent.side_effect = [
    (_doc_changed_evt, _evt_doc_changed),
    (_doc_closed_evt, _evt_doc_closed),
]

import importlib
import pdf_a11y.core.document as doc_mod

# After import, reload the side_effect so the module-level NewEvent calls ran
# and use the real bound names from the module
DocChangedEvent = doc_mod.DocChangedEvent
DocClosedEvent = doc_mod.DocClosedEvent
PdfDocument = doc_mod.PdfDocument
Command = doc_mod.Command
CompoundCommand = doc_mod.CompoundCommand
CommandStack = doc_mod.CommandStack


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _ToggleCommand(Command):
    """A simple test command that toggles a list value."""

    def __init__(self, lst: list[int], value: int) -> None:
        self._lst = lst
        self._value = value

    @property
    def description(self) -> str:
        return f"Toggle {self._value}"

    def execute(self) -> None:
        self._lst.append(self._value)

    def undo(self) -> None:
        self._lst.remove(self._value)


# ---------------------------------------------------------------------------
# CommandStack tests
# ---------------------------------------------------------------------------

class TestCommandStack:
    def test_initial_state(self):
        stack = CommandStack()
        assert not stack.can_undo
        assert not stack.can_redo
        assert stack.undo_description is None
        assert stack.redo_description is None

    def test_push_executes_command(self):
        stack = CommandStack()
        log: list[int] = []
        cmd = _ToggleCommand(log, 1)
        stack.push(cmd)
        assert log == [1]
        assert stack.can_undo
        assert not stack.can_redo

    def test_undo(self):
        stack = CommandStack()
        log: list[int] = []
        cmd = _ToggleCommand(log, 1)
        stack.push(cmd)
        result = stack.undo()
        assert result is cmd
        assert log == []
        assert not stack.can_undo
        assert stack.can_redo

    def test_redo(self):
        stack = CommandStack()
        log: list[int] = []
        cmd = _ToggleCommand(log, 42)
        stack.push(cmd)
        stack.undo()
        result = stack.redo()
        assert result is cmd
        assert log == [42]
        assert stack.can_undo
        assert not stack.can_redo

    def test_push_clears_redo_stack(self):
        stack = CommandStack()
        log: list[int] = []
        stack.push(_ToggleCommand(log, 1))
        stack.undo()
        assert stack.can_redo
        stack.push(_ToggleCommand(log, 2))
        assert not stack.can_redo

    def test_undo_empty_returns_none(self):
        stack = CommandStack()
        assert stack.undo() is None

    def test_redo_empty_returns_none(self):
        stack = CommandStack()
        assert stack.redo() is None

    def test_max_size_enforced(self):
        stack = CommandStack(max_size=3)
        log: list[int] = []
        for i in range(5):
            stack.push(_ToggleCommand(log, i))
        # Only 3 commands remain in the undo stack
        count = 0
        while stack.can_undo:
            stack.undo()
            count += 1
        assert count == 3

    def test_clear(self):
        stack = CommandStack()
        log: list[int] = []
        stack.push(_ToggleCommand(log, 1))
        stack.undo()
        stack.clear()
        assert not stack.can_undo
        assert not stack.can_redo

    def test_undo_description(self):
        stack = CommandStack()
        log: list[int] = []
        cmd = _ToggleCommand(log, 99)
        stack.push(cmd)
        assert stack.undo_description == "Toggle 99"

    def test_redo_description(self):
        stack = CommandStack()
        log: list[int] = []
        cmd = _ToggleCommand(log, 7)
        stack.push(cmd)
        stack.undo()
        assert stack.redo_description == "Toggle 7"


# ---------------------------------------------------------------------------
# CompoundCommand tests
# ---------------------------------------------------------------------------

class TestCompoundCommand:
    def test_execute_all_in_order(self):
        log: list[int] = []
        cmds = [_ToggleCommand(log, i) for i in range(3)]
        compound = CompoundCommand(cmds, "batch")
        compound.execute()
        assert log == [0, 1, 2]

    def test_undo_all_in_reverse(self):
        log: list[int] = []
        cmds = [_ToggleCommand(log, i) for i in range(3)]
        compound = CompoundCommand(cmds, "batch")
        compound.execute()
        compound.undo()
        assert log == []

    def test_description(self):
        compound = CompoundCommand([], "my batch")
        assert compound.description == "my batch"


# ---------------------------------------------------------------------------
# PdfDocument tests -- no wx event sink
# ---------------------------------------------------------------------------

class TestPdfDocumentBasic:
    """Tests that do not require an open file."""

    def test_initial_state(self):
        doc = PdfDocument()
        assert not doc.is_open
        assert doc.path is None
        assert not doc.is_dirty
        assert doc.page_count == 0

    def test_pdf_raises_when_closed(self):
        doc = PdfDocument()
        with pytest.raises(ValueError, match="No document open"):
            _ = doc.pdf

    def test_get_page_raises_when_closed(self):
        doc = PdfDocument()
        with pytest.raises(ValueError):
            doc.get_page(0)

    def test_save_raises_without_path(self):
        doc = PdfDocument()
        with pytest.raises(ValueError, match="No file path"):
            doc.save()

    def test_save_as_raises_when_closed(self):
        doc = PdfDocument()
        with pytest.raises(ValueError, match="No document open"):
            doc.save_as("/tmp/out.pdf")

    def test_title_returns_empty_when_closed(self):
        doc = PdfDocument()
        assert doc.title == ""

    def test_language_returns_empty_when_closed(self):
        doc = PdfDocument()
        assert doc.language == ""

    def test_language_raises_when_closed(self):
        doc = PdfDocument()
        with pytest.raises(ValueError):
            doc.language = "en-US"


class TestPdfDocumentWithFile:
    """Tests that require an open PDF file."""

    def test_open_sets_properties(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        assert doc.is_open
        assert doc.path == minimal_pdf
        assert not doc.is_dirty
        assert doc.page_count == 1

    def test_open_with_string_path(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(str(minimal_pdf))
        assert doc.path == minimal_pdf

    def test_close_resets_state(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        doc.close()
        assert not doc.is_open
        assert doc.path is None
        assert not doc.is_dirty
        assert doc.page_count == 0

    def test_page_count_two_pages(self, two_page_pdf):
        doc = PdfDocument()
        doc.open(two_page_pdf)
        assert doc.page_count == 2
        doc.close()

    def test_get_page_valid_index(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        page = doc.get_page(0)
        assert page is not None
        doc.close()

    def test_get_page_out_of_range(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        with pytest.raises(IndexError):
            doc.get_page(5)
        doc.close()

    def test_get_page_negative_index(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        with pytest.raises(IndexError):
            doc.get_page(-1)
        doc.close()

    def test_get_page_dimensions(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        width, height = doc.get_page_dimensions(0)
        # The fixture uses MediaBox [0, 0, 612, 792]
        assert width == pytest.approx(612.0)
        assert height == pytest.approx(792.0)
        doc.close()

    def test_title_read_write(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        doc.title = "Test Title"
        assert doc.title == "Test Title"
        assert doc.is_dirty
        doc.close()

    def test_author_read_write(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        doc.author = "Jane Doe"
        assert doc.author == "Jane Doe"
        doc.close()

    def test_subject_read_write(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        doc.subject = "Accessibility testing"
        assert doc.subject == "Accessibility testing"
        doc.close()

    def test_language_read_write(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        doc.language = "en-US"
        assert doc.language == "en-US"
        assert doc.is_dirty
        doc.close()

    def test_open_clears_command_stack(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        log: list[int] = []
        doc.push_command(_ToggleCommand(log, 1))
        doc.open(minimal_pdf)  # re-open should clear stack
        assert not doc.commands.can_undo
        doc.close()

    def test_dirty_after_push_command(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        assert not doc.is_dirty
        log: list[int] = []
        doc.push_command(_ToggleCommand(log, 5))
        assert doc.is_dirty
        doc.close()

    def test_undo_redo_via_document(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        log: list[int] = []
        doc.push_command(_ToggleCommand(log, 10))
        assert log == [10]
        doc.undo()
        assert log == []
        doc.redo()
        assert log == [10]
        doc.close()

    def test_save_as_updates_path(self, minimal_pdf, tmp_path):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        new_path = tmp_path / "saved.pdf"
        doc.save_as(new_path)
        assert doc.path == new_path
        assert not doc.is_dirty
        assert new_path.exists()
        doc.close()

    def test_save_to_same_path(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        doc.title = "Saved Title"
        doc.save()
        assert not doc.is_dirty
        doc.close()

    def test_event_sink_notified_on_open(self, minimal_pdf):
        doc = PdfDocument()
        sink = MagicMock()
        doc.event_sink = sink
        with patch.object(doc_mod.wx, "PostEvent") as post:
            doc.open(minimal_pdf)
            assert post.called
        doc.close()

    def test_event_sink_notified_on_close(self, minimal_pdf):
        doc = PdfDocument()
        doc.open(minimal_pdf)
        sink = MagicMock()
        doc.event_sink = sink
        with patch.object(doc_mod.wx, "PostEvent") as post:
            doc.close()
            assert post.called

    def test_no_notification_without_sink(self, minimal_pdf):
        doc = PdfDocument()
        doc.event_sink = None
        # Should not raise
        doc.open(minimal_pdf)
        doc.title = "No Sink"
        doc.close()

    def test_pdf_property_returns_pikepdf_object(self, minimal_pdf):
        import pikepdf
        doc = PdfDocument()
        doc.open(minimal_pdf)
        assert isinstance(doc.pdf, pikepdf.Pdf)
        doc.close()
