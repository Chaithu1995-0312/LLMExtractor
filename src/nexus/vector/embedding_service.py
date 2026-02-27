import time
import logging
import numpy as np
from nexus.vector.embedder import VectorEmbedder

logger = logging.getLogger(__name__)

# Retry policy constants
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0   # seconds  (delay = base^attempt: 2s, 4s, 8s)


class EmbeddingService:
    """
    Deterministic embedding service for drift detection.
    Wraps the underlying VectorEmbedder to enforce a strict contract.

    Improvements (P0 fix):
    - embed() now retries up to _MAX_RETRIES times with exponential backoff
      instead of failing silently on transient model errors.
    - model_available() provides a lightweight health-check probe.
    """

    def __init__(self):
        # We hardcode the model name here to ensure consistency across the drift engine.
        # VectorEmbedder handles the singleton/shared model loading.
        self.model_name = "all-MiniLM-L6-v2"
        self._embedder = VectorEmbedder(self.model_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed(self, text: str) -> np.ndarray:
        """
        Embeds a single string into a 1D float32 numpy array.

        Retry contract:
          - Attempts up to _MAX_RETRIES times.
          - Uses exponential backoff: 2^attempt seconds between retries.
          - Raises RuntimeError after all retries are exhausted so callers
            can handle the failure explicitly rather than receiving silent NaN/None.
        """
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                # embed_query returns a 1xN array — flatten to N
                vector = self._embedder.embed_query(text, use_genai=False)
                return vector.flatten().astype("float32")
            except Exception as exc:
                last_exc = exc
                wait = _BACKOFF_BASE ** attempt
                logger.warning(
                    "[EmbeddingService] embed() failed on attempt %d/%d: %s. "
                    "Retrying in %.1fs...",
                    attempt + 1, _MAX_RETRIES, exc, wait,
                )
                time.sleep(wait)

        # All retries exhausted
        logger.error(
            "[EmbeddingService] embed() permanently failed after %d attempts. "
            "Last error: %s", _MAX_RETRIES, last_exc,
        )
        raise RuntimeError(
            f"EmbeddingService.embed() failed after {_MAX_RETRIES} retries: {last_exc}"
        ) from last_exc

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """
        Embeds a list of strings. Each item is independently retried.
        Raises RuntimeError on the first text that permanently fails.
        """
        return [self.embed(t) for t in texts]

    def model_available(self) -> bool:
        """
        Lightweight probe: attempts to embed a single test token.
        Returns True if the model is responsive, False otherwise.
        Does NOT retry — intended as a fast health-check.
        """
        try:
            result = self._embedder.embed_query("ping", use_genai=False)
            return result is not None and result.size > 0
        except Exception as exc:
            logger.warning("[EmbeddingService] model_available() probe failed: %s", exc)
            return False

    def model_version(self) -> str:
        """
        Returns the version string of the model being used.
        This allows the system to detect when a re-index is required.
        """
        return self.model_name
