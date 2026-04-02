---
applyTo: "src/pdf_a11y/core/**"
---
# Core Module Rules -- No wxPython

## Forbidden Imports

Core modules must **never** import wxPython:

```python
# WRONG -- breaks headless testing and violates MVC
import wx
from wx.lib.newevent import NewEvent

# RIGHT -- use callbacks or define event types as plain tuples
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import wx  # type-checking only, never at runtime
```

## Why

- Core modules are the **Model** layer. They must be testable without a display.
- wx imports at the top level cause `ImportError` in headless environments.
- All wx interaction happens in `src/pdf_a11y/ui/` panels, which bind to core
  events and call core methods.

## Event Pattern

Core modules that need to notify the UI define event types using `wx.lib.newevent`
**only in document.py** (the central model). Other core modules should accept
callback functions or return data that UI panels can observe through `EVT_DOC_CHANGED`.

## Command Pattern

Every mutation to a pikepdf object must go through a `Command` subclass:

```python
class MyEditCommand(Command):
    def execute(self) -> None: ...
    def undo(self) -> None: ...
```

Never mutate pikepdf objects directly from outside a Command.
