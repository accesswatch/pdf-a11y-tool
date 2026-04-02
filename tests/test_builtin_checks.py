"""Tests for pdf_a11y.core.builtin_checks."""
from __future__ import annotations

import pikepdf
import pytest

from pdf_a11y.core.builtin_checks import BuiltinChecker
from pdf_a11y.core.validator import Finding


@pytest.fixture
def checker():
    return BuiltinChecker()


@pytest.fixture
def blank_pdf():
    """A minimal PDF with no accessibility features."""
    return pikepdf.Pdf.new()


@pytest.fixture
def tagged_pdf():
    """A PDF with StructTreeRoot, MarkInfo, title, and language."""
    pdf = pikepdf.Pdf.new()
    page = pikepdf.Page(
        pikepdf.Dictionary(
            Type=pikepdf.Name("/Page"),
            MediaBox=[0, 0, 612, 792],
        )
    )
    pdf.pages.append(page)

    # MarkInfo
    pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)

    # StructTreeRoot with one P element
    p_elem = pikepdf.Dictionary(
        S=pikepdf.Name("/P"),
        Type=pikepdf.Name("/StructElem"),
    )
    struct_root = pikepdf.Dictionary(
        Type=pikepdf.Name("/StructTreeRoot"),
        K=pikepdf.Array([pdf.make_indirect(p_elem)]),
    )
    pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)

    # Metadata
    pdf.docinfo["/Title"] = "Test Document"
    pdf.Root["/Lang"] = pikepdf.String("en-US")
    pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

    return pdf


class TestMissingTitle:
    def test_no_title_reports_error(self, checker, blank_pdf):
        findings = checker.run(blank_pdf)
        title_findings = [f for f in findings if f.rule_id == "PDFUA.TITLE"]
        assert len(title_findings) >= 1
        assert title_findings[0].severity == "error"

    def test_with_title_no_finding(self, checker, tagged_pdf):
        findings = checker.run(tagged_pdf)
        title_findings = [f for f in findings if f.rule_id == "PDFUA.TITLE"]
        assert len(title_findings) == 0


class TestMissingLanguage:
    def test_no_lang_reports_error(self, checker, blank_pdf):
        findings = checker.run(blank_pdf)
        lang_findings = [f for f in findings if f.rule_id == "PDFUA.LANG"]
        assert len(lang_findings) >= 1
        assert lang_findings[0].severity == "error"

    def test_with_lang_no_finding(self, checker, tagged_pdf):
        findings = checker.run(tagged_pdf)
        lang_findings = [f for f in findings if f.rule_id == "PDFUA.LANG"]
        assert len(lang_findings) == 0


class TestTagged:
    def test_untagged_reports_error(self, checker, blank_pdf):
        findings = checker.run(blank_pdf)
        tagged_findings = [f for f in findings if f.rule_id == "PDFUA.TAGGED"]
        assert any(f.severity == "error" for f in tagged_findings)

    def test_tagged_no_finding(self, checker, tagged_pdf):
        findings = checker.run(tagged_pdf)
        tagged_findings = [
            f
            for f in findings
            if f.rule_id == "PDFUA.TAGGED"
               and "not tagged" in f.description.lower()
        ]
        assert len(tagged_findings) == 0


class TestFigureAltText:
    def test_figure_without_alt_text(self, checker, tagged_pdf):
        # Add a Figure element with no Alt
        struct_root = tagged_pdf.Root["/StructTreeRoot"]
        fig = pikepdf.Dictionary(
            S=pikepdf.Name("/Figure"),
            Type=pikepdf.Name("/StructElem"),
        )
        kids = struct_root["/K"]
        kids.append(tagged_pdf.make_indirect(fig))

        findings = checker.run(tagged_pdf)
        alt_findings = [f for f in findings if f.rule_id == "PDFUA.IMG.ALT"]
        assert len(alt_findings) >= 1

    def test_figure_with_alt_text(self, checker, tagged_pdf):
        struct_root = tagged_pdf.Root["/StructTreeRoot"]
        fig = pikepdf.Dictionary(
            S=pikepdf.Name("/Figure"),
            Type=pikepdf.Name("/StructElem"),
            Alt=pikepdf.String("A photo of a cat"),
        )
        kids = struct_root["/K"]
        kids.append(tagged_pdf.make_indirect(fig))

        findings = checker.run(tagged_pdf)
        alt_findings = [f for f in findings if f.rule_id == "PDFUA.IMG.ALT"]
        assert len(alt_findings) == 0


