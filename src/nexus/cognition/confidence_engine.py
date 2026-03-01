import numpy as np
from typing import Dict, Any, List, Optional
from nexus.vector.embedding_service import EmbeddingService

# Retrieval confidence gate threshold constants.
# Gate pass = retrieval_confidence >= RETRIEVAL_CONFIDENCE_MIN
RETRIEVAL_CONFIDENCE_MIN: float = 0.40   # below this → block generation
RETRIEVAL_AMBIGUITY_EPSILON: float = 1e-9


class ConfidenceEngine:
    """
    Computes composite confidence scores for cognitive outputs.
    Combines Model Self-Report (M), Structural Validity (S), Embedding Alignment (E), and Consistency (C).

    Also provides compute_retrieval_confidence() for Memory Layer gating —
    the single source of epistemic policy for all retrieval quality decisions.
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

    def compute_retrieval_confidence(
        self,
        top_score: float,
        all_scores: List[float],
        retrieved_texts: List[str],
        query_text: str,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Computes composite retrieval confidence for Memory Layer gating.

        This is the single epistemic authority for deciding whether retrieved
        context is strong enough to justify LLM generation. Memory Layer callers
        MUST NOT define their own thresholds — they delegate here.

        Components:
          M (top_score):  Normalised top chunk cosine similarity [0,1].
                          Already normalised by ChromaMemoryVectorStore:
                          score = 1 - (chroma_distance / 2).
          S (margin):     Score gap between top-1 and top-2 chunks,
                          normalized. Low margin → ambiguous retrieval.
                          Mirrors ambiguity_margin_threshold logic from
                          sync/router.py._select_primary().
          E (alignment):  Average embedding cosine sim between query and
                          top-3 retrieved texts. Uses _compute_embedding_score().
          C (coverage):   Ratio of chunks at or above 0.5 score (decent recall).

        Formula: (0.35*M) + (0.25*S) + (0.25*E) + (0.15*C)

        Args:
            top_score:        Highest score from RetrievalResult (already [0,1]).
            all_scores:       All chunk scores from RetrievalResult.
            retrieved_texts:  Text content of top chunks (used for alignment).
            query_text:       Original query string (used for alignment).
            threshold:        Override gate threshold. Defaults to
                              RETRIEVAL_CONFIDENCE_MIN if not provided.

        Returns:
            {
              "retrieval_confidence": float,   # composite [0,1]
              "gate_pass":            bool,    # True → safe to generate
              "threshold_used":       float,
              "components": {
                "M": float,   # top score
                "S": float,   # margin score
                "E": float,   # embedding alignment
                "C": float,   # coverage ratio
              },
              "diagnostics": {
                "chunk_count":   int,
                "mean_score":    float,
                "top_score":     float,
                "score_margin":  float,
              }
            }
        """
        gate_threshold = threshold if threshold is not None else RETRIEVAL_CONFIDENCE_MIN

        # ── Guard: no chunks returned ──────────────────────────────────────
        if not all_scores:
            return {
                "retrieval_confidence": 0.0,
                "gate_pass": False,
                "threshold_used": gate_threshold,
                "components": {"M": 0.0, "S": 0.0, "E": 0.0, "C": 0.0},
                "diagnostics": {
                    "chunk_count": 0,
                    "mean_score": 0.0,
                    "top_score": 0.0,
                    "score_margin": 0.0,
                },
            }

        # ── Component M: top score (already [0,1]) ─────────────────────────
        m_score = float(top_score)

        # ── Component S: score gap (ambiguity margin) ──────────────────────
        sorted_scores = sorted(all_scores, reverse=True)
        second_score = sorted_scores[1] if len(sorted_scores) > 1 else 0.0
        score_margin = (m_score - second_score) / (m_score + RETRIEVAL_AMBIGUITY_EPSILON)
        s_score = float(score_margin)

        # ── Component E: embedding alignment (query vs top-3 texts) ────────
        e_score = 0.5  # neutral fallback
        if query_text and retrieved_texts:
            top_texts = retrieved_texts[:3]
            alignment_scores = []
            for txt in top_texts:
                try:
                    sim = self._compute_embedding_score(query_text, txt)
                    alignment_scores.append(sim)
                except Exception:
                    alignment_scores.append(0.5)
            e_score = sum(alignment_scores) / max(len(alignment_scores), 1)

        # ── Component C: coverage ratio (chunks >= 0.5 threshold) ──────────
        decent_chunks = sum(1 for s in all_scores if s >= 0.5)
        c_score = decent_chunks / max(len(all_scores), 1)

        # ── Composite ──────────────────────────────────────────────────────
        final = (
            (0.35 * m_score) +
            (0.25 * s_score) +
            (0.25 * e_score) +
            (0.15 * c_score)
        )
        final = round(min(max(final, 0.0), 1.0), 4)

        mean_score = sum(all_scores) / len(all_scores)

        return {
            "retrieval_confidence": final,
            "gate_pass": final >= gate_threshold,
            "threshold_used": gate_threshold,
            "components": {
                "M": round(m_score, 4),
                "S": round(s_score, 4),
                "E": round(e_score, 4),
                "C": round(c_score, 4),
            },
            "diagnostics": {
                "chunk_count": len(all_scores),
                "mean_score": round(mean_score, 6),
                "top_score": round(m_score, 6),
                "score_margin": round(score_margin, 6),
            },
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
