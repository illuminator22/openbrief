"""Research Agent — retrieves relevant document passages for a given query.

This agent wraps the existing pgvector retriever and structures the results
for downstream agents (Analysis, Draft, Fact-Check).

In the targeted question flow, this is the first agent to run.
In the full review flow, this agent is SKIPPED (all chunks are loaded directly).

Query reformulation rationale:
    When enabled, the agent uses the cheapest available LLM to generate 2-3
    alternative search queries before running vector search. This addresses
    a known retrieval weakness: a query like "what is the termination clause"
    only matches chunks with high similarity to that exact phrasing, but misses
    related content (e.g., Section 1 mentioning "terminate for convenience").
    Reformulating into multiple queries ("termination clause", "how can the
    agreement be ended", "termination for cause or convenience") casts a wider
    net and significantly improves retrieval precision on inference questions.
    Cost: ~$0.001 per query with nano models. Latency: +300-500ms for the LLM
    call plus extra retrieval time. Both are negligible compared to the main
    answer-generation LLM call (3-5 seconds).
"""

import json
import logging
import time
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.agents.state import AgentState, RetrievedPassage
from core.rag.retriever import retrieve_chunks

logger = logging.getLogger(__name__)

# Cheapest model per provider for query reformulation
_REFORMULATION_MODELS: dict[str, str] = {
    "openai": "gpt-5.4-nano",
    "anthropic": "claude-haiku-4-5-20251001",
    "deepseek": "deepseek-reasoner",
}

_REFORMULATION_PROMPT = """You are a legal search assistant. A user asked this question about a legal document:

"{query}"

Generate exactly 3 DIFFERENT search queries that would help find relevant sections in the document. Each query MUST use different wording, synonyms, or legal terminology — do NOT repeat or paraphrase the original query.

Rules:
- Query 1: the original question as-is
- Query 2: rephrase using different legal terminology (e.g., "termination" → "cancellation or ending of agreement")
- Query 3: focus on a related concept the document might address (e.g., "termination clause" → "notice period for ending the contract")

Return a JSON object with a "queries" key containing an array of 3 strings. No explanation.
Example: {"queries": ["what is the termination clause", "cancellation or ending of agreement provisions", "notice period required to end the contract"]}"""


