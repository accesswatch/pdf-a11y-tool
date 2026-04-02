"""
scan_all.py — Multi-Format Accessibility Audit Orchestrator
============================================================
Scans a folder (or a single file) for accessibility issues across:
  - PDF  (.pdf)  → scan_metadata + scan_tags + scan_forms
  - Word (.docx) → scan_word
  - Excel (.xlsx)→ scan_excel
  - PowerPoint (.pptx) → scan_pptx
  - ePub (.epub) → scan_epub
  - Markdown (.md) → scan_markdown

Merges all findings per file, computes an aggregate accessibility score/grade,
writes a combined JSON result file, and automatically generates the final
dual-audience Markdown and HTML reports via report_md.py and report_html.py.

Usage:
    python tools/scan_all.py <folder_or_file> [--output results.json] [--verbose]
    python tools/scan_all.py <folder_or_file> --type pdf          # scan only PDFs
    python tools/scan_all.py <folder_or_file> --type word excel   # scan Word + Excel
    python tools/scan_all.py <folder_or_file> --json-only         # skip report generation

Supported --type values (case-insensitive, multiple allowed):
    pdf, word/docx, excel/xlsx, powerpoint/pptx, epub, markdown/md

Output JSON structure:
{
  "scan_date": "ISO-8601",
  "target": "/path/scanned",
  "summary": {
    "total_files": N,
    "errors": N, "warnings": N, "info": N,
    "score": 0-100, "grade": "A-F",
    "by_type": {"pdf": N, "docx": N, "xlsx": N, "pptx": N, "epub": N, "md": N}
  },
  "files": [
    {
      "file": "name.pdf",
      "path": "/full/path.pdf",
      "type": "pdf",
      "score": 0-100,
      "grade": "A-F",
      "findings": [...merged findings from all scanners...],
      "scanner_results": {
        "metadata": {...},   # PDF only
        "tags": {...},       # PDF only
        "forms": {...},      # PDF only
        "word": {...},       # DOCX only
        "excel": {...},      # XLSX only
        "pptx": {...},       # PPTX only
        "epub": {...},       # EPUB only
      }
    }
  ]
}

Scoring system:
  Error   = -10 points each (capped at -50 per file)
  Warning = -3  points each (capped at -21)
  Info    = -0  points (informational, not penalised)
  Start   = 100 points
  Floor   = 0 points (never negative)

Grade thresholds:
  90-100 = A   |  80-89 = B   |  70-79 = C   |  60-69 = D   |  0-59 = F

This file is PERMANENT — do not delete.
"""

import sys
import json
import shutil
import argparse
import datetime
from pathlib import Path
from typing import TypedDict
from zipfile import ZipFile, BadZipFile

# ---------------------------------------------------------------------------
# Scanner result schema (TypedDict for type-checker support)
# ---------------------------------------------------------------------------

class Finding(TypedDict, total=False):
    """Single accessibility finding from any scanner."""
    rule: str
    severity: str          # "Error" | "Warning" | "Info"
    confidence: str        # "High" | "Medium" | "Low"
    message: str
    fix: str


class ScanResult(TypedDict, total=False):
    """Return shape shared by all per-format scanner wrappers."""
    type: str              # e.g. "pdf", "docx", "xlsx", "pptx", "epub", "md"
    findings: list[Finding]
    scanner_results: dict


# ---------------------------------------------------------------------------
# Scanner imports — each is optional; missing scanners produce a warning only.
# ---------------------------------------------------------------------------
try:
    from scan_metadata import extract_metadata
    _HAS_META = True
except ImportError:
    _HAS_META = False

try:
    from scan_tags import scan_tags
    _HAS_TAGS = True
except ImportError:
    _HAS_TAGS = False

try:
    from scan_forms import scan_forms
    _HAS_FORMS = True
except ImportError:
    _HAS_FORMS = False

try:
    from scan_word import scan_word
    _HAS_WORD = True
