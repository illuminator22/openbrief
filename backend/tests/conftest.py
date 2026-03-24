"""Shared pytest fixtures for OpenBrief tests."""

from pathlib import Path

import fitz  # PyMuPDF
import pytest

from core.ingestion.embedder import EmbeddingService, get_embedding_service

_FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Fake legal contract text spread across 3 pages
_PAGE_1_TEXT = """MASTER SERVICES AGREEMENT

This Master Services Agreement ("Agreement") is entered into as of January 15, 2026,
by and between BrainX Corp, a Delaware corporation ("Company"), and Acme Legal
Services LLC, a California limited liability company ("Client").

ARTICLE I - DEFINITIONS

1.1 "Services" means the legal document analysis and intelligence services provided
by Company through its OpenBrief platform, including but not limited to document
ingestion, entity extraction, and AI-powered legal analysis.

1.2 "Confidential Information" means any non-public information disclosed by either
party to the other in connection with this Agreement, including but not limited to
trade secrets, business plans, financial data, customer lists, and technical
specifications. The obligations of confidentiality shall survive termination of this
Agreement for a period of five years.

1.3 "Effective Date" means the date first written above, which shall be the date
upon which this Agreement becomes binding on both parties and their respective
successors and assigns."""

_PAGE_2_TEXT = """Section 2.1 Payment Terms

Client shall pay Company a monthly subscription fee of Ten Thousand Dollars
($10,000.00) for access to the OpenBrief platform, payable within thirty (30) days
of invoice date. The fee shall be adjusted annually based on the Consumer Price
Index as published by the Bureau of Labor Statistics.

Section 2.2 Late Payment

Any amounts not paid when due shall bear interest at the rate of 1.5 percent per
month or the maximum rate permitted by applicable law, whichever is less. Client
shall also be responsible for all reasonable costs of collection including attorneys
fees and court costs.

Section 2.3 Taxes

All fees are exclusive of taxes. Client shall be responsible for all sales, use, and
excise taxes, and any other similar taxes, duties, and charges of any kind imposed
by any governmental authority on any amounts payable by Client hereunder."""

_PAGE_3_TEXT = """Section 3. Termination

3.1 Either party may terminate this Agreement immediately upon written notice if
the other party materially breaches this Agreement and fails to cure such breach
within thirty (30) days after receipt of written notice specifying the nature of
the breach in reasonable detail.

3.2 Either party may terminate this Agreement for convenience upon sixty (60) days
prior written notice to the other party.

ARTICLE IV - GOVERNING LAW

4.1 This Agreement shall be governed by and construed in accordance with the laws
of the State of Delaware, without regard to its conflict of laws principles.

4.2 LIMITATION OF LIABILITY. IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY
INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF
OR RELATED TO THIS AGREEMENT, REGARDLESS OF WHETHER SUCH DAMAGES ARE BASED ON
CONTRACT, TORT, STRICT LIABILITY, OR ANY OTHER THEORY."""


def _generate_test_pdf(path: Path) -> Path:
    """Generate a 3-page fake legal contract PDF for testing.

    Uses PyMuPDF (fitz) for PDF generation to ensure compatibility
    with pymupdf4llm's layout analysis model.
    """
    doc = fitz.open()
    font = fitz.Font("helv")

    for page_text in [_PAGE_1_TEXT, _PAGE_2_TEXT, _PAGE_3_TEXT]:
        page = doc.new_page()
        tw = fitz.TextWriter(page.rect)
        # Inset rect to leave margins
        text_rect = page.rect + (36, 36, -36, -36)
        tw.fill_textbox(text_rect, page_text, fontsize=10, font=font)
        tw.write_text(page)

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture(scope="session")
def test_pdf_path() -> Path:
    """Provide the path to a generated test PDF.

    Generated once per test session and reused across all tests.
    """
    path = _FIXTURES_DIR / "test_contract.pdf"
    if not path.exists():
        _generate_test_pdf(path)
    return path


@pytest.fixture(scope="session")
def embedding_service() -> EmbeddingService:
    """Provide the shared EmbeddingService singleton.

    The model loads once per test session, not per test.
    """
    return get_embedding_service()
