"""RAG evaluation engine using DeepEval.

Measures hallucination, answer relevancy, faithfulness, and contextual
precision for RAG pipeline responses. Uses a separate eval API key
(not the user's BYOK key) for LLM-as-judge scoring.
"""

import asyncio
import logging
import os
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.rag.pipeline import query_document
from db.models import EvaluationLog, User

logger = logging.getLogger(__name__)


def _configure_deepeval() -> None:
    """Configure DeepEval to use the eval API key from settings."""
    if not settings.eval_api_key:
        raise RuntimeError(
            "EVAL_API_KEY is not configured. Set it in .env to run evaluations."
        )
    os.environ["OPENAI_API_KEY"] = settings.eval_api_key


def _run_single_evaluation(
    question: str,
    answer: str,
    retrieved_context: list[str],
    expected_answer: str | None = None,
) -> dict:
    """Run DeepEval metrics synchronously (called via asyncio.to_thread).

    Args:
        question: The user's question.
        answer: The RAG pipeline's answer.
        retrieved_context: List of chunk content strings.
        expected_answer: Optional known-correct answer.

    Returns:
        Dict with scores for each metric.
    """
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        ContextualPrecisionMetric,
        FaithfulnessMetric,
        HallucinationMetric,
    )
    from deepeval.test_case import LLMTestCase

    _configure_deepeval()

    test_case = LLMTestCase(
        input=question,
        actual_output=answer,
        retrieval_context=retrieved_context,
        expected_output=expected_answer,
    )

    metrics_config = [
        ("hallucination", HallucinationMetric(model=settings.eval_model, threshold=0.5)),
        ("answer_relevancy", AnswerRelevancyMetric(model=settings.eval_model, threshold=0.5)),
        ("faithfulness", FaithfulnessMetric(model=settings.eval_model, threshold=0.5)),
    ]

    # ContextualPrecision requires expected_output
    if expected_answer:
        metrics_config.append(
            ("contextual_precision", ContextualPrecisionMetric(model=settings.eval_model, threshold=0.5))
        )

    results: dict = {}

    for name, metric in metrics_config:
        try:
            metric.measure(test_case)
            results[name] = {
                "score": round(metric.score, 4) if metric.score is not None else None,
                "passed": metric.is_successful(),
                "reason": metric.reason if hasattr(metric, "reason") else None,
            }
        except Exception as exc:
            logger.warning("Metric '%s' failed: %s", name, exc)
            results[name] = {
                "score": None,
                "passed": False,
                "reason": f"Metric failed: {exc}",
            }

    return results


async def evaluate_rag_response(
    question: str,
    answer: str,
    retrieved_context: list[str],
    expected_answer: str | None = None,
) -> dict:
    """Evaluate a single RAG response using DeepEval metrics.

    Args:
        question: The user's question.
        answer: The RAG pipeline's answer.
        retrieved_context: List of chunk content strings that were retrieved.
        expected_answer: Optional known-correct answer for comparison.

    Returns:
        Dict with scores for each metric (0.0 to 1.0), plus pass/fail for each.
    """
    return await asyncio.to_thread(
        _run_single_evaluation,
        question,
        answer,
        retrieved_context,
        expected_answer,
    )


