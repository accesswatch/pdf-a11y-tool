# PDF Accessibility Tool — User Guide

> **Note:** This user guide will be expanded as the tool matures through each development phase.

## Getting Started

### Opening a PDF

1. Launch the application with `pdf-a11y-tool` or `python -m pdf_a11y`
2. Use **File → Open** (`Ctrl+O`) to open an existing PDF file
3. Or use **File → New Blank PDF** (`Ctrl+N`) to create a new tagged document from scratch

### The Main Window

The application window is divided into several dockable panels:

- **Page View** (centre) — Displays the rendered PDF page
- **Tag Tree** (left) — Shows the PDF structure tree hierarchy
- **Reading Order** (left, below Tag Tree) — Lists elements in reading sequence
- **Properties** (right) — Shows properties of the selected element
- **Bottom tabs** — Issues, Fields, Alt Text, Tables, Screen Reader Preview

All panels can be docked, undocked, resized, or hidden using the **View → Panels** menu.

## Checking Accessibility

Press **F5** or use **Check → Run Full Check** to run an accessibility audit.
Results appear in the **Issues** tab at the bottom of the window.

Each issue shows:
- **Severity** — Error, Warning, or Info
- **Rule** — The rule ID that was violated
- **WCAG** — The corresponding WCAG 2.1 success criterion
- **Description** — What was found and how to fix it
- **Page** — The page number where the issue occurs

Double-click an issue to navigate to the related element.

## Editing the Tag Tree

The **Tag Tree** panel shows the PDF structure hierarchy. You can:

- **Change tag type** — Right-click a node and select Change Type, or use **Tags → Change Type**
- **Set alt text** — Select a Figure element and use `Ctrl+Alt+A`
- **Set language** — Select an element and use `Ctrl+Alt+L`
- **Delete element** — Select and press Delete, or use **Tags → Delete Element**
- **Reorder children** — Drag and drop within the tree

## Working with Forms

Use the **Forms** menu to add new form fields to the document:
- Text fields, checkboxes, radio buttons, dropdowns, and push buttons

Select a field in the **Fields** tab to edit its properties (name, tooltip, required status).

Use `Alt+Up` / `Alt+Down` in the Fields list to change tab order.

## Screen Reader Preview

The **SR Preview** tab shows the document content as a screen reader would announce it —
derived from the structure tree in reading order. Use this to verify the reading experience
before distributing the document.

## Saving

- **Ctrl+S** — Save to the current file (the title bar shows `*` for unsaved changes)
- **Ctrl+Shift+S** — Save as a new file

## Keyboard Shortcuts

See [keyboard-shortcuts.md](keyboard-shortcuts.md) for the complete reference.
