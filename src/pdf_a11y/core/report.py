"""Audit report generation (Markdown and CSV).

This module takes a list of Finding objects and renders them as
human-readable Markdown or machine-readable CSV reports, suitable for
export or inclusion in documentation.

Public API
----------
ReportFormat     -- Enum: MARKDOWN or CSV.
ReportGenerator  -- Accepts findings and a document path; produces a
                    formatted report string or writes to a file.
"""
from __future__ import annotations

import csv
import enum
import io
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pdf_a11y.core.validator import Finding

logger = logging.getLogger(__name__)


class ReportFormat(enum.Enum):
    """Supported report output formats."""

    MARKDOWN = "markdown"
    CSV = "csv"


class ReportAudience(enum.Enum):
    """Target audience for remediation instructions.

    TOOL  -- Instructions reference PDF Accessibility Tool shortcuts and panels.
    ACROBAT -- Instructions reference Adobe Acrobat Pro menus and dialogs.
    """

    TOOL = "tool"
    ACROBAT = "acrobat"


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

# Weight per severity level used for the accessibility score.
_SEVERITY_WEIGHTS: dict[str, float] = {
    "error": 5.0,
    "warning": 2.0,
    "tip": 0.5,
}

# Grade thresholds (inclusive lower bound).
_GRADE_THRESHOLDS: list[tuple[int, str]] = [
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (50, "D"),
    (0, "F"),
]


def compute_score(findings: list[Finding]) -> tuple[int, str]:
    """Compute an accessibility score (0-100) and letter grade.

    ``Score = max(0, 100 - sum(weight_per_finding))``.
    """
    penalty = sum(_SEVERITY_WEIGHTS.get(f.severity, 1.0) for f in findings)
    score = max(0, int(100 - penalty))
    grade = "F"
    for threshold, letter in _GRADE_THRESHOLDS:
        if score >= threshold:
            grade = letter
            break
    return score, grade


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def _findings_by_severity(findings: list[Finding]) -> dict[str, list[Finding]]:
    groups: dict[str, list[Finding]] = {"error": [], "warning": [], "tip": []}
    for f in findings:
        groups.setdefault(f.severity, []).append(f)
    return groups


def _findings_by_page(findings: list[Finding]) -> dict[int | None, list[Finding]]:
    groups: dict[int | None, list[Finding]] = {}
    for f in findings:
        groups.setdefault(f.page, []).append(f)
    return groups


def _remediation_for_audience(
    finding: Finding, audience: ReportAudience
) -> str:
    """Return the remediation text appropriate for the audience."""
    if audience == ReportAudience.ACROBAT:
        return finding.acrobat_remediation or finding.remediation
    return finding.remediation


def _audience_label(audience: ReportAudience) -> str:
    """Human-readable label for the target audience."""
    if audience == ReportAudience.ACROBAT:
        return "Adobe Acrobat Pro"
    return "PDF Accessibility Tool"


