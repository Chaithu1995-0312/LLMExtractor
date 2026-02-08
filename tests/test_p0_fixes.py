
import os
import sqlite3
import json
from nexus.graph.manager import GraphManager
from nexus.graph.schema import EdgeType, Intent, IntentLifecycle, IntentType, Edge
from nexus.sync.db import SyncDatabase
from nexus.sync.compiler import NexusCompiler

def test_p0_cycle_prevention():
    print("\n--- Testing P0.1: Real-Time Cycle Prevention ---")
    db_path = "test_nexus_p0.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    manager = GraphManager(db_path)
    
    # Create two intents
    i1 = Intent(id="intent_1", statement="Statement 1", lifecycle=IntentLifecycle.FROZEN, intent_type=IntentType.FACT)
    i2 = Intent(id="intent_2", statement="Statement 2", lifecycle=IntentLifecycle.FROZEN, intent_type=IntentType.FACT)
    manager.add_intent(i1)
    manager.add_intent(i2)
    
    # 1. Add valid edge: i1 overrides i2
    print("Adding edge: intent_1 -> intent_2 (OVERRIDES)")
    manager.register_edge(("intent", "intent_1"), ("intent", "intent_2"), EdgeType.OVERRIDES)
    
    # 2. Add circular edge: i2 overrides i1 (Should fail)
    print("Attempting circular edge: intent_2 -> intent_1 (OVERRIDES)")
    try:
        manager.register_edge(("intent", "intent_2"), ("intent", "intent_1"), EdgeType.OVERRIDES)
        print("❌ FAILED: Cycle was NOT detected.")
    except ValueError as e:
        print(f"✅ SUCCESS: Cycle detected: {e}")

def test_p0_incremental_boundary():
    print("\n--- Testing P0.2: Incremental Boundary Guard ---")
    db_path = "test_nexus_p0.db"
    sync_db = SyncDatabase(db_path)
    
    run_id = "test_run_incremental"
    raw_content = {
        "messages": [
            {"role": "user", "content": "Message 0"},
            {"role": "user", "content": "Message 1"},
            {"role": "user", "content": "Message 2"}
        ]
    }
    
    # Register run
    sync_db.register_run(run_id, raw_content)
    
    # Mock LLM Client
    class MockLLM:
        def __init__(self):
            self.calls = 0
            self.last_content = None
        def generate(self, system, user):
            self.calls += 1
            self.last_content = user
            return json.dumps({"extracted_pointers": []})

    mock_llm = MockLLM()
    compiler = NexusCompiler(sync_db, mock_llm)
    
    # Create a topic
    topic_id = "test_topic"
    sync_db.create_topic(topic_id, "Test Topic", {"scope_description": "test"})
    
    # 1. First compile: Should see all 3 messages
    print("First compile...")
    compiler.compile_run(run_id, topic_id)
    print(f"LLM calls: {mock_llm.calls}")
    # Verify boundary updated
    run = sync_db.get_run(run_id)
    print(f"Last processed index: {run['last_processed_index']}")
    
    # 2. Second compile: Should see 0 new messages
    print("Second compile (no new messages)...")
    compiler.compile_run(run_id, topic_id)
    print(f"LLM calls: {mock_llm.calls} (Expected: 1)")
    
    # 3. Add more messages and re-register (update raw_content)
    print("Adding new messages...")
    raw_content["messages"].append({"role": "user", "content": "Message 3"})
    # Manual update for test
    conn = sync_db._get_conn()
    conn.execute("UPDATE source_runs SET raw_content = ? WHERE id = ?", (json.dumps(raw_content), run_id))
    conn.commit()
    conn.close()
    
    # 4. Third compile: Should see only 1 new message
    print("Third compile (1 new message)...")
    compiler.compile_run(run_id, topic_id)
    print(f"LLM calls: {mock_llm.calls} (Expected: 2)")
    if "Message 3" in mock_llm.last_content and "Message 0" not in mock_llm.last_content:
        print("✅ SUCCESS: Incremental filtering worked.")
    else:
        print("❌ FAILED: Incremental filtering failed.")

if __name__ == "__main__":
    test_p0_cycle_prevention()
    test_p0_incremental_boundary()
    # Clean up
    if os.path.exists("test_nexus_p0.db"):
        os.remove("test_nexus_p0.db")
