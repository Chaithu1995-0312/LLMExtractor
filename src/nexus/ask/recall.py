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

def recall_bricks(query: str, k: int = 10, allowed_scopes: List[str] = ["global"]) -> List[Dict]:
    if _local_index.index.ntotal == 0:
        print("DEBUG FAISS index empty — skipping recall")
        return []
        
    embedder = get_embedder()
    query_vec = embedder.embed_query(query)
    # Oversampling for post-filtering ACLs
    oversample_k = k * 5
    
    # print("DEBUG query vector shape =", query_vec.shape)
    # print("DEBUG index dim =", _local_index.index.d)
    
    distances, indices = _local_index.search(query_vec, oversample_k)
    
    candidates = []
    flat_indices = _normalize_faiss_output(indices)
    flat_distances = _normalize_faiss_output(distances)

    allowed_scopes_set = set(s.lower() for s in allowed_scopes)

    for i, idx in enumerate(flat_indices):
        if idx != -1 and idx < len(_local_index.brick_ids):
            brick_id = _local_index.brick_ids[idx]
            
            # Hydrate metadata first for filtering
            metadata = _brick_store.get_brick_metadata(brick_id)
            brick_scope = (metadata.get("scope", "global") if metadata else "global").lower()
            
            # ACL Enforcement
            if brick_scope not in allowed_scopes_set:
                continue

            confidence = _normalize_distance_to_confidence(flat_distances[i])
            brick_text = _brick_store.get_brick_text(brick_id)
            
            # Priority Scoping
            priority_boost = 0.0
            if brick_scope != "global":
                priority_boost = 0.1 # Boost allowed non-global intents
            
            candidates.append({
                "brick_id": brick_id,
                "base_confidence": confidence + priority_boost,
                "brick_text": brick_text if brick_text else "",
                "scope": brick_scope
            })
            
    # Minimum Yield Check
    if len(candidates) < k:
        print(f"WARNING: ACL Filtering reduced candidates to {len(candidates)} (requested {k}).")

    # Limit to top k * 2 before reranking to save compute, or just rerank all filtered
    # Reranking is expensive, so let's cap it at a reasonable number if oversampling found many
    candidates_to_rerank = candidates[:k*2] # Only rerank the best vector matches that passed ACL
            
    # Apply Reranker
    reranked_results = get_reranker().rerank(query, candidates_to_rerank)

    # Map back and slice to k
    results = []
    for res in reranked_results:
        results.append({
            "brick_id": res["brick_id"],
            "confidence": res.get("final_score", res["base_confidence"]),
            "reranker_used": res.get("reranker_used", "none")
        })
            
    return results[:k]

def recall_bricks_readonly(query: str, k: int = 10, allowed_scopes: List[str] = ["global"]) -> List[Dict]:
    # print("DEBUG recall invoked, query =", query)
    
    # This is essentially the same as recall_bricks, but explicitly marked as read-only
    # and intended for use by Cortex to prevent direct Nexus imports.
    # It ensures no mutation or side effects occur.
    return recall_bricks(query, k, allowed_scopes)

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

def get_related_intents(brick_ids: List[str]) -> List[str]:
    """
    Graph Traversal: Find Intents or Artifacts derived from these bricks.
    Returns a list of formatted context strings.
    """
    if not brick_ids:
        return []
    
    # Lazy import to avoid circular dependencies
    try:
        from nexus.graph.manager import GraphManager
        from nexus.graph.schema import EdgeType
    except ImportError:
        # Fallback if graph module not available or path issues
        return []
    
    graph = GraphManager()
    related_context = []
    seen_ids = set()
    
    for bid in brick_ids:
        # Get incoming edges (Source -> Target=Brick)
        # Note: DERIVED_FROM is Intent -> Source(Brick)
        edges = graph.get_edges_for_node(bid)
        for edge in edges:
            # Check for incoming DERIVED_FROM edges
            if edge.edge_type == EdgeType.DERIVED_FROM and edge.target_id == bid:
                source_id = edge.source_id
                if source_id in seen_ids:
                    continue
                seen_ids.add(source_id)
                
                node_info = graph.get_node(source_id)
                if not node_info:
                    continue
                    
                node_type, node_data = node_info
                
                if node_type == "intent":
                    stmt = node_data.get("statement", "")
                    lifecycle = node_data.get("lifecycle", "loose")
                    if stmt:
                        related_context.append(f"[Verified Intent ({lifecycle})]: {stmt}")
                        
                elif node_type == "artifact":
                    # Extract facts from artifact payload
                    payload = node_data.get("payload", {})
                    facts = payload.get("extracted_facts", [])
                    topic = node_data.get("topic", "Unknown Topic")
                    
                    if facts:
                        # Limit facts to avoid context explosion
                        fact_str = "; ".join(facts[:3]) 
                        if len(facts) > 3:
                            fact_str += f"... (+{len(facts)-3} more)"
                        related_context.append(f"[Artifact '{topic}']: {fact_str}")

    return list(set(related_context))
