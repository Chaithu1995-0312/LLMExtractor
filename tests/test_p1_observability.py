
import os
import json
import time
from nexus.graph.manager import GraphManager
from nexus.graph.schema import AuditEventType, DecisionAction, ModelTier
from nexus.sync.db import SyncDatabase
from nexus.sync.compiler import NexusCompiler

def test_p1_audit_logging():
    print("\n--- Testing P1: Cost & Decision Observability ---")
    db_path = "test_nexus_p1.db"
    audit_path = "test_audit_trail.jsonl"
    
    if os.path.exists(db_path): os.remove(db_path)
    if os.path.exists(audit_path): os.remove(audit_path)
    
    # 1. Test GraphManager Audit
    print("Testing GraphManager audit...")
    manager = GraphManager(db_path)
    # Monkeypatch audit path for test
    def mock_log_path(self):
        return audit_path
    
    # Actually, GraphManager._log_audit_event uses a hardcoded relative path.
    # We'll just check if it writes to services/cortex/phase3_audit_trace.jsonl or similar if we can.
    # For this test, I'll temporarily override the method logic or just run it and check the default file.
    
    manager._log_audit_event(
        event_type=AuditEventType.NODE_KILLED,
        agent="test_actor",
        component="graph",
        decision_action=DecisionAction.REJECTED,
        reason="Test reason"
    )
    
    # 2. Test Compiler Audit
    print("Testing Compiler audit...")
    sync_db = SyncDatabase(db_path)
    run_id = "run_audit_test"
    sync_db.register_run(run_id, {"messages": [{"content": "msg"}]})
    sync_db.create_topic("topic_audit", "Topic Audit", {"scope_description": "test"})
    
    class MockLLM:
        def generate(self, system, user):
            return json.dumps({"extracted_pointers": []})
            
    compiler = NexusCompiler(sync_db, MockLLM())
    compiler.compile_run(run_id, "topic_audit")
    
    print("Audit events should be logged. Checking services/cortex/phase3_audit_trace.jsonl...")
    
    # The actual path used in manager.py is relative to graph_dir
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    actual_audit_path = os.path.join("services", "cortex", "phase3_audit_trace.jsonl")
    
    if os.path.exists(actual_audit_path):
        with open(actual_audit_path, "r") as f:
            lines = f.readlines()
            last_line = json.loads(lines[-1])
            print(f"Latest Event: {last_line['event']}")
            if "cost" in last_line:
                print(f"Cost Info: {last_line['cost']}")
            if "decision" in last_line:
                print(f"Decision: {last_line['decision']}")
            
            if last_line['event'] == AuditEventType.RUN_COMPILE_COMPLETED:
                print("✅ SUCCESS: Compiler emitted completed event.")
    else:
        print(f"❌ FAILED: Audit file not found at {actual_audit_path}")

if __name__ == "__main__":
    test_p1_audit_logging()
