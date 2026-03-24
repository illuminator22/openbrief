"""Document ingestion pipeline: parse → chunk → embed → store.

Orchestrates the full ingestion flow for an uploaded PDF document.
Called synchronously from the upload endpoint after the file is saved.
"""

import logging
import time
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.ingestion.chunker import chunk_document
from core.ingestion.embedder import get_embedding_service
from core.ingestion.pdf_parser import parse_pdf_from_path
from db.models import Chunk, Document

logger = logging.getLogger(__name__)


async def ingest_document(document_id: uuid.UUID, db: AsyncSession) -> None:
    """Run the full ingestion pipeline for an uploaded document.

    Reads the saved PDF from disk, parses it, chunks it, generates
    embeddings, stores chunk records in the database, and updates
    the document status to 'completed'. If any step fails, the
    document status is set to 'failed'.

    Args:
        document_id: UUID of the document record (file is at uploads/{id}.pdf).
        db: Async database session (managed by the caller).
    """
    pipeline_start = time.time()

    try:
        # Locate the saved PDF
        file_path = Path(settings.upload_dir) / f"{document_id}.pdf"
        if not file_path.exists():
            raise FileNotFoundError(f"PDF not found at {file_path}")

        # Step 1: Parse PDF to markdown pages
        step_start = time.time()
        pages = parse_pdf_from_path(file_path)
        logger.info(
            "Document %s: parsed %d pages in %.2fs",
            document_id, len(pages), time.time() - step_start,
        )

        if not pages:
            raise ValueError("PDF produced no extractable text")

        # Step 2: Chunk pages into token-bounded pieces
        step_start = time.time()
        chunks = chunk_document(pages)
        logger.info(
            "Document %s: created %d chunks in %.2fs",
            document_id, len(chunks), time.time() - step_start,
        )

        if not chunks:
            raise ValueError("Chunker produced no chunks")

        # Step 3: Generate embeddings for all chunks
        step_start = time.time()
        embedding_service = get_embedding_service()
        texts = [chunk["content"] for chunk in chunks]
        embeddings = embedding_service.embed_chunks(texts)
        logger.info(
            "Document %s: embedded %d chunks in %.2fs",
            document_id, len(embeddings), time.time() - step_start,
        )

        # Step 4: Create Chunk database records and bulk insert
        step_start = time.time()
        chunk_records = []
        for chunk_data, embedding in zip(chunks, embeddings):
            record = Chunk(
                document_id=document_id,
                content=chunk_data["content"],
                chunk_index=chunk_data["chunk_index"],
                page_number=chunk_data["page_number"],
                section_title=chunk_data["section_title"],
                metadata_={"token_count": chunk_data["token_count"]},
                embedding=embedding,
            )
            chunk_records.append(record)

        db.add_all(chunk_records)
        await db.flush()
        logger.info(
            "Document %s: stored %d chunks in %.2fs",
            document_id, len(chunk_records), time.time() - step_start,
        )

        # Step 5: Update document status to completed
        document = await db.get(Document, document_id)
        if document is not None:
            document.upload_status = "completed"
            await db.flush()

        total_elapsed = time.time() - pipeline_start
        logger.info(
            "Document %s: ingestion complete in %.2fs "
            "(%d pages, %d chunks)",
            document_id, total_elapsed, len(pages), len(chunks),
        )

    except Exception:
        logger.exception("Document %s: ingestion failed", document_id)
        # Mark document as failed so the user knows
        try:
            document = await db.get(Document, document_id)
            if document is not None:
                document.upload_status = "failed"
                await db.flush()
        except Exception:
            logger.exception(
                "Document %s: failed to update status to 'failed'",
                document_id,
            )
        raise
