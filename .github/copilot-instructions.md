# PDF Accessibility Tool -- Copilot Instructions

## Project Overview

wxPython desktop app for PDF accessibility remediation, form building, and auto-tagging. Must be fully operable with NVDA/JAWS screen readers, keyboard only, and Windows High Contrast mode. See [PROJECT-PLAN.md](../PROJECT-PLAN.md) for the 12-phase roadmap and architecture details.

## Technology Stack

| Component | Library | Purpose |
|-----------|---------|---------|
| PDF manipulation | pikepdf 9.x+ | Structure tree, forms, metadata |
| PDF rendering | pypdfium2 4.x+ | Page bitmaps for page view panel |
| Desktop GUI | wxPython 4.2+ | AUI dockable panels, native a11y |
| Image processing | Pillow 10.x+ | pypdfium2-to-wx.Bitmap bridge |
| Config paths | platformdirs 4.x+ | Cross-platform user dirs |
| PDF/UA validation | veraPDF (optional) | Full conformance checking via CLI; requires Java 11+ |
| Auto-tagger ML | scikit-learn 1.4+ | Heading/paragraph/list classification |

## Architecture

**MVC with Command pattern:**

- `src/pdf_a11y/core/` -- Models and business logic. **No wx imports allowed.**
- `src/pdf_a11y/ui/` -- wxPython panels. Bind to model events, call model methods.
- `PdfDocument` (document.py) is the central model: open/save, undo/redo via `CommandStack`, fires `EVT_DOC_CHANGED` / `EVT_DOC_CLOSED`.
- All edits are `Command` subclasses with `execute()` and `undo()`. Group related edits in `CompoundCommand`.
- UI panels discover changes through wx events, not direct coupling.

## Build and Test

```bash
pip install -e ".[dev]"                    # Dev install
pytest                                     # Run tests
pytest --cov=pdf_a11y --cov-report=html    # With coverage
ruff check src tests                       # Lint
mypy src                                   # Type check (strict)
```

Entry points: `pdf-a11y-tool` CLI or `python -m pdf_a11y`.

## Code Conventions

- **Line length:** 100 characters (ruff + editors)
- **Type hints:** `from __future__ import annotations` in every module. mypy strict -- no implicit `Any`.
- **Imports:** Sorted by ruff/isort (`I` rule). Group: stdlib, third-party, local.
- **Naming:** `snake_case` functions, `PascalCase` classes (pep8-naming `N` rule).
- **Ruff rules:** `E, F, W, I, N, UP, B, SIM` -- do not disable without justification.
- **Docstrings:** Module-level docstring with `Public API:` section listing exported names.
- **Target Python:** 3.11+ (ruff target-version, mypy python_version).

## Testing Conventions

- Test files: `tests/test_<module>.py`. Classes: `Test<Feature>`. Methods: `test_<scenario>`.
- Fixtures in `tests/conftest.py`: `minimal_pdf`, `two_page_pdf` (create real pikepdf objects in `tmp_path`).
- **wx mocking:** GUI-dependent modules require mocking wx before import. Pattern:

  ```python
  wx_mock = MagicMock()
  sys.modules["wx"] = wx_mock
  sys.modules["wx.lib"] = MagicMock()
  sys.modules["wx.lib.newevent"] = MagicMock()
  # Configure side_effect for NewEvent calls, then import the module
  ```

- Use `pytest.mark` with registered markers only (`--strict-markers`).
- External tools (veraPDF, Java) must degrade gracefully in tests -- never require them.

## Key Patterns to Follow

1. **No wx in core/**: Core modules must not import wxPython. This enables headless testing and keeps MVC clean.
2. **Command pattern for edits**: Every change to the PDF must go through a `Command` subclass so undo/redo works. Never mutate pikepdf objects directly from UI code.
3. **veraPDF is optional**: `BuiltinChecker` (pure pikepdf, 13+ checks) works without external tools. `VeraPdfValidator` wraps veraPDF CLI but gracefully returns a warning if unavailable.
4. **pikepdf indirect references**: Use `_resolve()` helpers to follow indirect object references when traversing PDF dictionaries.
5. **Screen reader users are first-class**: Every UI panel needs proper `wx.Accessible` overrides, keyboard navigation, and meaningful control labels. See [docs/keyboard-shortcuts.md](../docs/keyboard-shortcuts.md).

## Development Phases

The project follows a 12-phase plan (see [PROJECT-PLAN.md](../PROJECT-PLAN.md)):

| Phase | Status | Area |
|-------|--------|------|
| 1. Core PDF engine | Done | document.py, renderer.py, main_frame.py |
| 2. Accessibility checker | Done | builtin_checks.py, validator.py, report.py, issues_panel.py |
| 3. Structure tree editor | In progress | tag_types.py, struct_tree.py, tag_tree_panel.py, reading_order_panel.py |
| 3.5--12 | Not started | SR preview, alt text, forms, tables, properties, content tagging, auto-tagger, tool a11y, packaging |

Most files in phases 3.5--12 are stubs with `from __future__ import annotations` and a docstring listing the planned public API.

## Documentation

- [README.md](../README.md) -- Installation, features, usage
- [PROJECT-PLAN.md](../PROJECT-PLAN.md) -- Full roadmap, architecture, risk register, decisions log
- [docs/user-guide.md](../docs/user-guide.md) -- Workflow guide, panel descriptions
- [docs/keyboard-shortcuts.md](../docs/keyboard-shortcuts.md) -- Complete keybinding reference

## Pitfalls

- **Package name mismatch**: CLI is `pdf-a11y-tool` (hyphens), Python package is `pdf_a11y` (underscores).
- **wxPython display requirement**: The app cannot run headless. Tests must mock wx modules before importing any `pdf_a11y.ui` or `pdf_a11y.core.document` module.
- **PyInstaller config**: `--onefile --windowed src/pdf_a11y/__main__.py`. Not yet automated in CI.
- **No CI yet**: Tests, linting, and type checking are manual. A GitHub Actions workflow is planned.
