import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from nexus.db import get_adapter

class ReflectionEngine:
    """
    Cognitive Reflection Layer (L5).
    Analyzes patterns in user thinking (Idea Gravity, Momentum, Stagnation).
    """
    def __init__(self):
        self.db = get_adapter()

    def analyze_thinking_patterns(self) -> Dict[str, Any]:
        """
        Returns a high-level analysis of thinking patterns.
        """
        print("[L5] Analyzing thinking patterns...")
        
        gravity = self._compute_idea_gravity()
        momentum = self._compute_momentum()
        stagnant = self._detect_stagnant_intents()
        
        return {
            "idea_gravity": gravity,
            "intent_momentum": momentum,
            "stagnant_projects": stagnant,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _compute_idea_gravity(self) -> List[Dict]:
        """
        Which intents attract the most bricks?
        """
        rows = self.db.fetch_all("""
            SELECT n.id, n.data->>'name', m.brick_count
            FROM graph.nodes n
            JOIN graph.intent_metrics m ON n.id = m.intent_id
            WHERE n.type = 'intent'
            ORDER BY m.brick_count DESC
            LIMIT 5
        """)
        
        return [{"id": r[0], "name": r[1], "brick_count": r[2]} for r in rows]

    def _compute_momentum(self) -> List[Dict]:
        """
        Rate of brick addition in the last 7 days.
        """
        # Calculate momentum: bricks added in last 7 days
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        rows = self.db.fetch_all("""
            SELECT e.source_id, n_i.data->>'name', COUNT(e.target_id) as weekly_count
            FROM graph.edges e
            JOIN graph.nodes n_b ON e.target_id = n_b.id
            JOIN graph.nodes n_i ON e.source_id = n_i.id
            WHERE e.edge_type = 'derived_from' 
              AND n_b.type = 'brick' 
              AND n_b.created_at >= %s
            GROUP BY e.source_id, n_i.data->>'name'
            ORDER BY weekly_count DESC
            LIMIT 5
        """, (seven_days_ago,))
        
        return [{"id": r[0], "name": r[1], "weekly_count": r[2]} for r in rows]

    def _detect_stagnant_intents(self) -> List[Dict]:
        """
        Intents with no activity in 30 days but marked as ACTIVE or FORMING.
        """
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        rows = self.db.fetch_all("""
            SELECT n.id, n.data->>'name', m.last_activity
            FROM graph.nodes n
            JOIN graph.intent_metrics m ON n.id = m.intent_id
            WHERE n.type = 'intent' 
              AND n.data->>'lifecycle' IN ('forming', 'active')
              AND m.last_activity < %s
        """, (thirty_days_ago,))
        
        return [{"id": r[0], "name": r[1], "last_active": str(r[2])} for r in rows]

if __name__ == "__main__":
    engine = ReflectionEngine()
    report = engine.analyze_thinking_patterns()
    print(json.dumps(report, indent=2))
