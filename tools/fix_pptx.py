"""
fix_pptx.py — PowerPoint Presentation Accessibility Auto-Fixer
================================================================
Applies deterministic accessibility fixes to .pptx files:
  - Missing presentation title
  - Missing presentation author
  - Missing slide titles
  - Missing alt text placeholders on images/shapes
  - Duplicate slide titles (appends sequence number)

Always creates a backup and writes to a new -fixed.pptx file.
Never overwrites the original.

This file is PERMANENT — do not delete.
"""

import json
import shutil
import sys
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False

# ---------------------------------------------------------------------------
# XML namespace constants (OOXML / PresentationML / DrawingML)
# ---------------------------------------------------------------------------
_NS_PML = "http://schemas.openxmlformats.org/presentationml/2006/main"
_NS_DML = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_SSD = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
_NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# ---------------------------------------------------------------------------
# Fix functions
# ---------------------------------------------------------------------------

def _fix_title(prs, title: str = "") -> dict:
    """Set presentation title if missing."""
    current = prs.core_properties.title or ""
    if current.strip():
        return {"rule": "PPTX-META.TITLE", "status": "skipped", "reason": "Title already set"}
    prs.core_properties.title = title or "TODO: Add descriptive presentation title"
    return {"rule": "PPTX-META.TITLE", "status": "fixed", "detail": f"Set title to '{prs.core_properties.title}'"}


def _fix_author(prs, author: str = "") -> dict:
    """Set presentation author if missing."""
    current = prs.core_properties.author or ""
    if current.strip():
        return {"rule": "PPTX-META.AUTHOR", "status": "skipped", "reason": "Author already set"}
    prs.core_properties.author = author or "TODO: Add author name"
    return {"rule": "PPTX-META.AUTHOR", "status": "fixed", "detail": f"Set author to '{prs.core_properties.author}'"}


def _get_slide_title_text(slide) -> str:
    """Extract title text from a slide if it has a title placeholder."""
    if slide.shapes.title is not None:
        return (slide.shapes.title.text or "").strip()
    return ""


def _fix_slide_titles(prs) -> list[dict]:
    """Report slides missing titles — these require human judgment."""
    results = []
    for i, slide in enumerate(prs.slides, 1):
        title_text = _get_slide_title_text(slide)
        if not title_text:
            has_title_placeholder = slide.shapes.title is not None
            if has_title_placeholder:
                slide.shapes.title.text = f"TODO: Title for Slide {i}"
                results.append({
                    "rule": "PPTX-SLIDE.TITLE",
                    "status": "fixed",
                    "detail": f"Slide {i}: Added placeholder title 'TODO: Title for Slide {i}'",
                })
            else:
                results.append({
                    "rule": "PPTX-SLIDE.TITLE",
                    "status": "needs-human",
                    "detail": f"Slide {i}: No title placeholder in layout — add title shape manually",
                })
    if not results:
        results.append({"rule": "PPTX-SLIDE.TITLE", "status": "skipped", "reason": "All slides have titles"})
    return results


def _fix_duplicate_titles(prs) -> list[dict]:
    """Detect and fix duplicate slide titles by appending sequence numbers."""
    results = []
    seen = {}
    for i, slide in enumerate(prs.slides, 1):
        title_text = _get_slide_title_text(slide)
        if not title_text or title_text.startswith("TODO:"):
            continue
        if title_text in seen:
            seen[title_text] += 1
            new_title = f"{title_text} ({seen[title_text]})"
            slide.shapes.title.text = new_title
            results.append({
                "rule": "PPTX-SLIDE.TITLE_UNIQUE",
                "status": "fixed",
                "detail": f"Slide {i}: Renamed duplicate '{title_text}' to '{new_title}'",
            })
        else:
            seen[title_text] = 1
    # Retroactively fix the first occurrence if there were duplicates
    # (The first occurrence keeps its original name — already unique enough)
    if not results:
        results.append({"rule": "PPTX-SLIDE.TITLE_UNIQUE", "status": "skipped", "reason": "No duplicate slide titles found"})
    return results


