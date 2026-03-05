from nexus.db import get_adapter
import json

def fix_missing_topics():
    db = get_adapter()
    print("[TopicFix] Scanning for bricks with missing Topic nodes...")
    
    with db.transaction() as cur:
        # 1. Find all distinct topic_ids referenced by bricks
        cur.execute("""
            SELECT DISTINCT data->>'topic_id', data->'metadata'->>'sync_topic_name'
            FROM graph.nodes
            WHERE type = 'brick'
        """)
        topic_refs = cur.fetchall()
        
        created_count = 0
        for topic_id, topic_name in topic_refs:
            if not topic_id:
                continue
            
            # 2. Check if topic node exists
            cur.execute("SELECT id FROM graph.nodes WHERE id = %s", (topic_id,))
            if not cur.fetchone():
                # 3. Create missing topic node
                display_name = topic_name or topic_id.replace("topic_", "")
                print(f"[TopicFix] Creating missing topic node: {topic_id} ({display_name})")
                
                topic_data = {
                    "name": display_name,
                    "canonical_name": display_name,
                    "metadata": {"auto_backfilled": True}
                }
                
                cur.execute(
                    "INSERT INTO graph.nodes (id, type, data, created_at) VALUES (%s, 'topic', %s, NOW())",
                    (topic_id, json.dumps(topic_data))
                )
                created_count += 1
                
    print(f"[TopicFix] Complete. Created {created_count} topic nodes.")

if __name__ == "__main__":
    fix_missing_topics()
