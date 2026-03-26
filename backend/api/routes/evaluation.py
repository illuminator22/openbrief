"""Evaluation endpoints for running and viewing RAG quality metrics."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user
from config import settings
from core.evaluation.evaluator import evaluate_test_suite
from core.evaluation.test_cases import get_test_cases
from db.database import get_db
from db.models import EvaluationLog, User

logger = logging.getLogger(__name__)

router = APIRouter()


class EvalRunResponse(BaseModel):
    """Response from running the evaluation test suite."""

    total_cases: int
    passed: int
    failed: int
    model_used: str
    averages: dict[str, float | None]
    category_averages: dict[str, dict[str, float | None]]


class EvalLogEntry(BaseModel):
    """A single evaluation log entry."""

    query: str
    hallucination_score: float | None
    retrieval_precision: float | None
    citation_accuracy: float | None
    answer_relevance: float | None
    response_time_ms: int | None
    model_used: str | None
    created_at: str


class EvalResultsResponse(BaseModel):
    """Response for evaluation results listing."""

    results: list[EvalLogEntry]
    total: int


class EvalSummaryResponse(BaseModel):
    """High-level evaluation summary."""

    total_evaluations: int
    avg_hallucination_score: float | None
    avg_retrieval_precision: float | None
    avg_citation_accuracy: float | None
    avg_answer_relevance: float | None
    avg_response_time_ms: int | None
    last_run: str | None


class EvalRunRequest(BaseModel):
    """Optional request body for evaluation run."""

    model_override: str | None = None


@router.post("/run", response_model=EvalRunResponse)
async def run_evaluation(
    request: EvalRunRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvalRunResponse:
    """Run the full evaluation test suite.

    Uses the current user's BYOK key for RAG pipeline calls and the
    configured eval_api_key for DeepEval LLM-as-judge scoring.
    Optionally accepts a model_override to run tests against a specific model.
    """
    if not settings.eval_api_key:
        raise HTTPException(
            status_code=400,
            detail="EVAL_API_KEY is not configured. Set it in .env.",
        )
    if not current_user.encrypted_llm_key:
        raise HTTPException(
            status_code=400,
            detail="No API key configured. Add one in Settings before running evaluation.",
        )

    try:
        test_cases = get_test_cases()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    model_override = request.model_override if request else None

    try:
        result = await evaluate_test_suite(
            test_cases=test_cases,
            db=db,
            user=current_user,
            model_override=model_override,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return EvalRunResponse(
        total_cases=result["total_cases"],
        passed=result["passed"],
        failed=result["failed"],
        model_used=result["model_used"],
        averages=result["averages"],
        category_averages=result.get("category_averages", {}),
    )


@router.get("/results", response_model=EvalResultsResponse)
async def get_evaluation_results(
    limit: int = Query(default=50, ge=1, le=500),
    model: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> EvalResultsResponse:
    """Get evaluation results from the evaluation_logs table.

    Supports filtering by model and limiting result count.
    Returns newest results first.
    """
    stmt = select(EvaluationLog).order_by(EvaluationLog.created_at.desc())

    if model:
        stmt = stmt.where(EvaluationLog.model_used == model)

    stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    logs = result.scalars().all()

    count_stmt = select(func.count()).select_from(EvaluationLog)
    if model:
        count_stmt = count_stmt.where(EvaluationLog.model_used == model)
    total = await db.scalar(count_stmt) or 0

    entries = [
        EvalLogEntry(
            query=log.query,
            hallucination_score=float(log.hallucination_score) if log.hallucination_score is not None else None,
            retrieval_precision=float(log.retrieval_precision) if log.retrieval_precision is not None else None,
            citation_accuracy=float(log.citation_accuracy) if log.citation_accuracy is not None else None,
            answer_relevance=float(log.answer_relevance) if log.answer_relevance is not None else None,
            response_time_ms=log.response_time_ms,
            model_used=log.model_used,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]

    return EvalResultsResponse(results=entries, total=total)


@router.get("/summary", response_model=EvalSummaryResponse)
async def get_evaluation_summary(
    db: AsyncSession = Depends(get_db),
) -> EvalSummaryResponse:
    """Get high-level evaluation summary with aggregate metrics.

    Returns overall averages across all evaluation runs.
    Powers the evaluation dashboard.
    """
    stmt = select(
        func.count().label("total"),
        func.avg(EvaluationLog.hallucination_score).label("avg_hallucination"),
        func.avg(EvaluationLog.retrieval_precision).label("avg_precision"),
        func.avg(EvaluationLog.citation_accuracy).label("avg_citation"),
        func.avg(EvaluationLog.answer_relevance).label("avg_relevance"),
        func.avg(EvaluationLog.response_time_ms).label("avg_time"),
    )
    result = await db.execute(stmt)
    row = result.one()

    # Get last run timestamp
    last_stmt = select(EvaluationLog.created_at).order_by(EvaluationLog.created_at.desc()).limit(1)
    last_result = await db.execute(last_stmt)
    last_row = last_result.scalar_one_or_none()

    return EvalSummaryResponse(
        total_evaluations=row.total or 0,
        avg_hallucination_score=round(float(row.avg_hallucination), 4) if row.avg_hallucination else None,
        avg_retrieval_precision=round(float(row.avg_precision), 4) if row.avg_precision else None,
        avg_citation_accuracy=round(float(row.avg_citation), 4) if row.avg_citation else None,
        avg_answer_relevance=round(float(row.avg_relevance), 4) if row.avg_relevance else None,
        avg_response_time_ms=int(row.avg_time) if row.avg_time else None,
        last_run=last_row.isoformat() if last_row else None,
    )
