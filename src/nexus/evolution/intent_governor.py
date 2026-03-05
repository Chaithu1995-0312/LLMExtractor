import json
from datetime import datetime, timezone
from nexus.db import get_adapter
from nexus.graph.schema import IntentLifecycle

class IntentGovernor:
    """
    Automates Intent status transitions and updates metrics.
    Rule: LOOSE -> FORMING if brick count > 5.
    """
    def __init__(self, forming_threshold: int = 5):
        self.db = get_adapter()
        self.forming_threshold = forming_threshold

    def refresh_metrics(self):
        """
        Recalculates metrics for all active intents.
        """
        print("[IntentGovernor] Refreshing intent metrics and statuses...")
        
        with self.db.transaction() as cur:
            # 1. Update brick counts from graph.edges (derived_from edges)
            cur.execute("""
                INSERT INTO graph.intent_metrics (intent_id, brick_count, last_activity)
                SELECT e.source_id, COUNT(e.target_id), MAX(n.created_at)
                FROM graph.edges e
                JOIN graph.nodes n ON e.target_id = n.id
                WHERE e.edge_type = 'derived_from' AND n.type = 'brick'
                GROUP BY e.source_id
                ON CONFLICT (intent_id) DO UPDATE SET
                    brick_count = EXCLUDED.brick_count,
                    last_activity = EXCLUDED.last_activity;
            """)
            
            # 2. Apply status transitions
            # Fetch intents that are LOOSE but have brick_count >= threshold
            cur.execute("""
                SELECT n.id, n.data, m.brick_count
                FROM graph.nodes n
                JOIN graph.intent_metrics m ON n.id = m.intent_id
                WHERE n.type = 'intent' AND n.data->>'lifecycle' = 'loose'
                  AND m.brick_count >= %s
            """, (self.forming_threshold,))
            
            to_promote = cur.fetchall()
            
            for i_id, i_data_raw, count in to_promote:
                i_data = i_data_raw if isinstance(i_data_raw, dict) else json.loads(i_data_raw)
                print(f"[IntentGovernor] Promoting Intent {i_id} ('{i_data.get('name')}') to FORMING (bricks: {count})")
                
                i_data["lifecycle"] = IntentLifecycle.FORMING.value
                i_data["promoted_at"] = datetime.now(timezone.utc).isoformat()
                
                cur.execute(
                    "UPDATE graph.nodes SET data = %s WHERE id = %s",
                    (json.dumps(i_data), i_id)
                )

if __name__ == "__main__":
    governor = IntentGovernor()
    governor.refresh_metrics()
