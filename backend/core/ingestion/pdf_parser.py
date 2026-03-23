"""PDF text extraction using PyMuPDF (fitz).

Future enhancement: use pdfplumber for table extraction from pages
that contain structured tabular data. For now, fitz handles all text.
"""

import logging
import re
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def _clean_text(raw: str) -> str:
    """Strip excessive whitespace while preserving paragraph breaks.

    Collapses runs of 3+ newlines to double newlines, and collapses
    runs of spaces/tabs within lines to a single space.
    """
    # Normalize line endings
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse horizontal whitespace (spaces/tabs) within lines
    text = re.sub(r"[^\S\n]+", " ", text)
    # Collapse 3+ consecutive newlines to exactly 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    # Strip leading/trailing whitespace from the whole result
    return text.strip()


def _extract_pages(doc: fitz.Document) -> list[dict]:
    """Extract text from each page of an opened fitz document.

    Returns:
        List of dicts with 'page_number' (1-indexed) and 'text'.
        Pages with no extractable text are skipped with a warning.
    """
    pages: list[dict] = []
    for i in range(len(doc)):
        page = doc[i]
        raw_text = page.get_text("text")
        cleaned = _clean_text(raw_text)

        if not cleaned:
            logger.warning(
                "Page %d has no extractable text (possibly image-only), skipping.",
                i + 1,
            )
            continue

        pages.append({
            "page_number": i + 1,
            "text": cleaned,
        })

    return pages


def parse_pdf_from_path(path: str | Path) -> list[dict]:
    """Extract text from a PDF file on disk.

    Args:
        path: Path to the PDF file.

    Returns:
        List of dicts: [{"page_number": 1, "text": "..."}, ...]
    """
    doc = fitz.open(str(path))
    try:
        return _extract_pages(doc)
    finally:
        doc.close()


def parse_pdf_from_bytes(content: bytes) -> list[dict]:
    """Extract text from PDF bytes in memory.

    Args:
        content: Raw PDF file bytes.

    Returns:
        List of dicts: [{"page_number": 1, "text": "..."}, ...]
    """
    doc = fitz.open(stream=content, filetype="pdf")
    try:
        return _extract_pages(doc)
    finally:
        doc.close()
