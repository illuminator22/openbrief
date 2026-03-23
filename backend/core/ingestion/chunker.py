"""Legal-aware recursive document chunker.

Splits parsed PDF pages into token-bounded chunks while respecting
legal document structure (section headers, clauses, paragraphs).
Uses tiktoken for accurate token counting.

This is a custom chunker — LangChain text splitters are not used here.
"""

import re

import tiktoken

from config import settings

_ENCODING = tiktoken.get_encoding("cl100k_base")

# --- Section header patterns (compiled once) ---

# ARTICLE I, ARTICLE II, ARTICLE IV, etc.
_RE_ARTICLE = re.compile(r"^ARTICLE\s+[IVXLCDM]+\.?", re.MULTILINE)

# Section 1., Section 1:, SECTION 1., numbered like 1. / 1.1 / 1.1.1 at start of line,
# or top-level numbers without period like "5 CONTRACT ADMINISTRATION:"
_RE_SECTION_NUMBERED = re.compile(
    r"^(?:(?:SECTION|Section)\s+\d+[\.:])|\d+(?:\.\d+)*\.|\d+\s+[A-Z]", re.MULTILINE
)

# (a), (b), (i), (ii) at start of line
_RE_LETTERED_CLAUSE = re.compile(
    r"^\([a-z]+\)|^\([ivxlcdm]+\)", re.MULTILINE
)

# ALL-CAPS lines that look like headings (at least 2 words, all uppercase letters/spaces/punctuation)
_RE_ALLCAPS_HEADING = re.compile(r"^[A-Z][A-Z \-:,;/&]{3,}$", re.MULTILINE)

# Combined pattern that matches any section header.
# Uses a capture group so re.split() preserves the matched header in results.
# All alternatives are ^-anchored to prevent mid-sentence false matches.
_SECTION_HEADER_RE = re.compile(
    r"("
    r"^ARTICLE\s+[IVXLCDM]+\.?"
    r"|^(?:SECTION|Section)\s+\d+[\.:]"
    r"|^\d+(?:\.\d+)*\."
    r"|^\d+\s+[A-Z]"
    r"|^\([a-z]+\)"
    r"|^\([ivxlcdm]+\)"
    r"|^[A-Z][A-Z \-:,;/&]{3,}$"
    r")",
    re.MULTILINE,
)

# Sentence boundary: period/question mark/exclamation followed by space(s) and uppercase letter
_RE_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _token_count(text: str) -> int:
    """Count tokens in text using cl100k_base encoding."""
    return len(_ENCODING.encode(text))


def _token_split_at_boundary(text: str, max_tokens: int) -> tuple[str, str]:
    """Split text at the last space boundary that fits within max_tokens.

    Returns (left, right) where left is at most max_tokens.
    Never splits mid-word.
    """
    tokens = _ENCODING.encode(text)
    if len(tokens) <= max_tokens:
        return text, ""

    # Decode the first max_tokens tokens, then find the last space
    truncated = _ENCODING.decode(tokens[:max_tokens])
    last_space = truncated.rfind(" ")

    if last_space <= 0:
        # No space found — take the whole truncated portion
        return truncated, text[len(truncated):]

    return truncated[:last_space], text[last_space + 1:]


def _detect_section_title(text: str) -> str | None:
    """Detect if text starts with a legal section header.

    Returns the header line if found, otherwise None.
    """
    first_line = text.split("\n", 1)[0].strip()

    if _RE_ARTICLE.match(first_line):
        return first_line
    if _RE_SECTION_NUMBERED.match(first_line):
        return first_line
    if _RE_ALLCAPS_HEADING.match(first_line):
        return first_line
    # Lettered clauses like (a) are sub-sections, not top-level titles
    return None


def _split_at_sections(text: str) -> list[str]:
    """Phase 1: Split text at every section header unconditionally.

    Section boundaries are structural — they always produce separate pieces
    regardless of size. This ensures every piece belongs to exactly one section.
    """
    raw_parts = _SECTION_HEADER_RE.split(text)
    if len(raw_parts) <= 1:
        return [text]

    # re.split with a capture group returns: [before, match, after, match, after, ...]
    # Re-attach each matched header to the text that follows it.
    pieces: list[str] = []
    if raw_parts[0].strip():
        pieces.append(raw_parts[0])
    for i in range(1, len(raw_parts), 2):
        matched = raw_parts[i]
        following = raw_parts[i + 1] if i + 1 < len(raw_parts) else ""
        pieces.append(matched + following)

    return [p for p in pieces if p.strip()]


