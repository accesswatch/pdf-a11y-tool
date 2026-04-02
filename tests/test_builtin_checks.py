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

    def test_dual_remediation(self, checker, blank_pdf):
        findings = checker.run(blank_pdf)
        title_f = [f for f in findings if f.rule_id == "PDFUA.TITLE"][0]
        assert title_f.remediation != ""
        assert title_f.acrobat_remediation != ""
        assert "Alt+Enter" in title_f.remediation
        assert "Properties" in title_f.acrobat_remediation


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


class TestNoHeadings:
    def test_no_headings_warning(self, checker, tagged_pdf):
        """Tagged document with only /P elements should trigger NO_HEADINGS."""
        findings = checker.run(tagged_pdf)
        nh = [f for f in findings if f.rule_id == "PDFBP.NO_HEADINGS"]
        assert len(nh) == 1
        assert nh[0].severity == "warning"

    def test_has_heading_no_finding(self, checker, tagged_pdf):
        """Document with at least one heading should NOT trigger NO_HEADINGS."""
        struct_root = tagged_pdf.Root["/StructTreeRoot"]
        kids = struct_root["/K"]
        h1 = pikepdf.Dictionary(S=pikepdf.Name("/H1"), Type=pikepdf.Name("/StructElem"))
        kids.append(tagged_pdf.make_indirect(h1))

        findings = checker.run(tagged_pdf)
        nh = [f for f in findings if f.rule_id == "PDFBP.NO_HEADINGS"]
        assert len(nh) == 0


class TestNonstdNoAlt:
    def test_nonstd_tag_without_alt(self, checker, tagged_pdf):
        """Non-standard tag (via RoleMap) without /Alt should trigger warning."""
        struct_root = tagged_pdf.Root["/StructTreeRoot"]
        # Add a RoleMap entry
        struct_root["/RoleMap"] = pikepdf.Dictionary(
            {"/InlineShape": pikepdf.Name("/Span")}
        )
        # Add an InlineShape element with no Alt
        elem = pikepdf.Dictionary(
            S=pikepdf.Name("/InlineShape"),
            Type=pikepdf.Name("/StructElem"),
        )
        kids = struct_root["/K"]
        kids.append(tagged_pdf.make_indirect(elem))

        findings = checker.run(tagged_pdf)
        ns = [f for f in findings if f.rule_id == "PDFBP.NONSTD_NO_ALT"]
        assert len(ns) >= 1

    def test_nonstd_tag_with_alt_no_finding(self, checker, tagged_pdf):
        """Non-standard tag with /Alt should NOT trigger warning."""
        struct_root = tagged_pdf.Root["/StructTreeRoot"]
        struct_root["/RoleMap"] = pikepdf.Dictionary(
            {"/InlineShape": pikepdf.Name("/Span")}
        )
        elem = pikepdf.Dictionary(
            S=pikepdf.Name("/InlineShape"),
            Type=pikepdf.Name("/StructElem"),
            Alt=pikepdf.String("Decorative border"),
        )
        kids = struct_root["/K"]
        kids.append(tagged_pdf.make_indirect(elem))

        findings = checker.run(tagged_pdf)
        ns = [f for f in findings if f.rule_id == "PDFBP.NONSTD_NO_ALT"]
        assert len(ns) == 0


