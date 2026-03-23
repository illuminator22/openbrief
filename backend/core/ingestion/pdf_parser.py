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


# Number of lines to inspect at the top/bottom of each page for repeating headers/footers
_HEADER_FOOTER_LINES = 3
# A line must appear on this fraction of pages (at the same position) to be considered repeating
_REPEAT_THRESHOLD = 0.5
# Minimum number of pages required before header/footer stripping kicks in
_MIN_PAGES_FOR_STRIPPING = 3


def _strip_repeating_headers_footers(pages: list[dict]) -> list[dict]:
    """Detect and remove repeating headers and footers from page text.

    Looks at the first and last few lines of each page. If the same line
    appears in the same position (top or bottom) on more than half the pages,
    it's treated as a repeating header/footer and stripped from all pages.
    """
    if len(pages) < _MIN_PAGES_FOR_STRIPPING:
        return pages

    threshold = max(3, int(len(pages) * _REPEAT_THRESHOLD))

    # Split each page into lines
    page_lines = [p["text"].split("\n") for p in pages]

    # Collect candidate lines by position
    # top_lines[i] = counter of line text at position i from the top
    from collections import Counter

    top_counts: dict[tuple[int, str], int] = Counter()
    bottom_counts: dict[tuple[int, str], int] = Counter()

    for lines in page_lines:
        for i in range(min(_HEADER_FOOTER_LINES, len(lines))):
            stripped = lines[i].strip()
            if stripped:
                top_counts[(i, stripped)] += 1

        for i in range(min(_HEADER_FOOTER_LINES, len(lines))):
            idx = len(lines) - 1 - i
            if idx >= 0:
                stripped = lines[idx].strip()
                if stripped:
                    bottom_counts[(i, stripped)] += 1

    # Find lines that repeat across enough pages
    repeating_top: set[str] = set()
    repeating_bottom: set[str] = set()

    for (pos, text), count in top_counts.items():
        if count >= threshold:
            repeating_top.add(text)
            logger.info("Detected repeating header: '%s' (appears on %d pages)", text, count)

    for (pos, text), count in bottom_counts.items():
        if count >= threshold:
            repeating_bottom.add(text)
            logger.info("Detected repeating footer: '%s' (appears on %d pages)", text, count)

    if not repeating_top and not repeating_bottom:
        return pages

    repeating_all = repeating_top | repeating_bottom

    # Strip repeating lines from all pages
    result: list[dict] = []
    for page in pages:
        lines = page["text"].split("\n")
        filtered = [line for line in lines if line.strip() not in repeating_all]
        cleaned = "\n".join(filtered).strip()

        if not cleaned:
            logger.warning(
                "Page %d is empty after stripping headers/footers, skipping.",
                page["page_number"],
            )
            continue

        result.append({
            "page_number": page["page_number"],
            "text": cleaned,
        })

    return result


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

    return _strip_repeating_headers_footers(pages)


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