class TestHeadingHierarchy:
    def test_skipped_heading_level(self, checker, tagged_pdf):
        struct_root = tagged_pdf.Root["/StructTreeRoot"]
        kids = struct_root["/K"]
        # H1 then H3 (skipping H2)
        h1 = pikepdf.Dictionary(S=pikepdf.Name("/H1"), Type=pikepdf.Name("/StructElem"))
        h3 = pikepdf.Dictionary(S=pikepdf.Name("/H3"), Type=pikepdf.Name("/StructElem"))
        kids.append(tagged_pdf.make_indirect(h1))
        kids.append(tagged_pdf.make_indirect(h3))

        findings = checker.run(tagged_pdf)
        heading_findings = [f for f in findings if f.rule_id == "PDFUA.HEADINGS"]
        assert len(heading_findings) >= 1
        assert "skipped" in heading_findings[0].description.lower()

    def test_consecutive_headings_ok(self, checker, tagged_pdf):
        struct_root = tagged_pdf.Root["/StructTreeRoot"]
        kids = struct_root["/K"]
        h1 = pikepdf.Dictionary(S=pikepdf.Name("/H1"), Type=pikepdf.Name("/StructElem"))
        h2 = pikepdf.Dictionary(S=pikepdf.Name("/H2"), Type=pikepdf.Name("/StructElem"))
        kids.append(tagged_pdf.make_indirect(h1))
        kids.append(tagged_pdf.make_indirect(h2))

        findings = checker.run(tagged_pdf)
        heading_findings = [f for f in findings if f.rule_id == "PDFUA.HEADINGS"]
        assert len(heading_findings) == 0


class TestFormFields:
    def test_form_field_without_tooltip(self, checker, tagged_pdf):
        field = pikepdf.Dictionary(
            T=pikepdf.String("name"),
            FT=pikepdf.Name("/Tx"),
        )
        tagged_pdf.Root["/AcroForm"] = pikepdf.Dictionary(
            Fields=pikepdf.Array([tagged_pdf.make_indirect(field)])
        )

        findings = checker.run(tagged_pdf)
        form_findings = [f for f in findings if f.rule_id == "PDFUA.FORMS"]
        assert any("tooltip" in f.description.lower() for f in form_findings)


class TestDisplayDocTitle:
    def test_missing_viewer_prefs(self, checker, blank_pdf):
        findings = checker.run(blank_pdf)
        ddt_findings = [f for f in findings if f.rule_id == "PDFBP.DISPLAY_TITLE"]
        assert len(ddt_findings) >= 1

    def test_with_display_doc_title(self, checker, tagged_pdf):
        findings = checker.run(tagged_pdf)
        ddt_findings = [f for f in findings if f.rule_id == "PDFBP.DISPLAY_TITLE"]
        assert len(ddt_findings) == 0


class TestBookmarks:
    def test_many_pages_no_bookmarks(self, checker):
        pdf = pikepdf.Pdf.new()
        for _ in range(25):
            page = pikepdf.Page(
                pikepdf.Dictionary(
                    Type=pikepdf.Name("/Page"),
                    MediaBox=[0, 0, 612, 792],
                )
            )
            pdf.pages.append(page)
        # Add basic metadata to avoid other errors
        pdf.docinfo["/Title"] = "Big Doc"
        pdf.Root["/Lang"] = pikepdf.String("en")

        findings = checker.run(pdf)
        bm_findings = [f for f in findings if f.rule_id == "PDFUA.BOOKMARKS"]
        assert len(bm_findings) >= 1

    def test_few_pages_no_finding(self, checker, tagged_pdf):
        findings = checker.run(tagged_pdf)
        bm_findings = [f for f in findings if f.rule_id == "PDFUA.BOOKMARKS"]
        assert len(bm_findings) == 0
