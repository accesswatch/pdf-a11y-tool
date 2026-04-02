"""Tests for pdf_a11y.core.report."""
from __future__ import annotations

import csv
import io

import pytest

from pdf_a11y.core.report import (
    ReportFormat,
    ReportGenerator,
    compute_score,
    generate_csv,
    generate_markdown,
)
from pdf_a11y.core.validator import Finding


@pytest.fixture
def sample_findings():
    return [
        Finding(
            rule_id="PDFUA.TITLE",
            severity="error",
            wcag="2.4.2",
            description="Document title is missing.",
            remediation="Set the title.",
        ),
        Finding(
            rule_id="PDFUA.LANG",
            severity="error",
            wcag="3.1.1",
            description="Document language is not set.",
            page=None,
            remediation="Set the language.",
        ),
        Finding(
            rule_id="PDFUA.HEADINGS",
            severity="warning",
            wcag="2.4.6",
            description="Heading level skipped: H1 to H3.",
            page=2,
            remediation="Fix heading hierarchy.",
        ),
    ]


class TestComputeScore:
    def test_no_findings(self):
        score, grade = compute_score([])
        assert score == 100
        assert grade == "A"

    def test_one_error(self):
        score, grade = compute_score(
            [Finding(rule_id="X", severity="error", wcag="", description="x")]
        )
        assert score == 95
        assert grade == "A"

    def test_many_errors(self):
        findings = [
            Finding(rule_id="X", severity="error", wcag="", description="x")
            for _ in range(25)
        ]
        score, grade = compute_score(findings)
        assert score == 0
        assert grade == "F"

    def test_grade_thresholds(self):
        # 2 errors (10 points) = 90 = A
        f2 = [Finding(rule_id="X", severity="error", wcag="", description="x")] * 2
        _, grade = compute_score(f2)
        assert grade == "A"

        # 3 errors (15 points) = 85 = B
        f3 = [Finding(rule_id="X", severity="error", wcag="", description="x")] * 3
        _, grade = compute_score(f3)
        assert grade == "B"


class TestMarkdownReport:
    def test_contains_header(self, sample_findings):
        md = generate_markdown(sample_findings, pdf_path="test.pdf")
        assert "# PDF Accessibility Audit Report" in md

    def test_contains_file_name(self, sample_findings):
        md = generate_markdown(sample_findings, pdf_path="my_doc.pdf")
        assert "my_doc.pdf" in md

    def test_contains_score(self, sample_findings):
        md = generate_markdown(sample_findings)
        assert "Score" in md
        assert "Grade" in md

    def test_no_findings(self):
        md = generate_markdown([])
        assert "No accessibility issues" in md

    def test_verapdf_flag(self, sample_findings):
        md_no = generate_markdown(sample_findings, verapdf_used=False)
        assert "built-in checks only" in md_no
        md_yes = generate_markdown(sample_findings, verapdf_used=True)
        assert "Yes" in md_yes


class TestCsvReport:
    def test_header_row(self, sample_findings):
        csv_text = generate_csv(sample_findings)
        reader = csv.reader(io.StringIO(csv_text))
        header = next(reader)
        assert "Rule ID" in header
        assert "Severity" in header
        assert "WCAG" in header

    def test_row_count(self, sample_findings):
        csv_text = generate_csv(sample_findings)
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        # 1 header + 3 data rows
        assert len(rows) == 4


class TestReportGenerator:
    def test_generate_markdown(self, sample_findings):
        gen = ReportGenerator(sample_findings, pdf_path="test.pdf")
        result = gen.generate(ReportFormat.MARKDOWN)
        assert "# PDF Accessibility Audit Report" in result

    def test_generate_csv(self, sample_findings):
        gen = ReportGenerator(sample_findings)
        result = gen.generate(ReportFormat.CSV)
        assert "Rule ID" in result

    def test_write(self, sample_findings, tmp_path):
        gen = ReportGenerator(sample_findings)
        out = gen.write(ReportFormat.MARKDOWN, tmp_path / "report.md")
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "PDF Accessibility Audit Report" in content

    def test_write_csv(self, sample_findings, tmp_path):
        gen = ReportGenerator(sample_findings)
        out = gen.write(ReportFormat.CSV, tmp_path / "report.csv")
        assert out.exists()
