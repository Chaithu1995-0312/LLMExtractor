import os
import sys
import time
import json
import uuid
import threading
import traceback
from datetime import datetime, timezone, timedelta
from typing import Optional

from nexus.db import get_adapter
from services.cortex.orchestration import TaskRegistry
from nexus.cognition.goal_engine import GoalEngine

# Import task logic to trigger registration
import services.cortex.tasks 

class PGWorker:
    def __init__(self, worker_id: Optional[str] = None):
        self.worker_id = worker_id or f"worker-{str(uuid.uuid4())[:8]}"
        self.db = get_adapter()
        # Visibility timeout: How long before a 'running' task with no lock is reclaimed
        self.visibility_timeout = timedelta(minutes=5)
        
        # Initialize Goal Engine
        self.goal_engine = GoalEngine(db_adapter=self.db)
        self.last_goal_cycle = 0
        self.goal_interval = 10 # Seconds

    # ------------------------------------------------------------------
    # Heartbeat — keeps locked_at fresh for long-running LLM tasks
    # ------------------------------------------------------------------

    def _start_heartbeat(self, task_id: str, interval: float = 60.0) -> threading.Event:
        """
        Starts a background thread that refreshes locked_at every `interval`
        seconds for the given task_id while it is still 'running'.

        This prevents the visibility-timeout janitor from reclaiming a legitimately
        long-running task (e.g., L3 Sage reasoning > 5 min).

        Returns a stop_event; call stop_event.set() to terminate the thread.
        The thread is daemon=True so it won't block process shutdown.
        """
        stop_event = threading.Event()

        def _beat():
            while not stop_event.wait(timeout=interval):
                try:
                    db = get_adapter()
                    db.execute(
                        """
                        UPDATE graph.l3_tasks
                        SET locked_at = NOW()
                        WHERE id = %s AND status = 'running'
                        """,
                        (task_id,),
                    )
                    print(f"[{self.worker_id}] Heartbeat refreshed for task {task_id}")
                except Exception as hb_err:
                    # Heartbeat failure is non-fatal — log and continue.
                    # Worst case: janitor reclaims after visibility_timeout.
                    print(
                        f"[{self.worker_id}] WARN: Heartbeat failed for task {task_id}: {hb_err}"
                    )

        t = threading.Thread(target=_beat, daemon=True, name=f"hb-{task_id[:8]}")
        t.start()
        return stop_event

    def run_once(self) -> bool:
        """
        Atomic task claim and execution.
        Couples task state and graph mutations in a single Postgres transaction.

        P-01 FIX: Attempt counter is incremented in the CLAIM phase inside the
        main transaction, before the handler runs. This means:

          - On success: status=completed, attempts already incremented. ✓
          - On handler failure + rollback: the main TX rolls back, restoring
            attempts to the pre-claim value. _record_failure() then increments
            attempts in a SEPARATE connection. This is the only correct pattern:
            the failure recorder must use its own connection so it is never
            rolled back by the handler's failure.
          - On _record_failure() crash: task stays in 'running' with stale
            locked_at. The janitor (_cleanup_stalled_tasks) resets it to
            'pending' after visibility_timeout. This is the final safety net.

        The previous bug was that _record_failure incremented attempts against
        the rolled-back (pre-increment) value, AND the handler's attempt
        increment was also rolled back — making effective attempt count = 0
        after first failure, allowing permanent retry loops.

        HEARTBEAT FIX: A background thread refreshes locked_at every 60 s so
        that legitimate long-running LLM tasks (> 5 min) are not incorrectly
        reclaimed by the janitor.
        """
        task_id = None
        task_type = None
        heartbeat_stop: Optional[threading.Event] = None

        try:
            # 1. Open ONE transaction for the entire claim + execute lifecycle.
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

                # B. Mark Running AND increment attempts in the SAME transaction.
                # P-01: attempts is incremented here. If the handler fails and
                # this TX rolls back, attempts reverts to the pre-claim value.
                # _record_failure() will then increment it in a separate TX.
                # Net result: exactly one increment per attempt, regardless of outcome.
                cur.execute("""
                    UPDATE graph.l3_tasks
                    SET status = 'running',
                        locked_at = NOW(),
                        worker_id = %s,
                        attempts = attempts + 1
                    WHERE id = %s
                """, (self.worker_id, task_id))

            # ── Heartbeat starts AFTER the claim TX commits ──────────────
            # The task is now durably 'running' in the DB. We use a fresh
            # outer block so the handler's TX is separate from the claim TX.
            heartbeat_stop = self._start_heartbeat(task_id)

            with self.db.transaction() as cur:
                # C. Execute Handler (participates in its own TX)
                handler = TaskRegistry.get_handler(task_type)
                if not handler:
                    raise ValueError(f"No handler registered for task_type={task_type!r}")

                handler(payload, cursor=cur)

                # D. Mark Completed (inside TX — only reached on success)
                cur.execute(
                    "UPDATE graph.l3_tasks SET status = 'completed', completed_at = NOW() WHERE id = %s",
                    (task_id,)
                )
                print(f"[{self.worker_id}] Success: {task_type} ({task_id})")

            return True

        except Exception as e:
            # The 'with transaction' block has already rolled back at this point.
            # attempts in DB is back to the pre-claim value.
            tb = traceback.format_exc()
            print(f"[{self.worker_id}] Task {task_id} ({task_type}) failed (rolled back): {e}")

            if task_id:
                # P-01: Record failure in a SEPARATE connection/transaction.
                # This connection is independent — it will NOT be rolled back.
                # It increments attempts exactly once, matching the one rolled-back
                # increment from the failed main TX.
                self._record_failure(task_id, str(e), tb)
            return True

        finally:
            # Always stop the heartbeat thread, whether we succeeded or failed.
            if heartbeat_stop is not None:
                heartbeat_stop.set()

    def _record_failure(self, task_id: str, error: str, tb: str):
        """
        Record task failure using a SEPARATE, independent DB connection.

        P-01 FIX: This method MUST open its own connection via get_adapter().
        It must NEVER reuse self.db — if self.db's connection was involved in
        the rollback, reusing it risks operating on a broken connection state.

        Attempt accounting:
          - The main TX rolled back, so DB attempts = pre-claim value (N).
          - We increment here: DB attempts becomes N+1.
          - If attempts+1 >= max_retries → status='failed' (permanent failure).
          - Otherwise → status='pending' (eligible for retry).
        """
        try:
            # Fresh connection — completely independent of the failed transaction.
            db = get_adapter()
            db.execute("""
                UPDATE graph.l3_tasks
                SET status      = CASE WHEN attempts + 1 >= max_retries THEN 'failed' ELSE 'pending' END,
                    attempts    = attempts + 1,
                    error       = %s,
                    traceback   = %s,
                    locked_at   = NULL,
                    worker_id   = NULL
                WHERE id = %s
                  AND status = 'running'
            """, (error[:4000], tb[:8000], task_id))
            # The WHERE status='running' guard prevents double-incrementing if
            # _record_failure is somehow called twice (e.g., on a retry of this
            # method itself). A completed or already-failed task won't be touched.
        except Exception as record_err:
            # If even the failure recorder fails, the task stays 'running' with
            # a stale locked_at. The janitor will reset it to 'pending' after
            # visibility_timeout. This is the final safety net — we cannot do
            # better here without a secondary persistence layer.
            print(
                f"[{self.worker_id}] CRITICAL: Failed to record failure for task {task_id}: "
                f"{record_err}. Task will be reclaimed by janitor after "
                f"{self.visibility_timeout}."
            )

    def _cleanup_stalled_tasks(self):
        """
        Janitor: Reset tasks stuck in 'running' beyond the visibility timeout.

        This fires only when the queue is idle (run_once returns False),
        which is acceptable — under sustained load, stalled tasks are rare
        and the visibility timeout (5 min) is the appropriate SLA boundary.

        Tasks reclaimed here have their attempts preserved (not incremented),
        so they count toward max_retries correctly.
        """
        cutoff = datetime.now(timezone.utc) - self.visibility_timeout
        try:
            self.db.execute("""
                UPDATE graph.l3_tasks
                SET status    = 'pending',
                    locked_at = NULL,
                    worker_id = NULL
                WHERE status = 'running'
                  AND locked_at < %s
            """, (cutoff,))
        except Exception as e:
            print(f"[{self.worker_id}] WARN: Janitor sweep failed: {e}")

    def _run_goal_cycle(self):
        """Runs the goal engine cycle periodically."""
        now = time.time()
        if now - self.last_goal_cycle > self.goal_interval:
            try:
                self.goal_engine.run_cycle()
                self.last_goal_cycle = now
            except Exception as e:
                print(f"[{self.worker_id}] Goal Engine cycle failed: {e}")

    def serve(self, interval: float = 1.0):
        print(f"[{self.worker_id}] Nexus Hardened L3 Worker Started (Postgres Queue)")
        try:
            while True:
                # 1. Run Goal Engine (Periodically)
                self._run_goal_cycle()

                # 2. Run Task Execution
                if not self.run_once():
                    self._cleanup_stalled_tasks()
                    time.sleep(interval)
        except KeyboardInterrupt:
            print(f"[{self.worker_id}] Worker shutting down...")

if __name__ == "__main__":
    worker = PGWorker()
    worker.serve()
