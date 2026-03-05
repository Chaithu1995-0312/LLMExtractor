from typing import List, Dict, Any, Optional
from enum import Enum
import numpy as np
from nexus.memory.embedder import MemoryEmbedder

class Lifecycle(Enum):
    LOOSE = "Loose"
    FORMING = "Forming"
    FROZEN = "Frozen"
    KILLED = "Killed"

class ConflictResolver:
    """
    Deterministic Conflict Resolver for Nexus Topics.
    Priority Order:
    1. Frozen Brick
    2. Hard Anchor
    3. Soft Anchor
    4. Pure semantic recall
    """

    def __init__(self):
        self.priority_map = {
            Lifecycle.FROZEN.value: 4,
            "hard_anchor": 3,
            "soft_anchor": 2,
            Lifecycle.FORMING.value: 1,
            Lifecycle.LOOSE.value: 0
        }
        self.embedder = MemoryEmbedder()

    def resolve(self, bricks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Resolves conflicts among a set of bricks.
        If contradictions exist, Frozen wins.
        Returns a structured object with resolved bricks and identified conflicts.
        """
        if not bricks:
            return {"resolved_bricks": [], "conflicts": []}

        conflicts = []
        # Detect Contradictions among Frozen bricks
        frozen_bricks = [b for b in bricks if b.get("lifecycle") == Lifecycle.FROZEN.value]
        
        if len(frozen_bricks) > 1:
            conflicts.append({
                "type": "MULTI_FROZEN",
                "brick_ids": sorted([b.get("id") for b in frozen_bricks])
            })

        # Detect semantic contradictions
        semantic_conflicts = self.detect_contradictions(bricks)
        conflicts.extend(semantic_conflicts)

        # Sort by priority descending and then by ID for deterministic tie-breaking
        sorted_bricks = sorted(
            bricks,
            key=lambda x: (
                self.priority_map.get(x.get("lifecycle", Lifecycle.LOOSE.value), 0),
                x.get("id", "")
            ),
            reverse=True
        )

        return {
            "resolved_bricks": sorted_bricks,
            "conflicts": conflicts
        }

    def detect_contradictions(self, bricks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        L2.2 Semantic Conflict Detection.
        Uses embeddings to find semantically similar but potentially contradictory bricks.
        """
        if len(bricks) < 2:
            return []

        conflicts = []
        # 1. Embed all bricks
        embeddings = []
        for b in bricks:
            text = b.get("statement") or b.get("content") or ""
            embeddings.append(self.embedder.embed(text))

        # 2. Pairwise similarity check
        for i in range(len(bricks)):
            for j in range(i + 1, len(bricks)):
                sim = self._cosine_similarity(embeddings[i], embeddings[j])
                
                # High similarity threshold for contradiction candidates
                if sim > 0.92:
                    text_i = (bricks[i].get("statement") or "").lower()
                    text_j = (bricks[j].get("statement") or "").lower()
                    
                    # Heuristic for negation/contradiction
                    negations = ["not ", "never ", "instead of ", "rather than "]
                    has_negation = any(n in text_i for n in negations) != any(n in text_j for n in negations)
                    
                    if has_negation:
                        conflicts.append({
                            "type": "SEMANTIC_CONTRADICTION",
                            "brick_ids": sorted([bricks[i]["id"], bricks[j]["id"]]),
                            "similarity": float(sim),
                            "reason": f"High similarity ({sim:.4f}) with contradictory negations detected."
                        })

        return conflicts

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        a = np.array(v1)
        b = np.array(v2)
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0:
            return 0.0
        return np.dot(a, b) / denom
