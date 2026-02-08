import os
from typing import List, Dict, Optional
from nexus.vector.local_index import LocalVectorIndex
from nexus.bricks.brick_store import BrickStore
from nexus.vector.embedder import get_embedder
from nexus.rerank.orchestrator import RerankOrchestrator

# Initialize LocalVectorIndex and BrickStore globally or pass them around
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
    # Map 0 (closest) to 1.0 confidence, 2 (furthest) to 0.0 confidence
    confidence = 1.0 - (distance / 2.0)
    return max(0.0, min(1.0, confidence))

def get_scope_hierarchy(gm, scope_id: str) -> List[str]:
    """Recursively fetch the parent scope hierarchy for a given scope."""
    hierarchy = [scope_id]
    edges = gm.get_edges_for_node(scope_id)
    for e in edges:
        # P4.3 Hierarchical Inheritance
        if e.target_id != scope_id and e.metadata.get("rel") == "parent":
             hierarchy.extend(get_scope_hierarchy(gm, e.target_id))
    return hierarchy

def recall_bricks(query: str, k: int = 10, allowed_scopes: List[str] = ["global"], use_genai: bool = False) -> List[Dict]:
    """
    Standard Recall: Vector Search + Hierarchical ACL Filtering + Reranking.
    """
    if _local_index.index.ntotal == 0:
        return []
        
    from nexus.graph.manager import GraphManager
    gm = GraphManager()
    
    # 1. Resolve Effective Scopes (Hierarchical Inheritance)
    effective_scopes = set(s.lower() for s in allowed_scopes)
    if allowed_scopes:
        for s_id in allowed_scopes:
            if s_id.lower() != "global":
                effective_scopes.update(s.lower() for s in get_scope_hierarchy(gm, s_id))

    embedder = get_embedder()
    query_vec = embedder.embed_query(query, use_genai=use_genai)
    oversample_k = k * 5
    
    distances, indices = _local_index.search(query_vec, oversample_k)
    
    candidates = []
    flat_indices = _normalize_faiss_output(indices)
    flat_distances = _normalize_faiss_output(distances)

    for i, idx in enumerate(flat_indices):
        if idx != -1 and idx < len(_local_index.brick_ids):
            brick_id = _local_index.brick_ids[idx]
            
            metadata = _brick_store.get_brick_metadata(brick_id)
            brick_scope = (metadata.get("scope", "global") if metadata else "global").lower()
            
            # ACL Enforcement (Strict or Global)
            if brick_scope != "global" and brick_scope not in effective_scopes:
                continue

            confidence = _normalize_distance_to_confidence(flat_distances[i])
            brick_text = _brick_store.get_brick_text(brick_id)
            
            candidates.append({
                "brick_id": brick_id,
                "base_confidence": confidence,
                "brick_text": brick_text if brick_text else "",
                "scope": brick_scope
            })
            
    # Reranking
    candidates_to_rerank = candidates[:k*2]
    reranked_results = get_reranker().rerank(query, candidates_to_rerank)

    results = []
    for res in reranked_results:
        results.append({
            "brick_id": res["brick_id"],
            "confidence": res.get("final_score", res["base_confidence"]),
            "reranker_used": res.get("reranker_used", "none")
        })
            
    return results[:k]

def recall_bricks_readonly(query: str, k: int = 10, allowed_scopes: List[str] = ["global"], use_genai: bool = False) -> List[Dict]:
    return recall_bricks(query, k, allowed_scopes, use_genai=use_genai)

def get_recall_brick_metadata(brick_id: str) -> Optional[Dict]:
    return _brick_store.get_brick_metadata(brick_id)

def get_related_intents(brick_ids: List[str]) -> List[str]:
    """Graph Traversal: Find Intents or Artifacts related to these bricks."""
    if not brick_ids:
        return []
    
    try:
        from nexus.graph.manager import GraphManager
        from nexus.graph.schema import EdgeType
    except ImportError:
        return []
    
    graph = GraphManager()
    related_context = []
    seen_ids = set()
    
    for bid in brick_ids:
        edges = graph.get_edges_for_node(bid)
        for edge in edges:
            # Topic Neighbors
            neighbor_id = edge.target_id if edge.source_id == bid else edge.source_id
            if neighbor_id in seen_ids: continue
            seen_ids.add(neighbor_id)
            
            node_info = graph.get_node(neighbor_id)
            if not node_info: continue
            node_type, node_data = node_info
            
            if node_type == "intent":
                stmt = node_data.get("statement", "")
                if stmt: related_context.append(f"[Graph Intent]: {stmt}")
            elif node_type == "topic":
                # Topic expansion
                topic_intents = graph.get_intents_by_topic(neighbor_id)
                for ti in topic_intents:
                    related_context.append(f"[Graph Topic Intent]: {ti.statement}")

    return list(set(related_context))