def _fix_image_alt_text(prs, use_alt_text_generator: bool = False,
                        alt_text_models: list[str] | None = None,
                        alt_text_context: str = "") -> list[dict]:
    """Add alt text to images/shapes missing it.

    When use_alt_text_generator is True, generates real alt text via
    the vision LLM. Otherwise, adds TODO placeholders.
    """
    results = []
    for i, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if shape.shape_type is not None and hasattr(shape, "image"):
                try:
                    name = shape.name or f"Image on Slide {i}"
                    desc = shape._element.attrib.get("descr", "").strip()
                    # Get cNvPr element for alt text
                    cNvPr_list = shape._element.findall(f".//{{{_NS_PML}}}cNvPr")
                    if not cNvPr_list:
                        cNvPr_list = shape._element.findall(f".//{{{_NS_SSD}}}cNvPr")
                    if not cNvPr_list:
                        # Try the pic element path
                        cNvPr_list = shape._element.findall(f".//{{{_NS_PML}}}nvPicPr/{{{_NS_PML}}}cNvPr")

                    # Use the non-visual properties approach
                    nvXxPr = shape._element.find(f".//{{{_NS_PML}}}nvSpPr")
                    if nvXxPr is None:
                        nvXxPr = shape._element.find(f".//{{{_NS_PML}}}nvPicPr")

                    if nvXxPr is not None:
                        cNvPr = nvXxPr.find(f"{{{_NS_PML}}}cNvPr")
                        if cNvPr is not None:
                            current_descr = cNvPr.get("descr", "").strip()
                            if not current_descr:
                                alt_text = None
                                if use_alt_text_generator:
                                    alt_text = _generate_alt_for_pptx_image(
                                        shape, i, name,
                                        alt_text_models, alt_text_context,
                                    )
                                if alt_text:
                                    cNvPr.set("descr", alt_text)
                                    results.append({
                                        "rule": "PPTX-IMG.ALT",
                                        "status": "fixed",
                                        "detail": f"Slide {i}, '{name}': Generated alt text: '{alt_text[:80]}...'",
                                    })
                                else:
                                    placeholder = f"TODO: Describe {name}"
                                    cNvPr.set("descr", placeholder)
                                    results.append({
                                        "rule": "PPTX-IMG.ALT",
                                        "status": "fixed",
                                        "detail": f"Slide {i}, '{name}': Added placeholder alt text",
                                    })
                except Exception:
                    pass  # Skip shapes that can't be processed

    if not results:
        results.append({"rule": "PPTX-IMG.ALT", "status": "skipped", "reason": "All images have alt text or no images found"})
    return results


def _generate_alt_for_pptx_image(
    shape, slide_num: int, name: str,
    models: list[str] | None, context: str,
) -> str | None:
    """Try to generate alt text using the alt-text generator."""
    try:
        from alt_text.client import generate_for_image
    except ImportError:
        return None

    try:
        image_bytes = shape.image.blob
        content_type = shape.image.content_type or "image/png"

        result = generate_for_image(
            image_bytes=image_bytes,
            mime_type=content_type,
            model=(models or ["openai/gpt-4.1"])[0],
            profile="auto",
            source_format="pptx",
            page_number=slide_num,
            image_name=name,
            context=context,
        )
        return result.concise_alt if result.concise_alt else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main fix orchestrator
# ---------------------------------------------------------------------------

_ALL_RULES = {
    "PPTX-META.TITLE": _fix_title,
    "PPTX-META.AUTHOR": _fix_author,
    "PPTX-SLIDE.TITLE": _fix_slide_titles,
    "PPTX-SLIDE.TITLE_UNIQUE": _fix_duplicate_titles,
    "PPTX-IMG.ALT": _fix_image_alt_text,
}


def fix_pptx(file_path: Path, output_path: Path | None = None,
             rules: list[str] | None = None,
             title: str = "", author: str = "") -> dict:
    """Apply accessibility fixes to a PowerPoint presentation.

    Args:
        file_path: Path to the original .pptx file.
        output_path: Where to save the fixed file. Defaults to <name>-fixed.pptx.
        rules: Optional list of rule IDs to fix. None = fix all.
        title: Custom title text. Empty = placeholder.
        author: Custom author text. Empty = placeholder.

    Returns:
        Dict with keys: file, output, backup, fixes (list), summary.
    """
    if not HAS_PPTX:
        return {"error": "python-pptx is not installed. Run: pip install python-pptx"}

    file_path = Path(file_path)
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}

    if output_path is None:
        output_path = file_path.with_stem(file_path.stem + "-fixed")
    else:
        output_path = Path(output_path)

    backup_path = file_path.with_stem(file_path.stem + "-backup")
    shutil.copy2(file_path, backup_path)

    prs = Presentation(str(file_path))
    all_fixes = []
    target_rules = rules if rules else list(_ALL_RULES.keys())

    for rule_id in target_rules:
        if rule_id not in _ALL_RULES:
            all_fixes.append({"rule": rule_id, "status": "unknown", "reason": f"Rule {rule_id} not supported for auto-fix"})
            continue

        func = _ALL_RULES[rule_id]
        if rule_id == "PPTX-META.TITLE":
            result = func(prs, title)
        elif rule_id == "PPTX-META.AUTHOR":
            result = func(prs, author)
        else:
            result = func(prs)

        if isinstance(result, list):
            all_fixes.extend(result)
        else:
            all_fixes.append(result)

    prs.save(str(output_path))

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

    parser = argparse.ArgumentParser(description="Fix PowerPoint accessibility issues")
    parser.add_argument("input", help="Path to .pptx file")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--rules", help="Comma-separated rule IDs to fix")
    parser.add_argument("--title", default="", help="Presentation title")
    parser.add_argument("--author", default="", help="Presentation author")
    args = parser.parse_args()

    rule_list = args.rules.split(",") if args.rules else None
    out = args.output if args.output else None
    result = fix_pptx(Path(args.input), Path(out) if out else None, rule_list, args.title, args.author)
    print(json.dumps(result, indent=2))