class TestFlatStructure:
    def test_flat_document_triggers_tip(self, checker):
        """Document with >10 direct children and no Sect should trigger tip."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Flat Doc"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        # Build a flat Document node with 15 /P children
        children = pikepdf.Array()
        for _ in range(15):
            p = pikepdf.Dictionary(S=pikepdf.Name("/P"), Type=pikepdf.Name("/StructElem"))
            children.append(pdf.make_indirect(p))

        doc_node = pikepdf.Dictionary(
            S=pikepdf.Name("/Document"),
            Type=pikepdf.Name("/StructElem"),
            K=children,
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(doc_node)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)

        checker_inst = BuiltinChecker()
        findings = checker_inst.run(pdf)
        flat = [f for f in findings if f.rule_id == "PDFBP.FLAT_STRUCTURE"]
        assert len(flat) == 1
        assert flat[0].severity == "tip"

    def test_sectioned_document_no_finding(self, checker):
        """Document with Sect grouping should NOT trigger flat structure tip."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Sectioned Doc"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        # Build a Document with one Sect containing children
        sect = pikepdf.Dictionary(
            S=pikepdf.Name("/Sect"),
            Type=pikepdf.Name("/StructElem"),
            K=pikepdf.Array(),
        )
        for _ in range(12):
            p = pikepdf.Dictionary(S=pikepdf.Name("/P"), Type=pikepdf.Name("/StructElem"))
            sect["/K"].append(pdf.make_indirect(p))

        doc_node = pikepdf.Dictionary(
            S=pikepdf.Name("/Document"),
            Type=pikepdf.Name("/StructElem"),
            K=pikepdf.Array([pdf.make_indirect(sect)]),
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(doc_node)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)

        checker_inst = BuiltinChecker()
        findings = checker_inst.run(pdf)
        flat = [f for f in findings if f.rule_id == "PDFBP.FLAT_STRUCTURE"]
        assert len(flat) == 0


# ---------------------------------------------------------------------------
# FORMS_DETACHED
# ---------------------------------------------------------------------------

def _build_forms_detached_pdf(n_text: int, n_form: int) -> pikepdf.Pdf:
    """Build a synthetic PDF with text leaves followed by form leaves at end.

    Each text leaf is a /P with an MCID; each form leaf is a /Form with an OBJR.
    """
    pdf = pikepdf.Pdf.new()
    page = pikepdf.Page(
        pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
    )
    pdf.pages.append(page)
    pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
    pdf.docinfo["/Title"] = "Detached Forms Doc"
    pdf.Root["/Lang"] = pikepdf.String("en")
    pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

    page_ref = pdf.pages[0].obj

    children = pikepdf.Array()
    # Text leaves first
    for i in range(n_text):
        p = pikepdf.Dictionary(
            S=pikepdf.Name("/P"),
            Type=pikepdf.Name("/StructElem"),
            K=i,  # Integer MCID → leaf
        )
        children.append(pdf.make_indirect(p))

    # Form leaves at end
    for _ in range(n_form):
        objr = pikepdf.Dictionary(
            Type=pikepdf.Name("/OBJR"),
            Pg=page_ref,
        )
        form = pikepdf.Dictionary(
            S=pikepdf.Name("/Form"),
            Type=pikepdf.Name("/StructElem"),
            K=pdf.make_indirect(objr),
        )
        children.append(pdf.make_indirect(form))

    doc_node = pikepdf.Dictionary(
        S=pikepdf.Name("/Document"),
        Type=pikepdf.Name("/StructElem"),
        K=children,
    )
    struct_root = pikepdf.Dictionary(
        Type=pikepdf.Name("/StructTreeRoot"),
        K=pikepdf.Array([pdf.make_indirect(doc_node)]),
    )
    pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
    return pdf


