"""
scan_metadata.py — PDF Accessibility Metadata Scanner
======================================================
Persistent utility for PDF accessibility audits.
Extracts: title, language, DisplayDocTitle, XMP metadata,
          PDF/UA identifier, producer, creator, dates.

Usage:
    python tools/scan_metadata.py <pdf_or_folder> [--json] [--output file.json]

Dependencies: pikepdf (pip install pikepdf)

This file is PERMANENT — do not delete. Used by agents and scan_all.py.
"""

import sys
import os
import json
import argparse
from pathlib import Path

try:
    import pikepdf
except ImportError:
    sys.exit("ERROR: pikepdf not installed. Run: pip install pikepdf")


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

def extract_metadata(pdf_path: Path) -> dict:
    """Extract all accessibility-relevant metadata from a PDF file."""
    result = {
        "file": pdf_path.name,
        "path": str(pdf_path),
        "pages": None,
        "title": None,
        "title_present": False,
        "language": None,
        "language_bcp47": None,
        "language_ok": None,   # None = can't determine without knowing expected lang
        "display_doc_title": False,
        "tagged": False,
        "xmp_present": False,
        "pdf_ua_identifier": False,
        "producer": None,
        "creator": None,
        "creation_date": None,
        "mod_date": None,
        "pdf_version": None,
        "file_size_kb": round(pdf_path.stat().st_size / 1024, 1),
        "findings": [],
        "errors": [],
    }

    try:
        with pikepdf.open(pdf_path) as pdf:
            result["pages"] = len(pdf.pages)
            result["pdf_version"] = str(pdf.pdf_version)

            # --- DocInfo dictionary ---
            docinfo = pdf.docinfo
            title = docinfo.get("/Title", None)
            if title:
                title_str = str(title)
                result["title"] = title_str
                result["title_present"] = bool(title_str.strip())
            else:
                result["title_present"] = False

            lang_raw = docinfo.get("/Lang", None)
            if lang_raw:
                result["language"] = str(lang_raw)
                result["language_bcp47"] = str(lang_raw).strip()

            result["producer"] = str(docinfo.get("/Producer", "")) or None
            result["creator"] = str(docinfo.get("/Creator", "")) or None
            result["creation_date"] = str(docinfo.get("/CreationDate", "")) or None
            result["mod_date"] = str(docinfo.get("/ModDate", "")) or None

            # --- Root-level /Lang (takes precedence over DocInfo for PDF/UA) ---
            root = pdf.Root
            root_lang = root.get("/Lang", None)
            if root_lang is not None:
                result["language"] = str(root_lang)
                result["language_bcp47"] = str(root_lang).strip()

            # --- MarkInfo → tagged ---
            mark_info = root.get("/MarkInfo", None)
            if mark_info:
                marked = mark_info.get("/Marked", None)
                result["tagged"] = bool(marked and str(marked) == "true")

            # --- ViewerPreferences → DisplayDocTitle ---
            viewer_prefs = root.get("/ViewerPreferences", None)
            if viewer_prefs:
                ddt = viewer_prefs.get("/DisplayDocTitle", None)
                result["display_doc_title"] = bool(ddt and str(ddt) == "true")

            # --- XMP metadata ---
            try:
                with pdf.open_metadata() as meta:
                    result["xmp_present"] = len(str(meta)) > 50  # non-trivial XMP
                    # Check for PDF/UA identifier
                    xmp_str = str(meta)
                    result["pdf_ua_identifier"] = "pdfuaid" in xmp_str.lower()
            except Exception:
                result["xmp_present"] = False

    except Exception as e:
        result["errors"].append(f"Could not open file: {e}")
        return result

    # --- Generate findings ---
    findings = result["findings"]

    if not result["title_present"]:
        findings.append({
            "rule": "PDFUA.METADATA.TITLE",
            "severity": "Error",
            "confidence": "High",
            "matterhorn": "12-001",
            "wcag": "2.4.2",
            "message": "Document title is absent or empty in DocInfo /Title.",
            "fix": "File → Document Properties → Description → Title field",
        })

    lang = result.get("language_bcp47") or ""
    if not lang:
        findings.append({
            "rule": "PDFUA.METADATA.LANG",
            "severity": "Error",
            "confidence": "High",
            "matterhorn": "11-001",
            "wcag": "3.1.1",
            "message": "No language declared (/Lang absent from Root and DocInfo).",
            "fix": "File → Document Properties → Advanced → Reading Options → Language",
        })
    elif lang.upper() in ("EN-US", "EN", "EN-GB"):
        # Flag for human review — we can't know the expected language from metadata alone
        findings.append({
            "rule": "PDFUA.METADATA.LANG.REVIEW",
            "severity": "Info",
            "confidence": "Medium",
            "matterhorn": "11-001",
            "wcag": "3.1.1",
            "message": f"Language is set to '{lang}'. Verify this is correct for the document content.",
            "fix": "If this is a Spanish document, change to 'es' or 'es-419'.",
        })

    if not result["display_doc_title"]:
        findings.append({
            "rule": "PDFBP.DISPLAY.DOCTITLE",
            "severity": "Warning",
            "confidence": "High",
            "matterhorn": "06-003",
            "wcag": "2.4.2",
            "message": "ViewerPreferences/DisplayDocTitle is not set to true.",
            "fix": "File → Document Properties → Initial View → Show: Document Title",
        })

    if not result["tagged"]:
        findings.append({
            "rule": "PDFUA.STRUCT.TAGGED",
            "severity": "Error",
            "confidence": "High",
            "matterhorn": "06-001",
            "wcag": "1.3.1",
            "message": "MarkInfo/Marked is false or absent — document is not tagged.",
            "fix": "Must be re-exported with tagging enabled or remediated in Acrobat.",
        })

    if not result["pdf_ua_identifier"]:
        findings.append({
            "rule": "PDFQ.METADATA.PDFUA",
            "severity": "Info",
            "confidence": "High",
            "matterhorn": "06-003",
            "wcag": None,
            "message": "PDF/UA identifier not present in XMP metadata.",
            "fix": "All Tools → Accessibility → Add PDF/UA Identifier (optional for compliance)",
        })

    return result


