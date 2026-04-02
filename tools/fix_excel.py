"""
fix_excel.py — Excel Workbook Accessibility Auto-Fixer
=======================================================
Applies deterministic accessibility fixes to .xlsx files:
  - Missing workbook title
  - Missing workbook author
  - Missing print title rows (repeat header rows)
  - Sheet names that are default ("Sheet1", etc.)

Always creates a backup and writes to a new -fixed.xlsx file.
Never overwrites the original.

This file is PERMANENT — do not delete.
"""

import json
import re
import shutil
import sys
from pathlib import Path

try:
    from openpyxl import load_workbook
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

# ---------------------------------------------------------------------------
# Fix functions
# ---------------------------------------------------------------------------

def _fix_title(wb, title: str = "") -> dict:
    """Set workbook title if missing."""
    current = wb.properties.title or ""
    if current.strip():
        return {"rule": "XLSX-META.TITLE", "status": "skipped", "reason": "Title already set"}
    wb.properties.title = title or "TODO: Add descriptive workbook title"
    return {"rule": "XLSX-META.TITLE", "status": "fixed", "detail": f"Set title to '{wb.properties.title}'"}


def _fix_author(wb, author: str = "") -> dict:
    """Set workbook author if missing."""
    current = wb.properties.creator or ""
    if current.strip():
        return {"rule": "XLSX-META.AUTHOR", "status": "skipped", "reason": "Author already set"}
    wb.properties.creator = author or "TODO: Add author name"
    return {"rule": "XLSX-META.AUTHOR", "status": "fixed", "detail": f"Set author to '{wb.properties.creator}'"}


_DEFAULT_SHEET_RE = re.compile(r"^Sheet\d*$", re.IGNORECASE)


def _fix_sheet_names(wb) -> list[dict]:
    """Flag default sheet names (Sheet1, Sheet2...) — these need human names."""
    results = []
    for ws in wb.worksheets:
        if _DEFAULT_SHEET_RE.match(ws.title):
            results.append({
                "rule": "XLSX-SHEET.NAME",
                "status": "needs-human",
                "detail": f"Sheet '{ws.title}' has a default name — rename to describe its content",
            })
    if not results:
        results.append({"rule": "XLSX-SHEET.NAME", "status": "skipped", "reason": "All sheets have descriptive names"})
    return results


def _fix_print_titles(wb) -> list[dict]:
    """Set print title (repeat header) row 1 on sheets that have data but no print titles."""
    results = []
    for ws in wb.worksheets:
        if ws.max_row and ws.max_row > 1:
            if ws.print_title_rows is None or ws.print_title_rows == "":
                ws.print_title_rows = "1:1"
                results.append({
                    "rule": "XLSX-TABLE.PRINT_TITLES",
                    "status": "fixed",
                    "detail": f"Set print title rows to 1:1 on '{ws.title}'",
                })
    if not results:
        results.append({"rule": "XLSX-TABLE.PRINT_TITLES", "status": "skipped", "reason": "All data sheets already have print titles"})
    return results


def _fix_image_alt_text(wb, use_alt_text_generator: bool = False,
                        alt_text_models: list[str] | None = None,
                        alt_text_context: str = "") -> list[dict]:
    """Add alt text to images missing descriptions.

    When use_alt_text_generator is True, generates real alt text via
    the vision LLM. Otherwise, adds TODO placeholders.
    """
    results = []
    for ws in wb.worksheets:
        for img in ws._images:
            desc = getattr(img, "desc", None) or ""
            if not desc.strip():
                name = getattr(img, "name", None) or "Image"

                if use_alt_text_generator:
                    alt = _generate_alt_for_xlsx_image(
                        img, ws.title, alt_text_models, alt_text_context
                    )
                    if alt:
                        try:
                            img.desc = alt
                            results.append({
                                "rule": "XLSX-IMG.ALT",
                                "status": "fixed",
                                "detail": f"Generated alt text for '{name}' on '{ws.title}': '{alt[:80]}...'",
                            })
                            continue
                        except (AttributeError, TypeError):
                            pass

                # Fallback: placeholder
                placeholder = f"TODO: Describe {name}"
                try:
                    img.desc = placeholder
                    results.append({
                        "rule": "XLSX-IMG.ALT",
                        "status": "fixed",
                        "detail": f"Added placeholder alt text to '{name}' on '{ws.title}'",
                    })
                except (AttributeError, TypeError):
                    results.append({
                        "rule": "XLSX-IMG.ALT",
                        "status": "failed",
                        "reason": f"Could not set alt text on '{name}' in '{ws.title}' — openpyxl limitation",
                    })
    if not results:
        results.append({"rule": "XLSX-IMG.ALT", "status": "skipped", "reason": "All images have alt text or no images found"})
    return results


