"""pytest configuration and shared fixtures."""
from __future__ import annotations

import pytest
import pikepdf


@pytest.fixture
def minimal_pdf(tmp_path):
    """Create a minimal PDF file for testing."""
    pdf = pikepdf.Pdf.new()
    page = pikepdf.Page(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=[0, 0, 612, 792],
    ))
    pdf.pages.append(page)
    path = tmp_path / "test.pdf"
    pdf.save(path)
    return path


@pytest.fixture
def two_page_pdf(tmp_path):
    """Create a two-page PDF for testing."""
    pdf = pikepdf.Pdf.new()
    for _ in range(2):
        page = pikepdf.Page(pikepdf.Dictionary(
            Type=pikepdf.Name("/Page"),
            MediaBox=[0, 0, 612, 792],
        ))
        pdf.pages.append(page)
    path = tmp_path / "two_page.pdf"
    pdf.save(path)
    return path
