"""Full document review pipeline: single-call or map-reduce.

Orchestrates comprehensive legal document review by either sending the
full document to the LLM in one call (small docs) or processing chunks
individually then synthesizing (large docs).
"""

import asyncio
import json
import logging
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from api.exceptions import LLMProviderError, RAGQueryError
from config import settings
from core.llm.encryption import decrypt_api_key
from core.llm.provider import LLMProvider, get_llm_provider
from core.rag.prompts import (
    FULL_REVIEW_SYSTEM_PROMPT,
    FULL_REVIEW_USER_PROMPT,
    MAP_REDUCE_MAP_SYSTEM_PROMPT,
    MAP_REDUCE_MAP_USER_PROMPT,
    MAP_REDUCE_REDUCE_SYSTEM_PROMPT,
    MAP_REDUCE_REDUCE_USER_PROMPT,
    format_document_for_review,
    format_map_outputs,
)
from core.rag.retriever import load_all_chunks
from core.rag.token_counter import count_document_tokens, count_text_tokens, get_review_strategy
from db.models import Document, User

logger = logging.getLogger(__name__)

# Max concurrent map calls to avoid rate limits
_MAP_CONCURRENCY = 3

# Max tokens for review output (higher than targeted queries)
_REVIEW_MAX_TOKENS = 8192


