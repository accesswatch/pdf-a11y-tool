"""Tests for pdf_a11y.core.validator."""
from __future__ import annotations

from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest

from pdf_a11y.core.validator import (
    Finding,
    VeraPdfValidator,
    _find_verapdf_exe,
    _parse_verapdf_xml,
    is_available,
)


class TestFinding:
    def test_defaults(self):
        f = Finding(
            rule_id="TEST",
            severity="error",
            wcag="1.1.1",
            description="Test finding",
        )
        assert f.page is None
        assert f.element is None
        assert f.confidence == "high"
        assert f.remediation == ""

    def test_full(self):
        f = Finding(
            rule_id="TEST",
            severity="warning",
            wcag="2.4.2",
            description="Test",
            page=3,
            element="Figure1",
            confidence="medium",
            remediation="Fix it",
        )
        assert f.page == 3
        assert f.element == "Figure1"


class TestFindVeraPdfExe:
    def test_returns_none_when_not_found(self):
        with patch("shutil.which", return_value=None):
            result = _find_verapdf_exe()
        assert result is None

    def test_finds_on_path(self, tmp_path):
        bat = tmp_path / "verapdf.bat"
        bat.write_text("echo hi")
        with patch("shutil.which", return_value=str(bat)):
            result = _find_verapdf_exe()
        assert result == bat

    def test_explicit_preference_file(self, tmp_path):
        bat = tmp_path / "verapdf.bat"
        bat.write_text("echo hi")
        result = _find_verapdf_exe(str(bat))
        assert result == bat

    def test_explicit_preference_dir(self, tmp_path):
        bat = tmp_path / "verapdf.bat"
        bat.write_text("echo hi")
        result = _find_verapdf_exe(str(tmp_path))
        assert result == bat


class TestIsAvailable:
    def test_not_available(self):
        with patch("pdf_a11y.core.validator._find_verapdf_exe", return_value=None):
            assert is_available() is False

    def test_available(self, tmp_path):
        bat = tmp_path / "verapdf.bat"
        bat.write_text("echo")
        with patch("pdf_a11y.core.validator._find_verapdf_exe", return_value=bat):
            assert is_available() is True


class TestParseVeraPdfXml:
    def test_invalid_xml(self):
        findings = _parse_verapdf_xml("not xml at all")
        assert len(findings) == 1
        assert findings[0].rule_id == "TOOL.VERAPDF"

    def test_empty_report(self):
        xml = "<report><jobs><job><validationReport><details></details></validationReport></job></jobs></report>"
        findings = _parse_verapdf_xml(xml)
        assert findings == []

    def test_mapped_rule(self):
        xml = """<report><jobs><job><validationReport><details>
        <rule clause="7.21" testNumber="1" status="failed">
            <description>Missing title</description>
            <check status="failed"><context>Page[1]</context></check>
        </rule>
        </details></validationReport></job></jobs></report>"""
        findings = _parse_verapdf_xml(xml)
        assert len(findings) == 1
        assert findings[0].rule_id == "PDFUA.TITLE"
        assert findings[0].wcag == "2.4.2"
        assert findings[0].page == 1

    def test_unmapped_rule(self):
        xml = """<report><jobs><job><validationReport><details>
        <rule clause="99.99" testNumber="1" status="failed">
            <description>Unknown rule</description>
            <check status="failed"><context>somewhere</context></check>
        </rule>
        </details></validationReport></job></jobs></report>"""
        findings = _parse_verapdf_xml(xml)
        assert len(findings) == 1
        assert findings[0].rule_id.startswith("VERAPDF.")
        assert findings[0].confidence == "medium"

    def test_passed_rules_skipped(self):
        xml = """<report><jobs><job><validationReport><details>
        <rule clause="7.1" testNumber="1" status="passed">
            <description>Tagged OK</description>
        </rule>
        </details></validationReport></job></jobs></report>"""
        findings = _parse_verapdf_xml(xml)
        assert findings == []


class TestVeraPdfValidator:
    def test_not_available_returns_warning(self, tmp_path):
        # Create the file so we get past the file check to the "not installed" check
        pdf_file = tmp_path / "somefile.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")
        with patch("pdf_a11y.core.validator._find_verapdf_exe", return_value=None):
            v = VeraPdfValidator()
            findings = v.validate(str(pdf_file))
        assert len(findings) == 1
        assert findings[0].rule_id == "TOOL.VERAPDF"
        assert "not installed" in findings[0].description

    def test_file_not_found(self, tmp_path):
        bat = tmp_path / "verapdf.bat"
        bat.write_text("echo")
        with patch("pdf_a11y.core.validator._find_verapdf_exe", return_value=bat):
            v = VeraPdfValidator()
            findings = v.validate(tmp_path / "nonexistent.pdf")
        assert len(findings) == 1
        assert findings[0].rule_id == "TOOL.FILE"

    def test_available_property(self, tmp_path):
        bat = tmp_path / "verapdf.bat"
        bat.write_text("echo")
        with patch("pdf_a11y.core.validator._find_verapdf_exe", return_value=bat):
            v = VeraPdfValidator()
            assert v.available is True
            assert v.exe_path == bat
