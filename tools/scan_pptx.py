"""
scan_pptx.py — PowerPoint (.pptx) Accessibility Scanner
=========================================================
Permanent utility for document accessibility audits.
Inspects .pptx files for accessibility issues using python-pptx.

Checks performed:
  Metadata:
    - Presentation title set                [PPTX.META.TITLE]

  Per-slide:
    - Missing slide title                   [PPTX.SLIDE.TITLE]
    - Duplicate slide titles                [PPTX.SLIDE.TITLE_DUP]
    - Missing speaker notes                 [PPTX.SLIDE.NOTES]

  Reading order (critical risk area):
    - Title not first element read by AT    [PPTX.ORDER.TITLE_FIRST]
    - Significant content before title      [PPTX.ORDER.PRELUDE]
    - Two-column layout detected (manual)   [PPTX.ORDER.COLUMNS]
    - Mandatory AT verification flag        [PPTX.ORDER.VERIFY]

  Images and objects:
    - Missing alt text on images/charts     [PPTX.IMG.ALT]
    - Very short / placeholder alt text     [PPTX.IMG.ALT_QUALITY]

  Tables:
    - Table without header row marking      [PPTX.TABLE.HEADER]

  Media:
    - Embedded media without notes          [PPTX.MEDIA.CAPTIONS]

  Sections:
    - Generic or duplicate section names    [PPTX.SECTION.NAME]

  Hyperlinks:
    - Non-descriptive anchor text           [PPTX.LINKS.TEXT]

Usage:
    python tools/scan_pptx.py <pptx_or_folder> [--json] [--output file.json]

Dependencies: python-pptx (pip install python-pptx)

RESEARCH SOURCES:

  WebAIM — PowerPoint Accessibility (webaim.org/techniques/powerpoint):
  - Every slide must have a unique, descriptive title
  - Reading order: Selection Pane bottom-to-top = first-to-last read by AT
    python-pptx slide.shapes iterates in XML spTree order = AT reading order
    (first shape in spTree = first announced by screen reader)
  - Alt text: right-click → Edit Alt Text; 'Mark as decorative' for decorative;
    NEVER 'Generate description for me' — AI descriptions are unreliable
  - Tables: mark Header Row AND First Column where applicable
  - Embedded video: must have captions; embedded audio: must have transcript
  - Color-only information: add text/icons alongside color coding
  - Save As PDF: use Microsoft's built-in Save As PDF (NOT Adobe Acrobat tab)
    to best preserve alt text on export

  WebAIM Office Evaluation Guide:
  - Section names not 'Untitled Section', no duplicate section names
  - Duplicate slide titles are confusing in Navigation Pane
  - Reading order must be verified in Selection Pane: bottom = first read
  - Blank slides should be removed or titled 'Intentionally blank'

  Section508.gov — Create Accessible Presentations:
  - Every slide needs a title; identical titles confuse screen reader users
  - Slide notes help NVDA/JAWS users understand complex visual content
  - Layout placeholders should contain the intended content (not text boxes
    layered on top of placeholders)

  python-pptx confirmed APIs:
  - prs.core_properties.title / .author
  - prs.slides — SlidePage collection
  - slide.shapes — ShapeCollection in XML/AT reading order
  - slide.shapes.title — first title placeholder or None
  - shape.placeholder_format.type — PP_PLACEHOLDER enum values
  - shape.has_text_frame, shape.text_frame.text
  - shape.left, shape.top, shape.width, shape.height — EMU units (914400/inch)
  - slide.has_notes_slide, slide.notes_slide.notes_text_frame.text
  - shape.shape_type — MSO_SHAPE_TYPE values (PICTURE=13, MEDIA=16)

This file is PERMANENT — do not delete. Used by agents and scan_all.py.
"""

import sys
import json
import argparse
import re
from pathlib import Path
from collections import Counter
from zipfile import ZipFile, BadZipFile
from lxml import etree

try:
    from pptx import Presentation
    from pptx.util import Emu
except ImportError:
    sys.exit("ERROR: python-pptx not installed. Run: pip install python-pptx")

