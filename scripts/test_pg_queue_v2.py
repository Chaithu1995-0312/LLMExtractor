import os
import sys

# Setup paths
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(repo_root)
sys.path.append(os.path.join(repo_root, "src"))

import json
import time
from services.cortex.orchestration import TaskQueue
from nexus.db import get_adapter

def test_hardened_pg_queue():
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "postgresql://nexus:nexus@localhost:5432/nexus"
    
    db = get_adapter()
    
    print("--- 1. Enqueue Test Task ---")
    TaskQueue.enqueue("process_drift", {"node_id": "test-atomic-node"})
    
    print("--- 2. Verify in DB ---")
    row = db.fetch_one("SELECT id, task_type, status FROM graph.l3_tasks WHERE payload->>'node_id' = 'test-atomic-node' ORDER BY scheduled_at DESC LIMIT 1")
    if row:
        print(f"Task found: ID={row[0]}, Type={row[1]}, Status={row[2]}")
        task_id = row[0]
    else:
        print("Task NOT found in DB!")
        return

    print("--- 3. Run Hardened Worker Once ---")
    from services.cortex.worker import PGWorker
    worker = PGWorker(worker_id="hardened-worker")
    
    # This will now:
    # 1. Start TX
    # 2. Claim + Mark Running
    # 3. Start Heartbeat Thread
    # 4. Run DriftEngine (participating in TX)
    # 5. Mark Completed
    # 6. Commit
    worker.run_once()

    print("--- 4. Final Status Check ---")
    row = db.fetch_one("SELECT status, last_heartbeat, error FROM graph.l3_tasks WHERE id = %s", (task_id,))
    print(f"Final Status: {row[0]}")
    print(f"Heartbeat Recorded: {row[1] is not None}")
    if row[2]:
        print(f"Error: {row[2]}")

if __name__ == "__main__":
    test_hardened_pg_queue()
