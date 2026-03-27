"""Semantic routing for classifying user input as targeted question or full review.

Uses the same BGE embedding model already loaded for RAG (zero additional cost).
Compares user input against pre-computed example phrase embeddings to determine
the user's intent.

IMPORTANT: No BGE query prefix is applied here. This is classification between
example phrases, not document retrieval. Both examples and user input are encoded
as plain text (same as embed_chunks, not embed_query).
"""

import logging
import time

import numpy as np

from core.ingestion.embedder import get_embedding_service

logger = logging.getLogger(__name__)

# Example phrases for each route — expand these over time based on user feedback
FULL_REVIEW_EXAMPLES = [
    "give me a full review of this contract",
    "analyze the entire document",
    "due diligence review",
    "issue spot this agreement",
    "red flag anything concerning",
    "what are the problems with this document overall",
    "comprehensive analysis of all clauses",
    "review everything and summarize the key issues",
    "is this contract enforceable overall",
    "walk me through the whole agreement",
    "run a complete risk assessment",
    "what should I be worried about in this contract",
    "full analysis please",
    "check this whole document for issues",
    "give me the rundown on this agreement",
]

TARGETED_QUESTION_EXAMPLES = [
    "what is the termination clause",
    "when does this contract expire",
    "who are the parties involved",
    "is there a non-compete provision",
    "what is the liability cap",
    "summarize section 4",
    "what are the payment terms",
    "what happens if either party breaches",
    "is there an arbitration clause",
    "what is the governing law",
    "what are the insurance requirements",
    "how much notice is required for termination",
    "are there any indemnification provisions",
    "what is the dispute resolution process",
    "what are the confidentiality obligations",
]


class SemanticRouter:
    """Classifies user input as targeted question or full review request.

    Uses cosine similarity between the user's input embedding and
    pre-computed embeddings of example phrases for each route.
    Reuses the existing EmbeddingService singleton — no additional model load.

    Classification uses embed_chunks (no prefix), not embed_query,
    because this is phrase-to-phrase comparison, not document retrieval.
    """

    def __init__(self) -> None:
        """Pre-compute embeddings for all example phrases."""
        start = time.time()
        svc = get_embedding_service()

        # Encode examples as plain text (no query prefix)
        full_review_vecs = svc.embed_chunks(FULL_REVIEW_EXAMPLES)
        targeted_vecs = svc.embed_chunks(TARGETED_QUESTION_EXAMPLES)

        self._full_review_embeddings = np.array(full_review_vecs, dtype=np.float32)
        self._targeted_embeddings = np.array(targeted_vecs, dtype=np.float32)

        elapsed = time.time() - start
        logger.info(
            "SemanticRouter initialized in %.2fs (%d full_review, %d targeted examples)",
            elapsed, len(FULL_REVIEW_EXAMPLES), len(TARGETED_QUESTION_EXAMPLES),
        )

    def classify(
        self,
        user_input: str,
        confidence_threshold: float = 0.05,
    ) -> dict:
        """Classify user input as targeted question or full review.

        Args:
            user_input: The user's text input.
            confidence_threshold: Minimum score difference to be confident
                in the classification. Below this, defaults to targeted_question.

        Returns:
            Dict with: route, confidence, full_review_score, targeted_score,
            low_confidence (bool).
        """
        start = time.time()
        svc = get_embedding_service()

        # Encode user input as plain text (no query prefix — this is classification)
        input_vec = np.array(svc.embed_chunks([user_input])[0], dtype=np.float32)

        # Compute average cosine similarity against each route
        full_review_score = float(np.mean(input_vec @ self._full_review_embeddings.T))
        targeted_score = float(np.mean(input_vec @ self._targeted_embeddings.T))

        score_diff = abs(full_review_score - targeted_score)
        low_confidence = score_diff < confidence_threshold

        # Default to targeted_question (cheap/safe) when uncertain
        if low_confidence or targeted_score >= full_review_score:
            route = "targeted_question"
        else:
            route = "full_review"

        elapsed_ms = int((time.time() - start) * 1000)

        logger.info(
            "Routing '%s' → %s (full=%.4f, targeted=%.4f, diff=%.4f, low_conf=%s, %dms)",
            user_input[:60], route, full_review_score, targeted_score,
            score_diff, low_confidence, elapsed_ms,
        )

        return {
            "route": route,
            "confidence": round(score_diff, 4),
            "full_review_score": round(full_review_score, 4),
            "targeted_score": round(targeted_score, 4),
            "low_confidence": low_confidence,
        }


# Lazy singleton
_instance: SemanticRouter | None = None


def get_semantic_router() -> SemanticRouter:
    """Return the shared SemanticRouter singleton.

    Initializes on first call (pre-computes example embeddings).
    """
    global _instance
    if _instance is None:
        _instance = SemanticRouter()
    return _instance
