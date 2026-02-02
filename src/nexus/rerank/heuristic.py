import re
from typing import List, Dict

class HeuristicReranker:
    """
    Tertiary reranker (Safety Net).
    Uses token overlap and span proximity.
    Always available, zero dependencies.
    """
    
    def rank(self, query: str, candidates: List[Dict]) -> List[Dict]:
        """
        Ranks candidates based on heuristic signals.
        Returns modified list with 'final_score' and 'reranker_used'.
        """
        query_tokens = set(re.findall(r'\w+', query.lower()))
        
        for cand in candidates:
            text = cand.get("brick_text", "").lower()
            score = 0.0
            
            # 1. Token Overlap
            # Simple intersection count
            tokens = set(re.findall(r'\w+', text))
            overlap = query_tokens.intersection(tokens)
            # Normalize by query length to keep somewhat bounded
            if query_tokens:
                score += (len(overlap) / len(query_tokens)) * 0.5
            
            # 2. Exact Phrase Match (Boost)
            if query.lower() in text:
                score += 0.4
                
            # 3. Base Confidence Preservation (small factor)
            # If heuristic is weak, trust original vector recall slightly
            score += cand.get("base_confidence", 0.0) * 0.1
                
            # Clamp to [0, 1]
            cand["final_score"] = max(0.0, min(1.0, score))
            cand["reranker_used"] = "heuristic"
            
        # Sort descending by score
        candidates.sort(key=lambda x: x["final_score"], reverse=True)
        return candidates
