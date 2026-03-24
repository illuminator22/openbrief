"""Document upload and management endpoints."""

import logging
import uuid
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.exceptions import DocumentValidationError
from api.routes.auth import get_current_user
from config import settings
from core.ingestion.pipeline import ingest_document
from core.rag.retriever import retrieve_chunks
from db.database import get_db
from db.models import Document, User

logger = logging.getLogger(__name__)

router = APIRouter()

_PDF_MAGIC_BYTES = b"%PDF"
_MAX_FILE_SIZE_BYTES = settings.upload_max_size_mb * 1024 * 1024


class DocumentResponse(BaseModel):
    """Response schema for document endpoints."""

    id: uuid.UUID
    filename: str
    file_size: int
    page_count: int | None
    upload_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


def _validate_pdf(filename: str, file_header: bytes) -> None:
    """Validate that the uploaded file is a PDF by extension and magic bytes.

    Raises:
        DocumentValidationError: If validation fails.
    """
    if not filename.lower().endswith(".pdf"):
        raise DocumentValidationError("Only PDF files are supported (invalid extension)")

    if not file_header.startswith(_PDF_MAGIC_BYTES):
        raise DocumentValidationError("Only PDF files are supported (invalid file header)")


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Upload a legal document (PDF) for analysis.

    Validates the file, saves it to disk, extracts page count,
    and creates a database record with status 'processing'.
    """
    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate file size
    if file_size > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.upload_max_size_mb}MB",
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Validate PDF (extension + magic bytes)
    try:
        _validate_pdf(file.filename or "", content[:4])
    except DocumentValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Extract page count with PyMuPDF (from bytes, before saving to disk)
    try:
        pdf_doc = fitz.open(stream=content, filetype="pdf")
        page_count = len(pdf_doc)
        pdf_doc.close()
    except Exception:
        raise HTTPException(
            status_code=400, detail="Failed to read PDF. The file may be corrupted."
        )

    # Create database record first to get the document ID
    document = Document(
        user_id=current_user.id,
        filename=file.filename or "unnamed.pdf",
        file_size=file_size,
        page_count=page_count,
        upload_status="processing",
    )
    db.add(document)
    await db.flush()

    # Save file as {document.id}.pdf so the ingestion pipeline can find it
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{document.id}.pdf"
    file_path.write_bytes(content)

    # Run ingestion pipeline: parse → chunk → embed → store
    try:
        await ingest_document(document.id, db)
    except Exception:
        logger.exception("Ingestion failed for document %s", document.id)
        # ingest_document already sets status to "failed" internally,
        # but refresh the object to return the current status
        await db.refresh(document)

    return DocumentResponse.model_validate(document)


class ChunkSearchResult(BaseModel):
    """A single chunk result from similarity search."""

    chunk_id: uuid.UUID
    content: str
    section_title: str | None
    page_number: int | None
    chunk_index: int
    similarity_score: float


class SearchResponse(BaseModel):
    """Response schema for document search."""

    query: str
    document_id: uuid.UUID
    results: list[ChunkSearchResult]


@router.get("/{document_id}/search", response_model=SearchResponse)
async def search_document(
    document_id: uuid.UUID,
    q: str = Query(..., min_length=1, description="Search query"),
    top_k: int = Query(default=settings.rag_top_k, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResponse:
    """Search a document's chunks by semantic similarity.

    Embeds the query and retrieves the most relevant chunks
    using pgvector cosine distance search.
    """
    # Verify document exists and belongs to current user
    document = await db.get(Document, document_id)
    if document is None or document.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.upload_status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Document is not ready for search (status: {document.upload_status})",
        )

    results = await retrieve_chunks(
        query=q,
        document_id=document_id,
        db=db,
        top_k=top_k,
    )

    return SearchResponse(
        query=q,
        document_id=document_id,
        results=[ChunkSearchResult(**r) for r in results],
    )