except ImportError:
    _HAS_WORD = False

try:
    from scan_excel import scan_excel
    _HAS_EXCEL = True
except ImportError:
    _HAS_EXCEL = False

try:
    from scan_pptx import scan_pptx
    _HAS_PPTX = True
except ImportError:
    _HAS_PPTX = False

try:
    from scan_epub import scan_epub
    _HAS_EPUB = True
except ImportError:
    _HAS_EPUB = False

try:
    from scan_markdown import scan_markdown
    _HAS_MARKDOWN = True
except ImportError:
    _HAS_MARKDOWN = False

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
# Fix-tool imports — only needed when --fix is requested.
# ---------------------------------------------------------------------------
try:
    from fix_pdf import fix_pdf as _fix_pdf
    _HAS_FIX_PDF = True
except ImportError:
    _HAS_FIX_PDF = False

try:
    from fix_word import fix_word as _fix_word
    _HAS_FIX_WORD = True
except ImportError:
    _HAS_FIX_WORD = False

try:
    from fix_excel import fix_excel as _fix_excel
    _HAS_FIX_EXCEL = True
except ImportError:
    _HAS_FIX_EXCEL = False

try:
    from fix_pptx import fix_pptx as _fix_pptx
    _HAS_FIX_PPTX = True
except ImportError:
    _HAS_FIX_PPTX = False

try:
    from fix_epub import fix_epub as _fix_epub
    _HAS_FIX_EPUB = True
except ImportError:
    _HAS_FIX_EPUB = False

try:
    from fix_tiers import get_fixable_rules, TIER_LABELS
    _HAS_FIX_TIERS = True
except ImportError:
    _HAS_FIX_TIERS = False

# Alt text analysis imports -- optional, requires alt_text package + auth
try:
    from alt_text.client import generate_for_document
    from alt_text.scorer import score_alt_text, rank_alternatives, ranked_to_dict
    from alt_text.models import VISION_MODELS
    _HAS_ALT_TEXT = True
except ImportError:
    _HAS_ALT_TEXT = False

_FIX_DISPATCH = {
    "pdf":  ("_fix_pdf",  "_HAS_FIX_PDF"),
    "docx": ("_fix_word", "_HAS_FIX_WORD"),
    "xlsx": ("_fix_excel","_HAS_FIX_EXCEL"),
    "pptx": ("_fix_pptx", "_HAS_FIX_PPTX"),
    "epub": ("_fix_epub", "_HAS_FIX_EPUB"),
}


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

SEVERITY_PENALTY = {"Error": 10, "Warning": 3, "Info": 0}
ERROR_CAP = 50
WARNING_CAP = 21


def _score_file(findings: list) -> tuple[int, str]:
    """Compute a 0-100 accessibility score and A-F grade for one file."""
    errors   = sum(1 for f in findings if f.get("severity") == "Error")
    warnings = sum(1 for f in findings if f.get("severity") == "Warning")

    err_penalty  = min(errors   * SEVERITY_PENALTY["Error"],   ERROR_CAP)
    warn_penalty = min(warnings * SEVERITY_PENALTY["Warning"], WARNING_CAP)
    score = max(0, 100 - err_penalty - warn_penalty)

    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"

    return score, grade


def _aggregate_score(file_results: list) -> tuple[int, str]:
    """Average file scores for an overall audit score."""
    if not file_results:
        return 0, "F"
    scores = [f["score"] for f in file_results]
    avg = round(sum(scores) / len(scores))
    if avg >= 90: grade = "A"
    elif avg >= 80: grade = "B"
    elif avg >= 70: grade = "C"
    elif avg >= 60: grade = "D"
    else: grade = "F"
    return avg, grade


# ---------------------------------------------------------------------------
# Per-format scanners
# ---------------------------------------------------------------------------

