"""
scan_markdown.py -- Markdown (.md) Accessibility Scanner
=========================================================
Persistent utility for markdown document accessibility audits.
Checks against WCAG 2.2 AA mapped to markdown patterns.

Checks:
  Links:
    - Ambiguous link text (click here, read more, etc.)  [MD-A11Y.LINK.AMBIGUOUS]
    - Bare URL as link text                               [MD-A11Y.LINK.BARE_URL]
    - Links missing file type for downloads               [MD-A11Y.LINK.FILETYPE]

  Images:
    - Missing alt text                                    [MD-A11Y.IMG.ALT_MISSING]
    - Generic/filename alt text                           [MD-A11Y.IMG.ALT_QUALITY]

  Headings:
    - Multiple H1 headings                                [MD-A11Y.HEADING.MULTIPLE_H1]
    - Skipped heading levels                              [MD-A11Y.HEADING.SKIP]
    - No H1 heading                                       [MD-A11Y.HEADING.NO_H1]

  Tables:
    - Table without preceding description                 [MD-A11Y.TABLE.NO_DESC]
    - Empty header cell                                   [MD-A11Y.TABLE.EMPTY_HEADER]

  Emoji:
    - Emoji in headings                                   [MD-A11Y.EMOJI.HEADING]
    - Consecutive emoji sequences                         [MD-A11Y.EMOJI.CONSECUTIVE]

  Diagrams:
    - Mermaid without text description                    [MD-A11Y.DIAGRAM.MERMAID]
    - ASCII diagram without description                   [MD-A11Y.DIAGRAM.ASCII]

Usage:
    python tools/scan_markdown.py <file_or_folder> [--json] [--output file.json]

Dependencies: None (pure stdlib).

This file is PERMANENT -- do not delete. Used by agents and mcp_server.py.
"""

import sys
import json
import argparse
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Ambiguous link text patterns
# ---------------------------------------------------------------------------

AMBIGUOUS_EXACT = {
    "here", "click here", "read more", "learn more", "more", "more info",
    "link", "details", "info", "go", "see more", "continue", "start",
    "download", "view", "open", "submit", "this", "that",
}

AMBIGUOUS_STARTS = (
    "click here to", "read more about", "learn more about",
    "here to", "see more",
)

GENERIC_ALT = {
    "image", "screenshot", "photo", "picture", "img", "figure",
    "graphic", "icon", "logo", "banner", "diagram",
}

DOWNLOAD_EXTS = {".pdf", ".zip", ".docx", ".xlsx", ".pptx", ".epub", ".tar", ".gz"}


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _check_links(lines: list[str]) -> list[dict]:
    """Check for ambiguous and bare-URL link text."""
    findings = []
    link_re = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
    in_code_block = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        for m in link_re.finditer(line):
            text = m.group(1).strip()
            url = m.group(2).strip()
            lower = text.lower()

            # Skip badge links [![...](img)](url)
            if text.startswith("!["):
                continue

            if lower in AMBIGUOUS_EXACT:
                findings.append({
                    "rule": "MD-A11Y.LINK.AMBIGUOUS",
                    "severity": "Error",
                    "wcag": "2.4.4",
                    "line": i,
                    "message": f"Ambiguous link text: \"{text}\"",
                    "fix": "Replace with descriptive text that explains the link destination",
                })
            elif any(lower.startswith(p) for p in AMBIGUOUS_STARTS):
                findings.append({
                    "rule": "MD-A11Y.LINK.AMBIGUOUS",
                    "severity": "Error",
                    "wcag": "2.4.4",
                    "line": i,
                    "message": f"Ambiguous link text pattern: \"{text}\"",
                    "fix": "Rewrite link text to be self-descriptive without surrounding context",
                })
            elif re.match(r"https?://|www\.", lower):
                findings.append({
                    "rule": "MD-A11Y.LINK.BARE_URL",
                    "severity": "Warning",
                    "wcag": "2.4.4",
                    "line": i,
                    "message": f"URL used as link text: \"{text[:60]}\"",
                    "fix": "Replace URL text with a human-readable description",
                })

            # Check download links missing file type mention
            url_lower = url.lower()
            for ext in DOWNLOAD_EXTS:
                if url_lower.endswith(ext) and ext.lstrip(".") not in lower:
                    findings.append({
                        "rule": "MD-A11Y.LINK.FILETYPE",
                        "severity": "Warning",
                        "wcag": "2.4.4",
                        "line": i,
                        "message": f"Link to {ext} file does not mention file type in text: \"{text}\"",
                        "fix": f"Include \"{ext.upper().lstrip('.')}\" or the file type in the link text",
                    })
                    break

    return findings


