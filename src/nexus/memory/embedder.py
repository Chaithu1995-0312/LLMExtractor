"""
nexus.memory.embedder
=====================
Embedding interface for the Memory Layer.

Model: Ollama nomic-embed-text
  - Produces 768-dimensional float32 vectors.
  - Runs fully locally via the Ollama HTTP API.
  - No sentence-transformers, no ONNX, no external cloud calls.

Invariants:
  - MUST NOT use the GraphManager's VectorEmbedder or EmbeddingService.
  - MUST NOT share embedding state with the graph vector layer.
  - Embedding dimension is validated on first call and cached.
  - Ollama unavailability raises OllamaUnavailableError (not generic Exception).

Retry policy:
  - Up to MAX_RETRIES attempts with exponential back-off.
  - On final failure, raises — caller decides whether to skip or abort.

Batch embedding:
  - embed_batch() sends requests sequentially (Ollama /api/embed endpoint
    does not support true batching in all versions). Controlled concurrency
    is handled at the MemoryService level via a semaphore.
"""

import logging
import time
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

OLLAMA_BASE_URL: str = "http://localhost:11434"
EMBED_MODEL: str = "nomic-embed-text"
EMBED_ENDPOINT: str = f"{OLLAMA_BASE_URL}/api/embeddings"

# nomic-embed-text produces 768-dimensional vectors.
EXPECTED_DIMENSION: int = 768

REQUEST_TIMEOUT: int = 30   # seconds per embedding call
MAX_RETRIES: int = 3
RETRY_BASE_DELAY: float = 1.0   # seconds, doubles on each retry


# --------------------------------------------------------------------------
# Exceptions
# --------------------------------------------------------------------------

class OllamaUnavailableError(RuntimeError):
    """Raised when Ollama is not reachable after all retries."""


class EmbeddingDimensionError(ValueError):
    """Raised when the model returns a vector of unexpected dimensionality."""


# --------------------------------------------------------------------------
# Core embedder
# --------------------------------------------------------------------------

class MemoryEmbedder:
    """
    Wraps the Ollama /api/embeddings endpoint for the Memory Layer.

    Thread safety: instances are NOT shared across threads. Instantiate
    one MemoryEmbedder per worker/thread to avoid request collisions.

    Usage:
        embedder = MemoryEmbedder()
        vector = embedder.embed("Some text here")   # -> List[float] len=768
        batch  = embedder.embed_batch(["text1", "text2"])
    """

    def __init__(
        self,
        model: str = EMBED_MODEL,
        ollama_base_url: str = OLLAMA_BASE_URL,
        max_retries: int = MAX_RETRIES,
        request_timeout: int = REQUEST_TIMEOUT,
    ):
        self.model = model
        self.endpoint = f"{ollama_base_url}/api/embeddings"
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        self._validated_dimension: Optional[int] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def embed(self, text: str) -> List[float]:
        """
        Embed a single text string.

        Returns:
            List[float] of length EXPECTED_DIMENSION (768).

        Raises:
            OllamaUnavailableError: if Ollama is unreachable after retries.
            EmbeddingDimensionError: if returned vector dimension is wrong.
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text.")

        vector = self._call_with_retry(text)
        self._validate_dimension(vector)
        return vector

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts sequentially.

        Skips blank strings (returns empty list placeholder at that index).
        On per-text failure (after retries), raises immediately — partial
        results are not returned, preserving batch atomicity.

        Returns:
            List of float vectors, one per input text, preserving order.
        """
        results: List[List[float]] = []
        for idx, text in enumerate(texts):
            if not text or not text.strip():
                logger.warning("[MemoryEmbedder] Empty text at batch index %d — skipping.", idx)
                results.append([])
                continue
            vector = self.embed(text)
            results.append(vector)
        return results

    def check_availability(self) -> bool:
        """
        Probe Ollama to confirm nomic-embed-text is available.
        Returns True if a test embedding succeeds, False otherwise.
        Does not raise.
        """
        try:
            vec = self._post_embed("hello")
            return len(vec) > 0
        except Exception as exc:
            logger.warning("[MemoryEmbedder] Availability check failed: %s", exc)
            return False

    @property
    def dimension(self) -> int:
        """Return the validated embedding dimension (768 for nomic-embed-text)."""
        return self._validated_dimension or EXPECTED_DIMENSION

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_with_retry(self, text: str) -> List[float]:
        """
        POST to Ollama with exponential back-off retry.

        Raises OllamaUnavailableError after max_retries failures.
        """
        last_exc: Optional[Exception] = None
        delay = RETRY_BASE_DELAY

        for attempt in range(1, self.max_retries + 1):
            try:
                return self._post_embed(text)
            except requests.exceptions.ConnectionError as exc:
                last_exc = exc
                logger.warning(
                    "[MemoryEmbedder] Ollama connection error (attempt %d/%d): %s",
                    attempt, self.max_retries, exc,
                )
            except requests.exceptions.Timeout as exc:
                last_exc = exc
                logger.warning(
                    "[MemoryEmbedder] Ollama timeout (attempt %d/%d): %s",
                    attempt, self.max_retries, exc,
                )
            except requests.exceptions.HTTPError as exc:
                # HTTP errors (4xx/5xx) are non-retryable — Ollama returned a valid
                # response indicating a model or request error.
                logger.error("[MemoryEmbedder] HTTP error from Ollama: %s", exc)
                raise OllamaUnavailableError(f"Ollama HTTP error: {exc}") from exc

            if attempt < self.max_retries:
                logger.info("[MemoryEmbedder] Retrying in %.1fs …", delay)
                time.sleep(delay)
                delay *= 2.0  # exponential back-off

        raise OllamaUnavailableError(
            f"Ollama unreachable after {self.max_retries} attempts. Last error: {last_exc}"
        )

    def _post_embed(self, text: str) -> List[float]:
        """
        Raw HTTP POST to Ollama /api/embeddings.

        Returns:
            List[float] embedding vector.

        Raises:
            requests.exceptions.* on network / HTTP errors.
            ValueError if the response JSON is malformed.
        """
        payload = {"model": self.model, "prompt": text}
        response = requests.post(
            self.endpoint,
            json=payload,
            timeout=self.request_timeout,
        )
        response.raise_for_status()

        body = response.json()
        embedding = body.get("embedding")

        if not isinstance(embedding, list) or len(embedding) == 0:
            raise ValueError(
                f"[MemoryEmbedder] Ollama returned unexpected body: {body}"
            )

        return [float(v) for v in embedding]

    def _validate_dimension(self, vector: List[float]) -> None:
        """
        Validate vector dimension on first call and cache the result.
        Subsequent calls compare against the cached value.

        Raises EmbeddingDimensionError on mismatch.
        """
        dim = len(vector)

        if self._validated_dimension is None:
            if dim != EXPECTED_DIMENSION:
                raise EmbeddingDimensionError(
                    f"[MemoryEmbedder] Expected {EXPECTED_DIMENSION}-dim vector from "
                    f"'{self.model}', got {dim}. "
                    f"Ensure `ollama pull {self.model}` has been run."
                )
            self._validated_dimension = dim
            logger.debug("[MemoryEmbedder] Dimension validated: %d", dim)
        else:
            if dim != self._validated_dimension:
                raise EmbeddingDimensionError(
                    f"[MemoryEmbedder] Dimension changed mid-session: "
                    f"expected {self._validated_dimension}, got {dim}."
                )