# PP_PLACEHOLDER type values (int constants from pptx.enum.shapes)
PP_PH_TITLE = 1
PP_PH_BODY = 2
PP_PH_CENTER_TITLE = 3
PP_PH_SUBTITLE = 4

# MSO_SHAPE_TYPE int values
MSO_PICTURE = 13
MSO_MEDIA = 16
MSO_CHART = 3
MSO_TABLE = 19

# EMU units
EMU_PER_INCH = 914400

GENERIC_SECTION_NAMES = {
    "untitled section", "section 1", "section 2", "section 3",
    "section 4", "section 5", "default section", "new section",
}

VAGUE_LINK_RE = re.compile(
    r"^(click here|here|read more|learn more|more|link|more info|"
    r"this|details|info|go|view|see here|download|url)\.?$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Alt text extraction
# ---------------------------------------------------------------------------

def _get_alt_text(shape) -> tuple:
    """
    Return (alt_text: str | None, is_decorative: bool) for a shape.
    alt_text is None if the element has no cNvPr at all.
    alt_text is '' if cNvPr exists but descr is empty (may be decorative).
    is_decorative is True if the cNvPr 'hidden' attribute = '1' or 'true'
    (PowerPoint 2019+ mechanism for 'Mark as decorative').
    """
    elem = shape._element
    # Search all cNvPr elements regardless of namespace prefix
    for el in elem.iter():
        local = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if local == "cNvPr":
            descr = el.get("descr", None)
            # 'hidden' attribute indicates "Mark as decorative" in newer PPT
            hidden_val = el.get("hidden", "0")
            is_decorative = hidden_val in ("1", "true", "True")
            return (descr, is_decorative)
    return (None, False)


def _is_graphical_shape(shape) -> bool:
    """Return True if the shape is a picture, chart, SmartArt, or media."""
    try:
        st = int(shape.shape_type)
        return st in (MSO_PICTURE, MSO_MEDIA, MSO_CHART, 6, 7, 24, 26)
    except Exception:
        return False


def _is_title_placeholder(shape) -> bool:
    """Return True if the shape is a title-type placeholder."""
    try:
        pf = shape.placeholder_format
        if pf is not None:
            return int(pf.type) in (PP_PH_TITLE, PP_PH_CENTER_TITLE)
    except Exception:
        pass
    return False


def _shape_has_text(shape) -> bool:
    """Return True if shape has a text frame with actual text."""
    try:
        return shape.has_text_frame and bool(shape.text_frame.text.strip())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Reading order analysis
# ---------------------------------------------------------------------------

def analyze_slide_reading_order(slide, slide_idx: int, prs_width, prs_height) -> dict:
    """
    Analyze the reading order of shapes on a slide.

    AT reading order = XML order in <p:spTree> = python-pptx slide.shapes iteration order.

    Checks:
    1. Title placeholder position — it should be the first text-bearing shape
       read by AT. If it's not at index 0, content before it will be read first.
    2. Significant pre-title content — non-trivial text shapes before the title.
    3. Two-column heuristic — text shapes clustered in left and right halves
       (vertical bands) suggest a column layout needing manual verification.

    Returns dict with issues and recommendations.
    """
    result = {
        "slide_number": slide_idx + 1,
        "shape_count": len(slide.shapes),
        "title_at_index": None,
        "shapes_before_title": 0,
        "text_shapes_before_title": [],
        "suspected_columns": False,
        "column_evidence": "",
        "issues": [],
    }

    shapes = list(slide.shapes)
    title_idx = None

    for i, shape in enumerate(shapes):
        if _is_title_placeholder(shape):
            title_idx = i
            result["title_at_index"] = i
            break

    if title_idx is None:
        # No title placeholder — slide has no title (caught separately)
        result["issues"].append("no_title_placeholder")
        return result

    # Shapes before the title in AT reading order
    pre_title = shapes[:title_idx]
    result["shapes_before_title"] = len(pre_title)

    text_before_title = []
    for shape in pre_title:
        if _shape_has_text(shape):
            text = shape.text_frame.text.strip()[:60]
            text_before_title.append({"name": shape.name, "text_preview": text})

    result["text_shapes_before_title"] = text_before_title

    if text_before_title:
        result["issues"].append("text_before_title")

    # Two-column layout detection
    # Text shapes in the body area (below top 25% of slide)
    mid_x = prs_width / 2
    body_top = prs_height * 0.25
    left_body = []
    right_body = []

    for shape in shapes:
        if not _shape_has_text(shape):
            continue
        if _is_title_placeholder(shape):
            continue
        try:
            shape_top = shape.top or 0
            if shape_top < body_top:
                continue
            center_x = (shape.left or 0) + (shape.width or 0) / 2
            if center_x < mid_x:
                left_body.append(shape.name)
            else:
                right_body.append(shape.name)
        except Exception:
            pass

    if len(left_body) >= 1 and len(right_body) >= 1:
        result["suspected_columns"] = True
        result["column_evidence"] = (
            f"Left-half shapes: {left_body[:3]}; Right-half shapes: {right_body[:3]}"
        )
        result["issues"].append("suspected_columns")

    return result


# ---------------------------------------------------------------------------
# Metadata check
# ---------------------------------------------------------------------------

def check_metadata(prs) -> list:
    findings = []
    title = getattr(prs.core_properties, "title", None) or ""
    if not title.strip():
        findings.append({
            "rule": "PPTX.META.TITLE",
            "severity": "Error",
            "confidence": "High",
            "wcag": "2.4.2",
            "message": (
                "Presentation title is not set. Screen readers announce the title "
                "when the file is opened. Browsers and OS task bars also display it."
            ),
            "fix": (
                "File → Info → Properties → Title. "
                "Or File → Info → Advanced Properties → Summary → Title."
            ),
        })

    language = getattr(prs.core_properties, "language", None) or ""
    if not language.strip():
        findings.append({
            "rule": "PPTX.META.LANG",
            "severity": "Error",
            "confidence": "High",
            "wcag": "3.1.1",
            "message": (
                "Presentation language is not set in document properties. "
                "Screen readers use this to select the correct speech synthesizer."
            ),
            "fix": (
                "File → Info → Properties → Advanced Properties → Summary → Language. "
                "Also set the proofing language: Review → Language → Set Proofing Language."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Slide title checks
# ---------------------------------------------------------------------------

def check_slide_titles(prs) -> list:
    findings = []
    title_texts = []

    no_title_slides = []
    for i, slide in enumerate(prs.slides, 1):
        title_shape = slide.shapes.title
        if title_shape is None or not title_shape.has_text_frame:
            no_title_slides.append(i)
            title_texts.append(None)
        else:
            t = title_shape.text_frame.text.strip()
            title_texts.append(t if t else None)
            if not t:
                no_title_slides.append(i)

    if no_title_slides:
        findings.append({
            "rule": "PPTX.SLIDE.TITLE",
            "severity": "Error",
            "confidence": "High",
            "wcag": "2.4.6",
            "message": (
                f"{len(no_title_slides)} slide(s) have no title: "
                f"slides {no_title_slides[:10]}. "
                "Screen reader users navigate presentations by slide title. "
                "Untitled slides are indistinguishable from one another."
            ),
            "fix": (
                "Click the 'Click to add title' placeholder on each slide and type a "
                "descriptive title. If the placeholder was deleted, add it back: "
                "Insert → Text Box is NOT sufficient — use the title layout placeholder."
            ),
            "outcome": (
                "A screen reader user navigating by slide title hears only a slide number "
                "with no description. In a 30-slide deck, they must listen to every slide "
                "to find the one they need."
            ),
        })

    # Duplicate title check
    seen = Counter()
    for t in title_texts:
        if t:
            seen[t.lower()] += 1
    duplicates = [t for t, count in seen.items() if count > 1]
    if duplicates:
        findings.append({
            "rule": "PPTX.SLIDE.TITLE_DUP",
            "severity": "Warning",
            "confidence": "High",
            "wcag": "2.4.6",
            "message": (
                f"{len(duplicates)} duplicate slide title(s) found: "
                f"{[d[:40] for d in duplicates[:5]]}. "
                "Duplicate titles prevent screen reader users from distinguishing slides "
                "in the Navigation Pane."
            ),
            "fix": (
                "Make every slide title unique. For slides in a series, number them: "
                "'Background — Part 1', 'Background — Part 2'."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Speaker notes check
# ---------------------------------------------------------------------------

def check_notes(prs) -> list:
    """Check for slides with complex visual content but no speaker notes."""
    slides_without_notes = []
    complex_visual_slides = []

    for i, slide in enumerate(prs.slides, 1):
        has_notes = False
        if slide.has_notes_slide:
            notes_text = slide.notes_slide.notes_text_frame.text.strip()
            has_notes = bool(notes_text)

        # Detect slides with images or charts but no notes
        has_visuals = any(
            _is_graphical_shape(s) for s in slide.shapes
        )
        if has_visuals and not has_notes:
            complex_visual_slides.append(i)

        if not has_notes:
            slides_without_notes.append(i)

    findings = []
    if complex_visual_slides:
        findings.append({
            "rule": "PPTX.SLIDE.NOTES",
            "severity": "Warning",
            "confidence": "Medium",
            "wcag": "1.1.1",
            "message": (
                f"{len(complex_visual_slides)} slide(s) contain images or charts "
                "but have no speaker notes: slides "
                f"{complex_visual_slides[:10]}. "
                "Screen reader users rely on notes to understand complex visuals "
                "that alt text alone cannot fully describe."
            ),
            "fix": (
                "View → Notes. Add explanatory text describing the key information "
                "conveyed by the chart or image — not just what it looks like, "
                "but what conclusion the audience should draw from it."
            ),
            "outcome": (
                "A JAWS or NVDA user listening to this slide hears the alt text "
                "but misses the narrative context a sighted presenter would provide. "
                "Notes are the only channel for that context."
            ),
        })
    return findings


# ---------------------------------------------------------------------------
# Reading order — full presentation analysis
# ---------------------------------------------------------------------------

def check_reading_order(prs) -> list:
    """
    Analyze reading order across all slides.

    Reading order for AT = XML order in <p:spTree> = slide.shapes iteration order.
    The WebAIM guidance: Selection Pane bottom-to-top = first-to-last read.
    In python-pptx: shapes[0] = first read, shapes[-1] = last read.

    Every presentation gets a PPTX.ORDER.VERIFY finding (manual review required).
    Additional findings fire when automated heuristics detect specific problems.
    """
    findings = []

    try:
        prs_width = prs.slide_width or (10 * EMU_PER_INCH)
        prs_height = prs.slide_height or (7.5 * EMU_PER_INCH)
    except Exception:
        prs_width = 10 * EMU_PER_INCH
        prs_height = 7.5 * EMU_PER_INCH

    slides_with_prelude = []    # text content before title
    slides_with_columns = []   # suspected multi-column layout
    column_details = []

    for i, slide in enumerate(prs.slides):
        ro = analyze_slide_reading_order(slide, i, prs_width, prs_height)

        if ro["text_shapes_before_title"]:
            slides_with_prelude.append({
                "slide": i + 1,
                "shapes": ro["text_shapes_before_title"],
            })

        if ro["suspected_columns"]:
            slides_with_columns.append(i + 1)
            column_details.append({
                "slide": i + 1,
                "evidence": ro["column_evidence"],
            })

    # Specific finding: text read before slide title
    if slides_with_prelude:
        affected = [s["slide"] for s in slides_with_prelude]
        findings.append({
            "rule": "PPTX.ORDER.TITLE_FIRST",
            "severity": "Warning",
            "confidence": "High",
            "wcag": "1.3.2",
            "message": (
                f"{len(slides_with_prelude)} slide(s) have text shapes that appear "
                "before the title in AT reading order: slides "
                f"{affected[:10]}. "
                "Screen readers will announce this text BEFORE the slide title."
            ),
            "fix": (
                "Open the selection pane: Home → Arrange → Selection Pane. "
                "The title shape should be at the BOTTOM of the list (read first). "
                "Drag shapes to reorder. In python-pptx terms: title should be "
                "shapes[0] in the spTree."
            ),
            "outcome": (
                "A NVDA or JAWS user navigating slides by title hears the wrong "
                "content announced first, breaking their ability to orient to the slide."
            ),
        })

    # Specific finding: suspected columns needing manual verification
    if slides_with_columns:
        findings.append({
            "rule": "PPTX.ORDER.COLUMNS",
            "severity": "Info",
            "confidence": "Medium",
            "wcag": "1.3.2",
            "message": (
                f"{len(slides_with_columns)} slide(s) appear to use a two-column layout "
                f"(text shapes in both left and right halves): slides {slides_with_columns[:10]}. "
                "Multi-column layouts require manual verification — AT reads shapes in "
                "XML order, which may read the entire left column before the right column, "
                "or interleave them incorrectly."
            ),
            "fix": (
                "In Selection Pane, verify shapes are ordered to match intended reading "
                "sequence (e.g., H1: left-col, H2: left-col, then right-col content — "
                "or row-by-row if the layout is a side-by-side comparison). "
                "There is no single correct answer — the order must match the intended narrative."
            ),
            "outcome": (
                "If column order is wrong, a screen reader user hears all of the left "
                "column first, then all of the right — breaking any sentence, list, or "
                "argument that spans both columns."
            ),
            "manual_review": True,
            "details": column_details,
        })

    # Always: mandatory AT verification finding
    findings.append({
        "rule": "PPTX.ORDER.VERIFY",
        "severity": "Info",
        "confidence": "High",
        "wcag": "1.3.2",
        "message": (
            "Reading order requires manual verification using the Selection Pane "
            "and/or testing with a screen reader. Automated analysis can detect "
            "structural signals but cannot confirm correct logical sequence for "
            "every layout type."
        ),
        "fix": (
            "Home → Arrange → Selection Pane. "
            "The BOTTOM item is read FIRST by assistive technology. "
            "Verify each slide's shape order matches the intended reading sequence. "
            "Test with NVDA (Insert+Down for continuous reading) or JAWS."
        ),
        "manual_review": True,
        "outcome": (
            "If reading order is not verified, any slide with non-trivial layout — "
            "columns, overlapping shapes, layered text boxes — may be read in the "
            "wrong sequence by JAWS, NVDA, or Narrator users."
        ),
    })

    return findings


# ---------------------------------------------------------------------------
# Image alt text checks
# ---------------------------------------------------------------------------

def check_alt_text(prs) -> list:
    findings = []
    missing = []
    poor_quality = []

    for i, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if not _is_graphical_shape(shape):
                continue
            alt, is_decorative = _get_alt_text(shape)

            if is_decorative:
                continue  # explicitly marked decorative — OK

            if alt is None:
                # No cNvPr descr attribute at all
                missing.append({
                    "slide": i,
                    "shape": shape.name,
                    "reason": "no alt text element",
                })
            elif not alt.strip():
                # Empty string — could be intentional (decorative) or forgotten
                missing.append({
                    "slide": i,
                    "shape": shape.name,
                    "reason": "empty alt text (not marked decorative)",
                })
            elif len(alt.strip()) < 5:
                poor_quality.append({
                    "slide": i,
                    "shape": shape.name,
                    "alt": alt.strip(),
                })
            elif alt.strip().lower() in (
                "image", "picture", "photo", "graphic", "chart", "figure",
                "screenshot", "image1", "picture1",
            ):
                poor_quality.append({
                    "slide": i,
                    "shape": shape.name,
                    "alt": alt.strip(),
                })

    if missing:
        findings.append({
            "rule": "PPTX.IMG.ALT",
            "severity": "Error",
            "confidence": "High",
            "wcag": "1.1.1",
            "message": (
                f"{len(missing)} image(s) or chart(s) are missing alt text "
                "and are not marked as decorative. "
                f"Affected: slides {list({m['slide'] for m in missing})[:8]}."
            ),
            "fix": (
                "Right-click the image → Edit Alt Text. "
                "Enter a description of the image's content and its relevance to the slide. "
                "If the image adds no information, click 'Mark as decorative'. "
                "Do NOT use 'Generate a description for me' — AI-generated descriptions "
                "are often inaccurate and are not a substitute for human-authored alt text."
            ),
            "details": missing[:10],
        })

    if poor_quality:
        findings.append({
            "rule": "PPTX.IMG.ALT_QUALITY",
            "severity": "Warning",
            "confidence": "Medium",
            "wcag": "1.1.1",
            "message": (
                f"{len(poor_quality)} image(s) have placeholder or generic alt text "
                f"that does not meaningfully describe content: "
                f"{[p['alt'] for p in poor_quality[:5]]}."
            ),
            "fix": (
                "Replace generic alt text (e.g., 'Image', 'Chart') with a description "
                "of what the image shows and why it matters to the presentation."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Table checks
# ---------------------------------------------------------------------------

def check_tables(prs) -> list:
    findings = []
    tables_without_headers = []

    for i, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if not shape.has_table:
                continue
            table = shape.table
            # Check if first row is styled as header
            # In python-pptx, table.first_row attribute (bool) reflects the
            # table's "Header Row" checkbox in the Table Design tab
            try:
                has_header = table.first_row
            except AttributeError:
                # Older python-pptx — inspect XML directly
                tbl_el = shape.table._tbl
                tblPr = tbl_el.find(
                    "{http://schemas.openxmlformats.org/drawingml/2006/main}tblPr"
                )
                has_header = False
                if tblPr is not None:
                    # firstRow="1" in tblPr means header row banding enabled
                    has_header = tblPr.get("firstRow", "0") == "1"

            if not has_header:
                tables_without_headers.append({"slide": i, "shape": shape.name})

    if tables_without_headers:
        findings.append({
            "rule": "PPTX.TABLE.HEADER",
            "severity": "Warning",
            "confidence": "Medium",
            "wcag": "1.3.1",
            "message": (
                f"{len(tables_without_headers)} table(s) do not have the header row "
                "marked. Without this, screen readers cannot identify column headers "
                "when navigating cell by cell. "
                f"Affected: {[t['slide'] for t in tables_without_headers[:8]]}."
            ),
            "fix": (
                "Click in the table → Table Design tab → check 'Header Row' in "
                "Table Style Options. Also check 'First Column' if column headers are present."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Media / caption checks
# ---------------------------------------------------------------------------

def check_media(prs) -> list:
    findings = []
    media_without_notes = []

    for i, slide in enumerate(prs.slides, 1):
        has_media = any(
            int(s.shape_type) in (MSO_MEDIA, 6)
            for s in slide.shapes
        )
        if has_media:
            has_notes = (
                slide.has_notes_slide
                and bool(slide.notes_slide.notes_text_frame.text.strip())
            )
            if not has_notes:
                media_without_notes.append(i)

    if media_without_notes:
        findings.append({
            "rule": "PPTX.MEDIA.CAPTIONS",
            "severity": "Warning",
            "confidence": "Medium",
            "wcag": "1.2.2",
            "message": (
                f"{len(media_without_notes)} slide(s) contain embedded media "
                "but have no speaker notes providing a transcript or caption reference: "
                f"slides {media_without_notes[:10]}."
            ),
            "fix": (
                "For embedded video: ensure captions are burned in or a side-by-side "
                "transcript is linked. Add a note: 'Video transcript available at...' "
                "For embedded audio: add a full text transcript in the notes."
            ),
            "outcome": (
                "Deaf and hard-of-hearing users, and screen reader users who cannot "
                "play media, receive no equivalent information from the slide."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Section name checks
# ---------------------------------------------------------------------------

def check_sections(prs) -> list:
    findings = []
    try:
        sections = prs.sections
        if not sections:
            return findings
        generic = []
        seen_names = Counter()
        for section in sections:
            name = section.name.strip() if section.name else ""
            canon = name.lower()
            seen_names[canon] += 1
            if canon in GENERIC_SECTION_NAMES:
                generic.append(name)
        if generic:
            findings.append({
                "rule": "PPTX.SECTION.NAME",
                "severity": "Warning",
                "confidence": "High",
                "wcag": "2.4.6",
                "message": (
                    f"{len(generic)} section(s) have generic names: {generic}. "
                    "Screen readers announce section names when navigating."
                ),
                "fix": "Right-click the section divider → Rename Section. Use a descriptive name.",
            })
        duplicates = [n for n, c in seen_names.items() if c > 1]
        if duplicates:
            findings.append({
                "rule": "PPTX.SECTION.DUP",
                "severity": "Warning",
                "confidence": "High",
                "wcag": "2.4.6",
                "message": (
                    f"Duplicate section names: {duplicates}. "
                    "Users cannot distinguish between sections with the same name."
                ),
                "fix": "Rename duplicate sections to be unique.",
            })
    except Exception:
        pass
    return findings


# ---------------------------------------------------------------------------
# Hyperlink checks
# ---------------------------------------------------------------------------

def check_hyperlinks(prs) -> list:
    findings = []
    vague = []

    for i, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if run.hyperlink and run.hyperlink.address:
                        text = run.text.strip()
                        if not text or VAGUE_LINK_RE.match(text):
                            vague.append({
                                "slide": i,
                                "text": text or "(empty)",
                                "url": run.hyperlink.address[:60],
                            })

    if vague:
        findings.append({
            "rule": "PPTX.LINKS.TEXT",
            "severity": "Warning",
            "confidence": "High",
            "wcag": "2.4.4",
            "message": (
                f"{len(vague)} hyperlink(s) have non-descriptive anchor text. "
                f"Examples: {[v['text'] for v in vague[:5]]}."
            ),
            "fix": (
                "Select the link text → Insert → Link → change 'Text to display' "
                "to a description of the destination, e.g., "
                "'Medication Authorization Form (PDF)' instead of 'click here'."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Grouped shapes check
# ---------------------------------------------------------------------------

def check_grouped_shapes(prs) -> list:
    """Check grouped shapes for alt text.

    Grouped shapes in PowerPoint are treated as a single unit by screen readers.
    If the group doesn't have alt text, the content of all shapes inside
    the group is effectively hidden from assistive technology users.
    """
    findings = []
    groups_no_alt = []

    for i, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            try:
                if int(shape.shape_type) == 6:  # MSO_GROUP_SHAPE
                    alt_text, is_decorative = _get_alt_text(shape)
                    if is_decorative:
                        continue
                    if not alt_text or not alt_text.strip():
                        groups_no_alt.append({"slide": i, "name": shape.name})
            except Exception:
                pass

    if groups_no_alt:
        findings.append({
            "rule": "PPTX.GROUP.ALT",
            "severity": "Error",
            "confidence": "High",
            "wcag": "1.1.1",
            "message": (
                f"{len(groups_no_alt)} grouped shape(s) are missing alt text. "
                "Screen readers treat groups as single objects — without alt text, "
                "the content of all shapes inside is hidden. "
                f"Affected: slides {list({g['slide'] for g in groups_no_alt})[:8]}."
            ),
            "fix": (
                "Right-click the group → Edit Alt Text → describe what the group "
                "represents as a whole. If decorative, mark as decorative."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Animations / transitions check
# ---------------------------------------------------------------------------

_P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


def check_animations(pptx_path: Path) -> list:
    """Check for auto-advancing transitions and auto-playing animations.

    Auto-advancing slides and animations create timing barriers for users
    who need more time to read content. WCAG 2.2.1 requires users to be
    able to turn off, adjust, or extend time limits.
    """
    findings = []
    auto_advance_slides = []
    animated_slides = []

    try:
        with ZipFile(str(pptx_path), "r") as zf:
            slide_files = sorted(
                n for n in zf.namelist()
                if n.startswith("ppt/slides/slide") and n.endswith(".xml")
            )
            for sf in slide_files:
                slide_num = sf.replace("ppt/slides/slide", "").replace(".xml", "")
                try:
                    slide_num = int(slide_num)
                except ValueError:
                    continue

                tree = etree.parse(zf.open(sf))
                root = tree.getroot()

                # Check for auto-advance transition (advTm attribute on p:transition)
                for trans in root.iter(f"{{{_P_NS}}}transition"):
                    adv_tm = trans.get("advTm")
                    if adv_tm is not None:
                        try:
                            ms = int(adv_tm)
                            auto_advance_slides.append({
                                "slide": slide_num,
                                "seconds": round(ms / 1000, 1),
                            })
                        except ValueError:
                            pass

                # Check for animations (p:timing/p:tnLst presence)
                for timing in root.iter(f"{{{_P_NS}}}timing"):
                    tn_lst = timing.find(f".//{{{_P_NS}}}tnLst")
                    if tn_lst is not None and len(tn_lst) > 0:
                        animated_slides.append(slide_num)
                        break

    except (BadZipFile, Exception):
        pass

    if auto_advance_slides:
        details = [f"slide {a['slide']} ({a['seconds']}s)"
                   for a in auto_advance_slides[:5]]
        findings.append({
            "rule": "PPTX.TRANSITION.AUTO",
            "severity": "Warning",
            "confidence": "High",
            "wcag": "2.2.1",
            "message": (
                f"{len(auto_advance_slides)} slide(s) have auto-advance timing set: "
                f"{', '.join(details)}. "
                "Auto-advancing slides create a time barrier — users who read slowly "
                "or use assistive technology may not finish before the slide changes."
            ),
            "fix": (
                "Transitions tab → uncheck 'After' (auto-advance) for all slides. "
                "Use 'On Mouse Click' instead so users control the pace."
            ),
        })

    if len(animated_slides) > 5:
        findings.append({
            "rule": "PPTX.ANIM.EXCESSIVE",
            "severity": "Info",
            "confidence": "Medium",
            "wcag": "2.3.3",
            "message": (
                f"{len(animated_slides)} slide(s) use animations: "
                f"slides {animated_slides[:10]}. "
                "Excessive animation can distract users and trigger vestibular "
                "disorders. Content should be understandable without animations."
            ),
            "fix": (
                "Review whether each animation adds meaning. "
                "Remove purely decorative animations. Ensure all animated content "
                "is also readable when animations are disabled."
            ),
        })

    return findings


# ---------------------------------------------------------------------------
# Main scan function
# ---------------------------------------------------------------------------

def scan_pptx(pptx_path: Path) -> dict:
    result = {
        "file": pptx_path.name,
        "path": str(pptx_path),
        "format": "pptx",
        "slide_count": 0,
        "findings": [],
        "errors": [],
    }

    try:
        prs = Presentation(str(pptx_path))
        result["slide_count"] = len(prs.slides)

        all_findings = []
        all_findings.extend(check_metadata(prs))
        all_findings.extend(check_slide_titles(prs))
        all_findings.extend(check_notes(prs))
        all_findings.extend(check_reading_order(prs))
        all_findings.extend(check_alt_text(prs))
        all_findings.extend(check_tables(prs))
        all_findings.extend(check_media(prs))
        all_findings.extend(check_sections(prs))
        all_findings.extend(check_hyperlinks(prs))
        all_findings.extend(check_grouped_shapes(prs))
        all_findings.extend(check_animations(pptx_path))

        result["findings"] = all_findings

    except Exception as e:
        result["errors"].append(f"Could not open or analyze file: {e}")

    return result


def scan_folder(folder: Path) -> list:
    return [scan_pptx(p) for p in sorted(folder.glob("*.pptx"))]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scan PowerPoint (.pptx) files for accessibility issues."
    )
    parser.add_argument("path", help="PPTX file or folder containing PPTX files")
    parser.add_argument("--output", help="Write JSON output to this file")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args()

    target = Path(args.path)
    if target.is_dir():
        results = scan_folder(target)
    elif target.is_file():
        results = [scan_pptx(target)]
    else:
        sys.exit(f"ERROR: Path not found: {target}")

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"JSON written to {args.output}")
    elif args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            errs = sum(1 for f in r["findings"] if f.get("severity") == "Error")
            warns = sum(1 for f in r["findings"] if f.get("severity") == "Warning")
            manual = sum(1 for f in r["findings"] if f.get("manual_review"))
            print(f"\n{r['file']}")
            print(f"  Slides: {r.get('slide_count', 0)}")
            print(f"  Findings: {errs} errors, {warns} warnings, {manual} manual review")
            for f in r["findings"]:
                sev = f.get("severity", "?")
                rule = f.get("rule", "?")
                msg = f.get("message", "")[:90]
                marker = "⚠️" if f.get("manual_review") else ""
                print(f"    [{sev}] {rule}: {msg} {marker}")


if __name__ == "__main__":
    sys.exit(main())
