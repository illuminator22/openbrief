"""RAG query pipeline: retrieve → prompt → LLM → parse → return.

Orchestrates the full question-answering flow for a document,
using the retriever for chunk selection and a frontier LLM for
generating cited answers.
"""

import json
import logging
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from api.exceptions import LLMProviderError, RAGQueryError
from config import settings
from core.llm.encryption import decrypt_api_key
from core.llm.provider import get_llm_provider
from core.rag.prompts import RAG_SYSTEM_PROMPT, RAG_USER_PROMPT, format_chunks_for_prompt
from core.rag.retriever import retrieve_chunks
from db.models import Document, User

logger = logging.getLogger(__name__)

# Map confidence strings to numeric values for database storage
_CONFIDENCE_MAP = {"high": 0.9, "medium": 0.6, "low": 0.3}


def _parse_llm_response(raw: str, chunks: list[dict]) -> dict:
    """Parse the LLM's JSON response and enrich citations with chunk IDs.

    Args:
        raw: Raw response text from the LLM.
        chunks: Retrieved chunks (used to map excerpt_number → chunk_id).

    Returns:
        Parsed response dict with answer, citations, confidence, etc.

    Raises:
        ValueError: If the response is not valid JSON.
    """
    # Strip markdown code fences if the LLM included them despite instructions
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    parsed = json.loads(cleaned)

    # Enrich citations with chunk_id from the retrieved chunks
    for citation in parsed.get("citations", []):
        excerpt_num = citation.get("excerpt_number")
        if excerpt_num and 1 <= excerpt_num <= len(chunks):
            citation["chunk_id"] = str(chunks[excerpt_num - 1]["chunk_id"])
        else:
            citation["chunk_id"] = None

    return parsed


async def query_document(
    document_id: uuid.UUID,
    question: str,
    db: AsyncSession,
    user: User,
    top_k: int | None = None,
) -> dict:
    """Run the full RAG query pipeline for a document.

    Retrieves relevant chunks, constructs a prompt with context,
    calls the user's configured LLM, and returns a cited answer.

    Args:
        document_id: UUID of the document to query.
        question: The user's question.
        db: Async database session.
        user: The authenticated user (must have an API key stored).
        top_k: Number of chunks to retrieve. Defaults to settings.rag_top_k.

    Returns:
        Dict containing: answer, citations, confidence, insufficient_information,
        and metadata (model_used, chunks_retrieved, response_time_ms).

    Raises:
        RAGQueryError: If the pipeline fails for any reason.
    """
    pipeline_start = time.time()

    if top_k is None:
        top_k = settings.rag_top_k

    # Validate user has an API key
    if not user.encrypted_llm_key:
        raise RAGQueryError(
            "No API key configured. Add one in Settings before querying."
        )

    # Validate document exists and is ready
    document = await db.get(Document, document_id)
    if document is None or document.user_id != user.id:
        raise RAGQueryError("Document not found")
    if document.upload_status != "completed":
        raise RAGQueryError(
            f"Document is not ready for queries (status: {document.upload_status})"
        )

    # Step 1: Retrieve relevant chunks
    step_start = time.time()
    chunks = await retrieve_chunks(
        query=question,
        document_id=document_id,
        db=db,
        top_k=top_k,
    )
    retrieval_ms = int((time.time() - step_start) * 1000)
    logger.info(
        "RAG retrieval: %d chunks in %dms for document %s",
        len(chunks), retrieval_ms, document_id,
    )

    if not chunks:
        return {
            "answer": "No relevant excerpts were found in the document for this question.",
            "citations": [],
            "confidence": "low",
            "insufficient_information": True,
            "metadata": {
                "model_used": user.llm_model or settings.default_llm_model,
                "chunks_retrieved": 0,
                "response_time_ms": int((time.time() - pipeline_start) * 1000),
            },
        }

    # Step 2: Build prompt
    formatted_chunks = format_chunks_for_prompt(chunks)
    user_message = RAG_USER_PROMPT.format(
        question=question,
        formatted_chunks=formatted_chunks,
    )
    messages = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # Step 3: Decrypt key and get provider
    try:
        api_key = decrypt_api_key(user.encrypted_llm_key)
    except Exception as exc:
        raise RAGQueryError(f"Failed to decrypt API key: {exc}") from exc

    provider = get_llm_provider(api_key, user.llm_provider)
    model = user.llm_model or settings.default_llm_model

    # Step 4: Call LLM
    step_start = time.time()
    try:
        raw_response = await provider.complete(messages=messages, model=model)
    except LLMProviderError:
        raise
    except Exception as exc:
        raise RAGQueryError(f"LLM call failed: {exc}") from exc

    llm_ms = int((time.time() - step_start) * 1000)
    logger.info("RAG LLM call: %dms (model=%s)", llm_ms, model)

    # Step 5: Parse JSON response
    try:
        result = _parse_llm_response(raw_response, chunks)
    except (json.JSONDecodeError, ValueError):
        # Retry once with a JSON nudge
        logger.warning("LLM returned invalid JSON, retrying with nudge")
        retry_messages = messages + [
            {"role": "assistant", "content": raw_response},
            {"role": "user", "content": "Your response was not valid JSON. Please respond with ONLY the JSON object as specified in the system instructions."},
        ]
        try:
            retry_response = await provider.complete(messages=retry_messages, model=model)
            result = _parse_llm_response(retry_response, chunks)
        except Exception:
            # Fall back to raw text with empty citations
            logger.warning("JSON retry failed, returning raw text")
            result = {
                "answer": raw_response,
                "citations": [],
                "confidence": "low",
                "insufficient_information": False,
            }

    # Step 6: Build final response with metadata
    total_ms = int((time.time() - pipeline_start) * 1000)
    logger.info("RAG pipeline complete: %dms total", total_ms)

    result["metadata"] = {
        "model_used": model,
        "chunks_retrieved": len(chunks),
        "response_time_ms": total_ms,
    }

    return result
