import json
import uuid
from typing import Dict, List
from nexus.db import get_adapter
from nexus.graph.schema import Intent, IntentLifecycle, IntentType

def migrate_to_intents():
    """
    Safe Option A Migration:
    1. Group bricks by their existing sync_topic_id.
    2. Create an Intent object for each non-empty topic cluster.
    3. Update bricks to reference both Topic and Intent.
    """
    adapter = get_adapter()
    
    print("[Migration] Starting Option A Migration: Topics -> Intents separation...")
    
    with adapter.transaction() as cur:
        # 1. Fetch all bricks and their current topic info
        cur.execute("""
            SELECT id, data FROM graph.nodes WHERE type = 'brick'
        """)
        bricks = cur.fetchall()
        
        topic_clusters = {}
        for b_id, b_data_raw in bricks:
            b_data = b_data_raw if isinstance(b_data_raw, dict) else json.loads(b_data_raw)
            topic_id = b_data.get("metadata", {}).get("sync_topic_id")
            if topic_id:
                if topic_id not in topic_clusters:
                    topic_clusters[topic_id] = []
                topic_clusters[topic_id].append((b_id, b_data))

        # 2. For each cluster, create an Intent
        for topic_id, brick_list in topic_clusters.items():
            topic_name = brick_list[0][1].get("metadata", {}).get("sync_topic_name") or topic_id
            
            intent_id = str(uuid.uuid4())
            intent_name = f"Project: {topic_name}"
            
            print(f"[Migration] Creating Intent: {intent_name} (id: {intent_id}) for {len(brick_list)} bricks")
            
            # Insert Intent Node
            intent_data = {
                "name": intent_name,
                "summary": f"Automatically inferred project for topic {topic_name}",
                "lifecycle": IntentLifecycle.FORMING.value,
                "intent_type": IntentType.GOAL.value,
                "metadata": {"source_topic_id": topic_id}
            }
            
            cur.execute(
                "INSERT INTO graph.nodes (id, type, data, created_at) VALUES (%s, 'intent', %s, NOW())",
                (intent_id, json.dumps(intent_data))
            )
            
            # Insert Intent Metrics
            cur.execute(
                "INSERT INTO graph.intent_metrics (intent_id, brick_count, momentum_score) VALUES (%s, %s, %s)",
                (intent_id, len(brick_list), 1.0)
            )
            
            # 3. Update Bricks to link to this Intent and ensure Topic dimension is preserved
            for b_id, b_data in brick_list:
                b_data["intent_id"] = intent_id
                # Ensure topic_id is at top level for easy access in v1 pipeline
                b_data["topic_id"] = f"topic_{topic_id}"
                
                cur.execute(
                    "UPDATE graph.nodes SET data = %s WHERE id = %s",
                    (json.dumps(b_data), b_id)
                )
                
                # Create Edge: Brick -> Intent (derived_from / member_of)
                cur.execute(
                    "INSERT INTO graph.edges (source_id, target_id, edge_type, created_at) VALUES (%s, %s, 'derived_from', NOW())",
                    (intent_id, b_id)
                )

    print("[Migration] Option A Migration complete.")

if __name__ == "__main__":
    migrate_to_intents()
