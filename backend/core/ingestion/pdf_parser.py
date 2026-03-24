"""PDF text extraction using PyMuPDF4LLM.

Uses pymupdf4llm's layout analysis mode to extract text as Markdown
with automatic header/footer stripping. Section headings are output
as ## markdown headings, which the chunker uses for section detection.

Future enhancement: pdfplumber for table extraction on table-heavy pages.
"""

import logging
import re
from pathlib import Path

import fitz  # PyMuPDF
import pymupdf4llm

logger = logging.getLogger(__name__)


def _strip_repeating_headings(pages: list[dict]) -> list[dict]:
    """Strip markdown headings that repeat across most pages.

    pymupdf4llm strips plain-text headers/footers via header=False/footer=False,
    but repeating section-styled headings (e.g., a document title that appears
    as ## on every page) survive. This catches those by comparing heading lines
    across pages and removing any that appear on more than half the pages.
    """
    if len(pages) < 3:
        return pages

    from collections import Counter

    threshold = max(3, int(len(pages) * 0.5))

    # Count how many pages each heading line appears on
    heading_counts: Counter[str] = Counter()
    for page in pages:
        # Deduplicate within a single page
        seen: set[str] = set()
        for line in page["text"].split("\n"):
            stripped = line.strip()
            if stripped.startswith("#") and stripped not in seen:
                seen.add(stripped)
                heading_counts[stripped] += 1

    repeating = {h for h, count in heading_counts.items() if count >= threshold}

    if not repeating:
        return pages

    for h in repeating:
        logger.info("Stripping repeating heading: '%s' (appears on %d+ pages)", h, threshold)

    result: list[dict] = []
    for page in pages:
        lines = page["text"].split("\n")
        filtered = [line for line in lines if line.strip() not in repeating]
        cleaned = "\n".join(filtered).strip()

        if not cleaned:
            logger.warning(
                "Page %d is empty after stripping repeating headings, skipping.",
                page["page_number"],
            )
            continue

        result.append({
            "page_number": page["page_number"],
            "text": cleaned,
        })

    return result


def _clean_markdown(text: str) -> str:
    """Clean up pymupdf4llm markdown output.

    Removes image placeholders, collapses excessive blank lines,
    and strips trailing whitespace.
    """
    # Remove image placeholder lines
    text = re.sub(r"^.*intentionally omitted.*$", "", text, flags=re.MULTILINE)
    # Collapse 3+ consecutive newlines to exactly 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_pages_from_doc(doc: fitz.Document) -> list[dict]:
    """Extract markdown text from each page using pymupdf4llm layout analysis.

    Returns:
        List of dicts with 'page_number' (1-indexed) and 'text' (markdown).
        Pages with no extractable text are skipped with a warning.
    """
    page_chunks = pymupdf4llm.to_markdown(
        doc,
        page_chunks=True,
        header=False,
        footer=False,
    )

    pages: list[dict] = []
    for i, chunk in enumerate(page_chunks):
        text = _clean_markdown(chunk["text"])

        if not text:
            logger.warning(
                "Page %d has no extractable text (possibly image-only), skipping.",
                i + 1,
            )
            continue

        pages.append({
            "page_number": i + 1,
            "text": text,
        })

    return _strip_repeating_headings(pages)


def parse_pdf_from_path(path: str | Path) -> list[dict]:
    """Extract text from a PDF file on disk.

    Args:
        path: Path to the PDF file.

    Returns:
        List of dicts: [{"page_number": 1, "text": "..."}, ...]
    """
    doc = fitz.open(str(path))
    try:
        return _extract_pages_from_doc(doc)
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
        return _extract_pages_from_doc(doc)
    finally:
        doc.close()