def _check_images(lines: list[str]) -> list[dict]:
    """Check image alt text quality."""
    findings = []
    img_re = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    in_code_block = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        for m in img_re.finditer(line):
            alt = m.group(1).strip()
            src = m.group(2).strip()

            if not alt:
                findings.append({
                    "rule": "MD-A11Y.IMG.ALT_MISSING",
                    "severity": "Error",
                    "wcag": "1.1.1",
                    "line": i,
                    "message": f"Image missing alt text: {src[:60]}",
                    "fix": "Add descriptive alt text: ![Description of what the image shows](url)",
                })
            elif alt.lower() in GENERIC_ALT:
                findings.append({
                    "rule": "MD-A11Y.IMG.ALT_QUALITY",
                    "severity": "Warning",
                    "wcag": "1.1.1",
                    "line": i,
                    "message": f"Generic alt text: \"{alt}\"",
                    "fix": "Replace with specific description of what the image conveys",
                })
            elif re.match(r"^[\w-]+\.\w{2,4}$", alt):
                # Filename as alt text
                findings.append({
                    "rule": "MD-A11Y.IMG.ALT_QUALITY",
                    "severity": "Warning",
                    "wcag": "1.1.1",
                    "line": i,
                    "message": f"Filename used as alt text: \"{alt}\"",
                    "fix": "Replace filename with a meaningful description of the image",
                })

    return findings


def _check_headings(lines: list[str]) -> list[dict]:
    """Check heading hierarchy."""
    findings = []
    heading_re = re.compile(r"^(#{1,6})\s+(.+)")
    levels = []
    in_code_block = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        m = heading_re.match(line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            levels.append((i, level, text))

    # Check multiple H1
    h1s = [(ln, txt) for ln, lv, txt in levels if lv == 1]
    if len(h1s) > 1:
        for ln, txt in h1s[1:]:
            findings.append({
                "rule": "MD-A11Y.HEADING.MULTIPLE_H1",
                "severity": "Warning",
                "wcag": "1.3.1",
                "line": ln,
                "message": f"Multiple H1 headings -- \"{txt}\" should be H2",
                "fix": "Change to ## to maintain single H1 document structure",
            })

    # Check no H1
    if levels and not h1s:
        findings.append({
            "rule": "MD-A11Y.HEADING.NO_H1",
            "severity": "Warning",
            "wcag": "1.3.1",
            "line": levels[0][0],
            "message": "Document has no H1 heading",
            "fix": "Add a # heading as the document title or promote the first heading",
        })

    # Check skipped levels
    for idx in range(1, len(levels)):
        ln, level, _text = levels[idx]
        _pln, prev_level, _ptext = levels[idx - 1]
        if level > prev_level + 1:
            findings.append({
                "rule": "MD-A11Y.HEADING.SKIP",
                "severity": "Error",
                "wcag": "1.3.1",
                "line": ln,
                "message": f"Heading level skipped: H{prev_level} to H{level}",
                "fix": f"Use {'#' * (prev_level + 1)} instead of {'#' * level}",
            })

    return findings


def _check_tables(lines: list[str]) -> list[dict]:
    """Check table descriptions and header cells."""
    findings = []
    in_code_block = False
    table_start = None

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        is_table_row = "|" in stripped and stripped.startswith("|")
        is_separator = bool(re.match(r"^\|[\s:|-]+\|$", stripped))

        if is_table_row and table_start is None:
            table_start = i
            # Check for preceding description
            prev_idx = i - 2  # 0-indexed
            has_desc = False
            while prev_idx >= 0:
                prev = lines[prev_idx].strip()
                if not prev:
                    prev_idx -= 1
                    continue
                if prev.startswith("#"):
                    break  # heading only, no description
                has_desc = True
                break
            if not has_desc:
                findings.append({
                    "rule": "MD-A11Y.TABLE.NO_DESC",
                    "severity": "Warning",
                    "wcag": "1.3.1",
                    "line": i,
                    "message": "Table has no preceding text description",
                    "fix": "Add a sentence before the table explaining what data it contains",
                })

            # Check for empty header cells
            cells = [c.strip() for c in stripped.split("|")]
            # Filter out empty strings from split
            cells = [c for c in cells if c is not None]
            if cells and cells[0] == "":
                cells = cells[1:]
            if cells and cells[-1] == "":
                cells = cells[:-1]
            for idx, cell in enumerate(cells):
                if not cell.strip():
                    findings.append({
                        "rule": "MD-A11Y.TABLE.EMPTY_HEADER",
                        "severity": "Warning",
                        "wcag": "1.3.1",
                        "line": i,
                        "message": f"Empty header cell at column {idx + 1}",
                        "fix": "Add descriptive header text for every column",
                    })

        elif not is_table_row and not is_separator and table_start is not None:
            table_start = None

    return findings


def _check_emoji(lines: list[str]) -> list[dict]:
    """Check for emoji in headings and consecutive sequences."""
    findings = []
    # Broad emoji ranges
    emoji_re = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U0001F900-\U0001F9FF"  # supplemental
        "\U0001FA00-\U0001FA6F"  # chess & extended-A
        "\U0001FA70-\U0001FAFF"  # extended-A
        "\U00002600-\U000026FF"  # misc symbols
        "\U0000FE00-\U0000FE0F"  # variation selectors
        "\U0000200D"             # ZWJ
        "\U00002934-\U00002935"  # arrows
        "]+",
    )
    heading_re = re.compile(r"^#{1,6}\s+")
    in_code_block = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        matches = list(emoji_re.finditer(line))
        if not matches:
            continue

        if heading_re.match(line):
            for m in matches:
                findings.append({
                    "rule": "MD-A11Y.EMOJI.HEADING",
                    "severity": "Warning",
                    "wcag": "1.3.3",
                    "line": i,
                    "message": f"Emoji in heading: \"{m.group()}\"",
                    "fix": "Remove emoji from heading or replace with descriptive text",
                })

        # Check consecutive emoji (2+ in a row)
        for m in matches:
            if len(m.group()) >= 2:
                # Multiple emoji characters together
                findings.append({
                    "rule": "MD-A11Y.EMOJI.CONSECUTIVE",
                    "severity": "Info",
                    "wcag": "1.3.3",
                    "line": i,
                    "message": f"Consecutive emoji sequence: \"{m.group()[:20]}\"",
                    "fix": "Replace emoji sequence with descriptive text",
                })

    return findings