class ResearchAgent:
    """Retrieves relevant document passages using pgvector similarity search.

    Stateless — all data flows through AgentState. The agent reads the query
    and document_id from state, calls the existing retriever, and writes
    structured passages back to state.

    When reformulate_queries is enabled, uses a cheap LLM to generate
    alternative search queries before retrieval, improving recall on
    questions that use different terminology than the document.
    """

    async def run(
        self,
        state: AgentState,
        db: AsyncSession,
        reformulate_queries: bool = True,
        user=None,
    ) -> AgentState:
        """Execute the Research Agent.

        Args:
            state: The shared pipeline state with document_id and query set.
            db: Async database session for pgvector retrieval.
            reformulate_queries: If True, use LLM to generate alternative
                search queries before retrieval. Costs ~$0.001 per query.
            user: The User model instance (needed for LLM key if reformulating).
                If None and reformulate_queries is True, falls back to single query.

        Returns:
            The modified state with passages, timing, and trace populated.
        """
        state.current_agent = "research"
        start = time.time()

        try:
            # Determine search queries
            queries = [state.query]
            reformulation_ms = 0

            # Refresh user to ensure encrypted_llm_key is loaded (async SQLAlchemy
            # may not have it if the object was loaded in a different session scope)
            if reformulate_queries and user:
                try:
                    await db.refresh(user, ["encrypted_llm_key", "llm_provider"])
                except Exception:
                    pass  # If refresh fails, we'll check the attribute below

            has_key = bool(user and user.encrypted_llm_key)
            logger.info(
                "Research Agent: reformulate=%s, user=%s, has_key=%s, provider=%s",
                reformulate_queries, bool(user), has_key,
                getattr(user, "llm_provider", None) if user else None,
            )

            if reformulate_queries and has_key:
                try:
                    reform_start = time.time()
                    alt_queries = await self._reformulate(state.query, user)
                    queries = alt_queries
                    reformulation_ms = int((time.time() - reform_start) * 1000)
                    logger.info(
                        "Research Agent: reformulated into %d queries in %dms: %s",
                        len(queries), reformulation_ms, queries,
                    )
                except Exception as exc:
                    # Reformulation failure is non-fatal — fall back to original query
                    logger.warning("Research Agent: query reformulation failed, using original. Error: %r", exc)
                    queries = [state.query]

            # Run retrieval for all queries and deduplicate
            all_chunks: dict[str, dict] = {}  # chunk_id → chunk dict (dedup)
            for q in queries:
                chunks = await retrieve_chunks(
                    query=q,
                    document_id=state.document_id,
                    db=db,
                )
                for chunk in chunks:
                    cid = str(chunk["chunk_id"])
                    # Keep the highest similarity score if a chunk appears in multiple queries
                    if cid not in all_chunks or chunk["similarity_score"] > all_chunks[cid]["similarity_score"]:
                        all_chunks[cid] = chunk

            # Convert to RetrievedPassage objects, sort by similarity, take top_k
            top_k = settings.rag_top_k
            sorted_chunks = sorted(all_chunks.values(), key=lambda c: c["similarity_score"], reverse=True)[:top_k]

            passages = [
                RetrievedPassage(
                    chunk_id=str(chunk["chunk_id"]),
                    content=chunk["content"],
                    page_number=chunk.get("page_number"),
                    section_title=chunk.get("section_title"),
                    similarity_score=chunk["similarity_score"],
                    chunk_index=chunk["chunk_index"],
                )
                for chunk in sorted_chunks
            ]

            retrieval_ms = int((time.time() - start) * 1000)

            # Write results to state
            state.passages = passages
            state.retrieval_time_ms = retrieval_ms

            # Add trace entry
            state.agent_trace.append({
                "agent": "research",
                "action": "retrieve_passages",
                "document_id": str(state.document_id),
                "query": state.query,
                "queries_used": queries,
                "reformulated": len(queries) > 1,
                "reformulation_ms": reformulation_ms,
                "total_unique_chunks": len(all_chunks),
                "chunks_returned": len(passages),
                "top_similarity": passages[0].similarity_score if passages else None,
                "time_ms": retrieval_ms,
                "timestamp": datetime.utcnow().isoformat(),
            })

            if not passages:
                logger.warning(
                    "Research Agent: no passages found for query '%s' on document %s",
                    state.query[:60], state.document_id,
                )

            logger.info(
                "Research Agent: %d passages in %dms (%d queries, %d unique chunks, top=%.4f)",
                len(passages), retrieval_ms, len(queries),
                len(all_chunks), passages[0].similarity_score if passages else 0.0,
            )

        except Exception as exc:
            retrieval_ms = int((time.time() - start) * 1000)
            state.error = f"Research Agent failed: {exc}"
            state.agent_trace.append({
                "agent": "research",
                "action": "error",
                "error": str(exc),
                "time_ms": retrieval_ms,
                "timestamp": datetime.utcnow().isoformat(),
            })
            logger.exception("Research Agent failed for document %s", state.document_id)

        return state

    async def _reformulate(self, query: str, user) -> list[str]:
        """Generate alternative search queries using the cheapest available LLM.

        Args:
            query: The original user query.
            user: User model with encrypted_llm_key and llm_provider.

        Returns:
            List of search queries (original + alternatives).
        """
        from core.llm.encryption import decrypt_api_key
        from core.llm.provider import get_llm_provider

        api_key = decrypt_api_key(user.encrypted_llm_key)
        model = _REFORMULATION_MODELS.get(user.llm_provider, "gpt-5.4-nano")
        provider = get_llm_provider(api_key, user.llm_provider)

        prompt = _REFORMULATION_PROMPT.format(query=query)
        response = await provider.complete(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=200,
            json_mode=True,
        )

        # Parse JSON — handle both bare arrays and wrapped objects
        logger.info("Research Agent: raw reformulation response: %s", response[:500])
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        parsed = json.loads(cleaned.strip())

        # OpenAI json_mode returns objects, not bare arrays
        # Handle: {"queries": [...]} or {"alternatives": [...]} or [...]
        if isinstance(parsed, dict):
            # Find the first list value in the dict
            queries = None
            for v in parsed.values():
                if isinstance(v, list):
                    queries = v
                    break
            if queries is None:
                logger.warning("Reformulation returned dict with no list: %s", parsed)
                return [query]
        elif isinstance(parsed, list):
            queries = parsed
        else:
            logger.warning("Reformulation returned unexpected type: %s", type(parsed))
            return [query]

        if len(queries) == 0:
            return [query]

        # Ensure original query is included
        if query not in queries:
            queries.insert(0, query)

        # Cap at 4 queries to limit retrieval cost
        return queries[:4]
