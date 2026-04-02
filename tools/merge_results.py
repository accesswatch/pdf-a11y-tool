"""
merge_results.py — Merge Multiple Scan Result JSONs into a Single Audit
========================================================================
When scanning files individually (to avoid subfolder recursion, or to run
separate batches), each run produces its own JSON file.  This tool merges
those individual result files into one audit dict, regenerates the overall
score / grade, and optionally writes the unified Markdown + HTML reports.

Usage:
    python tools/merge_results.py documents/temp_*.json
    python tools/merge_results.py documents/temp_*.json --output documents/scan_results.json
    python tools/merge_results.py a.json b.json c.json --json-only
    python tools/merge_results.py documents/temp_*.json --report-name PDF-ACCESSIBILITY-AUDIT
    python tools/merge_results.py documents/temp_*.json --cleanup

Options:
    --output       Path for the merged JSON (default: scan_results.json next to first input)
    --json-only    Skip Markdown / HTML report generation
    --report-name  Base name for reports (default: ACCESSIBILITY-AUDIT)
    --cleanup      Delete the input temp JSON files after a successful merge

Output JSON has the same structure as scan_all.py produces, so it can be
consumed by report_md.py, report_html.py, and the MCP server tools without
any changes.

This file is PERMANENT — do not delete.
"""

import sys
import json
import argparse
import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Report-generator imports (optional — missing → reports skipped)
# ---------------------------------------------------------------------------
try:
    from report_md import generate_report as generate_md_report
    _HAS_REPORT_MD = True
except ImportError:
    _HAS_REPORT_MD = False

try:
    from report_html import generate_report as generate_html_report
    _HAS_REPORT_HTML = True
except ImportError:
    _HAS_REPORT_HTML = False


# ---------------------------------------------------------------------------
# Core merge logic (reusable from other Python code)
# ---------------------------------------------------------------------------

def merge_scan_results(json_paths: list[Path]) -> dict:
    """Read and merge multiple scan-result JSON files into one audit dict.

    Each input file must have the ``scan_all.py`` output shape::

        { "files": [ { "score": N, "findings": [...], ... } ], ... }

    Returns a merged audit dict ready for ``report_md.generate_report()``
    and ``report_html.generate_report()``.
    """
    all_files: list[dict] = []

    for p in json_paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        all_files.extend(data.get("files", []))

    # Aggregate scores
    scores = [fe["score"] for fe in all_files]
    avg = round(sum(scores) / len(scores)) if scores else 0
    if avg >= 90:
        grade = "A"
    elif avg >= 80:
        grade = "B"
    elif avg >= 70:
        grade = "C"
    elif avg >= 60:
        grade = "D"
    else:
        grade = "F"

    # Count severities
    sev_counts: dict[str, int] = {}
    for fe in all_files:
        for f in fe.get("findings", []):
            sev = f.get("severity", "Info")
            sev_counts[sev] = sev_counts.get(sev, 0) + 1

    # Count file types
    type_counts: dict[str, int] = {}
    for fe in all_files:
        t = fe.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "scan_date": datetime.datetime.now().isoformat(timespec="seconds"),
        "target": str(json_paths[0].parent) if json_paths else ".",
        "summary": {
            "total_files": len(all_files),
            "score": avg,
            "grade": grade,
            "errors": sev_counts.get("Error", 0),
            "warnings": sev_counts.get("Warning", 0),
            "info": sev_counts.get("Info", 0),
            "by_type": type_counts,
        },
        "files": all_files,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Merge individual scan-result JSON files into one audit and generate reports"
    )
    parser.add_argument(
        "inputs", nargs="+", metavar="FILE",
        help="Scan-result JSON files to merge (supports shell globs)"
    )
    parser.add_argument(
        "--output", default=None,
        help="Output path for merged JSON (default: scan_results.json next to first input)"
    )
    parser.add_argument(
        "--json-only", action="store_true",
        help="Write only the merged JSON — skip Markdown and HTML reports"
    )
    parser.add_argument(
        "--report-name", default="ACCESSIBILITY-AUDIT", metavar="STEM",
        help="Base filename for reports, e.g. PDF-ACCESSIBILITY-AUDIT (default: ACCESSIBILITY-AUDIT)"
    )
    parser.add_argument(
        "--cleanup", action="store_true",
        help="Delete the input JSON files after a successful merge"
    )
    args = parser.parse_args()

    # Resolve input paths
    paths = [Path(p).resolve() for p in args.inputs]
    missing = [p for p in paths if not p.exists()]
    if missing:
        sys.exit(f"ERROR: File(s) not found: {', '.join(str(m) for m in missing)}")
    if not paths:
        sys.exit("ERROR: No input files specified.")

    print(f"Merging {len(paths)} scan result file(s)…")
    for p in paths:
        print(f"  + {p.name}")

    audit = merge_scan_results(paths)
    s = audit["summary"]
    print(f"\nOverall: {s['score']}/100 Grade {s['grade']} "
          f"| {s['errors']}E {s['warnings']}W {s['info']}I "
          f"| {s['total_files']} files")

    # Alt text analysis summary
    alt_count = sum(1 for fe in audit["files"] if fe.get("alt_text_analysis"))
    if alt_count:
        print(f"Files with alt text analysis: {alt_count}/{s['total_files']}")

    # Write merged JSON
    if args.output:
        out = Path(args.output).resolve()
    else:
        out = paths[0].parent / "scan_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(audit, indent=2, default=str, ensure_ascii=False),
                   encoding="utf-8")
    print(f"\nMerged JSON: {out}")

    # Generate reports
    if not args.json_only:
        report_dir = out.parent
        stem = args.report_name

        if _HAS_REPORT_MD:
            md_path = report_dir / f"{stem}.md"
            md_path.write_text(generate_md_report(audit), encoding="utf-8")
            print(f"Markdown report: {md_path}")
        else:
            print("Warning: report_md.py not found — skipping Markdown report.")

        if _HAS_REPORT_HTML:
            html_path = report_dir / f"{stem}.html"
            html_path.write_text(generate_html_report(audit), encoding="utf-8")
            print(f"HTML report: {html_path}")
        else:
            print("Warning: report_html.py not found — skipping HTML report.")

    # Clean up temp files
    if args.cleanup:
        for p in paths:
            p.unlink()
        print(f"Cleaned up {len(paths)} input file(s)")

    print("\nDone!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMerge interrupted by user (Ctrl+C).")
        sys.exit(130)
