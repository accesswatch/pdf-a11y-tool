"""PDF document model: open/save, undo/redo command stack, metadata, page enumeration.

This module is the central model that all UI panels interact with.
"""
from __future__ import annotations

import abc
import threading
from pathlib import Path
from typing import Any

import pikepdf
import wx
import wx.lib.newevent

# ---------------------------------------------------------------------------
# Custom wx events for document change notifications
# ---------------------------------------------------------------------------

DocChangedEvent, EVT_DOC_CHANGED = wx.lib.newevent.NewEvent()
DocClosedEvent, EVT_DOC_CLOSED = wx.lib.newevent.NewEvent()


# ---------------------------------------------------------------------------
# Command pattern
# ---------------------------------------------------------------------------

class Command(abc.ABC):
    """Base class for all undoable commands."""

    @abc.abstractmethod
    def execute(self) -> None:
        """Perform the command action."""

    @abc.abstractmethod
    def undo(self) -> None:
        """Reverse the command action."""

    @property
    def description(self) -> str:
        """Human-readable description for undo/redo menu items."""
        return self.__class__.__name__


class CompoundCommand(Command):
    """A group of commands executed and undone as a single unit."""

    def __init__(self, commands: list[Command], description: str = "Compound command") -> None:
        self._commands = list(commands)
        self._description = description

    @property
    def description(self) -> str:
        return self._description

    def execute(self) -> None:
        for cmd in self._commands:
            cmd.execute()

    def undo(self) -> None:
        for cmd in reversed(self._commands):
            cmd.undo()


class CommandStack:
    """Undo/redo stack for Command objects."""

    def __init__(self, max_size: int = 100) -> None:
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []
        self._max_size = max_size

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def undo_description(self) -> str | None:
        return self._undo_stack[-1].description if self._undo_stack else None

    @property
    def redo_description(self) -> str | None:
        return self._redo_stack[-1].description if self._redo_stack else None

    def push(self, command: Command) -> None:
        """Execute the command and add it to the undo stack."""
        command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        if len(self._undo_stack) > self._max_size:
            self._undo_stack.pop(0)

    def undo(self) -> Command | None:
        """Undo the most recent command."""
        if not self._undo_stack:
            return None
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        return command

    def redo(self) -> Command | None:
        """Redo the most recently undone command."""
        if not self._redo_stack:
            return None
        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)
        return command

    def clear(self) -> None:
        """Clear both stacks (e.g., after save-as)."""
        self._undo_stack.clear()
        self._redo_stack.clear()


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------

