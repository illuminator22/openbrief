"""Chunk retrieval from pgvector.

Provides vector similarity search for targeted queries and
sequential loading for full document reviews.
"""

import logging
import time
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.ingestion.embedder import get_embedding_service
from db.models import Chunk

logger = logging.getLogger(__name__)


async def retrieve_chunks(
    query: str,
    document_id: uuid.UUID,
    db: AsyncSession,
    top_k: int | None = None,
) -> list[dict]:
    """Retrieve the most relevant chunks for a query within a document.

    Embeds the query using the BGE model (with query prefix), then
    performs cosine distance search against stored chunk embeddings
    using pgvector's <=> operator.

    Args:
        query: The user's search query string.
        document_id: UUID of the document to search within.
        db: Async database session.
        top_k: Number of results to return. Defaults to settings.rag_top_k.

    Returns:
        List of dicts ordered by relevance (most similar first), each containing:
            - chunk_id: UUID
            - content: str
            - section_title: str | None
            - page_number: int | None
            - chunk_index: int
            - similarity_score: float (1.0 = identical, 0.0 = unrelated)
    """
    if top_k is None:
        top_k = settings.rag_top_k

    start = time.time()

    # Embed the query with BGE prefix
    embedding_service = get_embedding_service()
    query_embedding = embedding_service.embed_query(query)

    # pgvector cosine distance: <=> returns distance (0 = identical, 2 = opposite)
    # We compute distance as a label and convert to similarity in the results.
    distance_expr = Chunk.embedding.cosine_distance(query_embedding)

    stmt = (
        select(Chunk, distance_expr.label("distance"))
        .where(Chunk.document_id == document_id)
        .order_by(distance_expr)
        .limit(top_k)
    )

    result = await db.execute(stmt)
    rows = result.all()

    results = []
    for chunk, distance in rows:
        results.append({
            "chunk_id": chunk.id,
            "content": chunk.content,
            "section_title": chunk.section_title,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "similarity_score": round(1.0 - distance, 4),
        })

    elapsed = time.time() - start
    logger.info(
        "Retrieved %d chunks for query '%s' on document %s in %.3fs",
        len(results),
        query[:80],
        document_id,
        elapsed,
    )

    return results


async def load_all_chunks(document_id: uuid.UUID, db: AsyncSession) -> list[dict]:
    """Load all chunks for a document, ordered by chunk_index.

    Used for full document reviews where the entire document content
    is needed, not just the most relevant chunks.

    Args:
        document_id: UUID of the document.
        db: Async database session.

    Returns:
        List of dicts ordered by chunk_index, each containing:
            - chunk_id: UUID
            - content: str
            - section_title: str | None
            - page_number: int | None
            - chunk_index: int
    """
    stmt = (
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
    )
    result = await db.execute(stmt)
    chunks = result.scalars().all()

    return [
        {
            "chunk_id": chunk.id,
            "content": chunk.content,
            "section_title": chunk.section_title,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
        }
        for chunk in chunks
    ]
