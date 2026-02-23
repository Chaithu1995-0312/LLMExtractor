import numpy as np
from nexus.vector.embedder import VectorEmbedder

class EmbeddingService:
    """
    Deterministic embedding service for drift detection.
    Wraps the underlying VectorEmbedder to enforce a strict contract.
    """
    def __init__(self):
        # We hardcode the model name here to ensure consistency across the drift engine.
        # VectorEmbedder handles the singleton/shared model loading.
        self.model_name = "all-MiniLM-L6-v2"
        self._embedder = VectorEmbedder(self.model_name)

    def embed(self, text: str) -> np.ndarray:
        """
        Embeds a single string into a 1D float32 numpy array.
        Uses the 'query' mode of the underlying embedder (though for symmetric models like MiniLM it's often the same).
        """
        # embed_query returns a 1xN array, we flatten it to N
        vector = self._embedder.embed_query(text, use_genai=False)
        return vector.flatten().astype("float32")

    def model_version(self) -> str:
        """
        Returns the version string of the model being used.
        This allows the system to detect when a re-index is required.
        """
        return self.model_name