class PdfDocument:
    """The central model wrapping a pikepdf.Pdf object.

    All panels read from and write to this object. Modifications are made
    via Command objects pushed onto the CommandStack so that every change
    is undoable.
    """

    def __init__(self) -> None:
        self._pdf: pikepdf.Pdf | None = None
        self._path: Path | None = None
        self._dirty: bool = False
        self._lock = threading.Lock()
        self.commands = CommandStack()
        # Event sink: a wx.EvtHandler that receives DocChangedEvent notifications.
        # Set by the application after creating the document model.
        self.event_sink: wx.EvtHandler | None = None

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def open(self, path: str | Path) -> None:
        """Open a PDF file. Raises pikepdf.PdfError on failure."""
        path = Path(path)
        with self._lock:
            if self._pdf is not None:
                self._pdf.close()
            self._pdf = pikepdf.open(path)
            self._path = path
            self._dirty = False
            self.commands.clear()
        self._notify_changed("open")

    def close(self) -> None:
        """Close the current document."""
        with self._lock:
            if self._pdf is not None:
                self._pdf.close()
                self._pdf = None
            self._path = None
            self._dirty = False
            self.commands.clear()
        self._notify_event(DocClosedEvent())

    def save(self) -> None:
        """Save to the current file path. Raises ValueError if no path set."""
        if self._path is None:
            raise ValueError("No file path set; use save_as() first.")
        self.save_as(self._path)

    def save_as(self, path: str | Path) -> None:
        """Save to a (possibly new) file path."""
        path = Path(path)
        if self._pdf is None:
            raise ValueError("No document open.")
        with self._lock:
            self._pdf.save(path)
            self._path = path
            self._dirty = False
        self._notify_changed("save")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_open(self) -> bool:
        return self._pdf is not None

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    @property
    def pdf(self) -> pikepdf.Pdf:
        if self._pdf is None:
            raise ValueError("No document open.")
        return self._pdf

    # ------------------------------------------------------------------
    # Page enumeration
    # ------------------------------------------------------------------

    @property
    def page_count(self) -> int:
        if self._pdf is None:
            return 0
        return len(self._pdf.pages)

    def get_page(self, index: int) -> pikepdf.Page:
        """Return the pikepdf.Page at zero-based index."""
        if self._pdf is None:
            raise ValueError("No document open.")
        if index < 0 or index >= len(self._pdf.pages):
            raise IndexError(f"Page index {index} out of range (0..{len(self._pdf.pages) - 1}).")
        return self._pdf.pages[index]

    def get_page_dimensions(self, index: int) -> tuple[float, float]:
        """Return (width, height) of page at index in PDF user units (points)."""
        page = self.get_page(index)
        media_box = page.mediabox
        width = float(media_box[2]) - float(media_box[0])
        height = float(media_box[3]) - float(media_box[1])
        return (width, height)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _get_info(self, key: str) -> str:
        """Read a string from the /Info dictionary."""
        if self._pdf is None:
            return ""
        try:
            info = self._pdf.docinfo
            val = info.get(f"/{key}")
            if val is None:
                return ""
            return str(val)
        except Exception:
            return ""

    def _set_info(self, key: str, value: str) -> None:
        """Write a string to the /Info dictionary."""
        if self._pdf is None:
            raise ValueError("No document open.")
        self._pdf.docinfo[f"/{key}"] = value
        self._dirty = True

    @property
    def title(self) -> str:
        return self._get_info("Title")

    @title.setter
    def title(self, value: str) -> None:
        self._set_info("Title", value)
        self._notify_changed("metadata")

    @property
    def author(self) -> str:
        return self._get_info("Author")

    @author.setter
    def author(self, value: str) -> None:
        self._set_info("Author", value)
        self._notify_changed("metadata")

    @property
    def subject(self) -> str:
        return self._get_info("Subject")

    @subject.setter
    def subject(self, value: str) -> None:
        self._set_info("Subject", value)
        self._notify_changed("metadata")

    @property
    def language(self) -> str:
        """Document language from /Lang entry in the catalog."""
        if self._pdf is None:
            return ""
        try:
            lang = self._pdf.Root.get("/Lang")
            return str(lang) if lang is not None else ""
        except Exception:
            return ""

    @language.setter
    def language(self, value: str) -> None:
        if self._pdf is None:
            raise ValueError("No document open.")
        self._pdf.Root["/Lang"] = pikepdf.String(value)
        self._dirty = True
        self._notify_changed("metadata")

    # ------------------------------------------------------------------
    # Command stack integration
    # ------------------------------------------------------------------

    def push_command(self, command: Command) -> None:
        """Execute a command and add it to the undo stack, marking the document dirty."""
        self.commands.push(command)
        self._dirty = True
        self._notify_changed("command")

    def undo(self) -> None:
        """Undo the most recent command."""
        cmd = self.commands.undo()
        if cmd is not None:
            self._dirty = True
            self._notify_changed("undo")

    def redo(self) -> None:
        """Redo the most recently undone command."""
        cmd = self.commands.redo()
        if cmd is not None:
            self._dirty = True
            self._notify_changed("redo")

    # ------------------------------------------------------------------
    # Event notification
    # ------------------------------------------------------------------

    def _notify_changed(self, reason: str = "") -> None:
        """Broadcast a DocChangedEvent to the event sink if set."""
        if self.event_sink is not None:
            evt = DocChangedEvent(reason=reason, document=self)
            wx.PostEvent(self.event_sink, evt)

    def _notify_event(self, evt: wx.Event) -> None:
        if self.event_sink is not None:
            wx.PostEvent(self.event_sink, evt)
