"""Manual test script for the PDF parsing and chunking pipeline.

Usage:
    python test_ingestion.py path/to/document.pdf
"""

import sys
from pathlib import Path

from core.ingestion.pdf_parser import parse_pdf_from_path
from core.ingestion.chunker import chunk_document


def main() -> None:
    """Parse a PDF and chunk it, printing detailed results."""
    if len(sys.argv) < 2:
        print("Usage: python test_ingestion.py <path-to-pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    # Parse
    print(f"\n--- Parsing: {pdf_path.name} ---\n")
    pages = parse_pdf_from_path(pdf_path)
    print(f"Total pages extracted: {len(pages)}")

    if not pages:
        print("No text extracted from PDF.")
        sys.exit(0)

    # Chunk
    chunks = chunk_document(pages)
    print(f"Total chunks created:  {len(chunks)}\n")

    if not chunks:
        print("No chunks produced.")
        sys.exit(0)

    # Per-chunk details
    print(f"{'Idx':<5} {'Page':<6} {'Tokens':<8} {'Section':<40} {'Preview'}")
    print("-" * 120)

    token_counts = []
    for chunk in chunks:
        token_counts.append(chunk["token_count"])
        section = chunk["section_title"] or "(none)"
        if len(section) > 38:
            section = section[:35] + "..."
        preview = chunk["content"][:100].replace("\n", " ")
        print(
            f"{chunk['chunk_index']:<5} "
            f"{chunk['page_number']:<6} "
            f"{chunk['token_count']:<8} "
            f"{section:<40} "
            f"{preview}"
        )

    # Summary stats
    print(f"\n--- Token count stats ---")
    print(f"Min:     {min(token_counts)}")
    print(f"Max:     {max(token_counts)}")
    print(f"Average: {sum(token_counts) / len(token_counts):.1f}")


if __name__ == "__main__":
    main()
