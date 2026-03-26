"""Analysis endpoints for querying documents with the RAG pipeline."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.exceptions import LLMProviderError, RAGQueryError
from api.routes.auth import get_current_user
from config import settings
from core.rag.full_review import full_review_document
from core.rag.pipeline import query_document, _CONFIDENCE_MAP
from core.rag.pricing import VALID_MODEL_IDS, estimate_cost
from core.rag.token_counter import count_document_tokens, count_text_tokens, get_review_strategy
from core.rag.prompts import RAG_SYSTEM_PROMPT
from db.database import get_db
from db.models import Analysis, Document, User

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    """Request body for document query."""

    document_id: uuid.UUID
    question: str = Field(..., min_length=1, max_length=2000)
    model: str | None = None


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
    if request.model and request.model not in VALID_MODEL_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model: '{request.model}'. "
            f"Supported: {', '.join(sorted(VALID_MODEL_IDS))}",
        )

    try:
        result = await query_document(
            document_id=request.document_id,
            question=request.question,
            db=db,
            user=current_user,
            model_override=request.model,
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


class EstimateRequest(BaseModel):
    """Request body for cost estimation."""

    document_id: uuid.UUID
    operation: str = Field(..., pattern="^(targeted_query|full_review)$")


class CostBreakdown(BaseModel):
    """Estimated cost breakdown in USD."""

    input_cost: float | None
    output_cost: float | None
    total: float | None


class EstimateResponse(BaseModel):
    """Response from cost estimation endpoint."""

    document_id: uuid.UUID
    operation: str
    model: str
    input_tokens: int
    estimated_output_tokens: int
    estimated_cost: CostBreakdown | None
    strategy: str | None
    threshold_tokens: int
    pricing_available: bool
    message: str


# Overhead estimates for prompt templates and formatting
_SYSTEM_PROMPT_TOKENS = count_text_tokens(RAG_SYSTEM_PROMPT)
_QUESTION_OVERHEAD_TOKENS = 100  # user question + formatting
_FULL_REVIEW_PROMPT_OVERHEAD = 500  # system prompt + instructions for full review
_TARGETED_QUERY_OUTPUT_ESTIMATE = 500  # reasonable default for a cited answer
_MAP_REDUCE_OVERHEAD_MULTIPLIER = 1.3  # reduce step adds ~30% input cost


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_cost_endpoint(
    request: EstimateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EstimateResponse:
    """Estimate the API cost for a document operation before executing it.

    Returns token counts, estimated costs, and strategy information.
    Actual cost may vary — estimates round up slightly to be safe.
    """
    # Validate document
    document = await db.get(Document, request.document_id)
    if document is None or document.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.upload_status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Document is not ready (status: {document.upload_status})",
        )

    # Get user's model
    model = current_user.llm_model or settings.default_llm_model

    # Count document tokens
    doc_tokens = await count_document_tokens(request.document_id, db)
    total_doc_tokens = doc_tokens["total_tokens"]
    chunk_count = doc_tokens["chunk_count"]
    avg_tokens = doc_tokens["avg_tokens_per_chunk"]

    if request.operation == "targeted_query":
        # Input = system prompt + top_k chunks + question overhead
        top_k = settings.rag_top_k
        input_tokens = _SYSTEM_PROMPT_TOKENS + (avg_tokens * top_k) + _QUESTION_OVERHEAD_TOKENS
        estimated_output = _TARGETED_QUERY_OUTPUT_ESTIMATE
        strategy = None

        cost_result = estimate_cost(input_tokens, estimated_output, model)

        total_cost = cost_result["total_estimated_cost"]
        cost_str = f"${total_cost:.2f}" if total_cost is not None else "unknown"
        message = (
            f"Targeted query across {chunk_count} chunks "
            f"(~{input_tokens:,} input tokens). "
            f"Estimated cost: ~{cost_str} with {model}."
        )

    else:  # full_review
        review_strategy = get_review_strategy(total_doc_tokens)
        strategy = review_strategy["strategy"]

        input_tokens = total_doc_tokens + _FULL_REVIEW_PROMPT_OVERHEAD
        # Output estimate: 20% of input, capped at 8192.
        # Note: provider max_tokens default (4096) will need updating when
        # we build the full review pipeline to allow longer responses.
        estimated_output = min(int(input_tokens * 0.2), 8192)

        if strategy == "map_reduce":
            # Map-reduce adds ~30% overhead from the reduce step
            input_tokens = int(input_tokens * _MAP_REDUCE_OVERHEAD_MULTIPLIER)

        cost_result = estimate_cost(input_tokens, estimated_output, model)

        total_cost = cost_result["total_estimated_cost"]
        cost_str = f"${total_cost:.2f}" if total_cost is not None else "unknown"
        strategy_label = "single call" if strategy == "single_call" else "map-reduce"
        message = (
            f"Full review of {chunk_count} chunks "
            f"(~{total_doc_tokens:,} tokens, {strategy_label}). "
            f"Estimated cost: ~{cost_str} with {model}."
        )

    # Build cost breakdown
    if cost_result["pricing_available"]:
        cost_breakdown = CostBreakdown(
            input_cost=cost_result["input_cost"],
            output_cost=cost_result["output_cost"],
            total=cost_result["total_estimated_cost"],
        )
    else:
        cost_breakdown = None

    if not current_user.encrypted_llm_key:
        message += " Note: No API key configured — add one in Settings before running."

    return EstimateResponse(
        document_id=request.document_id,
        operation=request.operation,
        model=model,
        input_tokens=input_tokens,
        estimated_output_tokens=estimated_output,
        estimated_cost=cost_breakdown,
        strategy=strategy,
        threshold_tokens=settings.full_review_token_threshold,
        pricing_available=cost_result["pricing_available"],
        message=message,
    )


# ---------------------------------------------------------------------------
# Full review endpoint
# ---------------------------------------------------------------------------


class FullReviewRequest(BaseModel):
    """Request body for full document review."""

    document_id: uuid.UUID


class FindingResponse(BaseModel):
    """A single finding from a full document review."""

    category: str
    severity: str
    title: str
    description: str
    section_reference: str | None = None
    recommendation: str | None = None


class DeadlineResponse(BaseModel):
    """A deadline found in the document."""

    description: str
    date_or_period: str
    section_reference: str | None = None


class FullReviewResponse(BaseModel):
    """Response from a full document review."""

    analysis_id: uuid.UUID
    summary: str
    document_type: str
    parties: list[str]
    key_findings: list[FindingResponse]
    deadlines: list[DeadlineResponse]
    overall_risk_assessment: str
    confidence: str
    model_used: str
    strategy_used: str
    response_time_ms: int
    total_tokens: int


_RISK_SCORE_MAP = {"low": 0.9, "moderate": 0.7, "high": 0.4, "critical": 0.2}


@router.post("/full-review", response_model=FullReviewResponse)
async def full_review(
    request: FullReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FullReviewResponse:
    """Run a comprehensive review of a legal document.

    Analyzes the entire document for risks, obligations, deadlines,
    unusual terms, missing clauses, contradictions, and ambiguities.
    Uses single-call or map-reduce strategy based on document size.
    """
    try:
        result = await full_review_document(
            document_id=request.document_id,
            db=db,
            user=current_user,
        )
    except RAGQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Store in analyses table
    risk_str = result.get("overall_risk_assessment", "unknown")
    confidence_num = _RISK_SCORE_MAP.get(risk_str, 0.5)

    analysis = Analysis(
        user_id=current_user.id,
        document_id=request.document_id,
        analysis_type="full_review",
        result=result,
        confidence_score=confidence_num,
    )
    db.add(analysis)
    await db.flush()

    # Build response
    metadata = result.get("metadata", {})

    findings = [
        FindingResponse(
            category=f.get("category", ""),
            severity=f.get("severity", ""),
            title=f.get("title", ""),
            description=f.get("description", ""),
            section_reference=f.get("section_reference"),
            recommendation=f.get("recommendation"),
        )
        for f in result.get("key_findings", [])
    ]

    deadlines = [
        DeadlineResponse(
            description=d.get("description", ""),
            date_or_period=d.get("date_or_period", ""),
            section_reference=d.get("section_reference"),
        )
        for d in result.get("deadlines", [])
    ]

    return FullReviewResponse(
        analysis_id=analysis.id,
        summary=result.get("summary", ""),
        document_type=result.get("document_type", "Unknown"),
        parties=result.get("parties", []),
        key_findings=findings,
        deadlines=deadlines,
        overall_risk_assessment=risk_str,
        confidence=result.get("confidence", "low"),
        model_used=metadata.get("model_used", "unknown"),
        strategy_used=metadata.get("strategy_used", "unknown"),
        response_time_ms=metadata.get("response_time_ms", 0),
        total_tokens=metadata.get("total_tokens", 0),
    )
