"""Analysis endpoints for querying documents with the RAG pipeline."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.exceptions import LLMProviderError, RAGQueryError
from api.routes.auth import get_current_user
from core.rag.pipeline import query_document, _CONFIDENCE_MAP
from db.database import get_db
from db.models import Analysis, User

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    """Request body for document query."""

    document_id: uuid.UUID
    question: str = Field(..., min_length=1, max_length=2000)


class CitationResponse(BaseModel):
    """A single citation from the RAG response."""

    excerpt_number: int
    chunk_id: str | None
    page_number: int | None
    section_title: str | None
    relevant_quote: str


class QueryResponse(BaseModel):
    """Response from a RAG document query."""

    analysis_id: uuid.UUID
    answer: str
    citations: list[CitationResponse]
    confidence: str
    insufficient_information: bool
    model_used: str
    response_time_ms: int


@router.post("/query", response_model=QueryResponse)
async def query_analysis(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryResponse:
    """Ask a question about a document using the RAG pipeline.

    Retrieves relevant chunks, sends them with the question to the
    user's configured LLM, and returns a cited answer.
    """
    try:
        result = await query_document(
            document_id=request.document_id,
            question=request.question,
            db=db,
            user=current_user,
        )
    except RAGQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Store in analyses table
    confidence_str = result.get("confidence", "low")
    confidence_num = _CONFIDENCE_MAP.get(confidence_str, 0.3)

    analysis = Analysis(
        user_id=current_user.id,
        document_id=request.document_id,
        analysis_type="targeted_question",
        query=request.question,
        result=result,
        confidence_score=confidence_num,
    )
    db.add(analysis)
    await db.flush()

    # Build citation list
    citations = []
    for c in result.get("citations", []):
        citations.append(CitationResponse(
            excerpt_number=c.get("excerpt_number", 0),
            chunk_id=c.get("chunk_id"),
            page_number=c.get("page_number"),
            section_title=c.get("section_title"),
            relevant_quote=c.get("relevant_quote", ""),
        ))

    metadata = result.get("metadata", {})

    return QueryResponse(
        analysis_id=analysis.id,
        answer=result.get("answer", ""),
        citations=citations,
        confidence=confidence_str,
        insufficient_information=result.get("insufficient_information", False),
        model_used=metadata.get("model_used", "unknown"),
        response_time_ms=metadata.get("response_time_ms", 0),
    )
