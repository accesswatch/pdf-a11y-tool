# PDF Accessibility Tool -- Copilot Instructions

## Project Overview

wxPython desktop app for PDF accessibility remediation, form building, and auto-tagging with an integrated agentic AI toolkit. The project supports two paths:

- **Desktop path**: wxPython GUI with 29+ built-in checks, guided remediation, offline operation. No cloud dependency.
- **Agentic path**: MCP server exposing 21+ tools to VS Code Copilot agents with vision-LLM alt text generation via GitHub Models API.

Both paths share the same scanner engine, rule definitions, and fix tier classification. Must be fully operable with NVDA/JAWS screen readers, keyboard only, and Windows High Contrast mode. See [PROJECT-PLAN.md](../PROJECT-PLAN.md) for the 14-phase roadmap and architecture details.

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
| AI alt text | tools/alt_text (agents extra) | Vision-LLM alt text via GitHub Models API |
| MCP server | FastMCP via mcp 1.x (agents extra) | Copilot agent tool interface |

## Architecture

**MVC with Command pattern (desktop path):**

- `src/pdf_a11y/core/` -- Models and business logic. **No wx imports allowed.**
- `src/pdf_a11y/ui/` -- wxPython panels. Bind to model events, call model methods.
- `PdfDocument` (document.py) is the central model: open/save, undo/redo via `CommandStack`, fires `EVT_DOC_CHANGED` / `EVT_DOC_CLOSED`.
- All edits are `Command` subclasses with `execute()` and `undo()`. Group related edits in `CompoundCommand`.
- UI panels discover changes through wx events, not direct coupling.

**Agentic toolkit (MCP path):**

- `tools/` -- Standalone Python scripts for scanning, fixing, and reporting. No wx dependency.
- `tools/mcp_server.py` -- FastMCP server exposing 21+ tools via stdio transport.
- `tools/alt_text/` -- Vision-LLM alt text package (GitHub Models API).
- `agents/` -- 18 Copilot agent definitions with skills and prompt files.
- `src/pdf_a11y/core/ai_bridge.py` -- Bridge connecting desktop UI to tools/alt_text.

**Shared engine**: Both paths use the same `builtin_checks.py` scanner, `fix_tiers.py` classification, and rule definitions.

## Build and Test

```bash
pip install -e ".[dev]"                    # Dev install (desktop only)
pip install -e ".[dev,agents]"             # Dev install with AI/agentic features
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
3. **veraPDF is optional**: `BuiltinChecker` (pure pikepdf, 29+ checks) works without external tools. `VeraPdfValidator` wraps veraPDF CLI but gracefully returns a warning if unavailable.
4. **pikepdf indirect references**: Use `_resolve()` helpers to follow indirect object references when traversing PDF dictionaries.
5. **Screen reader users are first-class**: Every UI panel needs proper `wx.Accessible` overrides, keyboard navigation, and meaningful control labels. See [docs/keyboard-shortcuts.md](../docs/keyboard-shortcuts.md).
6. **AI features are opt-in**: The `ai_bridge.py` module lazy-loads `tools/alt_text`. The desktop app works without the agents extra. Never make AI features a hard dependency.
7. **Graceful AI degradation**: All `AiBridge` methods return response dataclasses with an `error` field. Never raise exceptions to the UI layer.
8. **tools/ is self-contained**: The `tools/` directory has no imports from `src/pdf_a11y/`. The MCP server runs independently. The only bridge is `ai_bridge.py`.
9. **MCP server is stdio**: The MCP server uses stdin/stdout transport. No HTTP ports, no CORS. VS Code Copilot connects directly.
10. **GitHub token never in code**: Token comes from `GITHUB_TOKEN` environment variable or `gh auth token` CLI. Never commit tokens or store in config files.

## Development Phases

The project follows a 14-phase plan (see [PROJECT-PLAN.md](../PROJECT-PLAN.md)):

| Phase | Status | Area |
|-------|--------|------|
| 1. Core PDF engine | Done | document.py, renderer.py, main_frame.py |
| 2. Accessibility checker | Done | builtin_checks.py (29 checks), validator.py, report.py, issues_panel.py |
| 3. Structure tree editor | In progress | tag_types.py, struct_tree.py, tag_tree_panel.py, reading_order_panel.py |
| 3.5--12 | Not started | SR preview, alt text, forms, tables, properties, content tagging, auto-tagger, tool a11y, packaging |
| 13. Adaptive learning | Not started | Pattern recognition from user corrections |
| 14. AI/Agentic integration | Done | ai_bridge.py, tools/, agents/, MCP server, alt_text package |

Most files in phases 3.5--12 are stubs with `from __future__ import annotations` and a docstring listing the planned public API.

## Documentation

- [README.md](../README.md) -- Installation, features, usage
- [PROJECT-PLAN.md](../PROJECT-PLAN.md) -- Full roadmap, architecture, risk register, decisions log
- [docs/user-guide.md](../docs/user-guide.md) -- Workflow guide, panel descriptions
- [docs/keyboard-shortcuts.md](../docs/keyboard-shortcuts.md) -- Complete keybinding reference
- [agents/AGENTS.md](../agents/AGENTS.md) -- Copilot agent registry (18 agents)
- [tools/README.md](../tools/README.md) -- Scanner/fixer toolkit documentation

## Pitfalls

- **Package name mismatch**: CLI is `pdf-a11y-tool` (hyphens), Python package is `pdf_a11y` (underscores).
- **wxPython display requirement**: The app cannot run headless. Tests must mock wx modules before importing any `pdf_a11y.ui` or `pdf_a11y.core.document` module.
- **PyInstaller config**: `--onefile --windowed src/pdf_a11y/__main__.py`. Not yet automated in CI.
- **tools/ sys.path**: The `ai_bridge.py` module adds `tools/` to `sys.path` at runtime. Import `from alt_text.client` not `from tools.alt_text.client`.
- **agents extra**: AI features require `pip install -e ".[agents]"`. Tests for ai_bridge mock the alt_text package.
- **MCP server transport**: The MCP server uses stdio, not HTTP. Do not add port configuration or CORS headers.
- **No CI yet**: Tests, linting, and type checking are manual. A GitHub Actions workflow is planned.
