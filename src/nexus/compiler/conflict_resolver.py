from typing import List, Dict, Any, Optional
from enum import Enum

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

        # Sort by priority descending and then by ID for deterministic tie-breaking
        # IDs are used instead of created_at to ensure absolute determinism across environments
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
        Detection logic for contradictory bricks.
        For Phase 2, this is a placeholder for semantic contradiction detection.
        Currently returns empty list as 'unresolved' items are marked in GAPS_AND_RISKS.md
        """
        return []
