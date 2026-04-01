# PDF Accessibility Tool

An accessible PDF remediation, form building, and auto-tagging tool built with wxPython, pikepdf, pypdfium2, and Pillow.

## Overview

PDF Accessibility Tool helps you create and remediate PDF documents to meet accessibility standards (PDF/UA, WCAG 2.1). It provides:

- **Tag Tree Editor** — View and edit the PDF structure tree (change tag types, reorder elements, set alt text and language)
- **Reading Order Panel** — Visualize and reorder the document reading sequence
- **Form Builder** — Add and configure accessible AcroForm fields with tooltips and tab order
- **Auto-Tagger** — Heuristic and ML-based automatic structure tagging
- **Accessibility Checker** — Built-in checks plus optional veraPDF integration
- **Screen Reader Preview** — Linearized text preview showing what a screen reader would read

## Requirements

- Python 3.11 or later
- wxPython 4.2+
- Java 11+ (optional, for veraPDF integration)

## Installation

```bash
pip install pdf-a11y-tool
```

### Development installation

```bash
git clone https://github.com/your-org/pdf-a11y-tool.git
cd pdf-a11y-tool
pip install -e ".[dev]"
```

## Usage

Launch the GUI:

```bash
pdf-a11y-tool
```

Or run as a module:

```bash
python -m pdf_a11y
```

### Basic workflow

1. **Open** a PDF file with `Ctrl+O` or `File → Open`
2. **Check** accessibility with `F5` or `Check → Run Full Check`
3. **Fix issues** using the Tag Tree, Reading Order, and Alt Text panels
4. **Save** with `Ctrl+S`

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

## Keyboard Shortcuts

See [docs/keyboard-shortcuts.md](docs/keyboard-shortcuts.md) for the full reference.

## License

MIT License — see [LICENSE](LICENSE) for details.