def _scan_pdf(path: Path, verbose: bool) -> ScanResult:
    """Run all PDF scanners and merge findings."""
    findings = []
    scanner_results = {}

    if _HAS_META:
        if verbose:
            print(f"  [PDF] metadata …")
        meta = extract_metadata(path)
        scanner_results["metadata"] = meta
        findings.extend(meta.get("findings", []))
    else:
        print(f"  WARNING: scan_metadata.py not available — PDF metadata skipped.")

    if _HAS_TAGS:
        if verbose:
            print(f"  [PDF] tag tree …")
        tags = scan_tags(path)
        scanner_results["tags"] = tags
        findings.extend(tags.get("findings", []))
    else:
        print(f"  WARNING: scan_tags.py not available — PDF tag analysis skipped.")

    if _HAS_FORMS:
        if verbose:
            print(f"  [PDF] forms …")
        forms = scan_forms(path)
        scanner_results["forms"] = forms
        findings.extend(forms.get("findings", []))
    else:
        print(f"  WARNING: scan_forms.py not available — PDF form analysis skipped.")

    # Deduplicate findings by rule + message (can arise from metadata ↔ tags overlap)
    seen = set()
    unique_findings = []
    for f in findings:
        key = (f.get("rule", ""), f.get("message", ""))
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)

    return {
        "type": "pdf",
        "findings": unique_findings,
        "scanner_results": scanner_results,
    }


def _scan_docx(path: Path, verbose: bool) -> ScanResult:
    """Run Word scanner."""
    findings = []
    scanner_results = {}

    if _HAS_WORD:
        if verbose:
            print(f"  [DOCX] structure …")
        word = scan_word(path)
        scanner_results["word"] = word
        findings.extend(word.get("findings", []))
    else:
        print(f"  WARNING: scan_word.py not available — Word analysis skipped.")

    return {
        "type": "docx",
        "findings": findings,
        "scanner_results": scanner_results,
    }


def _scan_xlsx(path: Path, verbose: bool) -> ScanResult:
    """Run Excel scanner."""
    findings = []
    scanner_results = {}

    if _HAS_EXCEL:
        if verbose:
            print(f"  [XLSX] workbook …")
        excel = scan_excel(path)
        scanner_results["excel"] = excel
        findings.extend(excel.get("findings", []))
    else:
        print(f"  WARNING: scan_excel.py not available — Excel analysis skipped.")

    return {
        "type": "xlsx",
        "findings": findings,
        "scanner_results": scanner_results,
    }


def _scan_pptx(path: Path, verbose: bool) -> ScanResult:
    """Run PowerPoint scanner."""
    findings = []
    scanner_results = {}

    if _HAS_PPTX:
        if verbose:
            print(f"  [PPTX] presentation …")
        ppt = scan_pptx(path)
        scanner_results["pptx"] = ppt
        findings.extend(ppt.get("findings", []))
    else:
        print(f"  WARNING: scan_pptx.py not available — PowerPoint analysis skipped.")

    return {
        "type": "pptx",
        "findings": findings,
        "scanner_results": scanner_results,
    }


def _scan_epub(path: Path, verbose: bool) -> ScanResult:
    """Run ePub scanner."""
    findings = []
    scanner_results = {}

    if _HAS_EPUB:
        if verbose:
            print(f"  [EPUB] document …")
        epub = scan_epub(path)
        scanner_results["epub"] = epub
        findings.extend(epub.get("findings", []))
    else:
        print(f"  WARNING: scan_epub.py not available — ePub analysis skipped.")

    return {
        "type": "epub",
        "findings": findings,
        "scanner_results": scanner_results,
    }

def _scan_md(path: Path, verbose: bool) -> ScanResult:
    """Run Markdown scanner."""
    findings = []
    scanner_results = {}

    if _HAS_MARKDOWN:
        if verbose:
            print(f"  [MD] markdown \u2026")
        md = scan_markdown(path)
        scanner_results["markdown"] = md
        findings.extend(md.get("findings", []))
    else:
        print(f"  WARNING: scan_markdown.py not available \u2014 Markdown analysis skipped.")

    return {
        "type": "md",
        "findings": findings,
        "scanner_results": scanner_results,
    }

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

