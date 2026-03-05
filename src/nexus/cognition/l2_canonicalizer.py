import numpy as np
from typing import List, Dict, Optional, Tuple
from nexus.memory.embedder import MemoryEmbedder
from nexus.db import get_adapter
from nexus.graph.schema import Topic
import json
import uuid

class L2Canonicalizer:
    """
    Canonical Topic Resolver (L2.1).
    Prevents topic explosion by merging semantically similar topic names.
    """
    def __init__(self, similarity_threshold: float = 0.85):
        self.embedder = MemoryEmbedder()
        self.db = get_adapter()
        self.threshold = similarity_threshold

    def resolve_topic(self, topic_name: str) -> str:
        """
        Resolves a raw topic name to a Canonical Topic ID.
        """
        # 1. Embed the input topic name
        query_vec = self.embedder.embed(topic_name)
        
        # 2. Fetch all canonical topics from DB
        # Topic nodes have type='topic' and data->>'canonical_name' is not null
        rows = self.db.fetch_all("""
            SELECT id, data FROM graph.nodes WHERE type = 'topic'
        """)
        
        best_match_id = None
        max_sim = -1.0
        
        for topic_id, data_raw in rows:
            data = data_raw if isinstance(data_raw, dict) else json.loads(data_raw)
            canonical_vec = data.get("embedding")
            
            if canonical_vec:
                sim = self._cosine_similarity(query_vec, canonical_vec)
                if sim > max_sim:
                    max_sim = sim
                    best_match_id = topic_id
        
        # 3. Check against threshold
        if max_sim >= self.threshold:
            print(f"[L2.1] Merging '{topic_name}' into existing topic {best_match_id} (sim: {max_sim:.4f})")
            return best_match_id
        
        # 4. Create new Canonical Topic
        new_topic_id = f"topic_{str(uuid.uuid4())[:8]}"
        print(f"[L2.1] Creating new Canonical Topic: '{topic_name}' (id: {new_topic_id})")
        
        new_topic_data = {
            "name": topic_name,
            "canonical_name": topic_name,
            "embedding": query_vec,
            "metadata": {"auto_generated": True}
        }
        
        self.db.execute(
            "INSERT INTO graph.nodes (id, type, data, created_at) VALUES (%s, 'topic', %s, NOW())",
            (new_topic_id, json.dumps(new_topic_data))
        )
        
        return new_topic_id

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        a = np.array(v1)
        b = np.array(v2)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
