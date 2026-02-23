import os
import sys
import time
import json
import uuid
import traceback
from datetime import datetime, timezone, timedelta
from typing import Optional

from nexus.db import get_adapter
from services.cortex.orchestration import TaskRegistry

# Import task logic to trigger registration
import services.cortex.tasks 

class PGWorker:
    def __init__(self, worker_id: Optional[str] = None):
        self.worker_id = worker_id or f"worker-{str(uuid.uuid4())[:8]}"
        self.db = get_adapter()
        # Visibility timeout: How long before a 'running' task with no lock is reclaimed
        self.visibility_timeout = timedelta(minutes=5)

    def run_once(self) -> bool:
        """
        Atomic task claim and execution.
        Couples task state and graph mutations in a single Postgres transaction.
        """
        task_id = None
        
        try:
            # 1. Open ONE transaction for the entire lifecycle
            with self.db.transaction() as cur:
                # A. Claim Task (Atomic with Lock)
                cur.execute("""
                    SELECT id, task_type, payload, attempts
                    FROM graph.l3_tasks
                    WHERE status = 'pending'
                      AND (scheduled_at <= NOW())
                      AND (attempts < max_retries)
                    ORDER BY scheduled_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                """)
                task = cur.fetchone()
                
                if not task:
                    return False

                task_id, task_type, payload_raw, attempts = task
                payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
                
                print(f"[{self.worker_id}] Claimed {task_type} ({task_id}) - Attempt {attempts + 1}")

                # B. Mark Running (Inside TX)
                cur.execute("""
                    UPDATE graph.l3_tasks 
                    SET status = 'running', 
                        locked_at = NOW(), 
                        worker_id = %s, 
                        attempts = attempts + 1 
                    WHERE id = %s
                """, (self.worker_id, task_id))

                try:
                    # C. Execute Handler (Participating in TX)
                    handler = TaskRegistry.get_handler(task_type)
                    if not handler:
                        raise ValueError(f"No handler for {task_type}")
                    
                    handler(payload, cursor=cur)

                    # D. Mark Completed (Inside TX)
                    cur.execute(
                        "UPDATE graph.l3_tasks SET status = 'completed', completed_at = NOW() WHERE id = %s",
                        (task_id,)
                    )
                    print(f"[{self.worker_id}] Success: {task_type} ({task_id})")
                
                except Exception as e:
                    # Reraise to trigger DB rollback of the entire 'with transaction' block
                    raise e

            return True

        except Exception as e:
            # This block catches failures that caused a rollback (including Claim/Mark Running)
            tb = traceback.format_exc()
            print(f"[{self.worker_id}] Task failed (rolled back): {e}")
            
            # Separate transaction to record failure / increment attempt if task was claimed
            if task_id:
                self._record_failure(task_id, str(e), tb)
            return True

    def _record_failure(self, task_id, error, tb):
        """Record task failure in a separate connection to avoid rollback."""
        try:
            db = get_adapter()
            # Note: We don't increment 'attempts' here because it was already 
            # incremented inside the transaction that rolled back.
            # Actually, because it rolled back, the DB state still has the OLD attempt count.
            # So we MUST increment it here in this separate 'failure record' transaction.
            db.execute("""
                UPDATE graph.l3_tasks 
                SET status = CASE WHEN attempts + 1 >= max_retries THEN 'failed' ELSE 'pending' END,
                    attempts = attempts + 1,
                    error = %s,
                    traceback = %s,
                    locked_at = NULL
                WHERE id = %s
            """, (error, tb, task_id))
        except Exception as e:
            print(f"Critical: Failed to record task failure for {task_id}: {e}")

    def _cleanup_stalled_tasks(self):
        """
        Janitor: Reset tasks that have been 'running' for too long.
        Since we use FOR UPDATE, a worker crash will release the lock immediately,
        making SKIP LOCKED skip it if another worker is looking.
        However, if the process hangs but keeps the connection open, 
        this janitor provides a visibility-timeout safety net.
        """
        cutoff = datetime.now(timezone.utc) - self.visibility_timeout
        self.db.execute("""
            UPDATE graph.l3_tasks 
            SET status = 'pending', locked_at = NULL 
            WHERE status = 'running' 
              AND locked_at < %s
        """, (cutoff,))

    def serve(self, interval: float = 1.0):
        print(f"[{self.worker_id}] Nexus Hardened L3 Worker Started (Postgres Queue)")
        try:
            while True:
                if not self.run_once():
                    self._cleanup_stalled_tasks()
                    time.sleep(interval)
        except KeyboardInterrupt:
            print(f"[{self.worker_id}] Worker shutting down...")

if __name__ == "__main__":
    worker = PGWorker()
    worker.serve()