EXTENSION_MAP = {
    ".pdf":  _scan_pdf,
    ".docx": _scan_docx,
    ".xlsx": _scan_xlsx,
    ".pptx": _scan_pptx,
    ".epub": _scan_epub,
    ".md":   _scan_md,
}

# Natural-language aliases → canonical extensions for --type filtering
_TYPE_ALIASES: dict[str, set[str]] = {
    "pdf":        {".pdf"},
    "word":       {".docx"},
    "docx":       {".docx"},
    "excel":      {".xlsx"},
    "xlsx":       {".xlsx"},
    "spreadsheet": {".xlsx"},
    "powerpoint": {".pptx"},
    "pptx":       {".pptx"},
    "presentation": {".pptx"},
    "epub":       {".epub"},
    "markdown":   {".md"},
    "md":         {".md"},
}


def _resolve_type_filter(type_names: list[str] | None) -> set[str] | None:
    """Convert user-friendly type names to a set of extensions, or None for all."""
    if not type_names:
        return None
    exts: set[str] = set()
    for name in type_names:
        key = name.lower().strip(" .")
        if key in _TYPE_ALIASES:
            exts |= _TYPE_ALIASES[key]
        else:
            print(f"Warning: Unknown type '{name}' — ignored. "
                  f"Valid: {', '.join(sorted(_TYPE_ALIASES))}")
    return exts if exts else None


def _collect_files(target: Path, allowed_exts: set[str] | None = None) -> list[Path]:
    """Return all supported files under target (file or folder).

    Args:
        target: File or directory to scan.
        allowed_exts: If set, only collect files with these extensions.
                      None means all supported extensions.

    Skips:
    - Temporary Office files (~$*.docx, ~$*.xlsx, ~$*.pptx)
    - Hidden files and directories (starting with .)
    - System/lock files
    """
    active_exts = allowed_exts if allowed_exts else set(EXTENSION_MAP)

    if target.is_file():
        if target.suffix.lower() in active_exts and not target.name.startswith("~$"):
            return [target]
        return []

    results = []
    for p in target.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in active_exts:
            continue
        # Skip temp/lock files from Office
        if p.name.startswith("~$") or p.name.startswith(".~"):
            continue
        # Skip hidden directories
        if any(part.startswith(".") for part in p.relative_to(target).parts[:-1]):
            continue
        results.append(p)
    return sorted(results)


def _check_file_accessible(path: Path) -> tuple[bool, str]:
    """Check if a file can be opened and is not encrypted/password-protected.

    Returns (ok, reason). If ok is False, reason explains why.
    """
    ext = path.suffix.lower()
    try:
        if ext in (".docx", ".xlsx", ".pptx", ".epub"):
            # Office OOXML files are ZIP archives; encrypted ones are OLE compound docs
            try:
                with ZipFile(str(path), "r") as zf:
                    # If it opens as ZIP, check for encryption markers
                    if "EncryptedPackage" in zf.namelist():
                        return False, "File is password-protected (encrypted OOXML)"
                    return True, ""
            except BadZipFile:
                # Not a valid ZIP — likely OLE compound (encrypted) or corrupted
                # Check for OLE magic bytes
                with open(path, "rb") as f:
                    header = f.read(8)
                if header[:4] == b"\xd0\xcf\x11\xe0":
                    return False, "File is password-protected (OLE encrypted)"
                return False, "File appears corrupted (not a valid OOXML archive)"

        elif ext == ".pdf":
            # pikepdf will raise on encrypted PDFs at scan time, but we can
            # do a quick check for the /Encrypt dictionary entry
            try:
                import pikepdf
                with pikepdf.open(path) as pdf:
                    if pdf.is_encrypted:
                        return False, "PDF is encrypted/password-protected"
                    return True, ""
            except pikepdf.PasswordError:
                return False, "PDF requires a password to open"
            except Exception as e:
                return False, f"Cannot open PDF: {e}"

    except PermissionError:
        return False, "Permission denied — file may be locked by another application"
    except Exception as e:
        return False, f"Cannot access file: {e}"

    return True, ""


