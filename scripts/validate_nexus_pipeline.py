from nexus.db import get_adapter
import json

def verify_db():
    db = get_adapter()
    
    print("\n--- Validation: Intent Metrics ---")
    try:
        metrics = db.fetch_all("SELECT * FROM graph.intent_metrics LIMIT 5")
        print(f"Metrics Found: {len(metrics)}")
        for m in metrics:
            print(f"- {m}")
    except Exception as e:
        print(f"Error fetching metrics: {e}")

    print("\n--- Validation: Intent Nodes ---")
    try:
        intents = db.fetch_all("SELECT id, data FROM graph.nodes WHERE type='intent' LIMIT 5")
        print(f"Intents Found: {len(intents)}")
        for i_id, i_data in intents:
            name = (i_data if isinstance(i_data, dict) else json.loads(i_data)).get("name")
            print(f"- {i_id}: {name}")
    except Exception as e:
        print(f"Error fetching intents: {e}")

    print("\n--- Validation: Derived Edges ---")
    try:
        edges = db.fetch_all("SELECT COUNT(*) FROM graph.edges WHERE edge_type='derived_from'")
        print(f"Total Derived Edges: {edges[0][0]}")
    except Exception as e:
        print(f"Error fetching edges: {e}")

if __name__ == "__main__":
    verify_db()