def _generate_alt_for_xlsx_image(
    img_obj, sheet_name: str,
    models: list[str] | None, context: str,
) -> str | None:
    """Try to generate alt text using the alt-text generator."""
    try:
        from alt_text.client import generate_for_image
    except ImportError:
        return None

    try:
        if hasattr(img_obj, "_data"):
            image_bytes = img_obj._data()
        elif hasattr(img_obj, "ref"):
            image_bytes = img_obj.ref.getvalue() if hasattr(img_obj.ref, 'getvalue') else img_obj.ref.read()
        else:
            return None

        if not image_bytes:
            return None

        name = getattr(img_obj, "name", None) or "Image"
        result = generate_for_image(
            image_bytes=image_bytes,
            mime_type="image/png",
            model=(models or ["openai/gpt-4.1"])[0],
            profile="auto",
            source_format="xlsx",
            image_name=name,
            sheet_name=sheet_name,
            context=context,
        )
        return result.concise_alt if result.concise_alt else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main fix orchestrator
# ---------------------------------------------------------------------------

_ALL_RULES = {
    "XLSX-META.TITLE": _fix_title,
    "XLSX-META.AUTHOR": _fix_author,
    "XLSX-SHEET.NAME": _fix_sheet_names,
    "XLSX-TABLE.PRINT_TITLES": _fix_print_titles,
    "XLSX-IMG.ALT": _fix_image_alt_text,
}


def fix_excel(file_path: Path, output_path: Path | None = None,
              rules: list[str] | None = None,
              title: str = "", author: str = "") -> dict:
    """Apply accessibility fixes to an Excel workbook.

    Args:
        file_path: Path to the original .xlsx file.
        output_path: Where to save the fixed file. Defaults to <name>-fixed.xlsx.
        rules: Optional list of rule IDs to fix. None = fix all.
        title: Custom title text. Empty = placeholder.
        author: Custom author text. Empty = placeholder.

    Returns:
        Dict with keys: file, output, backup, fixes (list), summary.
    """
    if not HAS_OPENPYXL:
        return {"error": "openpyxl is not installed. Run: pip install openpyxl"}

    file_path = Path(file_path)
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}

    if output_path is None:
        output_path = file_path.with_stem(file_path.stem + "-fixed")
    else:
        output_path = Path(output_path)

    backup_path = file_path.with_stem(file_path.stem + "-backup")
    shutil.copy2(file_path, backup_path)

    wb = load_workbook(str(file_path))
    all_fixes = []
    target_rules = rules if rules else list(_ALL_RULES.keys())

    for rule_id in target_rules:
        if rule_id not in _ALL_RULES:
            all_fixes.append({"rule": rule_id, "status": "unknown", "reason": f"Rule {rule_id} not supported for auto-fix"})
            continue

        func = _ALL_RULES[rule_id]
        if rule_id == "XLSX-META.TITLE":
            result = func(wb, title)
        elif rule_id == "XLSX-META.AUTHOR":
            result = func(wb, author)
        else:
            result = func(wb)

        if isinstance(result, list):
            all_fixes.extend(result)
        else:
            all_fixes.append(result)

    wb.save(str(output_path))

    fixed_count = sum(1 for f in all_fixes if f["status"] == "fixed")
    skipped_count = sum(1 for f in all_fixes if f["status"] == "skipped")
    failed_count = sum(1 for f in all_fixes if f["status"] == "failed")
    human_count = sum(1 for f in all_fixes if f["status"] == "needs-human")

    return {
        "file": str(file_path),
        "output": str(output_path),
        "backup": str(backup_path),
        "fixes": all_fixes,
        "summary": {
            "fixed": fixed_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "needs_human": human_count,
            "total_rules_attempted": len(target_rules),
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix Excel workbook accessibility issues")
    parser.add_argument("input", help="Path to .xlsx file")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--rules", help="Comma-separated rule IDs to fix")
    parser.add_argument("--title", default="", help="Workbook title")
    parser.add_argument("--author", default="", help="Workbook author")
    args = parser.parse_args()

    rule_list = args.rules.split(",") if args.rules else None
    out = args.output if args.output else None
    result = fix_excel(Path(args.input), Path(out) if out else None, rule_list, args.title, args.author)
    print(json.dumps(result, indent=2))
