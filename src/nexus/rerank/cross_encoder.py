from typing import List, Dict

class CrossEncoderReranker:
    """
    Secondary reranker (Fallback).
    Uses sentence-transformers CrossEncoder.
    """
    def __init__(self):
        try:
            from sentence_transformers import CrossEncoder
            import torch
            # Lightweight model, deterministic on CPU
            torch.manual_seed(42)
            self.model = CrossEncoder('cross-encoder/ms-marco-TinyBERT-L-2-v2') 
        except ImportError:
            raise ImportError("sentence_transformers or torch not installed")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize CrossEncoder: {e}")

    def rank(self, query: str, candidates: List[Dict]) -> List[Dict]:
        """
        Ranks candidates using CrossEncoder.
        """
        if not candidates:
            return candidates
            
        # Prepare pairs
        pairs = [[query, c.get("brick_text", "")] for c in candidates]
        
        # Predict (batch process)
        import numpy as np
        scores = self.model.predict(pairs)
        if isinstance(scores, float): # Handle single result case if it happens
            scores = np.array([scores])
        
        # Normalize scores to [0, 1] for consistency
        # Logits can be anything, but we want a confident float.
        # Sigmoid is standard for cross-encoder logits if not already applied.
        # But for ranking, relative order matters. We'll do simple MinMax over the batch.
        
        if len(scores) > 0:
            min_s = float(min(scores))
            max_s = float(max(scores))
            range_s = max_s - min_s
            
            for i, cand in enumerate(candidates):
                raw_score = float(scores[i])
                if range_s > 0:
                    norm_score = (raw_score - min_s) / range_s
                else:
                    norm_score = 0.5
                
                cand["final_score"] = norm_score
                cand["reranker_used"] = "cross_encoder"
        
        # Sort
        candidates.sort(key=lambda x: x["final_score"], reverse=True)
        return candidates
