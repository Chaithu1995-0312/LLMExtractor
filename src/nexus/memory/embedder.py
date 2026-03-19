"""
nexus.memory.embedder
=====================
Unified Embedding interface for the Memory Layer.

Supports:
  - OpenAI (text-embedding-3-small, 1536 dim) - PRIMARY
  - Ollama (nomic-embed-text, 768 dim) - FALLBACK/LEGACY

Invariants:
  - Must respect `agents.yaml` configuration for provider/model.
  - Must validate dimensions against expected values.
  - Must handle provider failover if configured.
"""

import logging
import time
import os
from typing import List, Optional, Any

import requests
from nexus.config import get_agent_config

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Configuration Defaults
# --------------------------------------------------------------------------

DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_DIMENSION = 1536

# Legacy defaults
OLLAMA_BASE_URL = "http://localhost:11434"

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0

# --------------------------------------------------------------------------
# Exceptions
# --------------------------------------------------------------------------

class EmbedderUnavailableError(RuntimeError):
    """Raised when the embedding provider is not reachable."""


# Backward-compat alias (legacy imports still reference this name)
OllamaUnavailableError = EmbedderUnavailableError

class EmbeddingDimensionError(ValueError):
    """Raised when the model returns a vector of unexpected dimensionality."""

# --------------------------------------------------------------------------
# Core embedder
# --------------------------------------------------------------------------

class MemoryEmbedder:
    """
    Unified Embedder supporting OpenAI and Ollama.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        max_retries: int = MAX_RETRIES,
        request_timeout: int = REQUEST_TIMEOUT,
    ):
        self.config = get_agent_config("memory_embedder") or {}
        
        # Resolve Configuration
        self.provider = provider or self.config.get("provider", DEFAULT_PROVIDER)
        self.model = model or self.config.get("model", DEFAULT_MODEL)
        self.expected_dimension = self.config.get("dimension", DEFAULT_DIMENSION)
        
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        self.ollama_base_url = os.getenv("OLLAMA_HOST", OLLAMA_BASE_URL)
        
        self._openai_client = None
        self._validated_dimension: Optional[int] = None
        
        # API Key check for OpenAI
        if self.provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            logger.warning("[MemoryEmbedder] OpenAI provider selected but OPENAI_API_KEY not found. Fallback to Ollama?")
            # We don't auto-fallback here to avoid silent degradation, but we log it.

    def _get_openai_client(self):
        if self._openai_client is None:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise EmbedderUnavailableError("OPENAI_API_KEY not set in environment.")
            self._openai_client = OpenAI(api_key=api_key)
        return self._openai_client

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def embed(self, text: str) -> List[float]:
        """
        Embed a single text string.
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text.")

        vector = self._call_with_retry(text)
        self._validate_dimension(vector)
        return vector

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts. 
        OpenAI supports true batching; Ollama is sequential.
        """
        if not texts:
            return []
            
        # Filter empty strings to preserve index alignment
        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        valid_texts = [texts[i] for i in valid_indices]
        
        if not valid_texts:
            return [[] for _ in texts]

        try:
            vectors = []
            if self.provider == "openai":
                vectors = self._embed_batch_openai(valid_texts)
            else:
                # Ollama sequential fallback
                for text in valid_texts:
                    vectors.append(self.embed(text))
            
            # Reconstruct result list with empty placeholders
            results = []
            ptr = 0
            for i in range(len(texts)):
                if i in valid_indices:
                    results.append(vectors[ptr])
                    ptr += 1
                else:
                    results.append([]) # Zero vector or empty list? Interface says List[float]
                    # Actually typically downstream handles empty/zero. 
                    # Existing impl returned empty list for empty text.
            return results

        except Exception as e:
            logger.error(f"[MemoryEmbedder] Batch embedding failed: {e}")
            raise

    # ------------------------------------------------------------------
    # Internal Implementation
    # ------------------------------------------------------------------

    def _call_with_retry(self, text: str) -> List[float]:
        last_exc = None
        delay = RETRY_BASE_DELAY

        for attempt in range(1, self.max_retries + 1):
            try:
                if self.provider == "openai":
                    return self._embed_openai(text)
                else:
                    return self._embed_ollama(text)
            except Exception as e:
                last_exc = e
                logger.warning(
                    f"[MemoryEmbedder] {self.provider} error (attempt {attempt}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries:
                    time.sleep(delay)
                    delay *= 2.0
        
        raise EmbedderUnavailableError(f"Embedder {self.provider} failed after retries: {last_exc}") from last_exc

    def _embed_openai(self, text: str) -> List[float]:
        client = self._get_openai_client()
        # Clean text: replace newlines with spaces for best results with ada-002/v3
        clean_text = text.replace("\n", " ")
        response = client.embeddings.create(input=[clean_text], model=self.model)
        return response.data[0].embedding

    def _embed_batch_openai(self, texts: List[str]) -> List[List[float]]:
        client = self._get_openai_client()
        clean_texts = [t.replace("\n", " ") for t in texts]
        response = client.embeddings.create(input=clean_texts, model=self.model)
        # Ensure ordered results
        return [data.embedding for data in response.data]

    def _embed_ollama(self, text: str) -> List[float]:
        url = f"{self.ollama_base_url}/api/embeddings"
        payload = {"model": self.model, "prompt": text}
        
        response = requests.post(
            url,
            json=payload,
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        body = response.json()
        embedding = body.get("embedding")
        
        if not isinstance(embedding, list):
             raise ValueError(f"Ollama returned unexpected body: {body}")
             
        return [float(v) for v in embedding]

    def _validate_dimension(self, vector: List[float]) -> None:
        dim = len(vector)
        if self._validated_dimension is None:
            if dim != self.expected_dimension:
                logger.warning(
                    f"[MemoryEmbedder] Dimension Warning: Expected {self.expected_dimension}, got {dim}. "
                    f"Updating expectation if this is a migration."
                )
                # In migration scenario, we might accept it if we are flexible, 
                # but usually we want to enforce strictness to avoid pollution.
                # However, raising Error stops everything. 
                # Given strict architecture, we raise.
                raise EmbeddingDimensionError(
                    f"Expected {self.expected_dimension}-dim vector, got {dim}. Provider: {self.provider}"
                )
            self._validated_dimension = dim
        elif dim != self._validated_dimension:
             raise EmbeddingDimensionError(f"Dimension instability: {self._validated_dimension} vs {dim}")