def scan_folder(folder: Path) -> list:
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        print(f"No PDF files found in {folder}", file=sys.stderr)
        return []
    return [extract_metadata(p) for p in pdfs]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scan PDF metadata for accessibility issues."
    )
    parser.add_argument("path", help="PDF file or folder containing PDFs")
    parser.add_argument("--output", help="Write JSON output to this file")
    parser.add_argument(
        "--json", action="store_true", help="Print JSON to stdout (default: table)"
    )
    args = parser.parse_args()

    target = Path(args.path)
    if target.is_dir():
        results = scan_folder(target)
    elif target.is_file():
        results = [extract_metadata(target)]
    else:
        sys.exit(f"ERROR: Path not found: {target}")

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"JSON written to {out_path}")

    if args.json or args.output:
        if not args.output:
            print(json.dumps(results, indent=2))
    else:
        # Human-readable table
        print(f"\n{'File':<55} {'Pg':>3}  {'Title':>5}  {'Lang':<8}  {'DDT':>3}  {'Tagged':>6}  {'Errors':>6}")
        print("-" * 100)
        for r in results:
            title_ok = "✅" if r["title_present"] else "❌"
            lang_val = r.get("language_bcp47") or "—"
            ddt = "✅" if r["display_doc_title"] else "❌"
            tagged = "✅" if r["tagged"] else "❌"
            errs = sum(1 for f in r["findings"] if f["severity"] == "Error")
            pages = r["pages"] or "?"
            print(f"{r['file']:<55} {pages:>3}  {title_ok:>5}  {lang_val:<8}  {ddt:>3}  {tagged:>6}  {errs:>6}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
