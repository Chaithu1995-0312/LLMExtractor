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

def test_pg_queue():
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "postgresql://nexus:nexus@localhost:5432/nexus"
    
    db = get_adapter()
    
    print("--- 1. Enqueue Test Task ---")
    # We use a task that doesn't do much or we use 'process_drift' with a dummy ID
    TaskQueue.enqueue("process_drift", {"node_id": "test-dummy-node"})
    
    print("--- 2. Verify in DB ---")
    # Use standard SQL because adapter might return different types
    row = db.fetch_one("SELECT id, task_type, status FROM graph.l3_tasks WHERE payload->>'node_id' = 'test-dummy-node' ORDER BY scheduled_at DESC LIMIT 1")
    if row:
        print(f"Task found: ID={row[0]}, Type={row[1]}, Status={row[2]}")
        task_id = row[0]
    else:
        print("Task NOT found in DB!")
        return

    print("--- 3. Run Worker Once ---")
    from services.cortex.worker import PGWorker
    worker = PGWorker(worker_id="test-worker")
    # This should pick up the task, mark it running, call DriftEngine (which will fail to find node but return), and mark completed.
    worker.run_once()

    print("--- 4. Final Status Check ---")
    row = db.fetch_one("SELECT status, error FROM graph.l3_tasks WHERE id = %s", (task_id,))
    print(f"Final Status: {row[0]}")
    if row[1]:
        print(f"Error: {row[1]}")

if __name__ == "__main__":
    test_pg_queue()