class TestFormsDetached:
    def test_forms_at_end_triggers_error(self):
        """All form fields grouped after all text should trigger error."""
        pdf = _build_forms_detached_pdf(n_text=10, n_form=8)
        checker = BuiltinChecker()
        findings = checker.run(pdf)
        fd = [f for f in findings if f.rule_id == "PDFBP.FORMS_DETACHED"]
        assert len(fd) == 1
        assert fd[0].severity == "error"
        assert "8 of 8 form fields" in fd[0].description

    def test_interleaved_forms_no_finding(self):
        """Forms interleaved with text should NOT trigger."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Interleaved Doc"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        page_ref = pdf.pages[0].obj

        # Build interleaved: P, Form, P, Form, P, Form ...
        children = pikepdf.Array()
        for i in range(6):
            p = pikepdf.Dictionary(
                S=pikepdf.Name("/P"),
                Type=pikepdf.Name("/StructElem"),
                K=i,
            )
            children.append(pdf.make_indirect(p))
            objr = pikepdf.Dictionary(Type=pikepdf.Name("/OBJR"), Pg=page_ref)
            form = pikepdf.Dictionary(
                S=pikepdf.Name("/Form"),
                Type=pikepdf.Name("/StructElem"),
                K=pdf.make_indirect(objr),
            )
            children.append(pdf.make_indirect(form))

        doc_node = pikepdf.Dictionary(
            S=pikepdf.Name("/Document"),
            Type=pikepdf.Name("/StructElem"),
            K=children,
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(doc_node)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)

        checker = BuiltinChecker()
        findings = checker.run(pdf)
        fd = [f for f in findings if f.rule_id == "PDFBP.FORMS_DETACHED"]
        assert len(fd) == 0

    def test_single_form_no_finding(self):
        """Only one form field should not trigger (needs >= 2)."""
        pdf = _build_forms_detached_pdf(n_text=5, n_form=1)
        checker = BuiltinChecker()
        findings = checker.run(pdf)
        fd = [f for f in findings if f.rule_id == "PDFBP.FORMS_DETACHED"]
        assert len(fd) == 0


# ---------------------------------------------------------------------------
# UNDERSCORE_FILL
# ---------------------------------------------------------------------------

class TestUnderscoreFill:
    def test_underscore_fill_detected(self, tmp_path):
        """Pages with underscore fill lines should trigger warning."""
        from unittest.mock import MagicMock, patch

        # Create a fake pypdfium2 module that returns text with underscores
        mock_page = MagicMock()
        mock_tp = MagicMock()
        mock_tp.get_text_range.return_value = (
            "Name ________________________________\n"
            "Address ______________________________\n"
            "Normal text without fills\n"
        )
        mock_page.get_textpage.return_value = mock_tp

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)

        mock_pypdfium2 = MagicMock()
        mock_pypdfium2.PdfDocument.return_value = mock_doc

        # Create a real pikepdf PDF saved to disk so pdf.filename exists
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Underscore Doc"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        p_elem = pikepdf.Dictionary(
            S=pikepdf.Name("/P"),
            Type=pikepdf.Name("/StructElem"),
            K=0,
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(p_elem)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)

        pdf_path = tmp_path / "underscore.pdf"
        pdf.save(str(pdf_path))

        # Reopen so .filename is set
        pdf2 = pikepdf.open(str(pdf_path))

        with patch.dict("sys.modules", {"pypdfium2": mock_pypdfium2}):
            checker = BuiltinChecker()
            findings = checker.run(pdf2)

        pdf2.close()

        uf = [f for f in findings if f.rule_id == "PDFBP.UNDERSCORE_FILL"]
        assert len(uf) == 1
        assert uf[0].severity == "warning"
        assert "2 line(s)" in uf[0].description

    def test_no_underscores_no_finding(self, tmp_path):
        """Pages without underscore fills should NOT trigger."""
        from unittest.mock import MagicMock, patch

        mock_page = MagicMock()
        mock_tp = MagicMock()
        mock_tp.get_text_range.return_value = (
            "This is normal text.\n"
            "No underscores here at all.\n"
        )
        mock_page.get_textpage.return_value = mock_tp

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)

        mock_pypdfium2 = MagicMock()
        mock_pypdfium2.PdfDocument.return_value = mock_doc

        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Clean Doc"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        p_elem = pikepdf.Dictionary(
            S=pikepdf.Name("/P"),
            Type=pikepdf.Name("/StructElem"),
            K=0,
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(p_elem)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)

        pdf_path = tmp_path / "clean.pdf"
        pdf.save(str(pdf_path))
        pdf2 = pikepdf.open(str(pdf_path))

        with patch.dict("sys.modules", {"pypdfium2": mock_pypdfium2}):
            checker = BuiltinChecker()
            findings = checker.run(pdf2)

        pdf2.close()

        uf = [f for f in findings if f.rule_id == "PDFBP.UNDERSCORE_FILL"]
        assert len(uf) == 0


class TestTabOrder:
    def test_missing_tab_order_warns(self, checker, tagged_pdf):
        """Page without /Tabs /S should trigger PDFBP.NAV.TABORDER."""
        findings = checker.run(tagged_pdf)
        tab_findings = [f for f in findings if f.rule_id == "PDFBP.NAV.TABORDER"]
        assert len(tab_findings) >= 1
        assert tab_findings[0].severity == "warning"
        assert tab_findings[0].page == 1

    def test_correct_tab_order_no_finding(self, checker, tagged_pdf):
        """Page with /Tabs /S should NOT trigger."""
        tagged_pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")
        findings = checker.run(tagged_pdf)
        tab_findings = [f for f in findings if f.rule_id == "PDFBP.NAV.TABORDER"]
        assert len(tab_findings) == 0


class TestTextExtractable:
    def test_image_only_pdf_reports_error(self, tmp_path):
        """PDF with no extractable text should trigger error."""
        from unittest.mock import MagicMock, patch

        mock_page = MagicMock()
        mock_tp = MagicMock()
        mock_tp.get_text_range.return_value = ""
        mock_page.get_textpage.return_value = mock_tp

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=2)
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)

        mock_pypdfium2 = MagicMock()
        mock_pypdfium2.PdfDocument.return_value = mock_doc

        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.docinfo["/Title"] = "Scanned Doc"
        pdf.Root["/Lang"] = pikepdf.String("en")

        pdf_path = tmp_path / "scan.pdf"
        pdf.save(str(pdf_path))
        pdf2 = pikepdf.open(str(pdf_path))

        with patch.dict("sys.modules", {"pypdfium2": mock_pypdfium2}):
            checker = BuiltinChecker()
            findings = checker.run(pdf2)

        pdf2.close()

        ext = [f for f in findings if f.rule_id == "PDFBP.TEXT.EXTRACTABLE"]
        assert len(ext) == 1
        assert ext[0].severity == "error"
        assert "scanned" in ext[0].description.lower() or "image-only" in ext[0].description.lower()

    def test_text_pdf_no_finding(self, tmp_path):
        """PDF with extractable text should NOT trigger."""
        from unittest.mock import MagicMock, patch

        mock_page = MagicMock()
        mock_tp = MagicMock()
        mock_tp.get_text_range.return_value = "Hello world, this has real text content."
        mock_page.get_textpage.return_value = mock_tp

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)

        mock_pypdfium2 = MagicMock()
        mock_pypdfium2.PdfDocument.return_value = mock_doc

        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.docinfo["/Title"] = "Normal Doc"
        pdf.Root["/Lang"] = pikepdf.String("en")

        pdf_path = tmp_path / "normal.pdf"
        pdf.save(str(pdf_path))
        pdf2 = pikepdf.open(str(pdf_path))

        with patch.dict("sys.modules", {"pypdfium2": mock_pypdfium2}):
            checker = BuiltinChecker()
            findings = checker.run(pdf2)

        pdf2.close()

        ext = [f for f in findings if f.rule_id == "PDFBP.TEXT.EXTRACTABLE"]
        assert len(ext) == 0


class TestAltTextLength:
    def test_long_alt_text_warns(self, checker):
        """Figure with alt text >250 chars should warn."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Alt Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        long_alt = "A " * 150  # 300 chars
        fig = pikepdf.Dictionary(
            S=pikepdf.Name("/Figure"),
            Type=pikepdf.Name("/StructElem"),
            Alt=pikepdf.String(long_alt),
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(fig)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        alt_findings = [f for f in findings if f.rule_id == "PDFBP.ALT_LENGTH"]
        assert len(alt_findings) == 1
        assert alt_findings[0].severity == "warning"

    def test_normal_alt_text_no_finding(self, checker):
        """Figure with reasonable alt text should NOT trigger."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Alt Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        fig = pikepdf.Dictionary(
            S=pikepdf.Name("/Figure"),
            Type=pikepdf.Name("/StructElem"),
            Alt=pikepdf.String("A chart showing quarterly revenue growth."),
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(fig)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        alt_findings = [f for f in findings if f.rule_id == "PDFBP.ALT_LENGTH"]
        assert len(alt_findings) == 0


class TestAltTextQuality:
    def test_filename_alt_text_warns(self, checker):
        """Figure with filename as alt text should warn."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Quality Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        fig = pikepdf.Dictionary(
            S=pikepdf.Name("/Figure"),
            Type=pikepdf.Name("/StructElem"),
            Alt=pikepdf.String("DSC_0042.jpg"),
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(fig)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        qf = [f for f in findings if f.rule_id == "PDFBP.ALT_QUALITY"]
        assert len(qf) == 1
        assert qf[0].severity == "warning"
        assert "filename" in qf[0].description.lower() or "placeholder" in qf[0].description.lower()

    def test_placeholder_alt_text_warns(self, checker):
        """Figure with 'image1' alt text should warn."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Quality Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        fig = pikepdf.Dictionary(
            S=pikepdf.Name("/Figure"),
            Type=pikepdf.Name("/StructElem"),
            Alt=pikepdf.String("image1"),
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(fig)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        qf = [f for f in findings if f.rule_id == "PDFBP.ALT_QUALITY"]
        assert len(qf) == 1

    def test_good_alt_text_no_finding(self, checker):
        """Figure with descriptive alt text should NOT trigger."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Quality Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        fig = pikepdf.Dictionary(
            S=pikepdf.Name("/Figure"),
            Type=pikepdf.Name("/StructElem"),
            Alt=pikepdf.String("Company logo showing a blue shield with white text"),
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(fig)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        qf = [f for f in findings if f.rule_id == "PDFBP.ALT_QUALITY"]
        assert len(qf) == 0


class TestLangValid:
    def test_invalid_lang_reports_error(self, checker):
        """Invalid BCP 47 code should trigger PDFBP.LANG_VALID."""
        pdf = pikepdf.Pdf.new()
        pdf.docinfo["/Title"] = "Test"
        pdf.Root["/Lang"] = pikepdf.String("xyz-INVALID-99")

        findings = checker.run(pdf)
        lf = [f for f in findings if f.rule_id == "PDFBP.LANG_VALID"]
        assert len(lf) == 1
        assert lf[0].severity == "error"

    def test_valid_lang_no_finding(self, checker):
        """Valid BCP 47 code should NOT trigger."""
        pdf = pikepdf.Pdf.new()
        pdf.docinfo["/Title"] = "Test"
        pdf.Root["/Lang"] = pikepdf.String("en-US")

        findings = checker.run(pdf)
        lf = [f for f in findings if f.rule_id == "PDFBP.LANG_VALID"]
        assert len(lf) == 0

    def test_simple_lang_code_no_finding(self, checker):
        """Simple two-letter lang code should NOT trigger."""
        pdf = pikepdf.Pdf.new()
        pdf.docinfo["/Title"] = "Test"
        pdf.Root["/Lang"] = pikepdf.String("fr")

        findings = checker.run(pdf)
        lf = [f for f in findings if f.rule_id == "PDFBP.LANG_VALID"]
        assert len(lf) == 0


class TestLinkText:
    def test_click_here_link_warns(self, checker):
        """Link with 'click here' text should warn."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Link Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        link_elem = pikepdf.Dictionary(
            S=pikepdf.Name("/Link"),
            Type=pikepdf.Name("/StructElem"),
            Alt=pikepdf.String("click here"),
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(link_elem)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        lf = [f for f in findings if f.rule_id == "PDFBP.LINK_TEXT"]
        assert len(lf) == 1
        assert lf[0].severity == "warning"

    def test_descriptive_link_no_finding(self, checker):
        """Link with descriptive text should NOT trigger."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Link Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        link_elem = pikepdf.Dictionary(
            S=pikepdf.Name("/Link"),
            Type=pikepdf.Name("/StructElem"),
            Alt=pikepdf.String("Download the accessibility report (PDF)"),
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(link_elem)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        lf = [f for f in findings if f.rule_id == "PDFBP.LINK_TEXT"]
        assert len(lf) == 0


class TestEmptyTags:
    def test_empty_p_tags_warn(self, checker):
        """Tags with no /K children should trigger PDFBP.EMPTY_TAGS."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Empty Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        empty1 = pikepdf.Dictionary(S=pikepdf.Name("/P"), Type=pikepdf.Name("/StructElem"))
        empty2 = pikepdf.Dictionary(S=pikepdf.Name("/Span"), Type=pikepdf.Name("/StructElem"))
        normal = pikepdf.Dictionary(
            S=pikepdf.Name("/P"), Type=pikepdf.Name("/StructElem"), K=0,
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([
                pdf.make_indirect(empty1),
                pdf.make_indirect(empty2),
                pdf.make_indirect(normal),
            ]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        ef = [f for f in findings if f.rule_id == "PDFBP.EMPTY_TAGS"]
        assert len(ef) == 1
        assert ef[0].severity == "warning"
        assert "2 empty" in ef[0].description

    def test_no_empty_tags_no_finding(self, checker):
        """All tags have content -- should NOT trigger."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Content Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        # P tag WITH a /K (MCID reference) -- NOT empty
        p_elem = pikepdf.Dictionary(
            S=pikepdf.Name("/P"), Type=pikepdf.Name("/StructElem"), K=0,
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(p_elem)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        ef = [f for f in findings if f.rule_id == "PDFBP.EMPTY_TAGS"]
        assert len(ef) == 0


class TestDuplicateFieldNames:
    def test_duplicate_names_error(self, checker):
        """Two text fields with same name should trigger error."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.docinfo["/Title"] = "Form Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        field1 = pdf.make_indirect(pikepdf.Dictionary(
            T=pikepdf.String("Name"),
            TU=pikepdf.String("Your name"),
            FT=pikepdf.Name("/Tx"),
        ))
        field2 = pdf.make_indirect(pikepdf.Dictionary(
            T=pikepdf.String("Name"),
            TU=pikepdf.String("Your name again"),
            FT=pikepdf.Name("/Tx"),
        ))

        pdf.Root["/AcroForm"] = pikepdf.Dictionary(
            Fields=pikepdf.Array([field1, field2])
        )
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        df = [f for f in findings if f.rule_id == "PDFBP.FORMS.DUPLICATE_NAMES"]
        assert len(df) == 1
        assert df[0].severity == "error"
        assert "2 times" in df[0].description

    def test_unique_names_no_finding(self, checker):
        """Fields with different names should NOT trigger."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.docinfo["/Title"] = "Form Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        field1 = pdf.make_indirect(pikepdf.Dictionary(
            T=pikepdf.String("FirstName"),
            TU=pikepdf.String("First name"),
            FT=pikepdf.Name("/Tx"),
        ))
        field2 = pdf.make_indirect(pikepdf.Dictionary(
            T=pikepdf.String("LastName"),
            TU=pikepdf.String("Last name"),
            FT=pikepdf.Name("/Tx"),
        ))

        pdf.Root["/AcroForm"] = pikepdf.Dictionary(
            Fields=pikepdf.Array([field1, field2])
        )
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        df = [f for f in findings if f.rule_id == "PDFBP.FORMS.DUPLICATE_NAMES"]
        assert len(df) == 0

    def test_radio_buttons_same_name_allowed(self, checker):
        """Radio buttons sharing a group name should NOT trigger duplicate check."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.docinfo["/Title"] = "Radio Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        # Ff bit 15 = radio button (0x8000 = 32768)
        radio1 = pdf.make_indirect(pikepdf.Dictionary(
            T=pikepdf.String("DoYouLikeChocolate"),
            TU=pikepdf.String("Do you like chocolate?"),
            FT=pikepdf.Name("/Btn"),
            Ff=32768,
        ))
        radio2 = pdf.make_indirect(pikepdf.Dictionary(
            T=pikepdf.String("DoYouLikeChocolate"),
            TU=pikepdf.String("Do you like chocolate?"),
            FT=pikepdf.Name("/Btn"),
            Ff=32768,
        ))

        pdf.Root["/AcroForm"] = pikepdf.Dictionary(
            Fields=pikepdf.Array([radio1, radio2])
        )
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        df = [f for f in findings if f.rule_id == "PDFBP.FORMS.DUPLICATE_NAMES"]
        assert len(df) == 0


class TestRadioGroup:
    def test_single_radio_button_warns(self, checker):
        """Radio group with only 1 child option should warn."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.docinfo["/Title"] = "Radio Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        # Radio button with only 1 kid
        kid = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name("/Annot"),
            Subtype=pikepdf.Name("/Widget"),
        ))
        radio = pdf.make_indirect(pikepdf.Dictionary(
            T=pikepdf.String("LonelyRadio"),
            TU=pikepdf.String("Single option"),
            FT=pikepdf.Name("/Btn"),
            Ff=32768,
            Kids=pikepdf.Array([kid]),
        ))

        pdf.Root["/AcroForm"] = pikepdf.Dictionary(
            Fields=pikepdf.Array([radio])
        )
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        rf = [f for f in findings if f.rule_id == "PDFBP.FORMS.RADIO_GROUP"]
        assert len(rf) == 1
        assert rf[0].severity == "warning"

    def test_proper_radio_group_no_finding(self, checker):
        """Radio group with 2+ options should NOT trigger."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.docinfo["/Title"] = "Radio Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        kid1 = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name("/Annot"),
            Subtype=pikepdf.Name("/Widget"),
        ))
        kid2 = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name("/Annot"),
            Subtype=pikepdf.Name("/Widget"),
        ))
        radio = pdf.make_indirect(pikepdf.Dictionary(
            T=pikepdf.String("DoYouLikeChocolate"),
            TU=pikepdf.String("Do you like chocolate?"),
            FT=pikepdf.Name("/Btn"),
            Ff=32768,
            Kids=pikepdf.Array([kid1, kid2]),
        ))

        pdf.Root["/AcroForm"] = pikepdf.Dictionary(
            Fields=pikepdf.Array([radio])
        )
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        rf = [f for f in findings if f.rule_id == "PDFBP.FORMS.RADIO_GROUP"]
        assert len(rf) == 0


class TestListStructure:
    def test_bad_list_children_warn(self, checker):
        """L tag containing P instead of LI should trigger warning."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "List Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        bad_child = pikepdf.Dictionary(
            S=pikepdf.Name("/P"), Type=pikepdf.Name("/StructElem"), K=0,
        )
        list_elem = pikepdf.Dictionary(
            S=pikepdf.Name("/L"),
            Type=pikepdf.Name("/StructElem"),
            K=pikepdf.Array([pdf.make_indirect(bad_child)]),
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(list_elem)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        lf = [f for f in findings if f.rule_id == "PDFBP.LIST_STRUCT"]
        assert len(lf) >= 1
        assert any("non-LI" in f.description.lower() or "P" in f.description for f in lf)

    def test_proper_list_no_finding(self, checker):
        """L > LI > LBody structure should NOT trigger."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "List Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        lbody = pikepdf.Dictionary(
            S=pikepdf.Name("/LBody"), Type=pikepdf.Name("/StructElem"), K=0,
        )
        li = pikepdf.Dictionary(
            S=pikepdf.Name("/LI"),
            Type=pikepdf.Name("/StructElem"),
            K=pikepdf.Array([pdf.make_indirect(lbody)]),
        )
        list_elem = pikepdf.Dictionary(
            S=pikepdf.Name("/L"),
            Type=pikepdf.Name("/StructElem"),
            K=pikepdf.Array([pdf.make_indirect(li)]),
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(list_elem)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        lf = [f for f in findings if f.rule_id == "PDFBP.LIST_STRUCT"]
        assert len(lf) == 0


class TestArtTags:
    def test_art_tags_detected(self, checker):
        """Art tags should trigger PDFBP.ART_TAGS tip."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Art Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        art = pikepdf.Dictionary(
            S=pikepdf.Name("/Art"), Type=pikepdf.Name("/StructElem"),
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(art)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        af = [f for f in findings if f.rule_id == "PDFBP.ART_TAGS"]
        assert len(af) == 1
        assert af[0].severity == "tip"

    def test_no_art_tags_no_finding(self, checker, tagged_pdf):
        """Document without Art tags should NOT trigger."""
        tagged_pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")
        findings = checker.run(tagged_pdf)
        af = [f for f in findings if f.rule_id == "PDFBP.ART_TAGS"]
        assert len(af) == 0


class TestSectNesting:
    def test_deep_sect_nesting_warns(self, checker):
        """Sect nested >3 levels should trigger tip."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Sect Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        # Build 5 levels deep: Sect > Sect > Sect > Sect > Sect > P
        p_elem = pikepdf.Dictionary(
            S=pikepdf.Name("/P"), Type=pikepdf.Name("/StructElem"), K=0,
        )
        inner = pdf.make_indirect(p_elem)
        for _ in range(5):
            sect = pikepdf.Dictionary(
                S=pikepdf.Name("/Sect"),
                Type=pikepdf.Name("/StructElem"),
                K=pikepdf.Array([inner]),
            )
            inner = pdf.make_indirect(sect)

        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([inner]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        sf = [f for f in findings if f.rule_id == "PDFBP.SECT_NESTING"]
        assert len(sf) == 1
        assert sf[0].severity == "tip"

    def test_shallow_nesting_no_finding(self, checker):
        """Sect nested <=3 levels should NOT trigger."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Sect Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        p_elem = pikepdf.Dictionary(
            S=pikepdf.Name("/P"), Type=pikepdf.Name("/StructElem"), K=0,
        )
        sect = pikepdf.Dictionary(
            S=pikepdf.Name("/Sect"),
            Type=pikepdf.Name("/StructElem"),
            K=pikepdf.Array([pdf.make_indirect(p_elem)]),
        )
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([pdf.make_indirect(sect)]),
        )
        pdf.Root["/StructTreeRoot"] = pdf.make_indirect(struct_root)
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        sf = [f for f in findings if f.rule_id == "PDFBP.SECT_NESTING"]
        assert len(sf) == 0