def _check_diagrams(lines: list[str]) -> list[dict]:
    """Check for Mermaid and ASCII diagrams without descriptions."""
    findings = []
    in_code_block = False
    block_lang = ""

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                in_code_block = False
                block_lang = ""
            else:
                in_code_block = True
                block_lang = stripped[3:].strip().lower()

                if block_lang == "mermaid":
                    # Check for preceding description
                    prev_idx = i - 2
                    has_desc = False
                    while prev_idx >= 0:
                        prev = lines[prev_idx].strip()
                        if not prev:
                            prev_idx -= 1
                            continue
                        if prev.startswith("#") or prev.startswith("```"):
                            break
                        has_desc = True
                        break
                    if not has_desc:
                        findings.append({
                            "rule": "MD-A11Y.DIAGRAM.MERMAID",
                            "severity": "Error",
                            "wcag": "1.1.1",
                            "line": i,
                            "message": "Mermaid diagram without text description",
                            "fix": "Add a paragraph before the diagram describing what it shows, "
                                   "then wrap the Mermaid source in a <details> block",
                        })
            continue

    # ASCII art detection: look for lines with heavy box-drawing chars outside code blocks
    ascii_re = re.compile(r"^[\s+\-|><^v*=]{10,}$")
    in_code_block = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        if ascii_re.match(stripped) and len(stripped) > 10:
            prev_idx = i - 2
            has_desc = False
            while prev_idx >= 0:
                prev = lines[prev_idx].strip()
                if not prev:
                    prev_idx -= 1
                    continue
                if prev.startswith("#"):
                    break
                has_desc = True
                break
            if not has_desc:
                findings.append({
                    "rule": "MD-A11Y.DIAGRAM.ASCII",
                    "severity": "Warning",
                    "wcag": "1.1.1",
                    "line": i,
                    "message": "Possible ASCII diagram without text description",
                    "fix": "Add a text description before the diagram and consider wrapping it in a <details> block",
                })

    return findings


# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------

def scan_markdown(file_path: Path) -> dict:
    """Scan a markdown file for accessibility issues.

    Args:
        file_path: Path to the .md file.

    Returns:
        Dict with keys: file, lines, findings, severity_counts.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}

    text = file_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    findings = []
    findings.extend(_check_links(lines))
    findings.extend(_check_images(lines))
    findings.extend(_check_headings(lines))
    findings.extend(_check_tables(lines))
    findings.extend(_check_emoji(lines))
    findings.extend(_check_diagrams(lines))

    # Sort by line number
    findings.sort(key=lambda f: f.get("line", 0))

    severity_counts = {"Error": 0, "Warning": 0, "Info": 0}
    for f in findings:
        sev = f.get("severity", "Info")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
        "file": str(file_path),
        "lines": len(lines),
        "findings": findings,
        "severity_counts": severity_counts,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan markdown files for accessibility issues")
    parser.add_argument("input", help="Path to .md file or folder")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--output", help="Write JSON to file")
    args = parser.parse_args()

    target = Path(args.input)
    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(target.rglob("*.md"))
    else:
        print(f"Not found: {target}", file=sys.stderr)
        sys.exit(1)

    all_results = []
    for f in files:
        result = scan_markdown(f)
        all_results.append(result)
        if not args.json:
            count = len(result.get("findings", []))
            print(f"  {f.name}: {count} finding(s)")

    if args.json or args.output:
        output = json.dumps(all_results if len(all_results) > 1 else all_results[0], indent=2)
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"Wrote {args.output}")
        else:
            print(output)
