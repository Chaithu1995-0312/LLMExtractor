import os
from typing import List, Dict
from nexus.vector.local_index import LocalVectorIndex
from nexus.bricks.brick_store import BrickStore
from nexus.vector.embedder import get_embedder
from nexus.rerank.orchestrator import RerankOrchestrator

# Initialize LocalVectorIndex and BrickStore globally or pass them around
# For simplicity and to avoid circular imports during initial setup, we'll initialize here
# In a more complex app, dependency injection would be preferred.
_local_index = LocalVectorIndex()
_brick_store = BrickStore()
_reranker = None
def _normalize_faiss_output(x):
    if x is None:
        return []
    if hasattr(x, "flatten"):
        return x.flatten().tolist()
    if isinstance(x, list):
        return x
    return list(x)

def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = RerankOrchestrator()
    return _reranker
def _normalize_distance_to_confidence(distance: float) -> float:
    # FAISS L2 distance needs to be converted to cosine similarity and then normalized.
    # L2 distance is sqrt(2 * (1 - cos_similarity)). So cos_similarity = 1 - (distance**2) / 2
    # Normalize to 0-1 range. A smaller distance (closer) means higher confidence.
    # The actual range of distances depends on the embeddings. For simplicity, we'll map 
    # 0 distance to 1.0 confidence, and larger distances (up to a heuristic max) to 0.0.
    
    # Heuristic: max_distance observed in some tests, adjust as needed
    # For normalized vectors, L2 distance ranges from 0 (identical) to sqrt(2) (orthogonal) to 2 (opposite)
    # If embeddings are normalized, cos_sim = 1 - (dist^2)/2. So dist^2 = 2 * (1 - cos_sim)
    # cos_sim range [-1, 1], so dist^2 range [0, 4]
    # dist range [0, 2]

    # Map 0 (closest) to 1.0 confidence, 2 (furthest) to 0.0 confidence
    # Linear interpolation: confidence = 1 - (distance / 2)
    # Ensure within 0.0-1.0 bounds
    confidence = 1.0 - (distance / 2.0)
    return max(0.0, min(1.0, confidence))

def recall_bricks(query: str, k: int = 10) -> List[Dict]:
    if _local_index.index.ntotal == 0:
        print("DEBUG FAISS index empty — skipping recall")
        return []
    embedder = get_embedder()
    query_vec = embedder.embed_query(query)
    print("DEBUG query vector shape =", query_vec.shape)
    print("DEBUG index dim =", _local_index.index.d)
    distances, indices = _local_index.search(query_vec, k)
    
    candidates = []
    flat_indices = _normalize_faiss_output(indices)
    flat_distances = _normalize_faiss_output(distances)

    for i, idx in enumerate(flat_indices):
        if idx != -1 and idx < len(_local_index.brick_ids):
            brick_id = _local_index.brick_ids[idx]
            confidence = _normalize_distance_to_confidence(flat_distances[i])
            
            # Hydrate with text for reranker
            brick_text = _brick_store.get_brick_text(brick_id)
            metadata = _brick_store.get_brick_metadata(brick_id)
            
            # Bug Fix: Priority Scoping
            # Narrower scopes (e.g. project-specific) get a priority boost.
            # Global or broad scopes have lower priority.
            priority_boost = 0.0
            if metadata and "scope" in metadata:
                scope = metadata["scope"].lower()
                if scope != "global":
                    priority_boost = 0.1 # Boost non-global intents
            
            candidates.append({
                "brick_id": brick_id,
                "base_confidence": confidence + priority_boost,
                "brick_text": brick_text if brick_text else "",
                "scope": metadata.get("scope") if metadata else "global"
            })
            
    # Apply Reranker
    reranked_results = get_reranker().rerank(query, candidates)

    
    # Map back to expected output format
    results = []
    for res in reranked_results:
        results.append({
            "brick_id": res["brick_id"],
            "confidence": res.get("final_score", res["base_confidence"]),
            "reranker_used": res.get("reranker_used", "none")
        })
            
    return results

def recall_bricks_readonly(query: str, k: int = 10) -> List[Dict]:
    print("DEBUG recall invoked, query =", query)
    import os
    print("DEBUG CWD:", os.getcwd())


    # This is essentially the same as recall_bricks, but explicitly marked as read-only
    # and intended for use by Cortex to prevent direct Nexus imports.
    # It ensures no mutation or side effects occur.
    return recall_bricks(query, k)

def get_recall_brick_metadata(brick_id: str) -> Dict | None:
    """
    Return metadata for a recall brick produced by FAISS.
    Must include:
      - source_file
      - source_span { message_id, block_index }
    Read-only. No persistence.
    """
    # Reuse the same loaded metadata store that recall_bricks depends on
    return _brick_store.get_brick_metadata(brick_id)