class TestTooltipQuality:
    def test_generic_tooltip_warns(self, checker):
        """Generic tooltip like 'text' should warn."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.docinfo["/Title"] = "Tooltip Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        field = pdf.make_indirect(pikepdf.Dictionary(
            T=pikepdf.String("field1"),
            TU=pikepdf.String("text"),
            FT=pikepdf.Name("/Tx"),
        ))
        pdf.Root["/AcroForm"] = pikepdf.Dictionary(
            Fields=pikepdf.Array([field])
        )
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        tf = [f for f in findings if f.rule_id == "PDFBP.FORMS.TOOLTIP_QUALITY"]
        assert len(tf) == 1
        assert tf[0].severity == "warning"

    def test_descriptive_tooltip_no_finding(self, checker):
        """Descriptive tooltip should NOT trigger."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.docinfo["/Title"] = "Tooltip Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        field = pdf.make_indirect(pikepdf.Dictionary(
            T=pikepdf.String("firstName"),
            TU=pikepdf.String("First Name"),
            FT=pikepdf.Name("/Tx"),
        ))
        pdf.Root["/AcroForm"] = pikepdf.Dictionary(
            Fields=pikepdf.Array([field])
        )
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        tf = [f for f in findings if f.rule_id == "PDFBP.FORMS.TOOLTIP_QUALITY"]
        assert len(tf) == 0