def generate_markdown(
    findings: list[Finding],
    pdf_path: str | Path | None = None,
    verapdf_used: bool = False,
    audience: ReportAudience = ReportAudience.TOOL,
) -> str:
    """Generate a Markdown accessibility audit report.

    Parameters
    ----------
    audience:
        Controls which remediation instructions appear.  ``TOOL`` emits
        PDF Accessibility Tool instructions; ``ACROBAT`` emits Adobe
        Acrobat Pro instructions.
    """
    lines: list[str] = []
    score, grade = compute_score(findings)
    by_severity = _findings_by_severity(findings)
    error_count = len(by_severity.get("error", []))
    warning_count = len(by_severity.get("warning", []))
    tip_count = len(by_severity.get("tip", []))
    total = len(findings)
    tool_label = _audience_label(audience)

    # Header
    lines.append(f"# PDF Accessibility Audit Report ({tool_label})")
    lines.append("")

    # Audit info
    lines.append("## Audit Information")
    lines.append("")
    lines.append(f"- **Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    if pdf_path:
        lines.append(f"- **File**: {Path(pdf_path).name}")
    lines.append(f"- **Remediation tool**: {tool_label}")
    lines.append(f"- **veraPDF**: {'Yes' if verapdf_used else 'No (built-in checks only)'}")
    lines.append("")

    # Executive summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- **Score**: {score}/100 (Grade: {grade})")
    lines.append(f"- **Errors**: {error_count}")
    lines.append(f"- **Warnings**: {warning_count}")
    lines.append(f"- **Tips**: {tip_count}")
    lines.append(f"- **Total findings**: {total}")
    lines.append("")

    if total == 0:
        lines.append("No accessibility issues were found.")
        lines.append("")
        return "\n".join(lines)

    # Most common issue
    rule_counts = Counter(f.rule_id for f in findings)
    most_common_rule, most_common_count = rule_counts.most_common(1)[0]
    lines.append(f"- **Most common issue**: {most_common_rule} ({most_common_count} occurrences)")
    lines.append("")

    # Findings by page
    by_page = _findings_by_page(findings)
    lines.append("## Findings by Page")
    lines.append("")
    for page_num in sorted(by_page.keys(), key=lambda x: x if x is not None else 0):
        page_label = f"Page {page_num}" if page_num is not None else "Document-level"
        page_findings = by_page[page_num]
        lines.append(f"### {page_label}")
        lines.append("")
        for f in page_findings:
            severity_icon = {"error": "[ERROR]", "warning": "[WARNING]", "tip": "[TIP]"}.get(
                f.severity, f"[{f.severity.upper()}]"
            )
            lines.append(f"- {severity_icon} **{f.rule_id}** (WCAG {f.wcag}): {f.description}")
            if f.element:
                lines.append(f"  - Element: {f.element}")
            fix_text = _remediation_for_audience(f, audience)
            if fix_text:
                lines.append(f"  - How to fix: {fix_text}")
        lines.append("")

    # Findings by rule
    lines.append("## Findings by Rule")
    lines.append("")
    lines.append("| Rule ID | Count | Severity | WCAG |")
    lines.append("|---------|-------|----------|------|")
    for rule_id, count in rule_counts.most_common():
        sample = next(f for f in findings if f.rule_id == rule_id)
        lines.append(f"| {rule_id} | {count} | {sample.severity} | {sample.wcag} |")
    lines.append("")

    # Remediation priority
    lines.append("## Remediation Priority")
    lines.append("")
    if error_count:
        lines.append("### Immediate (Errors)")
        lines.append("")
        for f in by_severity.get("error", []):
            lines.append(f"1. **{f.rule_id}**: {f.description}")
            fix_text = _remediation_for_audience(f, audience)
            if fix_text:
                lines.append(f"   - {fix_text}")
        lines.append("")
    if warning_count:
        lines.append("### Soon (Warnings)")
        lines.append("")
        for f in by_severity.get("warning", []):
            lines.append(f"1. **{f.rule_id}**: {f.description}")
            fix_text = _remediation_for_audience(f, audience)
            if fix_text:
                lines.append(f"   - {fix_text}")
        lines.append("")
    if tip_count:
        lines.append("### When Possible (Tips)")
        lines.append("")
        for f in by_severity.get("tip", []):
            lines.append(f"1. **{f.rule_id}**: {f.description}")
            fix_text = _remediation_for_audience(f, audience)
            if fix_text:
                lines.append(f"   - {fix_text}")
            if f.acrobat_remediation:
                lines.append(f"   - Adobe Acrobat Pro: {f.acrobat_remediation}")
        lines.append("")

    # Scorecard
    lines.append("## Accessibility Scorecard")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Score | {score}/100 |")
    lines.append(f"| Grade | {grade} |")
    lines.append(f"| Errors | {error_count} |")
    lines.append(f"| Warnings | {warning_count} |")
    lines.append(f"| Tips | {tip_count} |")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CSV report
# ---------------------------------------------------------------------------


def generate_csv(
    findings: list[Finding],
    audience: ReportAudience = ReportAudience.TOOL,
) -> str:
    """Generate a CSV report with one row per finding.

    The *Remediation* column contains instructions for the selected
    ``audience`` only.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    tool_label = _audience_label(audience)
    writer.writerow(
        ["Rule ID", "Severity", "WCAG", "Page", "Element", "Description",
         f"Remediation ({tool_label})"]
    )
    for f in findings:
        writer.writerow(
            [
                f.rule_id,
                f.severity,
                f.wcag,
                f.page if f.page is not None else "",
                f.element or "",
                f.description,
                _remediation_for_audience(f, audience),
            ]
        )
    return output.getvalue()


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------


class ReportGenerator:
    """Generate accessibility reports in Markdown or CSV format.

    Usage::

        gen = ReportGenerator(findings, pdf_path="doc.pdf")
        md_text = gen.generate(ReportFormat.MARKDOWN)  # default: TOOL audience
        gen.write(ReportFormat.CSV, "report.csv", audience=ReportAudience.ACROBAT)

        # Write both reports at once:
        paths = gen.write_all(ReportFormat.MARKDOWN, "reports/")
    """

    def __init__(
        self,
        findings: list[Finding],
        pdf_path: str | Path | None = None,
        verapdf_used: bool = False,
    ) -> None:
        self._findings = findings
        self._pdf_path = pdf_path
        self._verapdf_used = verapdf_used

    def generate(
        self,
        fmt: ReportFormat = ReportFormat.MARKDOWN,
        audience: ReportAudience = ReportAudience.TOOL,
    ) -> str:
        """Return the report as a string for the given audience."""
        if fmt == ReportFormat.MARKDOWN:
            return generate_markdown(
                self._findings, self._pdf_path, self._verapdf_used,
                audience=audience,
            )
        elif fmt == ReportFormat.CSV:
            return generate_csv(self._findings, audience=audience)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def write(
        self,
        fmt: ReportFormat,
        output_path: str | Path,
        audience: ReportAudience = ReportAudience.TOOL,
    ) -> Path:
        """Write a single report to a file and return the path."""
        output_path = Path(output_path)
        content = self.generate(fmt, audience=audience)
        output_path.write_text(content, encoding="utf-8")
        logger.info("Report written to %s", output_path)
        return output_path

    def write_all(
        self,
        fmt: ReportFormat,
        output_dir: str | Path,
        stem: str = "AUDIT",
    ) -> list[Path]:
        """Write one report per audience to *output_dir* and return paths.

        For Markdown this produces::

            <stem>-tool.md
            <stem>-acrobat.md

        For CSV::

            <stem>-tool.csv
            <stem>-acrobat.csv
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        ext = ".md" if fmt == ReportFormat.MARKDOWN else ".csv"
        paths: list[Path] = []
        for audience in ReportAudience:
            filename = f"{stem}-{audience.value}{ext}"
            p = self.write(fmt, output_dir / filename, audience=audience)
            paths.append(p)
        return paths
