import os
import sys
import json
import time
from dotenv import load_dotenv
load_dotenv()

from nexus.db import get_adapter
from nexus.evolution.drift_engine import DriftEngine

def setup_test_nodes(db):
    print("--- Setting up Test Nodes ---")
    nodes = [
        ("test_drift_A", "We use SQLite for the database."),
        ("test_drift_B", "SQLite is the chosen database engine."), # Expected: REFINES A
        ("test_drift_C", "We should migrate to Postgres for scalability."), # Expected: Maybe unrelated or low score
        ("test_drift_D", "Postgres is better than SQLite."), # Expected: REFINES C or B
        ("test_drift_E", "The UI should be blue."), # Expected: Unrelated
    ]

    engine = DriftEngine()
    
    for node_id, statement in nodes:
        # Check if exists
        exists = db.fetch_one("SELECT id FROM graph.nodes WHERE id = %s", (node_id,))
        if not exists:
            data = {"statement": statement, "lifecycle": "forming", "vector_status": "indexed"}
            db.execute(
                "INSERT INTO graph.nodes (id, type, data, created_at) VALUES (%s, 'intent', %s, NOW())",
                (node_id, json.dumps(data))
            )
            print(f"Inserted {node_id}")
        else:
            # Force update vector_status to indexed
            data = {"statement": statement, "lifecycle": "forming", "vector_status": "indexed"}
            db.execute(
                "UPDATE graph.nodes SET data = %s WHERE id = %s",
                (json.dumps(data), node_id)
            )
            print(f"Node {node_id} already exists, forced vector_status=indexed")
            
        # Also ensure vector store has it
        if not engine.vector_store.exists(node_id):
            vector = engine.embedding_service.embed(statement)
            engine.vector_store.add(node_id, vector)
            print(f"Embedded and added {node_id} to VectorStore")
            
    engine.vector_store.save()
    
    return [n[0] for n in nodes]

def run_test():
    print("\n--- Starting Drift Engine Test ---")
    db = get_adapter()
    engine = DriftEngine()
    
    # 1. Setup
    node_ids = setup_test_nodes(db)
    
    # 2. Process Nodes
    print("\n--- Processing Nodes ---")
    for node_id in node_ids:
        print(f"Processing {node_id}...")
        engine.process_node(node_id)
        # Sleep slightly to ensure timestamps differ if we were using them
        time.sleep(0.1)
    
    # Manual save for test (since we insert < 10 items)
    engine.vector_store.save()

    # 3. Verify Candidates
    print("\n--- Verifying Candidates ---")
    rows = db.fetch_all("""
        SELECT source_intent_id, target_intent_id, suggested_edge_type, similarity_score 
        FROM graph.edge_candidates 
        WHERE source_intent_id LIKE %s
        ORDER BY similarity_score DESC
    """, ('test_drift_%',))
    
    if not rows:
        print("FAILURE: No candidates generated.")
    else:
        print(f"SUCCESS: Generated {len(rows)} candidates.")
        for r in rows:
            print(f"  {r[0]} -> {r[1]} [{r[2]}] (sim={r[3]:.4f})")

    # 4. Verify Vector Meta
    print("\n--- Verifying Vector Meta ---")
    meta_rows = db.fetch_all("SELECT node_id, embedding_model FROM graph.vector_meta WHERE node_id LIKE %s", ('test_drift_%',))
    print(f"Vector Meta count: {len(meta_rows)}")
    for r in meta_rows:
        print(f"  {r[0]}: {r[1]}")

    # 5. Idempotency Test
    print("\n--- Idempotency Check ---")
    before_count = len(rows)
    for node_id in node_ids:
        engine.process_node(node_id)
    
    after_rows = db.fetch_all("""
        SELECT source_intent_id, target_intent_id, suggested_edge_type 
        FROM graph.edge_candidates 
        WHERE source_intent_id LIKE %s
    """, ('test_drift_%',))
    if len(after_rows) == before_count:
        print("SUCCESS: Idempotency confirmed (no new duplicates).")
    else:
        print(f"FAILURE: Candidates count changed from {before_count} to {len(after_rows)}")

    # 6. Persistence Check (Simulated)
    # We can't easily kill the process memory here, but we can verify file existence
    if os.path.exists("data/vector_index.faiss"):
        print("\nSUCCESS: FAISS index file exists.")
    else:
        print("\nFAILURE: FAISS index file missing.")

if __name__ == "__main__":
    run_test()
