"""
compaction_worker.py — Scheduled background maintenance worker
==============================================================
Runs three independent jobs on a fixed schedule:

  1. metrics_refresh   (every 30 min)
     - Calls REFRESH MATERIALIZED VIEW CONCURRENTLY on all evolution
       and cognition materialized views so dashboards always have
       up-to-date data without hammering the OLTP tables.

  2. vector_prune      (every 6 hours)
     - Deletes embeddings whose parent nodes are in lifecycle
       KILLED or SUPERSEDED and whose deletion_protected flag is
       unset.  Reclaims pgvector index space and keeps recall
       latency low.

  3. stalled_task_sweep (every 10 min)
     - Safety-net janitor: resets any l3_tasks rows stuck in
       'running' beyond the visibility timeout (identical to the
       inline janitor in PGWorker, but runs even when no worker
       process is active).

Usage
-----
  python -m services.cortex.compaction_worker          # runs forever
  python -m services.cortex.compaction_worker --once   # run all jobs once and exit

Design decisions
----------------
- Each job opens its own short-lived DB connection via get_adapter()
  so a failure in one job never poisons another job's connection.
- All jobs catch and log exceptions without crashing the loop, so a
  temporary DB hiccup does not take down the worker.
- Uses threading.Event for the sleep so SIGTERM / KeyboardInterrupt
  can interrupt the sleep instantly instead of waiting up to 30 min.
"""

import argparse
import logging
import threading
import time
from datetime import datetime, timezone, timedelta

from nexus.db import get_adapter

logger = logging.getLogger("compaction_worker")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

# ── Configurable intervals ────────────────────────────────────
METRICS_REFRESH_INTERVAL_SEC  = 30 * 60   # 30 minutes
VECTOR_PRUNE_INTERVAL_SEC     = 6 * 60 * 60  # 6 hours
STALLED_SWEEP_INTERVAL_SEC    = 10 * 60   # 10 minutes
VISIBILITY_TIMEOUT_MIN        = 5          # must match PGWorker.visibility_timeout

# ── Materialized views to refresh ─────────────────────────────
MATERIALIZED_VIEWS = [
    "graph.mv_concept_drift_summary",
    "graph.mv_node_lifecycle_counts",
    "graph.mv_promotion_candidates",
    "graph.mv_weekly_evolution_stats",
]


# ─── Job 1: Metrics Refresh ───────────────────────────────────

def job_metrics_refresh() -> None:
    """
    Refresh all evolution/cognition materialized views CONCURRENTLY.

    CONCURRENTLY avoids locking reads — readers continue to see the
    old version while the refresh runs, at the cost of needing at
    least one unique index on each view.
    """
    db = get_adapter()
    refreshed, skipped = 0, 0
    for view in MATERIALIZED_VIEWS:
        try:
            db.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}")
            logger.info("Refreshed %s", view)
            refreshed += 1
        except Exception as e:
            # View may not exist yet (schema not applied) — log and skip.
            logger.warning("Could not refresh %s: %s", view, e)
            skipped += 1
    logger.info(
        "metrics_refresh complete: %d refreshed, %d skipped", refreshed, skipped
    )


# ─── Job 2: Vector Prune ──────────────────────────────────────

def job_vector_prune() -> None:
    """
    Remove embeddings for dead nodes (KILLED / SUPERSEDED) that are
    not marked deletion_protected.

    Two-phase:
      1. Collect node_ids of dead nodes (read-only, cheap).
      2. DELETE from vector.embeddings in batches of 500 to avoid
         large single-transaction lock contention.
    """
    db = get_adapter()

    # Phase 1: collect candidates
    try:
        rows = db.fetchall(
            """
            SELECT n.node_id
            FROM   graph.nodes n
            LEFT   JOIN graph.node_flags f ON f.node_id = n.node_id
            WHERE  n.lifecycle IN ('KILLED', 'SUPERSEDED')
              AND  (f.deletion_protected IS NULL OR f.deletion_protected = FALSE)
            """,
        )
    except Exception as e:
        logger.error("vector_prune: failed to fetch dead nodes: %s", e)
        return

    if not rows:
        logger.info("vector_prune: no dead nodes found, nothing to prune")
        return

    dead_ids = [r[0] for r in rows]
    total_deleted = 0
    batch_size = 500

    for i in range(0, len(dead_ids), batch_size):
        batch = dead_ids[i : i + batch_size]
        try:
            db.execute(
                """
                DELETE FROM vector.embeddings
                WHERE node_id = ANY(%s)
                """,
                (batch,),
            )
            total_deleted += len(batch)
            logger.debug("vector_prune: pruned batch %d/%d", i + len(batch), len(dead_ids))
        except Exception as e:
            logger.error("vector_prune: batch delete failed (offset %d): %s", i, e)

    logger.info(
        "vector_prune complete: %d candidate nodes, %d embeddings pruned",
        len(dead_ids), total_deleted,
    )


