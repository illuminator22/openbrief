"""Embedding generation using Sentence Transformers.

Uses the BGE embedding model for document chunk and query encoding.
BGE models require a specific prefix for search queries but NOT for
document chunks — this distinction is critical for retrieval quality.
"""

import logging
import time

from sentence_transformers import SentenceTransformer

from config import settings

logger = logging.getLogger(__name__)

# BGE query prefix — exact string including trailing space.
# Used ONLY for search queries, NEVER for document chunks.
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class EmbeddingService:
    """Manages embedding generation for document chunks and search queries.

    Loads the sentence-transformers model once on initialization and reuses
    it for all subsequent calls. The model name is read from config so it
    can be changed via environment variable without code changes.

    BGE embedding rules:
        - Document chunks: encode raw text, no prefix
        - Search queries: prepend _QUERY_PREFIX before encoding
        - All embeddings are L2-normalized so cosine similarity works
          correctly with pgvector's <=> (cosine distance) operator
    """

    def __init__(self) -> None:
        """Load the embedding model and log dimensions and timing."""
        start = time.time()
        self._model = SentenceTransformer(settings.embedding_model)
        elapsed = time.time() - start

        self._dimensions = self._model.get_sentence_embedding_dimension()
        logger.info(
            "Loaded embedding model '%s' in %.2fs (dimensions=%d)",
            settings.embedding_model,
            elapsed,
            self._dimensions,
        )

    @property
    def dimensions(self) -> int:
        """Return the embedding vector dimensionality."""
        return self._dimensions

    def embed_chunks(self, texts: list[str]) -> list[list[float]]:
        """Encode document chunks into normalized embedding vectors.

        No prefix is applied — chunks are encoded as raw text per BGE spec.

        Args:
            texts: List of chunk text strings to embed.

        Returns:
            List of embedding vectors as Python float lists (not numpy arrays),
            one per input text. Each vector has `self.dimensions` elements.
        """
        if not texts:
            return []

        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Encode a search query into a normalized embedding vector.

        Prepends the BGE query prefix before encoding per BGE spec:
        "Represent this sentence for searching relevant passages: " + query

        Args:
            query: The user's search query string.

        Returns:
            A single embedding vector as a Python float list.
        """
        prefixed = _QUERY_PREFIX + query
        embedding = self._model.encode(prefixed, normalize_embeddings=True)
        return embedding.tolist()


# Lazy singleton — loaded once on first access, reused for all requests.
# Safe for FastAPI's async event loop (single-threaded coroutine execution).
_instance: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Return the shared EmbeddingService singleton.

    Loads the model on first call. Subsequent calls return the same instance.
    """
    global _instance
    if _instance is None:
        _instance = EmbeddingService()
    return _instance
