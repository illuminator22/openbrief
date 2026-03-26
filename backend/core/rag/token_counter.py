"""Token counting for documents and cost estimation.

Uses tiktoken cl100k_base encoding (same as the chunker) for accurate
token counts. Reads stored token_count from chunk metadata when available,
falls back to re-encoding with tiktoken.
"""

import uuid

import tiktoken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models import Chunk

_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_text_tokens(text: str) -> int:
    """Count tokens in a text string using tiktoken cl100k_base.

    Args:
        text: The text to count tokens for.

    Returns:
        Number of tokens.
    """
    return len(_ENCODING.encode(text))


async def count_document_tokens(document_id: uuid.UUID, db: AsyncSession) -> dict:
    """Count total tokens across all chunks for a document.

    Uses the token_count stored in chunk metadata during ingestion.
    Falls back to tiktoken re-encoding if metadata is missing.

    Args:
        document_id: UUID of the document.
        db: Async database session.

    Returns:
        Dict with: total_tokens, chunk_count, avg_tokens_per_chunk.
    """
    stmt = select(Chunk.content, Chunk.metadata_).where(Chunk.document_id == document_id)
    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return {"total_tokens": 0, "chunk_count": 0, "avg_tokens_per_chunk": 0}

    total_tokens = 0
    for content, metadata in rows:
        # Try to read from stored metadata first
        if metadata and "token_count" in metadata:
            total_tokens += metadata["token_count"]
        else:
            total_tokens += count_text_tokens(content)

    chunk_count = len(rows)
    avg_tokens = total_tokens // chunk_count if chunk_count > 0 else 0

    return {
        "total_tokens": total_tokens,
        "chunk_count": chunk_count,
        "avg_tokens_per_chunk": avg_tokens,
    }


def get_review_strategy(total_tokens: int) -> dict:
    """Determine the review strategy based on token count.

    Args:
        total_tokens: Total tokens in the document.

    Returns:
        Dict with: strategy, threshold, reason.
    """
    threshold = settings.full_review_token_threshold

    if total_tokens <= threshold:
        return {
            "strategy": "single_call",
            "threshold": threshold,
            "reason": (
                f"Document has {total_tokens:,} tokens, under the "
                f"{threshold:,} token threshold. Will send the full document "
                f"to the model in a single API call for best cross-reference quality."
            ),
        }
    else:
        return {
            "strategy": "map_reduce",
            "threshold": threshold,
            "reason": (
                f"Document has {total_tokens:,} tokens, exceeding the "
                f"{threshold:,} token threshold. Will process chunks individually "
                f"(map) then synthesize findings (reduce). This adds ~30% overhead."
            ),
        }