# ─── Job 3: Stalled Task Sweep ────────────────────────────────

def job_stalled_sweep() -> None:
    """
    Reset l3_tasks rows stuck in 'running' beyond visibility_timeout.

    This is the global safety net — it fires even when PGWorker is
    not running (e.g., after a crash or deploy with no active worker
    processes).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=VISIBILITY_TIMEOUT_MIN)
    try:
        db = get_adapter()
        db.execute(
            """
            UPDATE graph.l3_tasks
            SET    status    = 'pending',
                   locked_at = NULL,
                   worker_id = NULL
            WHERE  status = 'running'
              AND  locked_at < %s
            """,
            (cutoff,),
        )
        logger.info("stalled_sweep complete (cutoff=%s)", cutoff.isoformat())
    except Exception as e:
        logger.error("stalled_sweep failed: %s", e)


# ─── Scheduler ────────────────────────────────────────────────

class _Job:
    """Tracks next-run time for a periodic job."""

    def __init__(self, name: str, fn, interval_sec: int):
        self.name = name
        self.fn = fn
        self.interval_sec = interval_sec
        # Run all jobs immediately on first tick
        self.next_run: float = 0.0

    def is_due(self) -> bool:
        return time.monotonic() >= self.next_run

    def run(self) -> None:
        logger.info("Starting job: %s", self.name)
        try:
            self.fn()
        except Exception as e:
            logger.error("Job %s raised uncaught exception: %s", self.name, e)
        finally:
            self.next_run = time.monotonic() + self.interval_sec
            logger.info(
                "Job %s done — next run in %.0f s",
                self.name, self.interval_sec,
            )


def run_forever(stop_event: threading.Event | None = None) -> None:
    """
    Main loop.  Polls every 60 s and dispatches jobs when they are due.
    Uses stop_event so tests and signal handlers can break the loop.
    """
    if stop_event is None:
        stop_event = threading.Event()

    jobs = [
        _Job("metrics_refresh",   job_metrics_refresh, METRICS_REFRESH_INTERVAL_SEC),
        _Job("vector_prune",      job_vector_prune,    VECTOR_PRUNE_INTERVAL_SEC),
        _Job("stalled_sweep",     job_stalled_sweep,   STALLED_SWEEP_INTERVAL_SEC),
    ]

    logger.info(
        "CompactionWorker started — metrics every %dm, prune every %dh, sweep every %dm",
        METRICS_REFRESH_INTERVAL_SEC // 60,
        VECTOR_PRUNE_INTERVAL_SEC // 3600,
        STALLED_SWEEP_INTERVAL_SEC // 60,
    )

    while not stop_event.is_set():
        for job in jobs:
            if job.is_due():
                job.run()
        # Sleep 60 s but wake immediately if stop_event is set
        stop_event.wait(timeout=60)

    logger.info("CompactionWorker stopping — stop event received")


def run_once() -> None:
    """Run all jobs exactly once in sequence (used for --once flag / tests)."""
    logger.info("Running all compaction jobs once…")
    for fn, name in [
        (job_metrics_refresh, "metrics_refresh"),
        (job_vector_prune,    "vector_prune"),
        (job_stalled_sweep,   "stalled_sweep"),
    ]:
        logger.info("Running: %s", name)
        try:
            fn()
        except Exception as e:
            logger.error("Job %s failed: %s", name, e)
    logger.info("All compaction jobs complete")


# ─── Entrypoint ───────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexus compaction/maintenance worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run all jobs once and exit (useful for cron / CI)",
    )
    args = parser.parse_args()

    try:
        if args.once:
            run_once()
        else:
            run_forever()
    except KeyboardInterrupt:
        logger.info("CompactionWorker interrupted — exiting")