class TestFigureCaption:
    def test_orphaned_caption_triggers_tip(self, checker):
        """Caption tag not adjacent to Figure should trigger tip."""
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(Type=pikepdf.Name("/Page"), MediaBox=[0, 0, 612, 792])
        )
        pdf.pages.append(page)
        pdf.Root["/MarkInfo"] = pikepdf.Dictionary(Marked=True)
        pdf.docinfo["/Title"] = "Caption Test"
        pdf.Root["/Lang"] = pikepdf.String("en")
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)

        # Caption with no sibling Figure -- parent is struct root
        caption = pikepdf.Dictionary(
            S=pikepdf.Name("/Caption"), Type=pikepdf.Name("/StructElem"),
        )
        p_elem = pikepdf.Dictionary(
            S=pikepdf.Name("/P"), Type=pikepdf.Name("/StructElem"), K=0,
        )
        caption_ref = pdf.make_indirect(caption)
        p_ref = pdf.make_indirect(p_elem)
        struct_root = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructTreeRoot"),
            K=pikepdf.Array([caption_ref, p_ref]),
        )
        root_ref = pdf.make_indirect(struct_root)
        # Set parent references
        caption["/P"] = root_ref
        p_elem["/P"] = root_ref
        pdf.Root["/StructTreeRoot"] = root_ref
        pdf.pages[0]["/Tabs"] = pikepdf.Name("/S")

        findings = checker.run(pdf)
        cf = [f for f in findings if f.rule_id == "PDFBP.FIGURE_CAPTION"]
        assert len(cf) == 1
        assert cf[0].severity == "tip"
