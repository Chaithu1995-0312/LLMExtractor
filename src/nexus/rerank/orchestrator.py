from typing import List, Dict
import logging

from .llm_reranker import LlmReranker
from .cross_encoder import CrossEncoderReranker
from .heuristic import HeuristicReranker

class RerankOrchestrator:
    """
    Manages the 3-stage reranking pipeline.
    Try (2) LLM -> (1) CrossEncoder -> (3) Heuristic
    """
    def __init__(self):
        self.primary = None
        self.secondary = None
        self.tertiary = HeuristicReranker() # Always safe
        
        # Try loading Primary
        try:
            self.primary = LlmReranker()
        except Exception:
            # Silent fallback during init
            pass
            
        # Try loading Secondary
        try:
            self.secondary = CrossEncoderReranker()
        except Exception:
            # Silent fallback during init
            pass

    def rerank(self, query: str, candidates: List[Dict]) -> List[Dict]:
        """
        Executes reranking with fallback logic.
        """
        if not candidates:
            return candidates

        # 1. Try Primary (LLM)
        if self.primary:
            try:
                return self.primary.rank(query, candidates)
            except Exception:
                # Fallback to next
                pass
                
        # 2. Try Secondary (CrossEncoder)
        if self.secondary:
            try:
                return self.secondary.rank(query, candidates)
            except Exception:
                # Fallback to next
                pass
                
        # 3. Fallback to Tertiary (Heuristic)
        return self.tertiary.rank(query, candidates)
