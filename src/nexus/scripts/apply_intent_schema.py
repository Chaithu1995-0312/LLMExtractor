from nexus.db import get_adapter

def apply_intent_schema():
    adapter = get_adapter()
    
    with adapter.transaction() as cur:
        # 1. Create intent_metrics table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS graph.intent_metrics (
                intent_id TEXT PRIMARY KEY REFERENCES graph.nodes(id) ON DELETE CASCADE,
                brick_count INTEGER DEFAULT 0,
                momentum_score FLOAT DEFAULT 0.0,
                last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        # 2. Add intent_id and topic_id columns to graph.nodes if they don't exist as explicit columns
        # Note: Nexus uses JSONB for 'data' primarily, but for indexing performance, 
        # we might want them as generated columns or just rely on JSONB.
        # For now, let's ensure we have a way to query them efficiently.
        
        # Add GIN index for faster JSONB searching if not exists
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nodes_data_jsonb ON graph.nodes USING GIN (data);")
        
        # Ensure 'topic' type nodes are distinct from bricks
        # Existing bricks might have topic_id in metadata.
        
        print("[Schema] Intent and Metrics schema applied.")

if __name__ == "__main__":
    apply_intent_schema()