async def evaluate_test_suite(
    test_cases: list[dict],
    db: AsyncSession,
    user: User,
    model_override: str | None = None,
) -> dict:
    """Run evaluation on a full test suite and store results.

    For each test case: runs the actual RAG pipeline (using user's BYOK key),
    evaluates the response (using eval_api_key), and stores results.

    Args:
        test_cases: List of dicts with: id, question, document_id, expected_answer (optional).
        db: Database session for storing results in evaluation_logs.
        user: The authenticated user (must have BYOK key for RAG pipeline calls).
        model_override: Optional model to use instead of user's configured model.

    Returns:
        Dict with: total_cases, passed, failed, average scores per metric, results list.
    """
    if not settings.eval_api_key:
        raise RuntimeError("EVAL_API_KEY is not configured.")
    if not user.encrypted_llm_key:
        raise RuntimeError("User has no API key configured for RAG pipeline calls.")

    # Temporarily override model if requested
    original_model = user.llm_model
    if model_override:
        user.llm_model = model_override

    total = len(test_cases)
    results: list[dict] = []
    metric_totals: dict[str, list[float]] = {
        "hallucination": [],
        "answer_relevancy": [],
        "faithfulness": [],
        "contextual_precision": [],
    }

    model_used = model_override or user.llm_model or settings.default_llm_model

    try:
        for i, tc in enumerate(test_cases, start=1):
            tc_start = time.time()
            tc_id = tc.get("id", f"TC{i:03d}")
            logger.info("Evaluating case %s (%d/%d)", tc_id, i, total)

            try:
                # Run the actual RAG pipeline
                doc_id = uuid.UUID(tc["document_id"]) if isinstance(tc["document_id"], str) else tc["document_id"]
                pipeline_result = await query_document(
                    document_id=doc_id,
                    question=tc["question"],
                    db=db,
                    user=user,
                )

                answer = pipeline_result.get("answer", "")
                citations = pipeline_result.get("citations", [])
                metadata = pipeline_result.get("metadata", {})
                response_time_ms = metadata.get("response_time_ms", 0)

                # Extract retrieved context from the pipeline
                # The retriever returns chunks, but pipeline doesn't expose them directly.
                # We reconstruct from citations or re-retrieve.
                from core.rag.retriever import retrieve_chunks
                chunks = await retrieve_chunks(
                    query=tc["question"],
                    document_id=doc_id,
                    db=db,
                )
                retrieved_context = [c["content"] for c in chunks]

                # Run evaluation
                eval_result = await evaluate_rag_response(
                    question=tc["question"],
                    answer=answer,
                    retrieved_context=retrieved_context,
                    expected_answer=tc.get("expected_answer"),
                )

                # Store in evaluation_logs
                log_entry = EvaluationLog(
                    query=tc["question"],
                    retrieved_chunks=[{"chunk_id": str(c["chunk_id"]), "content": c["content"][:200]} for c in chunks],
                    generated_answer=answer,
                    hallucination_score=eval_result.get("hallucination", {}).get("score"),
                    retrieval_precision=eval_result.get("contextual_precision", {}).get("score"),
                    citation_accuracy=eval_result.get("faithfulness", {}).get("score"),
                    answer_relevance=eval_result.get("answer_relevancy", {}).get("score"),
                    response_time_ms=response_time_ms,
                    model_used=model_used,
                )
                db.add(log_entry)
                await db.flush()

                # Accumulate scores
                for metric_name in metric_totals:
                    score = eval_result.get(metric_name, {}).get("score")
                    if score is not None:
                        metric_totals[metric_name].append(score)

                tc_elapsed = time.time() - tc_start
                results.append({
                    "id": tc_id,
                    "status": "success",
                    "scores": eval_result,
                    "response_time_ms": response_time_ms,
                    "elapsed_s": round(tc_elapsed, 2),
                })

            except Exception as exc:
                logger.exception("Test case %s failed", tc_id)
                results.append({
                    "id": tc_id,
                    "status": "error",
                    "error": str(exc),
                })

    finally:
        # Restore original model
        if model_override:
            user.llm_model = original_model

    # Compute averages
    averages: dict[str, float | None] = {}
    for metric_name, scores in metric_totals.items():
        averages[metric_name] = round(sum(scores) / len(scores), 4) if scores else None

    passed = sum(1 for r in results if r.get("status") == "success")
    failed = sum(1 for r in results if r.get("status") == "error")

    return {
        "total_cases": total,
        "passed": passed,
        "failed": failed,
        "model_used": model_used,
        "averages": averages,
        "results": results,
    }
