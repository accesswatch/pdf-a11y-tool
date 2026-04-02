---
applyTo: "tests/**"
---
# wxPython Test Isolation

## Required wx Mocking

Tests for any module that imports `wx` (directly or transitively) must mock the wx
module family **before** importing the module under test:

```python
import sys
from unittest.mock import MagicMock

wx_mock = MagicMock()
sys.modules["wx"] = wx_mock
sys.modules["wx.lib"] = MagicMock()
sys.modules["wx.lib.newevent"] = MagicMock()

# Configure NewEvent to return distinct event tuples
_evt_cls, _EVT_BINDER = object(), object()
wx_mock.lib.newevent.NewEvent.side_effect = [
    (_evt_cls, _EVT_BINDER),
    # Add more tuples if the module creates multiple events
]

# NOW import the module under test
import pdf_a11y.core.document as doc_mod
```

This is necessary because wxPython requires a display and will crash in headless
CI or test environments.

## Conventions

- Test file: `tests/test_<module>.py`
- Test class: `Test<Feature>` (group related scenarios)
- Test method: `test_<scenario_description>` (descriptive, not abbreviated)
- Fixtures go in `conftest.py`; use `tmp_path` for PDF files created with pikepdf
- Use `pytest.mark` only with registered markers (`--strict-markers` is enforced)
- External tools (veraPDF, Java) must never be required; mock or skip gracefully
