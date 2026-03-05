import os
import numpy as np
from typing import List, Optional
import logging
from nexus.memory.embedder import MemoryEmbedder

class VectorEmbedder:
    """
    Handles text embedding generation using MemoryEmbedder (Ollama).
    Standardized on 768 dimensions (nomic-embed-text).
    """
    _shared_embedder = None

    def __init__(self, model_name: str = "nomic-embed-text"):
        self.model_name = model_name

    def _get_embedder(self):
        if VectorEmbedder._shared_embedder is None:
            try:
                print(f"Initializing MemoryEmbedder with model: {self.model_name} ...")
                VectorEmbedder._shared_embedder = MemoryEmbedder(model=self.model_name)
            except Exception as e:
                print(f"Error initializing MemoryEmbedder: {e}")
                raise
        return VectorEmbedder._shared_embedder

    def _rewrite_with_llm(self, original_query: str) -> str:
        """
        Optional GENAI call to expand or refine the query.
        """
        # Kept for compatibility, though implementation requires OpenAI key which might not be set for local run
        return original_query

    def embed_query(self, query: str, use_genai: bool = False) -> np.ndarray:
        """
        Embeds a single query string into a 1x768 vector.
        """
        search_text = query
        if use_genai:
            search_text = self._rewrite_with_llm(query)

        embedder = self._get_embedder()
        try:
            vector = embedder.embed(search_text)
            return np.array(vector, dtype="float32").reshape(1, -1)
        except Exception as e:
            print(f"Embedding failed: {e}")
            # Return zero vector as fallback or raise?
            # Creating a zero vector of correct dimension
            return np.zeros((1, 768), dtype="float32")

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Embeds a list of texts into a Nx768 matrix.
        """
        if not texts:
            return np.array([], dtype="float32").reshape(0, 768)

        embedder = self._get_embedder()
        
        # MemoryEmbedder.embed_batch handles batching but sequentially for Ollama
        try:
            vectors = embedder.embed_batch(texts)
            # Handle potentially empty results from embed_batch (if text was empty)
            # Replace empty lists with zero vectors
            cleaned_vectors = []
            for v in vectors:
                if v:
                    cleaned_vectors.append(v)
                else:
                    cleaned_vectors.append([0.0] * 768)
            
            return np.array(cleaned_vectors, dtype="float32")
        except Exception as e:
            print(f"Batch embedding failed: {e}")
            return np.zeros((len(texts), 768), dtype="float32")

# Global singleton accessor
def get_embedder():
    return VectorEmbedder()
