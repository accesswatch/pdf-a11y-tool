"""veraPDF integration (optional, requires Java 11+).

This module invokes the veraPDF CLI tool as a subprocess and parses its XML
output into a list of Finding objects. When veraPDF is not installed or Java
is unavailable, the validator gracefully degrades.

Public API
----------
Finding          -- Dataclass shared with builtin_checks.py.
VeraPdfValidator -- Locates veraPDF, runs a check on a PDF path, returns
                    list[Finding].
is_available()   -- True when veraPDF can be located on this system.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Finding dataclass (shared with builtin_checks.py)
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """A single accessibility finding from veraPDF or built-in checks."""

    rule_id: str
    severity: str
    wcag: str
    description: str
    page: int | None = None
    element: str | None = None
    confidence: str = "high"
    remediation: str = ""
    acrobat_remediation: str = ""


# ---------------------------------------------------------------------------
# veraPDF rule ID mapping
# ---------------------------------------------------------------------------
# Maps veraPDF clause identifiers (from the XML ``clause`` + ``testNumber``
# attributes) to (internal_rule_id, wcag, severity, description, remediation).
# The keys use the format "clause/testNumber" as emitted by veraPDF.

VERAPDF_RULE_MAP: dict[str, tuple[str, str, str, str, str]] = {
    # --- Document-level --------------------------------------------------
    "7.1/1": (
        "PDFUA.TAGGED",
        "1.3.1",
        "error",
        "PDF is not tagged (no StructTreeRoot).",
        "Add a structure tree to the document. "
        "Re-export from the authoring tool with 'Tagged PDF' enabled.",
    ),
    "7.1/2": (
        "PDFUA.TAGGED",
        "1.3.1",
        "error",
        "Structure tree is present but MarkInfo/Marked is not true.",
        "Set MarkInfo/Marked to true in the document catalog.",
    ),
    "7.2/1": (
        "PDFUA.LANG",
        "3.1.1",
        "error",
        "Document language is not set.",
        "Set the document language in File > Properties > Advanced > Language.",
    ),
    "7.21/1": (
        "PDFUA.TITLE",
        "2.4.2",
        "error",
        "Document title is missing.",
        "Set the document title in File > Properties > Description > Title.",
    ),
    "7.21/2": (
        "PDFBP.DISPLAY_TITLE",
        "2.4.2",
        "warning",
        "DisplayDocTitle is not set to true.",
        "Set ViewerPreferences/DisplayDocTitle to true so the title shows in the title bar.",
    ),
    # --- Structure elements ----------------------------------------------
    "7.3/1": (
        "PDFUA.TAGGED",
        "1.3.1",
        "error",
        "Content is not enclosed in a structure element.",
        "Tag all content inside appropriate structure elements (P, H1-H6, Table, etc.).",
    ),
    "7.4.4/1": (
        "PDFUA.HEADINGS",
        "2.4.6",
        "warning",
        "Heading level is skipped (e.g., H1 then H3).",
        "Ensure heading levels do not skip (H1 > H2 > H3). Fix in the tag tree.",
    ),
    # --- Images and figures ----------------------------------------------
    "7.3/2": (
        "PDFUA.IMG.ALT",
        "1.1.1",
        "error",
        "Figure element does not have an Alt attribute.",
        "Add alt text to the Figure element or mark it as an artifact if decorative.",
    ),
    "7.18.1/1": (
        "PDFUA.IMG.ALT",
        "1.1.1",
        "error",
        "Image used as Figure lacks alternative text.",
        "Add descriptive alt text to the image's Figure tag.",
    ),
    # --- Tables ----------------------------------------------------------
    "7.5/1": (
        "PDFBP.TABLE_HEADERS",
        "1.3.1",
        "warning",
        "Table has no header cells (TH elements).",
        "Add TH elements to the first row or column of the table.",
    ),
    "7.5/2": (
        "PDFBP.TABLE_SCOPE",
        "1.3.1",
        "warning",
        "TH element is missing the Scope attribute.",
        "Set the Scope attribute on each TH to 'Row', 'Column', or 'Both'.",
    ),
    # --- Forms -----------------------------------------------------------
    "7.18.3/1": (
        "PDFUA.FORMS",
        "4.1.2",
        "error",
        "Form field is missing a tooltip (TU entry).",
        "Add a tooltip (TU) to each interactive form field for screen reader accessibility.",
    ),
    "7.18.3/2": (
        "PDFUA.FORMS",
        "4.1.2",
        "error",
        "Form field is missing a name.",
        "Set the T (name) entry on each form field widget.",
    ),
    # --- Bookmarks -------------------------------------------------------
    "7.11/1": (
        "PDFUA.BOOKMARKS",
        "2.4.1",
        "warning",
        "Document with more than 20 pages has no bookmarks.",
        "Add bookmarks (Outlines) that mirror the heading structure.",
    ),
    # --- Annotations and links -------------------------------------------
    "7.18/1": (
        "PDFUA.ANNOT",
        "4.1.2",
        "error",
        "Annotation is not tagged.",
        "Ensure all annotations (links, form fields) are contained within a structure element.",
    ),
    "7.18.5/1": (
        "PDFUA.LINK",
        "2.4.4",
        "error",
        "Link annotation has no Contents or Alt entry.",
        "Add a Contents or Alt description to the link annotation.",
    ),
    # --- Reading order ---------------------------------------------------
    "7.2/2": (
        "PDFBP.READING_ORDER",
        "1.3.2",
        "warning",
        "Content order in the structure tree may not match visual layout.",
        "Review reading order in the tag tree and reorder elements as needed.",
    ),
    # --- Colour contrast (veraPDF heuristic) -----------------------------
    "7.7/1": (
        "PDFUA.CONTRAST",
        "1.4.3",
        "warning",
        "Text may have insufficient contrast against its background.",
        "Ensure text has a contrast ratio of at least 4.5:1 (3:1 for large text).",
    ),
}

# Windows-specific common install locations for veraPDF.
_WINDOWS_SEARCH_DIRS: list[str] = [
    r"C:\Program Files\veraPDF",
    r"C:\Program Files (x86)\veraPDF",
    r"C:\veraPDF",
    os.path.expandvars(r"%LOCALAPPDATA%\veraPDF"),
]

_VERAPDF_BAT = "verapdf.bat"
_VERAPDF_SH = "verapdf"

_DEFAULT_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Locator helpers
# ---------------------------------------------------------------------------


def _find_verapdf_exe(preference_path: str | None = None) -> Path | None:
    """Locate the veraPDF executable.

    Search order:
    1. Explicit *preference_path* (from user preferences).
    2. ``PATH`` environment variable (via :func:`shutil.which`).
    3. Common Windows installation directories.

    Returns the resolved :class:`Path` or ``None``.
    """
    # 1. User preference
    if preference_path:
        p = Path(preference_path)
        if p.is_file():
            return p
        # Maybe the user pointed at the directory
        if p.is_dir():
            for name in (_VERAPDF_BAT, _VERAPDF_SH):
                candidate = p / name
                if candidate.is_file():
                    return candidate

    # 2. PATH lookup
    for name in (_VERAPDF_BAT, _VERAPDF_SH):
        found = shutil.which(name)
        if found:
            return Path(found)

    # 3. Common Windows directories
    if os.name == "nt":
        for d in _WINDOWS_SEARCH_DIRS:
            for name in (_VERAPDF_BAT, _VERAPDF_SH):
                candidate = Path(d) / name
                if candidate.is_file():
                    return candidate

    return None


def is_available(preference_path: str | None = None) -> bool:
    """Return ``True`` if veraPDF can be located on this system."""
    return _find_verapdf_exe(preference_path) is not None


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------


def _parse_verapdf_xml(xml_text: str) -> list[Finding]:
    """Parse veraPDF XML output into a list of :class:`Finding` objects."""
    findings: list[Finding] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.error("Failed to parse veraPDF XML: %s", exc)
        findings.append(
            Finding(
                rule_id="TOOL.VERAPDF",
                severity="error",
                wcag="",
                description=f"veraPDF returned invalid XML: {exc}",
                confidence="high",
                remediation="Re-run the check. If the problem persists, update veraPDF.",
            )
        )
        return findings

    # veraPDF XML structure (simplified):
    # <report>
    #   <jobs>
    #     <job>
    #       <validationReport ... >
    #         <details>
    #           <rule clause="7.1" testNumber="1" status="failed" ...>
    #             <description>...</description>
    #             <check status="failed" ...>
    #               <context>...</context>
    #             </check>
    #           </rule>
    #         </details>
    #       </validationReport>
    #     </job>
    #   </jobs>
    # </report>

    for rule_el in root.iter("rule"):
        status = rule_el.get("status", "")
        if status != "failed":
            continue

        clause = rule_el.get("clause", "")
        test_number = rule_el.get("testNumber", "")
        key = f"{clause}/{test_number}"

        desc_el = rule_el.find("description")
        verapdf_desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

        # Look up our internal mapping
        mapped = VERAPDF_RULE_MAP.get(key)

        for check_el in rule_el.iter("check"):
            if check_el.get("status") != "failed":
                continue

            context_el = check_el.find("context")
            element_text = (
                context_el.text.strip()
                if context_el is not None and context_el.text
                else None
            )

            page_number = _extract_page_number(check_el, element_text)

            if mapped:
                rule_id, wcag, severity, description, remediation = mapped
                findings.append(
                    Finding(
                        rule_id=rule_id,
                        severity=severity,
                        wcag=wcag,
                        description=description,
                        page=page_number,
                        element=element_text,
                        confidence="high",
                        remediation=remediation,
                    )
                )
            else:
                # Unmapped rule: pass through veraPDF info with a generic mapping
                findings.append(
                    Finding(
                        rule_id=f"VERAPDF.{clause}.{test_number}",
                        severity="warning",
                        wcag="",
                        description=verapdf_desc or f"veraPDF rule {key} failed.",
                        page=page_number,
                        element=element_text,
                        confidence="medium",
                        remediation="Review the veraPDF documentation for this rule.",
                    )
                )

    return findings


def _extract_page_number(
    check_el: ET.Element, context_text: str | None
) -> int | None:
    """Try to extract a page number from a veraPDF ``<check>`` element.

    veraPDF doesn't always provide a direct page number, so we look at:
    1. A ``page`` attribute on the check element.
    2. A ``pages`` child element.
    3. The context string for patterns like ``page 3`` or ``Page[2]``.
    """
    # Direct attribute
    page_attr = check_el.get("page")
    if page_attr is not None:
        try:
            return int(page_attr)
        except ValueError:
            pass

    # Child element
    pages_el = check_el.find("pages")
    if pages_el is not None and pages_el.text:
        try:
            return int(pages_el.text.strip())
        except ValueError:
            pass

    # Context string heuristic
    if context_text:
        import re

        m = re.search(r"[Pp]age\s*\[?(\d+)]?", context_text)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass

    return None


# ---------------------------------------------------------------------------
# Main validator class
# ---------------------------------------------------------------------------


class VeraPdfValidator:
    """Locate veraPDF and run PDF/UA validation on a file.

    Parameters
    ----------
    preference_path:
        Optional filesystem path to the veraPDF executable or its parent
        directory, typically read from user preferences.
    timeout:
        Maximum seconds to wait for veraPDF to finish. Defaults to 60.
    """

    def __init__(
        self,
        preference_path: str | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self._exe = _find_verapdf_exe(preference_path)
        self._timeout = timeout

    # -- Properties --------------------------------------------------------

    @property
    def available(self) -> bool:
        """``True`` if the veraPDF executable was found."""
        return self._exe is not None

    @property
    def exe_path(self) -> Path | None:
        """Resolved path to the veraPDF executable, or ``None``."""
        return self._exe

    # -- Public API --------------------------------------------------------

    def validate(self, pdf_path: str | Path) -> list[Finding]:
        """Run veraPDF on *pdf_path* and return a list of findings.

        If veraPDF is not available, returns a single informational finding.
        On timeout or crash the error is captured as a finding rather than
        propagating an exception.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.is_file():
            return [
                Finding(
                    rule_id="TOOL.FILE",
                    severity="error",
                    wcag="",
                    description=f"File not found: {pdf_path}",
                    confidence="high",
                    remediation="Provide a valid file path.",
                )
            ]

        if not self.available:
            return [
                Finding(
                    rule_id="TOOL.VERAPDF",
                    severity="warning",
                    wcag="",
                    description=(
                        "veraPDF is not installed or could not be found. "
                        "Install veraPDF and Java 11+ for full PDF/UA validation."
                    ),
                    confidence="high",
                    remediation=(
                        "Download veraPDF from https://verapdf.org and ensure "
                        "Java 11 or later is installed."
                    ),
                )
            ]

        assert self._exe is not None  # guaranteed by available check

        cmd: list[str] = [
            str(self._exe),
            "--format",
            "xml",
            "--profile",
            "ua1",
            str(pdf_path),
        ]

        logger.info("Running veraPDF: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except subprocess.TimeoutExpired:
            logger.error("veraPDF timed out after %d seconds", self._timeout)
            return [
                Finding(
                    rule_id="TOOL.VERAPDF",
                    severity="error",
                    wcag="",
                    description=(
                        f"veraPDF timed out after {self._timeout} seconds. "
                        "The PDF may be very large or complex."
                    ),
                    confidence="high",
                    remediation=(
                        "Try increasing the timeout or running veraPDF on a "
                        "smaller file."
                    ),
                )
            ]
        except OSError as exc:
            logger.error("Failed to run veraPDF: %s", exc)
            return [
                Finding(
                    rule_id="TOOL.VERAPDF",
                    severity="error",
                    wcag="",
                    description=f"Failed to run veraPDF: {exc}",
                    confidence="high",
                    remediation="Verify the veraPDF installation and Java availability.",
                )
            ]

        if result.returncode not in (0, 1):
            # veraPDF returns 1 when validation failures are found, 0 on pass.
            # Any other code indicates a crash or misconfiguration.
            stderr_snippet = (result.stderr or "")[:500]
            logger.error(
                "veraPDF exited with code %d: %s",
                result.returncode,
                stderr_snippet,
            )
            return [
                Finding(
                    rule_id="TOOL.VERAPDF",
                    severity="error",
                    wcag="",
                    description=(
                        f"veraPDF exited with unexpected code {result.returncode}. "
                        f"{stderr_snippet}"
                    ),
                    confidence="high",
                    remediation="Check the veraPDF installation and Java version.",
                )
            ]

        xml_output = result.stdout
        if not xml_output or not xml_output.strip():
            return [
                Finding(
                    rule_id="TOOL.VERAPDF",
                    severity="error",
                    wcag="",
                    description="veraPDF produced no output.",
                    confidence="high",
                    remediation="Re-run the check. Ensure veraPDF is correctly installed.",
                )
            ]

        return _parse_verapdf_xml(xml_output)
