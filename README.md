# PDF Accessibility Tool

An accessible PDF remediation, form building, and auto-tagging tool built with wxPython, pikepdf, pypdfium2, and Pillow. Includes an integrated AI toolkit with vision-LLM alt text generation and an MCP server for VS Code Copilot agents.

## Overview

PDF Accessibility Tool helps you create and remediate PDF documents to meet accessibility standards (PDF/UA, WCAG 2.2). It supports two complementary workflows:

### Desktop Path (wxPython GUI)

- **Tag Tree Editor** -- View and edit the PDF structure tree (change tag types, reorder elements, set alt text and language)
- **Reading Order Panel** -- Visualize and reorder the document reading sequence
- **Form Builder** -- Add and configure accessible AcroForm fields with tooltips and tab order
- **Auto-Tagger** -- Heuristic and ML-based automatic structure tagging
- **Accessibility Checker** -- 29+ built-in checks plus optional veraPDF integration
- **Screen Reader Preview** -- Linearized text preview showing what a screen reader would read
- **Guided Remediation** -- One-click "Fix Now" for automated fixes with full undo support

### Agentic Path (VS Code Copilot)

- **MCP Server** -- 21+ tools for scanning, fixing, and reporting via VS Code Copilot
- **18 Copilot Agents** -- Specialized agents for PDF, Word, Excel, PowerPoint, ePub, and Markdown
- **Vision-LLM Alt Text** -- AI-generated alt text using 10+ vision models via GitHub Models API
- **Batch Scanning** -- Scan entire folders of mixed document types
- **Quality Scoring** -- 0-100 alt text quality scoring with automated flags

Both paths share the same scanner engine, rule definitions, and fix tier classification.

## Requirements

- Python 3.11 or later
- wxPython 4.2+ (desktop path)
- Java 11+ (optional, for veraPDF integration)
- GitHub token (optional, for AI alt text generation)

## Installation

```bash
pip install pdf-a11y-tool
```

### Development installation

```bash
git clone https://github.com/accesswatch/pdf-a11y-tool.git
cd pdf-a11y-tool
pip install -e ".[dev]"
```

### With AI/agentic features

```bash
pip install -e ".[dev,agents]"
```

This adds vision-LLM alt text generation, MCP server, and multi-format document scanning.

## Usage

### Desktop GUI

Launch the GUI:

```bash
pdf-a11y-tool
```

Or run as a module:

```bash
python -m pdf_a11y
```

#### Basic workflow

1. **Open** a PDF file with `Ctrl+O` or `File` then `Open`
2. **Check** accessibility with `F5` or `Check` then `Run Full Check`
3. **Fix issues** using the Tag Tree, Reading Order, and Alt Text panels
4. **Save** with `Ctrl+S`

### VS Code Copilot Agents

The MCP server is automatically configured when you open this repository in VS Code. Use Copilot Chat to invoke agents:

- `@document-accessibility-wizard` -- Run a full guided accessibility audit
- `@pdf-accessibility` -- Scan a PDF for accessibility issues
- `@pdf-remediator` -- Fix accessibility issues in a PDF

Or use prompt files from `.github/prompts/`:

- `quick-document-check.prompt.md` -- Fast single-document scan
- `audit-all-documents.prompt.md` -- Scan all documents in a folder
- `auto-remediate.prompt.md` -- Apply automated fixes
- `verify-fixes.prompt.md` -- Verify fixes were applied correctly

## Development

### Running tests

```bash
pytest
```

### Running with coverage

```bash
pytest --cov=pdf_a11y --cov-report=html
```

### Linting and type checking

```bash
ruff check src tests
mypy src
```

### Building a standalone executable

```bash
pyinstaller --onefile --windowed src/pdf_a11y/__main__.py
```

## Project Structure

```
src/pdf_a11y/          Desktop application (wxPython GUI)
  core/                Business logic, PDF manipulation, AI bridge
  ui/                  wxPython panels and dialogs
tools/                 Agentic toolkit (standalone, no wx dependency)
  mcp_server.py        FastMCP server for VS Code Copilot
  scan_*.py            Document scanners (PDF, Word, Excel, PowerPoint, ePub, Markdown)
  fix_*.py             Document fixers
  alt_text/            Vision-LLM alt text generation package
agents/                Copilot agent definitions (18 agents)
  skills/              Domain knowledge packages (8 skills)
.github/prompts/       Pre-built prompt workflows (16 prompts)
Samples/               Sample PDF documents for testing
tests/                 Pytest test suite
```

## Keyboard Shortcuts

See [docs/keyboard-shortcuts.md](docs/keyboard-shortcuts.md) for the full reference.

## License

MIT License -- see [LICENSE](LICENSE) for details.