def _split_by_size(text: str, max_tokens: int) -> list[str]:
    """Phase 2: Recursively split text into pieces that fit within max_tokens.

    Uses only size-based separators (no section headers — those are
    handled by _split_at_sections before this is called).

    Splitting hierarchy:
        1. Paragraph breaks (double newlines)
        2. Single newlines
        3. Sentence boundaries
        4. Spaces (last resort, never mid-word)
    """
    if _token_count(text) <= max_tokens:
        return [text]

    separators: list[str | re.Pattern[str]] = [
        r"\n\n",         # Level 1: paragraph breaks
        r"\n",           # Level 2: single newlines
        _RE_SENTENCE,    # Level 3: sentence boundaries
    ]

    for sep in separators:
        if isinstance(sep, re.Pattern):
            parts = sep.split(text)
        else:
            parts = text.split(sep)

        if len(parts) <= 1:
            continue

        # Re-join small parts and recursively split large ones
        result: list[str] = []
        current = parts[0]
        joiner = "" if isinstance(sep, re.Pattern) else sep

        for part in parts[1:]:
            candidate = current + joiner + part if current else part
            if _token_count(candidate) <= max_tokens:
                current = candidate
            else:
                if current.strip():
                    result.extend(_split_by_size(current, max_tokens))
                current = part

        if current.strip():
            result.extend(_split_by_size(current, max_tokens))

        if len(result) > 1 or (len(result) == 1 and _token_count(result[0]) <= max_tokens):
            return result

    # Level 4: split at spaces (last resort, never mid-word)
    pieces: list[str] = []
    remaining = text
    while remaining:
        left, remaining = _token_split_at_boundary(remaining, max_tokens)
        if left.strip():
            pieces.append(left)
    return pieces


def _build_page_index(pages: list[dict]) -> list[tuple[int, int]]:
    """Build an index mapping character offsets to page numbers.

    Returns list of (start_offset, page_number) tuples for the merged text.
    """
    index: list[tuple[int, int]] = []
    offset = 0
    for page in pages:
        index.append((offset, page["page_number"]))
        # +2 for the "\n\n" join separator
        offset += len(page["text"]) + 2
    return index


def _page_at_offset(page_index: list[tuple[int, int]], char_offset: int) -> int:
    """Return the page number for a given character offset in the merged text."""
    page_num = page_index[0][1]
    for start, pn in page_index:
        if start > char_offset:
            break
        page_num = pn
    return page_num


def chunk_document(pages: list[dict]) -> list[dict]:
    """Split parsed PDF pages into legal-aware, token-bounded chunks.

    Args:
        pages: Output from pdf_parser — [{"page_number": int, "text": str}, ...]

    Returns:
        List of chunk dicts, each containing:
            - content: str
            - chunk_index: int (sequential, 0-based)
            - page_number: int (starting page)
            - section_title: str | None
            - token_count: int
            - metadata: dict
    """
    if not pages:
        return []

    max_tokens = settings.rag_chunk_size
    overlap_tokens = settings.rag_chunk_overlap

    # Merge all pages into one text block, tracking page boundaries
    merged_text = "\n\n".join(page["text"] for page in pages)
    page_index = _build_page_index(pages)

    # Phase 1: Split at section headers unconditionally (structural split)
    section_pieces = _split_at_sections(merged_text)

    # Phase 2: Split any oversized section pieces by size (levels 2-5)
    raw_pieces: list[str] = []
    for piece in section_pieces:
        raw_pieces.extend(_split_by_size(piece, max_tokens))

    # Build chunks with overlap, section tracking, and page numbers
    chunks: list[dict] = []
    current_section: str | None = None
    char_offset = 0

    for i, piece in enumerate(raw_pieces):
        piece = piece.strip()
        if not piece:
            continue

        # Detect section title
        detected = _detect_section_title(piece)
        if detected is not None:
            current_section = detected

        # Find where this piece starts in the merged text
        piece_start = merged_text.find(piece, char_offset)
        if piece_start == -1:
            piece_start = char_offset
        char_offset = piece_start + len(piece)

        page_num = _page_at_offset(page_index, piece_start)

        # Apply overlap: prepend tail of previous chunk.
        # Only apply within the same section — never pull text across a section boundary.
        is_new_section = detected is not None
        if overlap_tokens > 0 and chunks and not is_new_section:
            prev_content = chunks[-1]["content"]
            prev_tokens = _ENCODING.encode(prev_content)
            if len(prev_tokens) > overlap_tokens:
                overlap_text = _ENCODING.decode(prev_tokens[-overlap_tokens:])
                # Find a clean word boundary in the overlap
                first_space = overlap_text.find(" ")
                if first_space > 0:
                    overlap_text = overlap_text[first_space + 1:]
                piece_with_overlap = overlap_text + " " + piece
            else:
                piece_with_overlap = prev_content + " " + piece

            # Trim if overlap pushed us over the limit
            if _token_count(piece_with_overlap) > max_tokens:
                piece_with_overlap = piece
        else:
            piece_with_overlap = piece

        tokens = _token_count(piece_with_overlap)

        chunks.append({
            "content": piece_with_overlap,
            "chunk_index": len(chunks),
            "page_number": page_num,
            "section_title": current_section,
            "token_count": tokens,
            "metadata": {},
        })

    return chunks
