import numpy as np
from typing import Dict, Any, List, Optional
from nexus.vector.embedding_service import EmbeddingService

class ConfidenceEngine:
    """
    Computes composite confidence scores for cognitive outputs.
    Combines Model Self-Report (M), Structural Validity (S), Embedding Alignment (E), and Consistency (C).
    """

    def __init__(self):
        self.embedding_service = EmbeddingService()

    def compute_l2_confidence(
        self,
        model_confidence: float,
        explanation: str,
        input_text_old: str,
        input_text_new: str,
        consistency_text: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Computes composite confidence for L2 Narrator (Supersession).
        Formula: (0.35*M) + (0.35*S) + (0.20*E) + (0.10*C)
        """
        # 1. Structural Score (S)
        s_score = self._compute_structural_score_l2(input_text_old, input_text_new, explanation)
        
        # 2. Embedding Score (E)
        e_score = self._compute_embedding_score(explanation, input_text_new)

        # 3. Consistency Score (C)
        c_score = 0.0
        if consistency_text:
            c_score = self._compute_embedding_score(explanation, consistency_text)
        else:
            c_score = model_confidence 

        # Composite Calculation
        final = (0.35 * model_confidence) + (0.35 * s_score) + (0.20 * e_score) + (0.10 * c_score)
        
        return {
            "final_confidence": round(final, 4),
            "components": {
                "M": model_confidence,
                "S": round(s_score, 4),
                "E": round(e_score, 4),
                "C": round(c_score, 4)
            }
        }

    def compute_l3_confidence(
        self,
        model_confidence: float,
        analysis: str,
        metrics_summary: str,
        consistency_text: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Computes composite confidence for L3 Sage (Audit).
        Weights Adjusted: M: 0.20, S: 0.20, E: 0.35, C: 0.25
        Embedding alignment is prioritized for strategic reasoning.
        """
        # 1. Structural/Logical Score (S)
        s_score = self._compute_keyword_overlap(analysis, metrics_summary)

        # 2. Embedding Score (E)
        e_score = self._compute_embedding_score(analysis, metrics_summary)

        # 3. Consistency Score (C)
        c_score = 0.0
        if consistency_text:
             c_score = self._compute_embedding_score(analysis, consistency_text)
        else:
             c_score = model_confidence

        final = (0.20 * model_confidence) + (0.20 * s_score) + (0.35 * e_score) + (0.25 * c_score)

        return {
            "final_confidence": round(final, 4),
            "components": {
                "M": model_confidence,
                "S": round(s_score, 4),
                "E": round(e_score, 4),
                "C": round(c_score, 4)
            }
        }

    def _compute_structural_score_l2(self, old: str, new: str, explanation: str) -> float:
        """
        L2 Structural Heuristics (0.0 Baseline):
        - Containment: Does new text strictly contain old text?
        - Token Overlap: Does explanation use words from the content delta?
        """
        # A. Containment Check
        is_refinement = old in new
        
        # B. Token Overlap between Explanation and (New - Old) Diff
        old_tokens = set(old.lower().split())
        new_tokens = set(new.lower().split())
        exp_tokens = set(explanation.lower().split())
        
        diff_tokens = new_tokens - old_tokens
        if not diff_tokens:
             diff_tokens = new_tokens

        overlap_count = len(diff_tokens.intersection(exp_tokens))
        overlap_ratio = overlap_count / max(len(diff_tokens), 1)
        
        # Score calculation from 0.0 baseline
        score = 0.3 * (1.0 if is_refinement else 0.0) + (0.7 * overlap_ratio)
            
        return min(score, 1.0)

    def _compute_keyword_overlap(self, analysis: str, summary: str) -> float:
        # Simple Jaccard-ish proxy
        a_tokens = set(analysis.lower().split())
        s_tokens = set(summary.lower().split())
        
        common = a_tokens.intersection(s_tokens)
        return len(common) / max(len(s_tokens), 1)

    def _compute_embedding_score(self, text1: str, text2: str) -> float:
        """
        Computes normalized cosine similarity [0, 1].
        """
        if not text1 or not text2:
            return 0.5 # Neutral fallback
            
        try:
            vec1 = self.embedding_service.embed(text1)
            vec2 = self.embedding_service.embed(text2)
            
            dot = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.5
                
            cosine = float(dot / (norm1 * norm2))
            # Normalize [-1, 1] -> [0, 1]
            return (cosine + 1.0) / 2.0
        except Exception as e:
            print(f"[ConfidenceEngine] Embedding error: {e}")
            return 0.5
