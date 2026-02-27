import os
import json
import numpy as np
import pickle
from typing import List, Tuple, Dict, Optional

class VectorStore:
    """
    Singleton FAISS wrapper for persistent vector storage.
    """
    _instance = None
    
    INDEX_FILE = "data/vector_index.faiss"
    ID_MAP_FILE = "data/vector_ids.pkl"
    DIMENSION = 384

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorStore, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss-cpu not installed. Please run: pip install faiss-cpu")

        self.index = None
        self.id_map: Dict[str, int] = {} # node_id -> faiss_internal_id
        self.reverse_id_map: Dict[int, str] = {} # faiss_internal_id -> node_id
        self.next_id = 0
        
        # Create data directory if not exists
        os.makedirs(os.path.dirname(self.INDEX_FILE), exist_ok=True)
        
        self._load()

    def _load(self):
        import faiss
        if os.path.exists(self.INDEX_FILE) and os.path.exists(self.ID_MAP_FILE):
            print(f"[VectorStore] Loading index from {self.INDEX_FILE}")
            self.index = faiss.read_index(self.INDEX_FILE)
            with open(self.ID_MAP_FILE, "rb") as f:
                self.id_map, self.reverse_id_map, self.next_id = pickle.load(f)
        else:
            print("[VectorStore] Creating new index")
            # Inner Product (IP) index for cosine similarity on normalized vectors
            self.index = faiss.IndexFlatIP(self.DIMENSION)
            self.id_map = {}
            self.reverse_id_map = {}
            self.next_id = 0

    def save(self):
        import faiss
        if self.index:
            faiss.write_index(self.index, self.INDEX_FILE)
            with open(self.ID_MAP_FILE, "wb") as f:
                pickle.dump((self.id_map, self.reverse_id_map, self.next_id), f)
            # print(f"[VectorStore] Index saved to {self.INDEX_FILE}")

    def exists(self, node_id: str) -> bool:
        return node_id in self.id_map

    def add(self, node_id: str, vector: np.ndarray):
        """
        Adds a vector to the index. Idempotent: if node_id exists, it is NOT updated (for Phase 1).
        """
        if self.exists(node_id):
            return # Already indexed

        if vector.shape != (self.DIMENSION,):
            raise ValueError(f"Vector dimension mismatch. Expected {self.DIMENSION}, got {vector.shape}")

        # Reshape for FAISS (1, D)
        vector_reshaped = vector.reshape(1, -1)
        
        self.index.add(vector_reshaped)
        
        # Update mappings
        internal_id = self.next_id
        self.id_map[node_id] = internal_id
        self.reverse_id_map[internal_id] = node_id
        self.next_id += 1
        
        # Auto-save (for safety in Phase 1)
        if self.next_id % 10 == 0:
            self.save()

    def get_vector(self, node_id: str) -> Optional[np.ndarray]:
        """
        Retrieve the stored vector for a node_id directly from the FAISS index.

        Phase 2: Used by DriftEngine.process_node so that drift processing
        reads the pre-built vector rather than re-embedding the statement.
        This preserves the invariant that EmbeddingService is only called
        from index_node — never from the drift path.

        Returns None if the node is not indexed (rather than raising), so
        callers can guard cleanly.

        Note: faiss.IndexFlatIP inherits from IndexFlat which supports
        reconstruct(). This returns an exact copy of the stored vector.
        """
        if node_id not in self.id_map:
            return None
        internal_id = self.id_map[node_id]
        try:
            vector = self.index.reconstruct(internal_id)
            return vector.astype(np.float32)
        except Exception as e:
            print(f"[VectorStore] WARN: reconstruct({node_id}) failed: {e}")
            return None

    def search(self, vector: np.ndarray, k: int = 10) -> List[Tuple[str, float]]:
        """
        Search for top-k similar vectors.
        Returns list of (node_id, score).
        """
        if self.index.ntotal == 0:
            return []

        if vector.shape != (self.DIMENSION,):
             raise ValueError(f"Vector dimension mismatch. Expected {self.DIMENSION}, got {vector.shape}")

        vector_reshaped = vector.reshape(1, -1)
        
        # D is distances (scores), I is indices
        D, I = self.index.search(vector_reshaped, k)
        
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx != -1 and idx in self.reverse_id_map:
                node_id = self.reverse_id_map[idx]
                results.append((node_id, float(score)))
        
        return results
