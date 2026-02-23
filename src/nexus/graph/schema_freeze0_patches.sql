-- =============================================================================
-- LEVEL-0 FREEZE PATCHES
-- Applied as part of the 4-blocker remediation.
-- Run this script ONCE against the production Postgres instance.
-- All statements are idempotent (IF NOT EXISTS / DO NOTHING patterns).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- D-01: Add stale-tracking columns to graph.vector_meta
--
-- DriftEngine._mark_vector_stale() writes to these columns when a node's
-- lifecycle transitions to 'superseded'. This prevents superseded nodes from
-- resurfacing in FAISS similarity searches as live drift candidates.
--
-- The actual FAISS index rebuild that physically removes stale entries must
-- be run separately via: scripts/maintenance/rebuild_vector_index.py
-- -----------------------------------------------------------------------------

ALTER TABLE graph.vector_meta
    ADD COLUMN IF NOT EXISTS is_stale      BOOLEAN   NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS stale_reason  TEXT,
    ADD COLUMN IF NOT EXISTS stale_at      TIMESTAMPTZ;

-- Index to allow rebuild_vector_index.py to efficiently query stale entries.
CREATE INDEX IF NOT EXISTS idx_vector_meta_stale
    ON graph.vector_meta (is_stale)
    WHERE is_stale = TRUE;

-- -----------------------------------------------------------------------------
-- P-01: Add traceback and worker_id columns to graph.l3_tasks (if missing)
--
-- PGWorker._record_failure() now writes error[:4000] and traceback[:8000].
-- These columns may already exist depending on schema version applied.
-- -----------------------------------------------------------------------------

ALTER TABLE graph.l3_tasks
    ADD COLUMN IF NOT EXISTS traceback  TEXT,
    ADD COLUMN IF NOT EXISTS worker_id  TEXT;

-- Index to allow the janitor query to efficiently find stalled tasks.
CREATE INDEX IF NOT EXISTS idx_l3_tasks_running_locked
    ON graph.l3_tasks (status, locked_at)
    WHERE status = 'running';

-- -----------------------------------------------------------------------------
-- FZ-02: Add vector_status column to graph.nodes
--
-- This is the visibility gate between graph insertion and vector indexing.
-- A node is invisible to DriftEngine._fetch_node() until this column is
-- explicitly flipped to 'indexed' by DriftEngine.process_node() after:
--   1. vector_store.add()     ✓
--   2. vector_store.save()    ✓
--   3. graph.vector_meta      ✓
--
-- Default is 'pending' — all existing nodes (pre-migration) are treated
-- as un-indexed until the next drift engine pass re-indexes them and flips
-- the status. This is conservative and correct: it prevents existing nodes
-- with stale or missing FAISS entries from generating ghost drift candidates.
--
-- Post-freeze optimization (non-blocking):
-- Add a second partial index on vector_status = 'indexed' for drift scan
-- queries once the 'pending' backlog is cleared.
-- -----------------------------------------------------------------------------

ALTER TABLE graph.nodes
    ADD COLUMN IF NOT EXISTS vector_status TEXT NOT NULL DEFAULT 'pending';

-- Partial index: allows efficient identification of nodes awaiting indexing.
-- Used by maintenance scripts and monitoring queries.
CREATE INDEX IF NOT EXISTS idx_nodes_vector_status_pending
    ON graph.nodes (vector_status)
    WHERE vector_status = 'pending';

-- =============================================================================
-- END OF FREEZE-0 PATCHES
-- =============================================================================