# ---------------------------------------------------------------------------
# Fix dispatch
# ---------------------------------------------------------------------------

def _apply_fix(path: Path, file_type: str, fixer_rules: list[str],
               verbose: bool, output_path: Path | None = None) -> dict | None:
    """Call the appropriate fixer for *file_type* with *fixer_rules*.

    Returns the fixer result dict, or None if no fixer is available.
    """
    fixers = {
        "pdf":  (_HAS_FIX_PDF,  _fix_pdf  if _HAS_FIX_PDF  else None),
        "docx": (_HAS_FIX_WORD, _fix_word if _HAS_FIX_WORD else None),
        "xlsx": (_HAS_FIX_EXCEL,_fix_excel if _HAS_FIX_EXCEL else None),
        "pptx": (_HAS_FIX_PPTX, _fix_pptx if _HAS_FIX_PPTX else None),
        "epub": (_HAS_FIX_EPUB, _fix_epub if _HAS_FIX_EPUB else None),
    }
    entry = fixers.get(file_type)
    if not entry or not entry[0]:
        if verbose:
            print(f"     No fixer available for {file_type}")
        return None

    fixer_fn = entry[1]
    if verbose:
        print(f"     Applying fixes: {', '.join(fixer_rules)}")
    try:
        kwargs: dict = {"rules": fixer_rules}
        if output_path is not None:
            kwargs["output_path"] = output_path
        return fixer_fn(path, **kwargs)
    except Exception as exc:
        print(f"     FIX ERROR: {exc}")
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Main audit function
# ---------------------------------------------------------------------------