def _parse_json_response(raw: str) -> dict:
    """Parse a JSON response from the LLM, stripping code fences if present.

    Args:
        raw: Raw response text from the LLM.

    Returns:
        Parsed dict.

    Raises:
        ValueError: If the response is not valid JSON.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())


async def _call_with_retry(
    provider: LLMProvider,
    messages: list[dict],
    model: str,
    max_tokens: int = _REVIEW_MAX_TOKENS,
) -> dict:
    """Call the LLM and parse JSON response, retrying once on parse failure.

    Args:
        provider: The LLM provider instance.
        messages: Chat messages to send.
        model: Model identifier.
        max_tokens: Maximum output tokens.

    Returns:
        Parsed JSON dict from the LLM response.
    """
    raw = await provider.complete(
        messages=messages, model=model, max_tokens=max_tokens, json_mode=True
    )

    try:
        return _parse_json_response(raw)
    except (json.JSONDecodeError, ValueError):
        logger.warning("LLM returned invalid JSON, retrying with nudge")
        retry_messages = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "Your response was not valid JSON. Please respond with ONLY the JSON object as specified in the system instructions."},
        ]
        try:
            retry_raw = await provider.complete(
                messages=retry_messages, model=model, max_tokens=max_tokens
            )
            return _parse_json_response(retry_raw)
        except Exception:
            logger.warning("JSON retry failed, returning raw text as summary")
            return {
                "summary": raw,
                "document_type": "Unknown",
                "parties": [],
                "key_findings": [],
                "deadlines": [],
                "overall_risk_assessment": "unknown",
                "confidence": "low",
            }


async def _single_call_review(
    chunks: list[dict],
    provider: LLMProvider,
    model: str,
) -> dict:
    """Run a full document review via a single LLM call.

    Sends the entire document content to the LLM in one call.
    Best for documents under the token threshold where the model
    can see all sections and cross-reference them.

    Args:
        chunks: All chunks for the document, ordered by chunk_index.
        provider: The LLM provider instance.
        model: Model identifier.

    Returns:
        Parsed review result dict.
    """
    step_start = time.time()

    formatted_doc = format_document_for_review(chunks)
    user_message = FULL_REVIEW_USER_PROMPT.format(formatted_document=formatted_doc)

    messages = [
        {"role": "system", "content": FULL_REVIEW_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    result = await _call_with_retry(provider, messages, model)

    elapsed = time.time() - step_start
    logger.info("Single-call review completed in %.2fs", elapsed)

    return result


async def _process_map_chunk(
    chunk: dict,
    index: int,
    total: int,
    provider: LLMProvider,
    model: str,
    semaphore: asyncio.Semaphore,
) -> dict | None:
    """Process a single chunk in the map step.

    Args:
        chunk: The chunk dict to process.
        index: 1-based index of this chunk.
        total: Total number of chunks.
        provider: The LLM provider instance.
        model: Model identifier.
        semaphore: Concurrency limiter.

    Returns:
        Parsed map result dict, or None if the chunk failed.
    """
    async with semaphore:
        try:
            user_message = MAP_REDUCE_MAP_USER_PROMPT.format(
                excerpt_number=index,
                total_excerpts=total,
                section_title=chunk.get("section_title") or "Untitled",
                page_number=chunk.get("page_number") or "?",
                content=chunk["content"],
            )

            messages = [
                {"role": "system", "content": MAP_REDUCE_MAP_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ]

            raw = await provider.complete(
                messages=messages, model=model, max_tokens=2048, json_mode=True
            )

            result = _parse_json_response(raw)
            logger.info("Map step: chunk %d/%d processed", index, total)
            return result

        except Exception:
            logger.exception("Map step: chunk %d/%d failed, skipping", index, total)
            return None


async def _map_reduce_review(
    chunks: list[dict],
    provider: LLMProvider,
    model: str,
) -> dict:
    """Run a full document review via map-reduce.

    Processes each chunk individually (map), then synthesizes all
    findings into a single review (reduce). Used for documents that
    exceed the token threshold.

    Args:
        chunks: All chunks for the document, ordered by chunk_index.
        provider: The LLM provider instance.
        model: Model identifier.

    Returns:
        Parsed review result dict.
    """
    # MAP STEP
    map_start = time.time()
    semaphore = asyncio.Semaphore(_MAP_CONCURRENCY)
    total = len(chunks)

    tasks = [
        _process_map_chunk(chunk, i, total, provider, model, semaphore)
        for i, chunk in enumerate(chunks, start=1)
    ]

    map_results_raw = await asyncio.gather(*tasks)
    map_elapsed = time.time() - map_start

    # Filter out failed chunks and boilerplate
    map_results: list[dict] = []
    map_chunks: list[dict] = []
    for result, chunk in zip(map_results_raw, chunks):
        if result is None:
            continue
        if result.get("is_boilerplate", False):
            logger.info("Map step: skipping boilerplate chunk %d", chunk["chunk_index"])
            continue
        if not result.get("findings"):
            continue
        map_results.append(result)
        map_chunks.append(chunk)

    logger.info(
        "Map step complete: %d/%d chunks produced findings in %.2fs",
        len(map_results), total, map_elapsed,
    )

    if not map_results:
        return {
            "summary": "No significant findings were identified in the document.",
            "document_type": "Unknown",
            "parties": [],
            "key_findings": [],
            "deadlines": [],
            "overall_risk_assessment": "low",
            "confidence": "low",
        }

    # REDUCE STEP
    reduce_start = time.time()

    formatted_outputs = format_map_outputs(map_results, map_chunks)
    reduce_tokens = count_text_tokens(formatted_outputs)
    threshold = settings.full_review_token_threshold

    if reduce_tokens > threshold:
        # Multi-level reduce: batch map outputs into groups
        logger.info(
            "Reduce input (%d tokens) exceeds threshold (%d), using multi-level reduce",
            reduce_tokens, threshold,
        )
        result = await _multi_level_reduce(
            map_results, map_chunks, provider, model, threshold
        )
    else:
        # Single reduce call
        user_message = MAP_REDUCE_REDUCE_USER_PROMPT.format(
            formatted_map_outputs=formatted_outputs
        )
        messages = [
            {"role": "system", "content": MAP_REDUCE_REDUCE_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        result = await _call_with_retry(provider, messages, model)

    reduce_elapsed = time.time() - reduce_start
    logger.info("Reduce step complete in %.2fs", reduce_elapsed)

    return result


async def _multi_level_reduce(
    map_results: list[dict],
    map_chunks: list[dict],
    provider: LLMProvider,
    model: str,
    threshold: int,
) -> dict:
    """Perform multi-level reduce when map outputs exceed the token threshold.

    Batches map outputs into groups that fit within the threshold,
    reduces each group, then does a final reduce on the group results.

    Args:
        map_results: All map step outputs.
        map_chunks: Corresponding chunks for metadata.
        provider: The LLM provider instance.
        model: Model identifier.
        threshold: Token threshold for a single reduce call.

    Returns:
        Final synthesized review result.
    """
    # Batch map outputs into groups that fit within threshold
    batches: list[tuple[list[dict], list[dict]]] = []
    current_results: list[dict] = []
    current_chunks: list[dict] = []
    current_tokens = 0

    for result, chunk in zip(map_results, map_chunks):
        result_tokens = count_text_tokens(json.dumps(result))
        if current_tokens + result_tokens > threshold and current_results:
            batches.append((current_results, current_chunks))
            current_results = []
            current_chunks = []
            current_tokens = 0
        current_results.append(result)
        current_chunks.append(chunk)
        current_tokens += result_tokens

    if current_results:
        batches.append((current_results, current_chunks))

    logger.info("Multi-level reduce: %d batches", len(batches))

    # Reduce each batch
    batch_results: list[dict] = []
    batch_chunks_for_format: list[dict] = []
    for i, (batch_results_list, batch_chunks_list) in enumerate(batches, start=1):
        formatted = format_map_outputs(batch_results_list, batch_chunks_list)
        user_message = MAP_REDUCE_REDUCE_USER_PROMPT.format(
            formatted_map_outputs=formatted
        )
        messages = [
            {"role": "system", "content": MAP_REDUCE_REDUCE_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        result = await _call_with_retry(provider, messages, model)
        batch_results.append(result)
        # Create a synthetic chunk for the format_map_outputs call in the final reduce
        batch_chunks_for_format.append({
            "section_title": f"Batch {i} synthesis",
            "page_number": None,
        })
        logger.info("Multi-level reduce: batch %d/%d complete", i, len(batches))

    # Final reduce on batch results
    formatted_final = format_map_outputs(batch_results, batch_chunks_for_format)
    user_message = MAP_REDUCE_REDUCE_USER_PROMPT.format(
        formatted_map_outputs=formatted_final
    )
    messages = [
        {"role": "system", "content": MAP_REDUCE_REDUCE_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    return await _call_with_retry(provider, messages, model)


async def full_review_document(
    document_id: uuid.UUID,
    db: AsyncSession,
    user: User,
) -> dict:
    """Run a full document review pipeline.

    Determines the optimal strategy (single-call vs map-reduce) based
    on document token count and the configured threshold, then executes
    the review and returns structured findings.

    Args:
        document_id: UUID of the document to review.
        db: Async database session.
        user: The authenticated user (must have an API key stored).

    Returns:
        Dict containing the full review result plus metadata.

    Raises:
        RAGQueryError: If the pipeline fails.
    """
    pipeline_start = time.time()

    # Validate user has an API key
    if not user.encrypted_llm_key:
        raise RAGQueryError(
            "No API key configured. Add one in Settings before running a review."
        )

    # Validate document
    document = await db.get(Document, document_id)
    if document is None or document.user_id != user.id:
        raise RAGQueryError("Document not found")
    if document.upload_status != "completed":
        raise RAGQueryError(
            f"Document is not ready for review (status: {document.upload_status})"
        )

    # Count tokens and determine strategy
    doc_tokens = await count_document_tokens(document_id, db)
    total_tokens = doc_tokens["total_tokens"]
    strategy_info = get_review_strategy(total_tokens)
    strategy = strategy_info["strategy"]

    logger.info(
        "Full review for document %s: %d tokens, strategy=%s",
        document_id, total_tokens, strategy,
    )

    # Load all chunks
    chunks = await load_all_chunks(document_id, db)
    if not chunks:
        raise RAGQueryError("Document has no chunks")

    # Decrypt key and get provider
    try:
        api_key = decrypt_api_key(user.encrypted_llm_key)
    except Exception as exc:
        raise RAGQueryError(f"Failed to decrypt API key: {exc}") from exc

    provider = get_llm_provider(api_key, user.llm_provider)
    model = user.llm_model or settings.default_llm_model

    # Route to the appropriate strategy
    try:
        if strategy == "single_call":
            result = await _single_call_review(chunks, provider, model)
        else:
            result = await _map_reduce_review(chunks, provider, model)
    except LLMProviderError:
        raise
    except Exception as exc:
        raise RAGQueryError(f"Full review failed: {exc}") from exc

    # Add metadata
    total_ms = int((time.time() - pipeline_start) * 1000)
    result["metadata"] = {
        "model_used": model,
        "strategy_used": strategy,
        "total_tokens": total_tokens,
        "chunk_count": len(chunks),
        "response_time_ms": total_ms,
    }

    logger.info(
        "Full review complete: %dms total, strategy=%s, model=%s",
        total_ms, strategy, model,
    )

    return result