def run_audit(target: Path, verbose: bool = False,
              file_types: list[str] | None = None,
              fix: bool = False, fix_tier: int = 1,
              alt_text: bool = False,
              alt_text_models: list[str] | None = None) -> dict:
    """Run the full accessibility audit and return structured results dict.

    Args:
        target: File or folder to scan.
        verbose: Print per-scanner progress.
        file_types: Optional list of type names to filter (e.g. ['pdf', 'word']).
                    None scans all supported types.
        fix: If True, apply automated fixes after scanning.
        fix_tier: Maximum tier to auto-fix (1 = safe only, 2 = safe + assisted).
        alt_text: If True, run alt text analysis on images in scanned files.
        alt_text_models: Model IDs for alt text generation (None = default set).
    """
    allowed_exts = _resolve_type_filter(file_types)
    files = _collect_files(target, allowed_exts)
    if not files:
        print(f"No supported files found under: {target}")
        return {}

    print(f"\nScanning {len(files)} file(s) in: {target}\n")

    file_results = []
    type_counts = {"pdf": 0, "docx": 0, "xlsx": 0, "pptx": 0, "epub": 0, "md": 0}
    total_by_severity = {"Error": 0, "Warning": 0, "Info": 0}

    for path in files:
        ext = path.suffix.lower()
        scanner_fn = EXTENSION_MAP[ext]
        print(f"→ {path.name}")
        # Pre-flight check: skip encrypted/corrupted/locked files
        ok, reason = _check_file_accessible(path)
        if not ok:
            print(f"     SKIPPED: {reason}")
            file_entry = {
                "file": path.name,
                "path": str(path),
                "type": ext.lstrip("."),
                "score": 0,
                "grade": "F",
                "findings": [{
                    "rule": "SCAN.FILE.INACCESSIBLE",
                    "severity": "Error",
                    "confidence": "High",
                    "message": f"File could not be scanned: {reason}",
                    "fix": "Ensure the file is not encrypted, password-protected, or locked.",
                }],
                "scanner_results": {},
                "skipped": True,
                "skip_reason": reason,
            }
            file_results.append(file_entry)
            type_counts[ext.lstrip(".")] = type_counts.get(ext.lstrip("."), 0) + 1
            total_by_severity["Error"] += 1
            continue
        result = scanner_fn(path, verbose)
        findings = result["findings"]
        score, grade = _score_file(findings)

        for f in findings:
            sev = f.get("severity", "Info")
            total_by_severity[sev] = total_by_severity.get(sev, 0) + 1

        file_entry = {
            "file": path.name,
            "path": str(path),
            "type": result["type"],
            "score": score,
            "grade": grade,
            "findings": findings,
            "scanner_results": result["scanner_results"],
        }

        # ── Auto-fix + rescan ────────────────────────────────────────
        if fix and _HAS_FIX_TIERS and result["type"] in ("pdf", "docx", "xlsx", "pptx", "epub"):
            fixer_rules = get_fixable_rules(findings, result["type"], max_tier=fix_tier)
            if fixer_rules:
                tier_label = TIER_LABELS.get(fix_tier, f"Tier {fix_tier}")
                print(f"     Fixing ({tier_label}): {', '.join(fixer_rules)}")
                # Route fixed files to fixed/ and backups to backup/
                fixed_dir = path.parent / "fixed"
                backup_dir = path.parent / "backup"
                fixed_dir.mkdir(exist_ok=True)
                backup_dir.mkdir(exist_ok=True)
                dest_output = fixed_dir / (path.stem + "-fixed" + path.suffix)
                fix_result = _apply_fix(path, result["type"], fixer_rules, verbose,
                                        output_path=dest_output)
                if fix_result and "error" not in fix_result:
                    # Move backup into backup/ subfolder
                    raw_backup = Path(fix_result.get("backup", ""))
                    if raw_backup.exists():
                        dest_backup = backup_dir / raw_backup.name
                        shutil.move(str(raw_backup), str(dest_backup))
                        fix_result["backup"] = str(dest_backup)
                    fixed_path = Path(fix_result.get("output", ""))
                    if fixed_path.exists():
                        # Rescan the fixed copy
                        print(f"     Rescanning fixed copy: {fixed_path.name}")
                        rescan = scanner_fn(fixed_path, verbose)
                        after_score, after_grade = _score_file(rescan["findings"])
                        file_entry["remediation"] = {
                            "applied": True,
                            "max_tier": fix_tier,
                            "fixed_file": str(fixed_path),
                            "fix_result": fix_result.get("fixes", []),
                            "fix_summary": fix_result.get("summary", {}),
                            "before": {"score": score, "grade": grade,
                                       "errors": sum(1 for f in findings if f.get("severity") == "Error"),
                                       "warnings": sum(1 for f in findings if f.get("severity") == "Warning")},
                            "after":  {"score": after_score, "grade": after_grade,
                                       "errors": sum(1 for f in rescan["findings"] if f.get("severity") == "Error"),
                                       "warnings": sum(1 for f in rescan["findings"] if f.get("severity") == "Warning")},
                        }
                        delta = after_score - score
                        arrow = "\u2191" if delta > 0 else ("\u2193" if delta < 0 else "\u2192")
                        print(f"     {arrow} Score: {score} \u2192 {after_score} ({after_grade})")
                    else:
                        file_entry["remediation"] = {
                            "applied": False,
                            "reason": "Fixed file not found after fixer ran.",
                        }
                elif fix_result and "error" in fix_result:
                    file_entry["remediation"] = {
                        "applied": False,
                        "reason": fix_result["error"],
                    }
            elif verbose:
                print(f"     No fixable rules at tier {fix_tier}")

        file_results.append(file_entry)
        type_counts[result["type"]] = type_counts.get(result["type"], 0) + 1

        if verbose:
            print(f"     Score: {score}/100 ({grade})  "
                  f"Errors: {sum(1 for f in findings if f.get('severity')=='Error')}  "
                  f"Warnings: {sum(1 for f in findings if f.get('severity')=='Warning')}")

    overall_score, overall_grade = _aggregate_score(file_results)

    audit = {
        "scan_date": datetime.datetime.now().isoformat(timespec="seconds"),
        "target": str(target),
        "summary": {
            "total_files": len(file_results),
            "score": overall_score,
            "grade": overall_grade,
            "errors":   total_by_severity.get("Error", 0),
            "warnings": total_by_severity.get("Warning", 0),
            "info":     total_by_severity.get("Info", 0),
            "by_type": type_counts,
        },
        "files": file_results,
    }

    # Add remediation summary if --fix was used
    if fix:
        fixed_files = [f for f in file_results if f.get("remediation", {}).get("applied")]
        if fixed_files:
            before_avg = round(sum(f["remediation"]["before"]["score"] for f in fixed_files) / len(fixed_files))
            after_avg = round(sum(f["remediation"]["after"]["score"] for f in fixed_files) / len(fixed_files))
            audit["remediation"] = {
                "enabled": True,
                "max_tier": fix_tier,
                "files_fixed": len(fixed_files),
                "before_avg_score": before_avg,
                "after_avg_score": after_avg,
                "score_improvement": after_avg - before_avg,
            }
        else:
            audit["remediation"] = {
                "enabled": True,
                "max_tier": fix_tier,
                "files_fixed": 0,
            }

    # ── Alt text analysis (optional) ─────────────────────────────────
    if alt_text and _HAS_ALT_TEXT:
        _ALT_TEXT_FORMATS = {"pdf", "docx", "xlsx", "pptx", "epub"}
        # Resolve models
        if alt_text_models and "all" in [m.lower() for m in alt_text_models]:
            use_models = list(VISION_MODELS.keys())
        elif alt_text_models:
            use_models = alt_text_models
        else:
            use_models = ["openai/gpt-4.1-mini", "openai/gpt-4o-mini"]

        print(f"\n── Alt Text Analysis ({'|'.join(use_models)}) ──\n")

        for fe in file_results:
            if fe.get("skipped") or fe["type"] not in _ALT_TEXT_FORMATS:
                continue
            fpath = Path(fe["path"])
            print(f"  Analyzing images in: {fpath.name}")
            try:
                report = generate_for_document(fpath, models=use_models)
                if not report.images:
                    if verbose:
                        print(f"     No images found.")
                    continue

                images_analysis = []
                for img_opts in report.images:
                    # Build (model, text) pairs for ranking
                    model_alts = [
                        (opt.model, opt.concise_alt)
                        for opt in img_opts.options
                    ]
                    ranked = rank_alternatives(
                        existing_alt=img_opts.existing_alt,
                        alternatives=model_alts,
                        context="",
                    )
                    images_analysis.append({
                        "location": img_opts.location,
                        "page": img_opts.page_number,
                        "image_index": img_opts.image_index,
                        "existing_alt": img_opts.existing_alt,
                        "analysis": ranked_to_dict(ranked),
                        "detailed": [
                            {"model": opt.model, "detailed_description": opt.detailed_description}
                            for opt in img_opts.options
                        ],
                    })

                fe["alt_text_analysis"] = {
                    "models_used": use_models,
                    "total_images": report.total_images,
                    "images": images_analysis,
                }
                print(f"     {report.total_images} image(s) analyzed, "
                      f"{len(use_models)} model(s)")

            except Exception as exc:
                print(f"     ALT TEXT ERROR: {exc}")
                fe["alt_text_analysis"] = {
                    "models_used": use_models,
                    "total_images": 0,
                    "images": [],
                    "error": str(exc),
                }

    elif alt_text and not _HAS_ALT_TEXT:
        print("\nWarning: --alt-text requested but alt_text package is not available.")
        print("Install with: pip install httpx PyMuPDF")

    print(f"\n{'='*60}")
    print(f"Audit complete — {len(file_results)} file(s)")
    print(f"Overall score: {overall_score}/100  Grade: {overall_grade}")
    print(f"Errors: {total_by_severity['Error']}  "
          f"Warnings: {total_by_severity['Warning']}  "
          f"Info: {total_by_severity['Info']}")
    print(f"{'='*60}\n")

    return audit


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Multi-format accessibility audit (PDF, DOCX, XLSX, PPTX, EPUB, Markdown)"
    )
    parser.add_argument("target", help="File or folder to scan")
    parser.add_argument(
        "--output", default="scan_results.json",
        help="Output JSON file path (default: scan_results.json)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print per-scanner progress"
    )
    parser.add_argument(
        "--type", nargs="+", metavar="FORMAT",
        help="Only scan these file types (e.g. --type pdf, --type word excel). "
             "Valid: pdf, word/docx, excel/xlsx, powerpoint/pptx, epub, markdown/md"
    )
    parser.add_argument(
        "--json-only", action="store_true",
        help="Write only the JSON results — skip Markdown and HTML report generation"
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="Apply automated fixes after scanning, then rescan to verify"
    )
    parser.add_argument(
        "--fix-tier", type=int, choices=[1, 2], default=1,
        help="Maximum fix tier: 1 = safe-only (default), 2 = safe + assisted"
    )
    parser.add_argument(
        "--alt-text", action="store_true",
        help="Run alt text analysis: extract images, generate alternatives from "
             "multiple vision models, score and rank all options"
    )
    parser.add_argument(
        "--alt-text-models", nargs="+", metavar="MODEL",
        help="Models to use for alt text generation (default: gpt-4.1-mini + gpt-4o-mini). "
             "Use 'all' for every available model."
    )
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if not target.exists():
        sys.exit(f"ERROR: Path not found: {target}")

    audit = run_audit(target, verbose=args.verbose, file_types=args.type,
                      fix=args.fix, fix_tier=args.fix_tier,
                      alt_text=args.alt_text,
                      alt_text_models=args.alt_text_models)
    if not audit:
        sys.exit(1)

    # Determine output directory — write reports where the files live
    if args.output != "scan_results.json":
        # User specified an explicit output path
        out = Path(args.output).resolve()
    else:
        # Default: put results in the scanned folder (or file's parent)
        files_dir = target if target.is_dir() else target.parent
        out = files_dir / "scan_results.json"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")
    print(f"Results written to: {out}")

    # ── Generate final reports automatically ──────────────────────────
    if not args.json_only:
        # Build a format-aware report name (e.g. PDF-ACCESSIBILITY-AUDIT)
        if args.type and len(args.type) == 1:
            type_label = args.type[0].upper()
            # Normalise aliases to canonical labels
            _label_map = {"DOCX": "WORD", "XLSX": "EXCEL", "PPTX": "POWERPOINT",
                          "SPREADSHEET": "EXCEL", "PRESENTATION": "POWERPOINT",
                          "MD": "MARKDOWN"}
            type_label = _label_map.get(type_label, type_label)
            report_stem = f"{type_label}-ACCESSIBILITY-AUDIT"
        else:
            report_stem = "ACCESSIBILITY-AUDIT"
        report_dir = out.parent

        if _HAS_REPORT_MD:
            md_path = report_dir / f"{report_stem}.md"
            md_path.write_text(generate_md_report(audit), encoding="utf-8")
            print(f"Markdown report written to: {md_path}")
        else:
            print("Warning: report_md.py not found — skipping Markdown report.")

        if _HAS_REPORT_HTML:
            html_path = report_dir / f"{report_stem}.html"
            html_path.write_text(generate_html_report(audit), encoding="utf-8")
            print(f"HTML report written to: {html_path}")
        else:
            print("Warning: report_html.py not found — skipping HTML report.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAudit interrupted by user (Ctrl+C). Partial results were not saved.")
        sys.exit(130)
